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
fn set_consent(enabled: bool, state: State<'_, PrivacyState>) -> bool {
  *state.0.lock().expect("privacy state lock") = enabled;
  enabled
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .manage(PrivacyState::default())
    .invoke_handler(tauri::generate_handler![get_consent, set_consent])
    .setup(|app| {
      let show = MenuItem::with_id(app, "show", "打开 Behavioral Guard", true, None::<&str>)?;
      let quit = MenuItem::with_id(app, "quit", "退出", true, None::<&str>)?;
      let menu = Menu::with_items(app, &[&show, &quit])?;
      TrayIconBuilder::new()
        .icon(app.default_window_icon().expect("window icon").clone())
        .menu(&menu)
        .on_menu_event(|app, event| match event.id().as_ref() {
          "show" => {
            if let Some(window) = app.get_webview_window("main") { let _ = window.show(); let _ = window.set_focus(); }
          }
          "quit" => app.exit(0),
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
