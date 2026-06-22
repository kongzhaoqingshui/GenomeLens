mod commands;

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_os::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            commands::cancel_run,
            commands::check_environment,
            commands::create_project,
            commands::get_analysis_schema,
            commands::get_template,
            commands::get_version,
            commands::list_artifacts,
            commands::list_projects,
            commands::open_path,
            commands::read_request_preview,
            commands::read_run_log,
            commands::read_run_snapshot,
            commands::read_summary,
            commands::run_analysis
        ])
        .run(tauri::generate_context!())
        .expect("error while running JCVI meow");
}
