//! Desktop install progress shell (ADR-0068 §12).
//! Outer launcher: branded splash while PyApp bootstraps; skip when env ready.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::{Duration, Instant};

use tao::event::{Event, StartCause, WindowEvent};
use tao::event_loop::{ControlFlow, EventLoopBuilder};
use tao::window::WindowBuilder;
use wry::WebViewBuilder;

const PROJECT: &str = "canto-0243";
/// Inner PyApp lives under payload subdir (not next to outer shell at package root).
const INNER_SUBDIR: &str = "runtime";
const INNER_WIN: &str = "Canto-0243-runtime.exe";
const INNER_UNIX: &str = "Canto-0243-runtime";

#[derive(Debug)]
enum UserEvent {
    Stage(u8),
    Failed(String),
    Ready,
}

fn payload_root() -> PathBuf {
    if let Ok(p) = std::env::var("CANTO_PAYLOAD_ROOT") {
        let t = p.trim();
        if !t.is_empty() {
            return PathBuf::from(t);
        }
    }
    std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|d| d.to_path_buf()))
        .unwrap_or_else(|| std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")))
}

fn inner_binary(root: &Path) -> PathBuf {
    let dir = root.join(INNER_SUBDIR);
    if cfg!(windows) {
        dir.join(INNER_WIN)
    } else {
        dir.join(INNER_UNIX)
    }
}

/// PyApp data layout: %LOCALAPPDATA%/pyapp/data/canto-0243/<dist>/<ver>/
fn pyapp_install_ready() -> bool {
    if let Ok(custom) = std::env::var(format!(
        "PYAPP_INSTALL_DIR_{}",
        PROJECT.to_uppercase().replace('-', "_")
    )) {
        if install_dir_looks_ready(Path::new(&custom)) {
            return true;
        }
    }
    let base = if cfg!(windows) {
        std::env::var_os("LOCALAPPDATA").map(PathBuf::from)
    } else if cfg!(target_os = "macos") {
        dirs_home().map(|h| h.join("Library/Application Support"))
    } else {
        std::env::var_os("XDG_DATA_HOME")
            .map(PathBuf::from)
            .or_else(|| dirs_home().map(|h| h.join(".local/share")))
    };
    let Some(base) = base else {
        return false;
    };
    let project = base.join("pyapp").join("data").join(PROJECT);
    if !project.is_dir() {
        return false;
    }
    walk_ready(&project, 0)
}

fn dirs_home() -> Option<PathBuf> {
    std::env::var_os("HOME").map(PathBuf::from)
}

fn walk_ready(dir: &Path, depth: u8) -> bool {
    if depth > 4 {
        return false;
    }
    if install_dir_looks_ready(dir) {
        return true;
    }
    let Ok(rd) = std::fs::read_dir(dir) else {
        return false;
    };
    for ent in rd.flatten() {
        let p = ent.path();
        if p.is_dir() && walk_ready(&p, depth + 1) {
            return true;
        }
    }
    false
}

fn install_dir_looks_ready(dir: &Path) -> bool {
    let candidates = [
        dir.join("Scripts").join("python.exe"),
        dir.join("Scripts").join("pythonw.exe"),
        dir.join("bin").join("python3"),
        dir.join("bin").join("python"),
        dir.join("python.exe"),
    ];
    candidates.iter().any(|p| p.is_file())
}

fn spawn_inner(root: &Path, inner: &Path) -> std::io::Result<std::process::Child> {
    let mut cmd = Command::new(inner);
    cmd.current_dir(root)
        .env("CANTO_PAYLOAD_ROOT", root)
        .env("PORTABLE", "1")
        .env("ENV", "local")
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        // Keep console for first-run diagnostics? Shell is GUI; pyapp may AllocConsole.
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
    cmd.spawn()
}

fn product_http_ready() -> bool {
    // Best-effort: try connecting to default product port.
    use std::net::TcpStream;
    let host = std::env::var("HOST").unwrap_or_else(|_| "127.0.0.1".into());
    let port = std::env::var("PORT").unwrap_or_else(|_| "8000".into());
    let addr = format!("{host}:{port}");
    TcpStream::connect_timeout(
        &addr.parse().unwrap_or_else(|_| "127.0.0.1:8000".parse().unwrap()),
        Duration::from_millis(250),
    )
    .is_ok()
}

fn main() {
    let root = payload_root();
    let inner = inner_binary(&root);

    if !inner.is_file() {
        show_fatal(
            "Canto-0243",
            &format!(
                "找不到執行核心（{}）。\n請重新下載完整 Desktop 套件。\n\nMissing {} next to the launcher.",
                inner.display(),
                if cfg!(windows) { INNER_WIN } else { INNER_UNIX }
            ),
        );
        std::process::exit(1);
    }

    // Fast path: PyApp env already present → no splash.
    if pyapp_install_ready() {
        match spawn_inner(&root, &inner) {
            Ok(child) => {
                // Detach: do not wait; product outlives shell.
                std::mem::forget(child);
            }
            Err(e) => {
                show_fatal("Canto-0243", &format!("無法啟動：{e}"));
                std::process::exit(1);
            }
        }
        return;
    }

    run_splash_and_bootstrap(root, inner);
}

