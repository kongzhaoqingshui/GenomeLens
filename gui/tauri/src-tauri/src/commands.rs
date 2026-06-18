use serde::Serialize;
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
