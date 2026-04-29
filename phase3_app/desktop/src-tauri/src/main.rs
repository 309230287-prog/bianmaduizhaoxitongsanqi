// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    env,
    io,
    net::{SocketAddr, TcpStream},
    path::{Path, PathBuf},
    process::{Child, Command},
    sync::Mutex,
    thread,
    time::{Duration, Instant},
};

use tauri::Manager;

struct BackendProcess(Mutex<Option<Child>>);

impl Drop for BackendProcess {
    fn drop(&mut self) {
        if let Ok(mut child) = self.0.lock() {
            if let Some(process) = child.as_mut() {
                let _ = process.kill();
            }
        }
    }
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let backend_process = match start_backend_if_needed() {
                Ok(process) => process,
                Err(error) => {
                    eprintln!("failed to start local backend: {error}");
                    None
                }
            };
            app.manage(BackendProcess(Mutex::new(backend_process)));
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn start_backend_if_needed() -> io::Result<Option<Child>> {
    if wait_for_backend(Duration::from_millis(300)) {
        return Ok(None);
    }

    let backend_dir = find_backend_dir().ok_or_else(|| {
        io::Error::new(
            io::ErrorKind::NotFound,
            "could not locate phase3 backend directory",
        )
    })?;
    let backend_src = backend_dir.join("src");
    let python = env::var("PHASE3_PYTHON").unwrap_or_else(|_| "python".to_string());

    let mut command = Command::new(python);
    command
        .current_dir(&backend_dir)
        .env("PYTHONPATH", backend_src)
        .args([
            "-m",
            "uvicorn",
            "product_code_mapper.api.app:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ]);

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        command.creation_flags(CREATE_NO_WINDOW);
    }

    let child = command.spawn()?;
    let _ = wait_for_backend(Duration::from_secs(20));
    Ok(Some(child))
}

fn find_backend_dir() -> Option<PathBuf> {
    let mut roots = Vec::new();

    if let Ok(exe_path) = env::current_exe() {
        if let Some(parent) = exe_path.parent() {
            roots.extend(parent.ancestors().map(Path::to_path_buf));
        }
    }

    if let Ok(current_dir) = env::current_dir() {
        roots.extend(current_dir.ancestors().map(Path::to_path_buf));
    }

    for root in roots {
        for candidate in [root.join("phase3_app").join("backend"), root.join("backend")] {
            if candidate
                .join("src")
                .join("product_code_mapper")
                .join("api")
                .join("app.py")
                .exists()
            {
                return Some(candidate);
            }
        }
    }

    None
}

fn wait_for_backend(timeout: Duration) -> bool {
    let deadline = Instant::now() + timeout;
    let address = SocketAddr::from(([127, 0, 0, 1], 8000));

    loop {
        if TcpStream::connect_timeout(&address, Duration::from_millis(200)).is_ok() {
            return true;
        }
        if Instant::now() >= deadline {
            return false;
        }
        thread::sleep(Duration::from_millis(250));
    }
}
