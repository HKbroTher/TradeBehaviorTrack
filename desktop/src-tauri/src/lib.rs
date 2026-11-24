use rusqlite::{Connection, params};
use std::path::PathBuf;
use std::sync::Mutex;
use tauri::menu::{Menu, MenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::{Manager, State, WindowEvent};

#[derive(Default)]
struct PrivacyState(Mutex<bool>);

#[tauri::command]
fn get_consent(state: State<'_, PrivacyState>) -> bool {
    *state.0.lock().expect("privacy state lock")
}

#[tauri::command]
fn set_consent(enabled: bool, state: State<'_, PrivacyState>) -> Result<bool, String> {
    if !enabled {
        stop_monitoring()?;
    }
    *state.0.lock().expect("privacy state lock") = enabled;
    Ok(enabled)
}

fn data_path() -> Result<PathBuf, String> {
    let root = std::env::var_os("LOCALAPPDATA").ok_or("LOCALAPPDATA is unavailable")?;
    Ok(PathBuf::from(root)
        .join("BehavioralGuard")
        .join("behavior.sqlite3"))
}

fn stop_monitoring() -> Result<(), String> {
    let path = data_path()?.with_file_name("stop-monitoring");
    std::fs::create_dir_all(path.parent().ok_or("Missing data directory")?)
        .map_err(|e| e.to_string())?;
    std::fs::write(path, b"stop").map_err(|e| e.to_string())
}

#[tauri::command]
fn pause_monitoring(state: State<'_, PrivacyState>) -> Result<(), String> {
    stop_monitoring()?;
    *state.0.lock().expect("privacy state lock") = false;
    Ok(())
}

#[tauri::command]
fn dashboard() -> Result<serde_json::Value, String> {
    let path = data_path()?;
    if !path.exists() {
        return Ok(
            serde_json::json!({"windows": 0, "days": 0, "latest_score": null, "alerts": []}),
        );
    }
    let connection = Connection::open(path).map_err(|e| e.to_string())?;
    let windows: i64 = connection
        .query_row("SELECT COUNT(*) FROM windows", [], |row| row.get(0))
        .map_err(|e| e.to_string())?;
    let days: i64 = connection.query_row("SELECT COUNT(DISTINCT SUBSTR(observed_at, 1, 10)) FROM windows WHERE baseline_eligible = 1", [], |row| row.get(0)).map_err(|e| e.to_string())?;
    let latest_score: Option<i64> = connection
        .query_row(
            "SELECT score FROM alerts ORDER BY id DESC LIMIT 1",
            [],
            |row| row.get(0),
        )
        .ok();
    let mut statement = connection.prepare("SELECT a.id, w.observed_at, a.score, a.reasons_json, a.feedback FROM alerts a JOIN windows w ON w.id = a.window_id ORDER BY a.id DESC LIMIT 20").map_err(|e| e.to_string())?;
    let rows = statement.query_map([], |row| {
    let reasons: String = row.get(3)?;
    Ok(serde_json::json!({"id": row.get::<_, i64>(0)?, "at": row.get::<_, String>(1)?, "score": row.get::<_, i64>(2)?, "reasons": serde_json::from_str::<serde_json::Value>(&reasons).unwrap_or_default(), "feedback": row.get::<_, Option<String>>(4)?}))
  }).map_err(|e| e.to_string())?;
    let alerts = rows
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;
    Ok(
        serde_json::json!({"windows": windows, "days": days, "latest_score": latest_score, "alerts": alerts}),
    )
}

#[tauri::command]
fn set_feedback(alert_id: i64, choice: String) -> Result<(), String> {
    if ![
        "ignore",
        "normal",
        "fatigue_or_emotion",
        "device_or_environment",
    ]
    .contains(&choice.as_str())
    {
        return Err("Unknown feedback".into());
    }
    let connection = Connection::open(data_path()?).map_err(|e| e.to_string())?;
    let changed = connection
        .execute(
            "UPDATE alerts SET feedback = ?1 WHERE id = ?2",
            params![choice, alert_id],
        )
        .map_err(|e| e.to_string())?;
    if changed == 0 {
        return Err("Unknown alert".into());
    }
    Ok(())
}

#[tauri::command]
fn delete_personal_data() -> Result<(), String> {
    let path = data_path()?;
    stop_monitoring()?;
    std::thread::sleep(std::time::Duration::from_millis(250));
    if !path.exists() {
        return Ok(());
    }
    let mut connection = Connection::open(path).map_err(|e| e.to_string())?;
    let transaction = connection.transaction().map_err(|e| e.to_string())?;
    transaction
        .execute("DELETE FROM alerts", [])
        .map_err(|e| e.to_string())?;
    transaction
        .execute("DELETE FROM windows", [])
        .map_err(|e| e.to_string())?;
    transaction.commit().map_err(|e| e.to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(PrivacyState::default())
        .invoke_handler(tauri::generate_handler![
            get_consent,
            set_consent,
            pause_monitoring,
            dashboard,
            set_feedback,
            delete_personal_data
        ])
        .setup(|app| {
            let show = MenuItem::with_id(app, "show", "打开 Behavioral Guard", true, None::<&str>)?;
            let pause = MenuItem::with_id(app, "pause", "暂停监测", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "退出", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show, &pause, &quit])?;
            TrayIconBuilder::new()
                .icon(app.default_window_icon().expect("window icon").clone())
                .menu(&menu)
                .on_menu_event(|app, event| match event.id().as_ref() {
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "quit" => {
                        let _ = stop_monitoring();
                        app.exit(0);
                    }
                    "pause" => {
                        let _ = stop_monitoring();
                        *app.state::<PrivacyState>()
                            .0
                            .lock()
                            .expect("privacy state lock") = false;
                    }
                    _ => {}
                })
                .build(app)?;
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while building tauri application");
}
