use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::{BTreeMap, HashSet};
use std::env;
use std::ffi::OsString;
use std::fs::File;
use std::io::{BufReader, Read, Seek, SeekFrom};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
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
    pid: u32,
    started_at: String,
    log_path: String,
    summary_path: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ReadSummaryInput {
    outdir: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ReadRequestPreviewInput {
    request_path: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RequestPreview {
    request_path: String,
    json: Value,
    method: Option<String>,
    workflow: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ListProjectsInput {
    workspace: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CreateProjectInput {
    workspace: String,
    name: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ProjectSummary {
    name: String,
    path: String,
    config_path: String,
    jcvi_config_path: Option<String>,
    updated_at: Option<String>,
    created_at: Option<String>,
    last_run_at: Option<String>,
    #[serde(flatten)]
    extra_fields: BTreeMap<String, Value>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ListArtifactsInput {
    outdir: String,
}

#[derive(Debug, Serialize, Clone, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct ArtifactSummary {
    path: String,
    name: String,
    format: String,
    source: String,
    preview: bool,
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
#[serde(rename_all = "camelCase")]
pub struct AnalysisStdoutEventPayload {
    run_id: String,
    outdir: String,
    request_path: String,
    started_at: String,
    line: String,
}

#[derive(Debug, Serialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct AnalysisStateEventPayload {
    run_id: String,
    outdir: String,
    request_path: String,
    started_at: String,
    state: String,
    progress: f64,
}

#[derive(Debug, Serialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct AnalysisFinishedEventPayload {
    run_id: String,
    outdir: String,
    request_path: String,
    started_at: String,
    finished_at: String,
    exit_code: Option<i32>,
    log_path: String,
    summary_path: String,
    status: String,
    summary: Option<Value>,
}

#[derive(Debug, Serialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct AnalysisErrorEventPayload {
    run_id: String,
    outdir: String,
    request_path: String,
    started_at: String,
    finished_at: Option<String>,
    exit_code: Option<i32>,
    log_path: String,
    summary_path: String,
    message: String,
    code: Option<String>,
    details: Option<Value>,
}

#[derive(Debug, Clone)]
struct RunEventContext {
    run_id: String,
    outdir: String,
    request_path: String,
    started_at: String,
    log_path: String,
    summary_path: String,
}

#[derive(Debug, Clone, Copy)]
enum CliTool {
    Platform,
    Engine,
}

#[derive(Debug, Clone)]
struct ResolvedCliCommand {
    program: OsString,
    display: String,
}

#[derive(Debug)]
struct CommandOutputResult {
    command_text: String,
    output: std::process::Output,
}

#[derive(Debug)]
struct SpawnedCliProcess {
    child: Child,
}

#[derive(Debug, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
struct ProjectMetadataFile {
    name: Option<String>,
    path: Option<String>,
    config_path: Option<String>,
    jcvi_config_path: Option<String>,
    updated_at: Option<String>,
    created_at: Option<String>,
    last_run_at: Option<String>,
    #[serde(flatten)]
    extra_fields: BTreeMap<String, Value>,
}

#[derive(Debug, Deserialize, Default)]
struct RunArtifactSummaryDoc {
    #[serde(default)]
    final_figures: Vec<String>,
    #[serde(default)]
    global_figures: Vec<String>,
    #[serde(default)]
    artifact_index: Vec<ArtifactIndexEntry>,
}

#[derive(Debug, Deserialize, Default)]
struct ArtifactIndexEntry {
    path: String,
    format: Option<String>,
    preview: Option<bool>,
}

const MAX_REQUEST_PREVIEW_BYTES: u64 = 8 * 1024 * 1024;

#[tauri::command]
pub fn get_version() -> VersionInfo {
    VersionInfo {
        platform: command_version(CliTool::Platform, &["--version"]),
        engine: command_version(CliTool::Engine, &["probe"]),
    }
}

#[tauri::command]
pub fn get_template(method: String) -> Result<Value, String> {
    run_json_command(CliTool::Platform, &["analyze", "template", &method])
}

#[tauri::command]
pub fn get_analysis_schema() -> Result<Value, String> {
    run_json_command(CliTool::Platform, &["analyze", "schema"])
}

#[tauri::command]
pub fn check_environment() -> Result<Value, String> {
    run_json_command(CliTool::Platform, &["check", "-j"])
}

#[tauri::command]
pub fn read_request_preview(input: ReadRequestPreviewInput) -> Result<RequestPreview, String> {
    let request_path = input.request_path.trim().to_string();
    let (request_file_path, request_metadata) =
        validate_existing_file_input(&request_path, "request preview")?;
    if request_metadata.len() > MAX_REQUEST_PREVIEW_BYTES {
        return Err(format!(
            "request preview file is too large ({} bytes, limit {} bytes): {}",
            request_metadata.len(),
            MAX_REQUEST_PREVIEW_BYTES,
            request_file_path.display()
        ));
    }

    let json = read_json_file(&request_file_path)?;
    let json_object = json.as_object().ok_or_else(|| {
        format!(
            "request preview file must contain a JSON object: {}",
            request_file_path.display()
        )
    })?;
    let method = json
        .get("method")
        .and_then(Value::as_str)
        .map(ToOwned::to_owned);
    let workflow = json_object
        .get("method_config")
        .and_then(Value::as_object)
        .and_then(|method_config| method_config.get("workflow"))
        .and_then(Value::as_str)
        .map(ToOwned::to_owned);

    Ok(RequestPreview {
        request_path,
        json,
        method,
        workflow,
    })
}

#[tauri::command]
pub fn list_projects(input: ListProjectsInput) -> Result<Vec<ProjectSummary>, String> {
    list_projects_from_workspace(Path::new(&input.workspace))
}

#[tauri::command]
pub fn create_project(input: CreateProjectInput) -> Result<ProjectSummary, String> {
    create_project_in_workspace(Path::new(&input.workspace), &input.name)
}

#[tauri::command]
pub fn read_summary(input: ReadSummaryInput) -> Result<Value, String> {
    let summary_path = Path::new(&input.outdir)
        .join("report")
        .join("run_summary.json");
    read_json_file(&summary_path)
}

#[tauri::command]
pub fn list_artifacts(input: ListArtifactsInput) -> Result<Vec<ArtifactSummary>, String> {
    list_artifacts_from_outdir(Path::new(&input.outdir))
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
    let request_path = input.request_path.trim().to_string();
    validate_existing_file_input(&request_path, "analysis request")
        .map_err(|error| format!("run analysis {}: {}", request_path, error))?;
    let outdir = input.outdir.clone();
    let log_path = Path::new(&outdir)
        .join("logs")
        .join("run.log")
        .to_string_lossy()
        .to_string();
    let summary_path = Path::new(&outdir)
        .join("report")
        .join("run_summary.json")
        .to_string_lossy()
        .to_string();

    let spawned = spawn_cli_process(CliTool::Platform, &["analyze", "run", &request_path])
        .map_err(|error| {
            let message = format!("run analysis {}: {}", request_path, error);
            let _ = app.emit(
                "analysis:error",
                AnalysisErrorEventPayload {
                    run_id: run_id.clone(),
                    outdir: outdir.clone(),
                    request_path: request_path.clone(),
                    started_at: started_at.clone(),
                    finished_at: None,
                    exit_code: None,
                    log_path: log_path.clone(),
                    summary_path: summary_path.clone(),
                    message: message.clone(),
                    code: Some("spawn_failed".to_string()),
                    details: None,
                },
            );
            message
        })?;
    let mut child = spawned.child;
    let pid = child.id();

    let app_handle = app.clone();
    let thread_context = RunEventContext {
        run_id: run_id.clone(),
        outdir: outdir.clone(),
        request_path: request_path.clone(),
        started_at: started_at.clone(),
        log_path: log_path.clone(),
        summary_path: summary_path.clone(),
    };

    thread::spawn(move || {
        let run_log_path = Path::new(&thread_context.outdir)
            .join("logs")
            .join("run.log");
        let mut offset = 0_u64;
        let mut partial = String::new();
        let mut last_state: Option<String> = None;

        let exit_status = loop {
            emit_new_log_lines(
                &app_handle,
                &run_log_path,
                &thread_context,
                false,
                &mut offset,
                &mut partial,
                &mut last_state,
            );

            match child.try_wait() {
                Ok(Some(status)) => break status,
                Ok(None) => thread::sleep(Duration::from_millis(200)),
                Err(error) => {
                    emit_new_log_lines(
                        &app_handle,
                        &run_log_path,
                        &thread_context,
                        true,
                        &mut offset,
                        &mut partial,
                        &mut last_state,
                    );

                    let summary = read_json_file(Path::new(&thread_context.summary_path)).ok();
                    let finished_at = system_time_to_iso_like(SystemTime::now());
                    let _ = app_handle.emit(
                        "analysis:error",
                        AnalysisErrorEventPayload {
                            run_id: thread_context.run_id.clone(),
                            outdir: thread_context.outdir.clone(),
                            request_path: thread_context.request_path.clone(),
                            started_at: thread_context.started_at.clone(),
                            finished_at: Some(finished_at.clone()),
                            exit_code: None,
                            log_path: thread_context.log_path.clone(),
                            summary_path: thread_context.summary_path.clone(),
                            message: format!("run {} wait error: {}", thread_context.run_id, error),
                            code: Some("wait_failed".to_string()),
                            details: Some(serde_json::json!({
                                "runId": thread_context.run_id,
                                "outdir": thread_context.outdir,
                                "requestPath": thread_context.request_path,
                                "startedAt": thread_context.started_at,
                            })),
                        },
                    );

                    let _ = app_handle.emit(
                        "analysis:finished",
                        AnalysisFinishedEventPayload {
                            run_id: thread_context.run_id.clone(),
                            outdir: thread_context.outdir.clone(),
                            request_path: thread_context.request_path.clone(),
                            started_at: thread_context.started_at.clone(),
                            finished_at,
                            exit_code: None,
                            log_path: thread_context.log_path.clone(),
                            summary_path: thread_context.summary_path.clone(),
                            status: summary
                                .as_ref()
                                .and_then(|value| value.get("status"))
                                .and_then(|value| value.as_str())
                                .unwrap_or("FAILED")
                                .to_string(),
                            summary,
                        },
                    );
                    return;
                }
            }
        };

        emit_new_log_lines(
            &app_handle,
            &run_log_path,
            &thread_context,
            true,
            &mut offset,
            &mut partial,
            &mut last_state,
        );

        let summary = read_json_file(Path::new(&thread_context.summary_path)).ok();
        let finished_at = system_time_to_iso_like(SystemTime::now());
        let exit_code = exit_status.code();
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
                    run_id: thread_context.run_id.clone(),
                    outdir: thread_context.outdir.clone(),
                    request_path: thread_context.request_path.clone(),
                    started_at: thread_context.started_at.clone(),
                    finished_at: Some(finished_at.clone()),
                    exit_code,
                    log_path: thread_context.log_path.clone(),
                    summary_path: thread_context.summary_path.clone(),
                    message: format!(
                        "run {} exited with status {}",
                        thread_context.run_id,
                        exit_status
                            .code()
                            .map(|code| code.to_string())
                            .unwrap_or_else(|| "terminated".to_string())
                    ),
                    code: Some("non_zero_exit".to_string()),
                    details: Some(serde_json::json!({
                        "runId": thread_context.run_id,
                        "outdir": thread_context.outdir,
                        "requestPath": thread_context.request_path,
                        "exitCode": exit_status.code(),
                        "startedAt": thread_context.started_at,
                        "finishedAt": finished_at,
                    })),
                },
            );
        }

        let _ = app_handle.emit(
            "analysis:finished",
            AnalysisFinishedEventPayload {
                run_id: thread_context.run_id,
                outdir: thread_context.outdir,
                request_path: thread_context.request_path,
                started_at: thread_context.started_at,
                finished_at,
                exit_code,
                log_path: thread_context.log_path,
                summary_path: thread_context.summary_path,
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
        pid,
        started_at,
        log_path,
        summary_path,
    })
}

fn emit_new_log_lines(
    app: &AppHandle,
    run_log_path: &Path,
    context: &RunEventContext,
    flush_partial: bool,
    offset: &mut u64,
    partial: &mut String,
    last_state: &mut Option<String>,
) {
    if !run_log_path.is_file() && (!flush_partial || partial.is_empty()) {
        return;
    }

    if run_log_path.is_file() {
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

        if metadata_len > *offset {
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
        }
    }

    for line in drain_buffered_log_lines(partial, flush_partial) {
        let _ = app.emit(
            "analysis:stdout",
            AnalysisStdoutEventPayload {
                run_id: context.run_id.clone(),
                outdir: context.outdir.clone(),
                request_path: context.request_path.clone(),
                started_at: context.started_at.clone(),
                line: line.clone(),
            },
        );

        if let Some((state, progress)) = map_log_line_to_state(&line) {
            if last_state.as_deref() != Some(state.as_str()) {
                *last_state = Some(state.clone());
                let _ = app.emit(
                    "analysis:state",
                    AnalysisStateEventPayload {
                        run_id: context.run_id.clone(),
                        outdir: context.outdir.clone(),
                        request_path: context.request_path.clone(),
                        started_at: context.started_at.clone(),
                        state,
                        progress,
                    },
                );
            }
        }
    }
}

fn drain_buffered_log_lines(partial: &mut String, flush_partial: bool) -> Vec<String> {
    let mut lines = Vec::new();

    while let Some(newline_index) = partial.find('\n') {
        let mut line = partial[..newline_index].to_string();
        if line.ends_with('\r') {
            line.pop();
        }
        partial.drain(..=newline_index);

        if line.trim().is_empty() {
            continue;
        }

        lines.push(line);
    }

    if flush_partial && !partial.trim().is_empty() {
        let mut line = std::mem::take(partial);
        if line.ends_with('\r') {
            line.pop();
        }
        if !line.trim().is_empty() {
            lines.push(line);
        }
    }

    lines
}

fn map_log_line_to_state(line: &str) -> Option<(String, f64)> {
    let step = extract_step(line)?;
    let state = match step.as_str() {
        "prepare_inputs" => "VALIDATING_INPUTS",
        "prepare_multi_species_workspace" => "PREPARING_WORKSPACE",
        "resolve_toolchain" | "probe_engine" => "CHECKING_TOOLCHAIN",
        "write_manifest" => "WRITING_MANIFEST",
        "run_engine" | "run_pairwise_job" => "RUNNING_ENGINE",
        "copy_pairwise_figures" => "PARSING_ENGINE_SUMMARY",
        "archive_figures"
        | "write_summary"
        | "optimize_layout"
        | "build_global_karyotype"
        | "write_multi_summary" => "FINALIZING",
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

fn list_projects_from_workspace(workspace: &Path) -> Result<Vec<ProjectSummary>, String> {
    if !workspace.exists() {
        return Ok(Vec::new());
    }

    if !workspace.is_dir() {
        return Err(format!(
            "workspace is not a directory: {}",
            workspace.display()
        ));
    }

    let mut projects = Vec::new();
    let entries = std::fs::read_dir(workspace)
        .map_err(|error| format!("read workspace {}: {error}", workspace.display()))?;

    for entry in entries {
        let entry = entry
            .map_err(|error| format!("read workspace entry {}: {error}", workspace.display()))?;
        let project_dir = entry.path();
        if !project_dir.is_dir() {
            continue;
        }

        let config_path = project_config_path(&project_dir);
        if !config_path.is_file() {
            continue;
        }

        let metadata = read_project_metadata(&project_dir, &config_path)?;
        projects.push(metadata);
    }

    projects.sort_by(|left, right| {
        left.name
            .to_lowercase()
            .cmp(&right.name.to_lowercase())
            .then_with(|| left.path.cmp(&right.path))
    });

    Ok(projects)
}

fn create_project_in_workspace(workspace: &Path, name: &str) -> Result<ProjectSummary, String> {
    let normalized_name = normalize_project_name(name)?;

    if workspace.exists() && !workspace.is_dir() {
        return Err(format!(
            "workspace is not a directory: {}",
            workspace.display()
        ));
    }

    std::fs::create_dir_all(workspace)
        .map_err(|error| format!("create workspace {}: {error}", workspace.display()))?;

    let project_dir = workspace.join(&normalized_name);
    if project_dir.exists() {
        return Err(format!("project already exists: {}", project_dir.display()));
    }

    let project_meta_dir = project_dir.join(".genomelens");
    std::fs::create_dir_all(&project_meta_dir).map_err(|error| {
        format!(
            "create project metadata dir {}: {error}",
            project_meta_dir.display()
        )
    })?;

    let now = system_time_to_iso_like(SystemTime::now());
    let config_path = project_meta_dir.join("project.json");
    let metadata = ProjectMetadataFile {
        name: Some(normalized_name.clone()),
        path: Some(project_dir.to_string_lossy().to_string()),
        config_path: Some(config_path.to_string_lossy().to_string()),
        jcvi_config_path: None,
        updated_at: Some(now.clone()),
        created_at: Some(now),
        last_run_at: None,
        extra_fields: BTreeMap::new(),
    };

    let serialized = serde_json::to_vec_pretty(&metadata).map_err(|error| {
        format!(
            "serialize project metadata {}: {error}",
            config_path.display()
        )
    })?;
    std::fs::write(&config_path, serialized)
        .map_err(|error| format!("write project metadata {}: {error}", config_path.display()))?;

    read_project_metadata(&project_dir, &config_path)
}

fn list_artifacts_from_outdir(outdir: &Path) -> Result<Vec<ArtifactSummary>, String> {
    let summary_path = outdir.join("report").join("run_summary.json");
    let summary_json = read_json_file(&summary_path)?;
    let summary: RunArtifactSummaryDoc = serde_json::from_value(summary_json)
        .map_err(|error| format!("parse run summary {}: {error}", summary_path.display()))?;

    let mut artifacts = Vec::new();

    for path in summary.final_figures {
        merge_artifact_summary(&mut artifacts, path, None, "final_figures", true);
    }

    for path in summary.global_figures {
        merge_artifact_summary(&mut artifacts, path, None, "global_figures", true);
    }

    for artifact in summary.artifact_index {
        merge_artifact_summary(
            &mut artifacts,
            artifact.path,
            artifact.format,
            "artifact_index",
            artifact.preview.unwrap_or(false),
        );
    }

    Ok(artifacts)
}

fn read_project_metadata(project_dir: &Path, config_path: &Path) -> Result<ProjectSummary, String> {
    let bytes = std::fs::read(config_path)
        .map_err(|error| format!("read project metadata {}: {error}", config_path.display()))?;
    let metadata: ProjectMetadataFile = serde_json::from_slice(&bytes)
        .map_err(|error| format!("parse project metadata {}: {error}", config_path.display()))?;
    Ok(project_metadata_to_summary(
        project_dir,
        config_path,
        metadata,
    ))
}

fn project_metadata_to_summary(
    project_dir: &Path,
    config_path: &Path,
    metadata: ProjectMetadataFile,
) -> ProjectSummary {
    let fallback_name = project_dir
        .file_name()
        .map(|name| name.to_string_lossy().to_string())
        .unwrap_or_else(|| project_dir.display().to_string());

    ProjectSummary {
        name: metadata.name.unwrap_or(fallback_name),
        path: metadata
            .path
            .unwrap_or_else(|| project_dir.to_string_lossy().to_string()),
        config_path: metadata
            .config_path
            .unwrap_or_else(|| config_path.to_string_lossy().to_string()),
        jcvi_config_path: metadata.jcvi_config_path,
        updated_at: metadata.updated_at,
        created_at: metadata.created_at,
        last_run_at: metadata.last_run_at,
        extra_fields: metadata.extra_fields,
    }
}

fn project_config_path(project_dir: &Path) -> PathBuf {
    project_dir.join(".genomelens").join("project.json")
}

fn normalize_project_name(name: &str) -> Result<String, String> {
    let normalized = name.trim();
    if normalized.is_empty() {
        return Err("project name must not be empty".to_string());
    }

    let invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*'];
    if normalized
        .chars()
        .any(|character| character.is_control() || invalid_chars.contains(&character))
    {
        return Err(format!(
            "project name contains invalid characters: {}",
            name
        ));
    }

    if normalized.ends_with('.') || normalized.ends_with(' ') {
        return Err(format!(
            "project name must not end with '.' or space: {}",
            name
        ));
    }

    Ok(normalized.to_string())
}

fn merge_artifact_summary(
    artifacts: &mut Vec<ArtifactSummary>,
    path: String,
    format: Option<String>,
    source: &str,
    preview: bool,
) {
    if path.trim().is_empty() {
        return;
    }

    if let Some(existing) = artifacts.iter_mut().find(|artifact| artifact.path == path) {
        existing.preview |= preview;
        if existing.format == "unknown" {
            if let Some(candidate_format) = format.filter(|value| !value.trim().is_empty()) {
                existing.format = candidate_format;
            }
        }
        return;
    }

    let format = format
        .filter(|value| !value.trim().is_empty())
        .unwrap_or_else(|| infer_artifact_format(&path, "unknown"));

    artifacts.push(ArtifactSummary {
        name: basename(&path),
        path,
        format,
        source: source.to_string(),
        preview,
    });
}

fn basename(path: &str) -> String {
    Path::new(path)
        .file_name()
        .map(|name| name.to_string_lossy().to_string())
        .unwrap_or_else(|| path.to_string())
}

fn infer_artifact_format(path: &str, fallback: &str) -> String {
    Path::new(path)
        .extension()
        .map(|extension| extension.to_string_lossy().to_ascii_lowercase())
        .filter(|extension| !extension.is_empty())
        .unwrap_or_else(|| fallback.to_string())
}

impl CliTool {
    fn command_name(self) -> &'static str {
        match self {
            Self::Platform => "genomelens",
            Self::Engine => "jcvi-genomelens",
        }
    }

    fn override_env_var(self) -> &'static str {
        match self {
            Self::Platform => "GENOMELENS_CLI",
            Self::Engine => "JCVI_GENOMELENS_CLI",
        }
    }
}

fn command_version(tool: CliTool, args: &[&str]) -> CommandVersion {
    match run_cli_output(tool, args) {
        Ok(result) if result.output.status.success() => CommandVersion {
            ok: true,
            command: result.command_text,
            version: String::from_utf8_lossy(&result.output.stdout)
                .trim()
                .to_string(),
            error: None,
        },
        Ok(result) => CommandVersion {
            ok: false,
            command: result.command_text,
            version: String::from_utf8_lossy(&result.output.stdout)
                .trim()
                .to_string(),
            error: Some(
                String::from_utf8_lossy(&result.output.stderr)
                    .trim()
                    .to_string(),
            ),
        },
        Err(error) => CommandVersion {
            ok: false,
            command: render_logical_command(tool, args),
            version: String::new(),
            error: Some(error.to_string()),
        },
    }
}

fn run_json_command(tool: CliTool, args: &[&str]) -> Result<Value, String> {
    let output = run_cli_output(tool, args)?;

    if !output.output.status.success() {
        let stderr = String::from_utf8_lossy(&output.output.stderr)
            .trim()
            .to_string();
        let stdout = String::from_utf8_lossy(&output.output.stdout)
            .trim()
            .to_string();
        let message = if stderr.is_empty() { stdout } else { stderr };
        return Err(format!("{}: {}", output.command_text, message));
    }

    serde_json::from_slice(&output.output.stdout)
        .map_err(|error| format!("{}: invalid JSON: {}", output.command_text, error))
}

fn run_cli_output(tool: CliTool, args: &[&str]) -> Result<CommandOutputResult, String> {
    let candidates = resolve_cli_candidates(tool);
    let mut attempt_texts = Vec::with_capacity(candidates.len());
    let mut errors = Vec::new();

    for candidate in candidates {
        let command_text = render_command_text(&candidate.display, args);
        attempt_texts.push(command_text.clone());

        match Command::new(&candidate.program).args(args).output() {
            Ok(output) => {
                return Ok(CommandOutputResult {
                    command_text,
                    output,
                });
            }
            Err(error) if is_not_found_error(&error) => {
                errors.push(format!("{command_text}: {error}"));
            }
            Err(error) => {
                return Err(format!("{}: {}", command_text, error));
            }
        }
    }

    Err(render_resolution_error(tool, &attempt_texts, &errors))
}

fn spawn_cli_process(tool: CliTool, args: &[&str]) -> Result<SpawnedCliProcess, String> {
    let candidates = resolve_cli_candidates(tool);
    let mut attempt_texts = Vec::with_capacity(candidates.len());
    let mut errors = Vec::new();

    for candidate in candidates {
        let command_text = render_command_text(&candidate.display, args);
        attempt_texts.push(command_text.clone());

        let mut command = Command::new(&candidate.program);
        command
            .args(args)
            .stdout(Stdio::null())
            .stderr(Stdio::null());

        match command.spawn() {
            Ok(child) => {
                return Ok(SpawnedCliProcess { child });
            }
            Err(error) if is_not_found_error(&error) => {
                errors.push(format!("{command_text}: {error}"));
            }
            Err(error) => {
                return Err(format!("{}: {}", command_text, error));
            }
        }
    }

    Err(render_resolution_error(tool, &attempt_texts, &errors))
}

fn resolve_cli_candidates(tool: CliTool) -> Vec<ResolvedCliCommand> {
    let mut candidates = Vec::new();
    let mut seen = HashSet::new();
    let explicit_override = env::var(tool.override_env_var()).ok();
    let conda_prefix = env::var_os("CONDA_PREFIX").map(PathBuf::from);
    let home_dir = resolve_home_dir();

    if let Some(override_value) = explicit_override.as_deref() {
        push_override_candidates(override_value, &mut candidates, &mut seen);
    }

    if let Some(prefix) = conda_prefix.as_deref() {
        push_conda_env_candidates(prefix, tool.command_name(), &mut candidates, &mut seen);
    }

    for env_root in common_conda_env_roots(home_dir.as_deref()) {
        push_conda_env_candidates(&env_root, tool.command_name(), &mut candidates, &mut seen);
    }

    push_named_candidate(tool.command_name(), &mut candidates, &mut seen);
    candidates
}

fn push_override_candidates(
    value: &str,
    candidates: &mut Vec<ResolvedCliCommand>,
    seen: &mut HashSet<String>,
) {
    if looks_like_path(value) {
        push_program_path_candidates(Path::new(value), candidates, seen);
    } else {
        push_named_candidate(value, candidates, seen);
    }
}

fn push_conda_env_candidates(
    env_root: &Path,
    program_name: &str,
    candidates: &mut Vec<ResolvedCliCommand>,
    seen: &mut HashSet<String>,
) {
    #[cfg(target_os = "windows")]
    {
        push_program_path_candidates(
            &env_root.join("Scripts").join(program_name),
            candidates,
            seen,
        );
        push_program_path_candidates(
            &env_root.join("Library").join("bin").join(program_name),
            candidates,
            seen,
        );
    }

    #[cfg(not(target_os = "windows"))]
    {
        push_program_path_candidates(&env_root.join("bin").join(program_name), candidates, seen);
    }
}

fn push_program_path_candidates(
    base_path: &Path,
    candidates: &mut Vec<ResolvedCliCommand>,
    seen: &mut HashSet<String>,
) {
    for candidate_path in command_path_variants(base_path) {
        let display = candidate_path.display().to_string();
        if seen.insert(display.clone()) {
            candidates.push(ResolvedCliCommand {
                program: candidate_path.into_os_string(),
                display,
            });
        }
    }
}

fn push_named_candidate(
    program_name: &str,
    candidates: &mut Vec<ResolvedCliCommand>,
    seen: &mut HashSet<String>,
) {
    let display = program_name.to_string();
    if seen.insert(display.clone()) {
        candidates.push(ResolvedCliCommand {
            program: OsString::from(program_name),
            display,
        });
    }
}

fn command_path_variants(base_path: &Path) -> Vec<PathBuf> {
    let mut variants = Vec::new();

    #[cfg(target_os = "windows")]
    if base_path.extension().is_none() {
        for extension in ["exe", "cmd", "bat"] {
            variants.push(base_path.with_extension(extension));
        }
    }

    variants.push(base_path.to_path_buf());
    variants
}

fn common_conda_env_roots(home_dir: Option<&Path>) -> Vec<PathBuf> {
    let Some(home_dir) = home_dir else {
        return Vec::new();
    };

    let mut roots = Vec::new();
    let mut seen = HashSet::new();
    for env_root in [
        home_dir.join(".conda").join("envs").join("genomelens"),
        home_dir.join("miniconda3").join("envs").join("genomelens"),
        home_dir.join("Miniconda3").join("envs").join("genomelens"),
        home_dir.join("anaconda3").join("envs").join("genomelens"),
        home_dir.join("Anaconda3").join("envs").join("genomelens"),
        home_dir.join("miniforge3").join("envs").join("genomelens"),
        home_dir.join("mambaforge").join("envs").join("genomelens"),
    ] {
        let display = env_root.display().to_string();
        if seen.insert(display) {
            roots.push(env_root);
        }
    }
    roots
}

fn resolve_home_dir() -> Option<PathBuf> {
    env::var_os("USERPROFILE")
        .or_else(|| env::var_os("HOME"))
        .map(PathBuf::from)
}

fn looks_like_path(value: &str) -> bool {
    value.contains('/') || value.contains('\\') || Path::new(value).is_absolute()
}

fn render_logical_command(tool: CliTool, args: &[&str]) -> String {
    render_command_text(tool.command_name(), args)
}

fn render_command_text(program: &str, args: &[&str]) -> String {
    std::iter::once(program)
        .chain(args.iter().copied())
        .collect::<Vec<_>>()
        .join(" ")
}

fn render_resolution_error(tool: CliTool, attempt_texts: &[String], errors: &[String]) -> String {
    let command_name = tool.command_name();
    if errors.is_empty() {
        return format!(
            "{command_name} not found. hint: {}",
            render_cli_resolution_hint(tool)
        );
    }

    format!(
        "{command_name} not found. attempted: {}. errors: {}. hint: {}",
        attempt_texts.join(" | "),
        errors.join(" | "),
        render_cli_resolution_hint(tool)
    )
}

fn is_not_found_error(error: &std::io::Error) -> bool {
    error.kind() == std::io::ErrorKind::NotFound
}

fn render_cli_resolution_hint(tool: CliTool) -> String {
    format!(
        "set {} to the executable path, activate the genomelens conda environment so CONDA_PREFIX is available, or ensure {} is on PATH",
        tool.override_env_var(),
        tool.command_name()
    )
}

fn validate_existing_file_input(
    path_text: &str,
    label: &str,
) -> Result<(PathBuf, std::fs::Metadata), String> {
    let trimmed = path_text.trim();
    if trimmed.is_empty() {
        return Err(format!("{label} path must not be empty"));
    }

    let path = PathBuf::from(trimmed);
    let metadata = std::fs::metadata(&path).map_err(|error| {
        if error.kind() == std::io::ErrorKind::NotFound {
            format!("{label} path does not exist: {}", path.display())
        } else {
            format!("read {label} path metadata {}: {error}", path.display())
        }
    })?;

    if metadata.is_dir() {
        return Err(format!(
            "{label} path is a directory, expected a file: {}",
            path.display()
        ));
    }

    if !metadata.is_file() {
        return Err(format!(
            "{label} path is not a regular file: {}",
            path.display()
        ));
    }

    Ok((path, metadata))
}

fn read_json_file(path: &Path) -> Result<Value, String> {
    let bytes = std::fs::read(path)
        .map_err(|error| format!("read json file {}: {error}", path.display()))?;
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

#[cfg(test)]
mod tests {
    use super::{
        command_path_variants, common_conda_env_roots, create_project_in_workspace,
        drain_buffered_log_lines, list_artifacts_from_outdir, list_projects_from_workspace,
        looks_like_path, map_log_line_to_state, normalize_project_name, read_request_preview,
        render_resolution_error, validate_existing_file_input, CliTool, ReadRequestPreviewInput,
        MAX_REQUEST_PREVIEW_BYTES,
    };
    use serde_json::json;
    use std::path::{Path, PathBuf};
    use std::time::{SystemTime, UNIX_EPOCH};

    #[test]
    fn drains_complete_lines_without_flushing_partial_tail() {
        let mut partial = String::from("line-1\nline-2");
        let lines = drain_buffered_log_lines(&mut partial, false);

        assert_eq!(lines, vec!["line-1"]);
        assert_eq!(partial, "line-2");
    }

    #[test]
    fn flushes_unterminated_tail_line_when_requested() {
        let mut partial = String::from("line-1\nline-2");
        let lines = drain_buffered_log_lines(&mut partial, true);

        assert_eq!(lines, vec!["line-1", "line-2"]);
        assert!(partial.is_empty());
    }

    #[test]
    fn maps_multi_species_steps_to_monotonic_workflow_states() {
        let mappings = [
            (
                "task_started step=prepare_multi_species_workspace status=running",
                "PREPARING_WORKSPACE",
                0.28_f64,
            ),
            (
                "task_started step=run_pairwise_job status=running",
                "RUNNING_ENGINE",
                0.78_f64,
            ),
            (
                "task_finished step=copy_pairwise_figures status=ok",
                "PARSING_ENGINE_SUMMARY",
                0.90_f64,
            ),
            (
                "task_started step=optimize_layout status=running",
                "FINALIZING",
                0.96_f64,
            ),
            (
                "task_started step=build_global_karyotype status=running",
                "FINALIZING",
                0.96_f64,
            ),
            (
                "task_finished step=write_multi_summary status=ok",
                "FINALIZING",
                0.96_f64,
            ),
        ];

        let mut previous_progress = 0.0_f64;
        for (line, expected_state, expected_progress) in mappings {
            let (state, progress) =
                map_log_line_to_state(line).expect("expected mapped workflow state");
            assert_eq!(state, expected_state);
            assert_eq!(progress, expected_progress);
            assert!(progress >= previous_progress);
            previous_progress = progress;
        }
    }

    #[test]
    fn detects_path_like_cli_overrides() {
        assert!(looks_like_path(
            r"C:\Users\demo\miniconda3\envs\genomelens\Scripts\genomelens.exe"
        ));
        assert!(looks_like_path("./genomelens"));
        assert!(!looks_like_path("genomelens"));
    }

    #[test]
    fn includes_common_conda_env_roots() {
        let home = Path::new(r"C:\Users\demo");
        let roots = common_conda_env_roots(Some(home));
        let rendered = roots
            .iter()
            .map(|path| path.display().to_string())
            .collect::<Vec<_>>();

        assert!(rendered
            .iter()
            .any(|path| path.ends_with(r".conda\envs\genomelens")));
        assert!(rendered
            .iter()
            .any(|path| path.ends_with(r"miniconda3\envs\genomelens")));
        assert!(rendered
            .iter()
            .any(|path| path.ends_with(r"anaconda3\envs\genomelens")));
    }

    #[cfg(target_os = "windows")]
    #[test]
    fn expands_windows_cli_path_variants() {
        let variants = command_path_variants(Path::new(
            r"C:\Users\demo\miniconda3\envs\genomelens\Scripts\genomelens",
        ))
        .into_iter()
        .map(|path| path.display().to_string())
        .collect::<Vec<_>>();

        assert_eq!(variants.len(), 4);
        assert!(variants[0].ends_with("genomelens.exe"));
        assert!(variants[1].ends_with("genomelens.cmd"));
        assert!(variants[2].ends_with("genomelens.bat"));
        assert!(variants[3].ends_with("genomelens"));
    }

    #[test]
    fn resolution_errors_include_override_and_conda_hints() {
        let message = render_resolution_error(
            CliTool::Platform,
            &["genomelens --version".to_string()],
            &["genomelens --version: not found".to_string()],
        );

        assert!(message.contains("GENOMELENS_CLI"));
        assert!(message.contains("CONDA_PREFIX"));
        assert!(message.contains("genomelens is on PATH"));
    }

    #[test]
    fn rejects_invalid_project_names() {
        assert!(normalize_project_name("  ").is_err());
        assert!(normalize_project_name("bad/name").is_err());
        assert!(normalize_project_name("bad. ").is_err());
    }

    #[test]
    fn creates_and_lists_workspace_projects() {
        let workspace = unique_temp_dir("workspace-projects");
        std::fs::create_dir_all(&workspace).expect("create workspace temp dir");

        let created = create_project_in_workspace(&workspace, "Alpha").expect("create project");
        assert_eq!(created.name, "Alpha");
        assert!(Path::new(&created.path).is_dir());
        assert!(Path::new(&created.config_path).is_file());

        let listed = list_projects_from_workspace(&workspace).expect("list projects");
        assert_eq!(listed.len(), 1);
        assert_eq!(listed[0].name, "Alpha");
        assert_eq!(listed[0].config_path, created.config_path);

        std::fs::remove_dir_all(&workspace).expect("cleanup workspace temp dir");
    }

    #[test]
    fn reads_request_preview_without_rewriting_request_json() {
        let temp_dir = unique_temp_dir("request-preview");
        std::fs::create_dir_all(&temp_dir).expect("create request preview temp dir");
        let request_path = temp_dir.join("request.json");
        let request = json!({
            "method": "mcscan",
            "options": {
                "threads": 4
            },
            "method_config": {
                "workflow": "pairwise"
            }
        });

        std::fs::write(
            &request_path,
            serde_json::to_vec_pretty(&request).expect("serialize request"),
        )
        .expect("write request");

        let preview = read_request_preview(ReadRequestPreviewInput {
            request_path: request_path.to_string_lossy().to_string(),
        })
        .expect("read request preview");

        assert_eq!(preview.request_path, request_path.to_string_lossy());
        assert_eq!(preview.method.as_deref(), Some("mcscan"));
        assert_eq!(preview.workflow.as_deref(), Some("pairwise"));
        assert_eq!(preview.json, request);

        std::fs::remove_dir_all(&temp_dir).expect("cleanup request preview temp dir");
    }

    #[test]
    fn reads_request_preview_without_method_or_workflow() {
        let temp_dir = unique_temp_dir("request-preview-missing-fields");
        std::fs::create_dir_all(&temp_dir).expect("create request preview temp dir");
        let request_path = temp_dir.join("request.json");
        let request = json!({
            "input": {
                "mode": "bed_cds"
            }
        });

        std::fs::write(
            &request_path,
            serde_json::to_vec_pretty(&request).expect("serialize request"),
        )
        .expect("write request");

        let preview = read_request_preview(ReadRequestPreviewInput {
            request_path: request_path.to_string_lossy().to_string(),
        })
        .expect("read request preview");

        assert_eq!(preview.method, None);
        assert_eq!(preview.workflow, None);
        assert_eq!(preview.json, request);

        std::fs::remove_dir_all(&temp_dir).expect("cleanup request preview temp dir");
    }

    #[test]
    fn request_preview_rejects_directory_paths() {
        let temp_dir = unique_temp_dir("request-preview-directory");
        std::fs::create_dir_all(&temp_dir).expect("create request preview temp dir");

        let error = read_request_preview(ReadRequestPreviewInput {
            request_path: temp_dir.to_string_lossy().to_string(),
        })
        .expect_err("directory path should fail request preview");

        assert!(error.contains("is a directory"));

        std::fs::remove_dir_all(&temp_dir).expect("cleanup request preview temp dir");
    }

    #[test]
    fn request_preview_rejects_oversized_files() {
        let temp_dir = unique_temp_dir("request-preview-large");
        std::fs::create_dir_all(&temp_dir).expect("create request preview temp dir");
        let request_path = temp_dir.join("request.json");
        let oversized = vec![b' '; (MAX_REQUEST_PREVIEW_BYTES as usize) + 1];
        std::fs::write(&request_path, oversized).expect("write oversized request");

        let error = read_request_preview(ReadRequestPreviewInput {
            request_path: request_path.to_string_lossy().to_string(),
        })
        .expect_err("oversized request preview should fail");

        assert!(error.contains("too large"));

        std::fs::remove_dir_all(&temp_dir).expect("cleanup request preview temp dir");
    }

    #[test]
    fn validates_existing_file_input_for_missing_and_directory_paths() {
        let missing = validate_existing_file_input("missing.json", "analysis request")
            .expect_err("missing file should fail");
        assert!(missing.contains("does not exist"));

        let temp_dir = unique_temp_dir("existing-file-input-directory");
        std::fs::create_dir_all(&temp_dir).expect("create temp dir");

        let directory_error =
            validate_existing_file_input(temp_dir.to_string_lossy().as_ref(), "analysis request")
                .expect_err("directory path should fail");
        assert!(directory_error.contains("is a directory"));

        std::fs::remove_dir_all(&temp_dir).expect("cleanup temp dir");
    }

    #[test]
    fn lists_artifacts_from_run_summary_without_duplicates() {
        let outdir = unique_temp_dir("artifact-summary");
        let report_dir = outdir.join("report");
        std::fs::create_dir_all(&report_dir).expect("create report dir");
        let summary_path = report_dir.join("run_summary.json");

        let summary = json!({
            "final_figures": [
                outdir.join("report").join("dotplot.png").to_string_lossy().to_string()
            ],
            "global_figures": [
                outdir.join("report").join("karyotype.svg").to_string_lossy().to_string()
            ],
            "artifact_index": [
                {
                    "artifact_id": "dotplot",
                    "artifact_type": "figure",
                    "path": outdir.join("report").join("dotplot.png").to_string_lossy().to_string(),
                    "format": "png",
                    "preview": true
                },
                {
                    "artifact_id": "anchors",
                    "artifact_type": "table",
                    "path": outdir.join("report").join("anchors.tsv").to_string_lossy().to_string(),
                    "format": "tsv",
                    "preview": false
                }
            ]
        });

        std::fs::write(
            &summary_path,
            serde_json::to_vec_pretty(&summary).expect("serialize summary"),
        )
        .expect("write summary");

        let artifacts = list_artifacts_from_outdir(&outdir).expect("list artifacts");
        assert_eq!(artifacts.len(), 3);
        assert_eq!(artifacts[0].source, "final_figures");
        assert_eq!(artifacts[1].source, "global_figures");
        assert_eq!(artifacts[2].source, "artifact_index");
        assert_eq!(artifacts[2].format, "tsv");

        std::fs::remove_dir_all(&outdir).expect("cleanup outdir temp dir");
    }

    fn unique_temp_dir(label: &str) -> PathBuf {
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("duration since epoch")
            .as_nanos();
        std::env::temp_dir().join(format!("genomelens-gui-{label}-{unique}"))
    }
}
