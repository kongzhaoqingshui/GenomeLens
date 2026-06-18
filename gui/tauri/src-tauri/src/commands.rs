use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::fs::File;
use std::io::{BufReader, Read, Seek, SeekFrom};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use tauri::{AppHandle, Emitter};

#[derive(Debug, Serialize)]
pub struct CommandVersion {
    ok: bool,
    command: String,
    version: String,
    error: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct VersionInfo {
    platform: CommandVersion,
    engine: CommandVersion,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RunAnalysisInput {
    request_path: String,
    outdir: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RunHandle {
    run_id: String,
    request_path: String,
    outdir: String,
    status: String,
    started_at: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ReadSummaryInput {
    outdir: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ReadRunLogInput {
    outdir: String,
    tail_lines: Option<usize>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RunLogSnapshot {
    outdir: String,
    log_path: String,
    text: String,
    lines: Vec<String>,
    truncated: bool,
    updated_at: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct OpenPathInput {
    path: String,
}

#[derive(Debug, Serialize, Clone)]
pub struct AnalysisStdoutEventPayload {
    line: String,
}

#[derive(Debug, Serialize, Clone)]
pub struct AnalysisStateEventPayload {
    state: String,
    progress: f64,
}

#[derive(Debug, Serialize, Clone)]
pub struct AnalysisFinishedEventPayload {
    status: String,
    summary: Option<Value>,
}

#[derive(Debug, Serialize, Clone)]
pub struct AnalysisErrorEventPayload {
    message: String,
    code: Option<String>,
    details: Option<Value>,
}

#[tauri::command]
pub fn get_version() -> VersionInfo {
    VersionInfo {
        platform: command_version("genomelens", &["--version"]),
        engine: command_version("jcvi-genomelens", &["probe"]),
    }
}

#[tauri::command]
pub fn get_template(method: String) -> Result<Value, String> {
    run_json_command("genomelens", &["analyze", "template", &method])
}

#[tauri::command]
pub fn get_analysis_schema() -> Result<Value, String> {
    run_json_command("genomelens", &["analyze", "schema"])
}

#[tauri::command]
pub fn check_environment() -> Result<Value, String> {
    run_json_command("genomelens", &["check", "-j"])
}

#[tauri::command]
pub fn read_summary(input: ReadSummaryInput) -> Result<Value, String> {
    let summary_path = Path::new(&input.outdir).join("report").join("run_summary.json");
    read_json_file(&summary_path)
}

#[tauri::command]
pub fn read_run_log(input: ReadRunLogInput) -> Result<RunLogSnapshot, String> {
    let log_path = Path::new(&input.outdir).join("logs").join("run.log");
    if !log_path.is_file() {
        return Ok(RunLogSnapshot {
            outdir: input.outdir,
            log_path: log_path.to_string_lossy().to_string(),
            text: String::new(),
            lines: Vec::new(),
            truncated: false,
            updated_at: None,
        });
    }

    let contents = std::fs::read_to_string(&log_path)
        .map_err(|error| format!("read run log {}: {error}", log_path.display()))?;

    let all_lines = contents
        .lines()
        .map(|line| line.to_string())
        .collect::<Vec<_>>();
    let tail_count = input.tail_lines.unwrap_or(all_lines.len());
    let start = all_lines.len().saturating_sub(tail_count);
    let lines = all_lines[start..].to_vec();
    let truncated = start > 0;
    let text = if lines.is_empty() {
        String::new()
    } else {
        format!("{}\n", lines.join("\n"))
    };

    let updated_at = std::fs::metadata(&log_path)
        .ok()
        .and_then(|metadata| metadata.modified().ok())
        .map(system_time_to_iso_like);

    Ok(RunLogSnapshot {
        outdir: input.outdir,
        log_path: log_path.to_string_lossy().to_string(),
        text,
        lines,
        truncated,
        updated_at,
    })
}

#[tauri::command]
pub fn open_path(input: OpenPathInput) -> Result<(), String> {
    let target = PathBuf::from(&input.path);
    if !target.exists() {
        return Err(format!("path does not exist: {}", target.display()));
    }

    #[cfg(target_os = "windows")]
    let mut command = {
        let mut command = Command::new("explorer.exe");
        command.arg(target.as_os_str());
        command
    };

    #[cfg(target_os = "macos")]
    let mut command = {
        let mut command = Command::new("open");
        command.arg(target.as_os_str());
        command
    };

    #[cfg(all(not(target_os = "windows"), not(target_os = "macos")))]
    let mut command = {
        let mut command = Command::new("xdg-open");
        command.arg(target.as_os_str());
        command
    };

    command
        .spawn()
        .map_err(|error| format!("open path {}: {error}", target.display()))?;

    Ok(())
}

#[tauri::command]
pub fn run_analysis(app: AppHandle, input: RunAnalysisInput) -> Result<RunHandle, String> {
    let run_id = format!("run-{}", unix_timestamp_millis());
    let started_at = system_time_to_iso_like(SystemTime::now());
    let request_path = input.request_path.clone();
    let outdir = input.outdir.clone();

    let mut child = Command::new("genomelens")
        .args(["analyze", "run", &request_path])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|error| {
            let message = format!("genomelens analyze run {}: {}", request_path, error);
            let _ = app.emit(
                "analysis:error",
                AnalysisErrorEventPayload {
                    message: message.clone(),
                    code: Some("spawn_failed".to_string()),
                    details: None,
                },
            );
            message
        })?;

    let app_handle = app.clone();
    let thread_run_id = run_id.clone();
    let thread_outdir = outdir.clone();
    let thread_started_at = started_at.clone();

    thread::spawn(move || {
        let run_log_path = Path::new(&thread_outdir).join("logs").join("run.log");
        let mut offset = 0_u64;
        let mut partial = String::new();
        let mut last_state: Option<String> = None;

        let exit_status = loop {
            emit_new_log_lines(
                &app_handle,
                &run_log_path,
                &mut offset,
                &mut partial,
                &mut last_state,
            );

            match child.try_wait() {
                Ok(Some(status)) => break status,
                Ok(None) => thread::sleep(Duration::from_millis(200)),
                Err(error) => {
                    let _ = app_handle.emit(
                        "analysis:error",
                        AnalysisErrorEventPayload {
                            message: format!("run {} wait error: {}", thread_run_id, error),
                            code: Some("wait_failed".to_string()),
                            details: Some(serde_json::json!({
                                "runId": thread_run_id,
                                "outdir": thread_outdir,
                                "startedAt": thread_started_at,
                            })),
                        },
                    );
                    return;
                }
            }
        };

        emit_new_log_lines(
            &app_handle,
            &run_log_path,
            &mut offset,
            &mut partial,
            &mut last_state,
        );

        let summary_path = Path::new(&thread_outdir).join("report").join("run_summary.json");
        let summary = read_json_file(&summary_path).ok();
        let finished_status = if exit_status.success() {
            "SUCCEEDED".to_string()
        } else {
            summary
                .as_ref()
                .and_then(|value| value.get("status"))
                .and_then(|value| value.as_str())
                .unwrap_or("FAILED")
                .to_string()
        };

        if !exit_status.success() {
            let _ = app_handle.emit(
                "analysis:error",
                AnalysisErrorEventPayload {
                    message: format!(
                        "run {} exited with status {}",
                        thread_run_id,
                        exit_status
                            .code()
                            .map(|code| code.to_string())
                            .unwrap_or_else(|| "terminated".to_string())
                    ),
                    code: Some("non_zero_exit".to_string()),
                    details: Some(serde_json::json!({
                        "runId": thread_run_id,
                        "outdir": thread_outdir,
                        "exitCode": exit_status.code(),
                        "startedAt": thread_started_at,
                    })),
                },
            );
        }

        let _ = app_handle.emit(
            "analysis:finished",
            AnalysisFinishedEventPayload {
                status: finished_status,
                summary,
            },
        );
    });

    Ok(RunHandle {
        run_id,
        request_path,
        outdir,
        status: "PENDING".to_string(),
        started_at,
    })
}

fn emit_new_log_lines(
    app: &AppHandle,
    run_log_path: &Path,
    offset: &mut u64,
    partial: &mut String,
    last_state: &mut Option<String>,
) {
    if !run_log_path.is_file() {
        return;
    }

    let file = match File::open(run_log_path) {
        Ok(file) => file,
        Err(_) => return,
    };

    let metadata_len = match file.metadata() {
        Ok(metadata) => metadata.len(),
        Err(_) => return,
    };

    if metadata_len < *offset {
        *offset = 0;
        partial.clear();
    }

    if metadata_len == *offset {
        return;
    }

    let mut reader = BufReader::new(file);
    if reader.seek(SeekFrom::Start(*offset)).is_err() {
        return;
    }

    let mut chunk = String::new();
    if reader.read_to_string(&mut chunk).is_err() {
        return;
    }

    *offset = metadata_len;
    partial.push_str(&chunk);

    while let Some(newline_index) = partial.find('\n') {
        let mut line = partial[..newline_index].to_string();
        if line.ends_with('\r') {
            line.pop();
        }
        partial.drain(..=newline_index);

        if line.trim().is_empty() {
            continue;
        }

        let _ = app.emit(
            "analysis:stdout",
            AnalysisStdoutEventPayload {
                line: line.clone(),
            },
        );

        if let Some((state, progress)) = map_log_line_to_state(&line) {
            if last_state.as_deref() != Some(state.as_str()) {
                *last_state = Some(state.clone());
                let _ = app.emit(
                    "analysis:state",
                    AnalysisStateEventPayload { state, progress },
                );
            }
        }
    }
}

fn map_log_line_to_state(line: &str) -> Option<(String, f64)> {
    let step = extract_step(line)?;
    let state = match step.as_str() {
        "prepare_inputs" => "VALIDATING_INPUTS",
        "resolve_toolchain" | "probe_engine" => "CHECKING_TOOLCHAIN",
        "write_manifest" => "WRITING_MANIFEST",
        "run_engine" => "RUNNING_ENGINE",
        "archive_figures" | "write_summary" => "FINALIZING",
        _ => return None,
    };

    Some((state.to_string(), workflow_progress(state)))
}

fn extract_step(line: &str) -> Option<String> {
    let marker = "step=";
    let start = line.find(marker)? + marker.len();
    let rest = &line[start..];
    let end = rest.find(char::is_whitespace).unwrap_or(rest.len());
    Some(rest[..end].to_string())
}

fn workflow_progress(state: &str) -> f64 {
    match state {
        "PENDING" => 0.0,
        "VALIDATING_INPUTS" => 0.08,
        "PREPROCESSING_ANNOTATIONS" => 0.18,
        "PREPARING_WORKSPACE" => 0.28,
        "CHECKING_TOOLCHAIN" => 0.42,
        "WRITING_MANIFEST" => 0.56,
        "RUNNING_ENGINE" => 0.78,
        "PARSING_ENGINE_SUMMARY" => 0.90,
        "FINALIZING" => 0.96,
        "SUCCEEDED" | "FAILED" | "CANCELLED" => 1.0,
        _ => 0.0,
    }
}

fn command_version(program: &str, args: &[&str]) -> CommandVersion {
    let command_text = std::iter::once(program)
        .chain(args.iter().copied())
        .collect::<Vec<_>>()
        .join(" ");

    match Command::new(program).args(args).output() {
        Ok(output) if output.status.success() => CommandVersion {
            ok: true,
            command: command_text,
            version: String::from_utf8_lossy(&output.stdout).trim().to_string(),
            error: None,
        },
        Ok(output) => CommandVersion {
            ok: false,
            command: command_text,
            version: String::from_utf8_lossy(&output.stdout).trim().to_string(),
            error: Some(String::from_utf8_lossy(&output.stderr).trim().to_string()),
        },
        Err(error) => CommandVersion {
            ok: false,
            command: command_text,
            version: String::new(),
            error: Some(error.to_string()),
        },
    }
}

fn run_json_command(program: &str, args: &[&str]) -> Result<Value, String> {
    let command_text = std::iter::once(program)
        .chain(args.iter().copied())
        .collect::<Vec<_>>()
        .join(" ");

    let output = Command::new(program)
        .args(args)
        .output()
        .map_err(|error| format!("{command_text}: {error}"))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
        let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
        let message = if stderr.is_empty() { stdout } else { stderr };
        return Err(format!("{command_text}: {message}"));
    }

    serde_json::from_slice(&output.stdout)
        .map_err(|error| format!("{command_text}: invalid JSON: {error}"))
}

fn read_json_file(path: &Path) -> Result<Value, String> {
    let bytes =
        std::fs::read(path).map_err(|error| format!("read json file {}: {error}", path.display()))?;
    serde_json::from_slice(&bytes)
        .map_err(|error| format!("parse json file {}: {error}", path.display()))
}

fn unix_timestamp_millis() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_millis())
        .unwrap_or(0)
}

fn system_time_to_iso_like(time: SystemTime) -> String {
    match time.duration_since(UNIX_EPOCH) {
        Ok(duration) => format!("unix-{}.{}", duration.as_secs(), duration.subsec_millis()),
        Err(_) => "unix-0.000".to_string(),
    }
}
