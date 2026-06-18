use serde::Serialize;
use serde_json::Value;
use std::process::Command;

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

#[tauri::command]
pub fn get_version() -> VersionInfo {
    VersionInfo {
        platform: command_version("genomelens", &["--version"]),
        engine: command_version("jcvi-genomelens", &["--version"]),
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

    serde_json::from_slice(&output.stdout).map_err(|error| format!("{command_text}: invalid JSON: {error}"))
}