fn run_splash_and_bootstrap(root: PathBuf, inner: PathBuf) {
    let event_loop = EventLoopBuilder::<UserEvent>::with_user_event().build();
    let proxy = event_loop.create_proxy();

    let window = WindowBuilder::new()
        .with_title("Canto-0243")
        .with_inner_size(tao::dpi::LogicalSize::new(440.0, 320.0))
        .with_resizable(false)
        .build(&event_loop)
        .expect("window");

    let html = include_str!("../assets/splash.html");
    let webview = WebViewBuilder::new()
        .with_html(html)
        .build(&window)
        .expect("webview");

    let _ = webview.evaluate_script("window.setSplashStage && window.setSplashStage(0)");

    let done = Arc::new(AtomicBool::new(false));
    let done_t = Arc::clone(&done);
    let proxy_t = proxy.clone();
    let root_t = root.clone();
    let inner_t = inner.clone();

    thread::spawn(move || {
        let _ = proxy_t.send_event(UserEvent::Stage(0));
        thread::sleep(Duration::from_millis(400));

        let mut child = match spawn_inner(&root_t, &inner_t) {
            Ok(c) => c,
            Err(e) => {
                let _ = proxy_t.send_event(UserEvent::Failed(format!("無法啟動執行核心：{e}")));
                return;
            }
        };

        let start = Instant::now();
        let mut stage: u8 = 1;
        let mut child_exited: Option<std::process::ExitStatus> = None;
        let _ = proxy_t.send_event(UserEvent::Stage(1));

        loop {
            if done_t.load(Ordering::SeqCst) {
                return;
            }

            // Heuristic stages while PyApp bootstraps (no public % API).
            let elapsed = start.elapsed().as_secs();
            let next = if elapsed < 4 {
                1
            } else if elapsed < 25 {
                2
            } else if elapsed < 55 {
                3
            } else {
                4
            };
            if next != stage {
                stage = next;
                let _ = proxy_t.send_event(UserEvent::Stage(stage));
            }

            if product_http_ready() {
                let _ = proxy_t.send_event(UserEvent::Stage(4));
                thread::sleep(Duration::from_millis(500));
                let _ = proxy_t.send_event(UserEvent::Ready);
                // Leave child running if still alive.
                let _ = child.try_wait();
                std::mem::forget(child);
                return;
            }

            if pyapp_install_ready() && stage < 4 {
                let _ = proxy_t.send_event(UserEvent::Stage(4));
                stage = 4;
            }

            if child_exited.is_none() {
                match child.try_wait() {
                    Ok(Some(status)) => {
                        child_exited = Some(status);
                        // PyApp GUI may exit after handing off — wait for product port.
                    }
                    Ok(None) => {}
                    Err(e) => {
                        let _ = proxy_t.send_event(UserEvent::Failed(format!("監控啟動失敗：{e}")));
                        return;
                    }
                }
            }

            if let Some(status) = child_exited {
                // Fail fast: signal kill / non-zero exit means bootstrap died.
                // Still allow a short grace if PyApp exits 0 after handoff (rare).
                let bad = !status.success();
                let grace_done = start.elapsed() > Duration::from_secs(if bad { 3 } else { 90 });
                if grace_done && !product_http_ready() && !pyapp_install_ready() {
                    let _ = proxy_t.send_event(UserEvent::Failed(format!(
                        "啟動未完成（結束代碼 {status}）。\n請確認網路後重試，或執行 runtime/Canto-0243-runtime 查看詳情。"
                    )));
                    return;
                }
                // Install finished but product not up yet — keep waiting until hard timeout.
                if grace_done && !product_http_ready() && pyapp_install_ready() && bad {
                    let _ = proxy_t.send_event(UserEvent::Failed(format!(
                        "執行環境已安裝但服務未就緒（結束代碼 {status}）。\n請再雙擊啟動一次；仍失敗則執行 runtime/Canto-0243-runtime。"
                    )));
                    return;
                }
            }

            if start.elapsed() > Duration::from_secs(480) {
                let _ = proxy_t.send_event(UserEvent::Failed(
                    "準備逾時。請檢查網路後重試，或刪除後重新下載完整套件。".into(),
                ));
                return;
            }

            thread::sleep(Duration::from_millis(500));
        }
    });

    event_loop.run(move |event, _, control_flow| {
        *control_flow = ControlFlow::Wait;
        match event {
            Event::NewEvents(StartCause::Init) => {}
            Event::UserEvent(UserEvent::Stage(i)) => {
                let _ = webview.evaluate_script(&format!(
                    "window.setSplashStage && window.setSplashStage({i})"
                ));
            }
            Event::UserEvent(UserEvent::Failed(msg)) => {
                done.store(true, Ordering::SeqCst);
                let escaped = msg.replace('\\', "\\\\").replace('\'', "\\'").replace('\n', "\\n");
                let _ = webview.evaluate_script(&format!(
                    "window.setSplashError && window.setSplashError('{escaped}')"
                ));
            }
            Event::UserEvent(UserEvent::Ready) => {
                done.store(true, Ordering::SeqCst);
                *control_flow = ControlFlow::Exit;
            }
            Event::WindowEvent {
                event: WindowEvent::CloseRequested,
                ..
            } => {
                done.store(true, Ordering::SeqCst);
                *control_flow = ControlFlow::Exit;
            }
            _ => {}
        }
    });
}

fn show_fatal(title: &str, text: &str) {
    #[cfg(windows)]
    {
        use std::os::windows::ffi::OsStrExt;
        fn wide(s: &str) -> Vec<u16> {
            std::ffi::OsStr::new(s)
                .encode_wide()
                .chain(std::iter::once(0))
                .collect()
        }
        #[link(name = "user32")]
        extern "system" {
            fn MessageBoxW(
                h_wnd: *mut core::ffi::c_void,
                lp_text: *const u16,
                lp_caption: *const u16,
                u_type: u32,
            ) -> i32;
        }
        let t = wide(text);
        let c = wide(title);
        unsafe {
            MessageBoxW(std::ptr::null_mut(), t.as_ptr(), c.as_ptr(), 0x10);
        }
        return;
    }
    #[cfg(not(windows))]
    {
        eprintln!("{title}: {text}");
    }
}
