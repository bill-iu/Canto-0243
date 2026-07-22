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
/// Windows: PyApp under payload `runtime/`. macOS ADR-0070: inside `.app` Resources.
const INNER_SUBDIR: &str = "runtime";
const INNER_WIN: &str = "Canto-0243-runtime.exe";
const INNER_UNIX: &str = "Canto-0243-runtime";
const MAC_APP_NAME: &str = "Canto-0243.app";

#[derive(Debug)]
enum UserEvent {
    Stage(u8),
    /// Stage-mapped bar → 100% (ADR-0068 §12); brief hold before Ready.
    Complete,
    Failed(String),
    Ready,
}

/// `…/Canto-0243.app/Contents/MacOS/<exe>` → `Canto-0243.app` directory.
fn macos_app_bundle(exe: &Path) -> Option<PathBuf> {
    let macos_dir = exe.parent()?;
    if macos_dir.file_name()?.to_str()? != "MacOS" {
        return None;
    }
    let contents = macos_dir.parent()?;
    if contents.file_name()?.to_str()? != "Contents" {
        return None;
    }
    let app = contents.parent()?;
    let name = app.file_name()?.to_str()?;
    if !name.ends_with(".app") {
        return None;
    }
    Some(app.to_path_buf())
}

/// Gatekeeper App Translocation copies only the `.app`; sidecars stay at the original folder.
/// Recover that original bundle path via Security.framework when present.
#[cfg(target_os = "macos")]
fn macos_original_app_path(app: &Path) -> Option<PathBuf> {
    use std::ffi::CString;
    use std::os::raw::{c_char, c_int, c_void};
    use std::ptr;

    #[link(name = "CoreFoundation", kind = "framework")]
    extern "C" {
        fn CFStringCreateWithCString(
            alloc: *const c_void,
            c_str: *const c_char,
            encoding: u32,
        ) -> *const c_void;
        fn CFURLCreateWithFileSystemPath(
            allocator: *const c_void,
            file_path: *const c_void,
            path_style: c_int,
            is_directory: u8,
        ) -> *const c_void;
        fn CFURLGetFileSystemRepresentation(
            url: *const c_void,
            resolve_against_base: u8,
            buffer: *mut u8,
            max_buf_len: isize,
        ) -> u8;
        fn CFRelease(cf: *const c_void);
    }

    #[link(name = "Security", kind = "framework")]
    extern "C" {
        fn SecTranslocateCreateOriginalPathForURL(
            path: *const c_void,
            error: *mut *const c_void,
        ) -> *const c_void;
    }

    const K_CF_STRING_ENCODING_UTF8: u32 = 0x0800_0100;
    let path_str = app.to_str()?;
    let c_path = CString::new(path_str).ok()?;
    unsafe {
        let cf_str =
            CFStringCreateWithCString(ptr::null(), c_path.as_ptr(), K_CF_STRING_ENCODING_UTF8);
        if cf_str.is_null() {
            return None;
        }
        // kCFURLPOSIXPathStyle = 0; .app is a directory bundle
        let url = CFURLCreateWithFileSystemPath(ptr::null(), cf_str, 0, 1);
        CFRelease(cf_str);
        if url.is_null() {
            return None;
        }
        let mut err: *const c_void = ptr::null();
        let orig = SecTranslocateCreateOriginalPathForURL(url, &mut err);
        CFRelease(url);
        if orig.is_null() {
            return None;
        }
        let mut buf = [0u8; 4096];
        let ok = CFURLGetFileSystemRepresentation(orig, 1, buf.as_mut_ptr(), buf.len() as isize);
        CFRelease(orig);
        if ok == 0 {
            return None;
        }
        let len = buf.iter().position(|&b| b == 0).unwrap_or(buf.len());
        let s = std::str::from_utf8(&buf[..len]).ok()?;
        if s.is_empty() {
            return None;
        }
        Some(PathBuf::from(s))
    }
}

fn payload_has_sidecars(dir: &Path) -> bool {
    dir.join("lyrics.db").is_file()
}

fn payload_root() -> PathBuf {
    if let Ok(p) = std::env::var("CANTO_PAYLOAD_ROOT") {
        let t = p.trim();
        if !t.is_empty() {
            return PathBuf::from(t);
        }
    }
    let exe = std::env::current_exe().ok();
    // ADR-0070: payload = directory containing .app + lyrics.db (parent of bundle).
    // When Gatekeeper App Translocation is active, prefer the pre-translocation parent
    // so lyrics.db / client/ next to the real extract folder stay visible.
    if let Some(ref e) = exe {
        if let Some(app) = macos_app_bundle(e) {
            let mut candidates: Vec<PathBuf> = Vec::new();
            #[cfg(target_os = "macos")]
            if let Some(orig) = macos_original_app_path(&app) {
                if orig != app {
                    candidates.push(orig);
                }
            }
            candidates.push(app);
            for bundle in &candidates {
                if let Some(parent) = bundle.parent() {
                    if payload_has_sidecars(parent) {
                        return parent.to_path_buf();
                    }
                }
            }
            // Fall back to first parent (fail-fast later if no lyrics.db).
            if let Some(parent) = candidates[0].parent() {
                return parent.to_path_buf();
            }
        }
    }
    exe.and_then(|p| p.parent().map(|d| d.to_path_buf()))
        .unwrap_or_else(|| std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")))
}

fn inner_binary(root: &Path) -> PathBuf {
    if cfg!(windows) {
        return root.join(INNER_SUBDIR).join(INNER_WIN);
    }
    // Prefer ADR-0070 layout: Canto-0243.app/Contents/Resources/runtime/…
    let in_app = root
        .join(MAC_APP_NAME)
        .join("Contents")
        .join("Resources")
        .join(INNER_SUBDIR)
        .join(INNER_UNIX);
    if in_app.is_file() {
        return in_app;
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(app) = macos_app_bundle(&exe) {
            let nested = app
                .join("Contents")
                .join("Resources")
                .join(INNER_SUBDIR)
                .join(INNER_UNIX);
            if nested.is_file() {
                return nested;
            }
        }
    }
    // Legacy folder layout (pre-0070): payload/runtime/Canto-0243-runtime
    root.join(INNER_SUBDIR).join(INNER_UNIX)
}

/// G1: clear quarantine on payload + .app before first spawn of runtime.
fn clear_download_quarantine(root: &Path) {
    #[cfg(target_os = "macos")]
    {
        let _ = Command::new("xattr")
            .args(["-cr"])
            .arg(root)
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status();
        let app = root.join(MAC_APP_NAME);
        if app.is_dir() {
            let _ = Command::new("xattr")
                .args(["-cr"])
                .arg(&app)
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .status();
        }
    }
    let _ = root;
}

/// PyApp install roots under the OS data-local base.
///
/// Observed layouts (PyApp versions differ):
/// - Windows (current): `%LOCALAPPDATA%/pyapp/data/canto-0243/<dist>/<ver>/`
/// - Some builds / macOS notes: `…/pyapp/canto-0243/<dist>/<ver>/` (no `data/`)
/// Check **both**; a mac-only strip of `data/` made Windows never see “env ready”
/// after a successful first install (child exit 0 → splash fail after 90s).
fn pyapp_project_candidates(base: &Path) -> [PathBuf; 2] {
    [
        base.join("pyapp").join("data").join(PROJECT),
        base.join("pyapp").join(PROJECT),
    ]
}

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
    for project in pyapp_project_candidates(&base) {
        // Only under project installs — do not walk pyapp/cache (distribution
        // trees can look like a ready env and skip real install).
        if project.is_dir() && walk_ready(&project, 0) {
            return true;
        }
    }
    false
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
    clear_download_quarantine(root);
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
                "找不到執行核心（{}）。\n請重新下載並完整解壓 Desktop 套件（{} 須與側車同層）。\n\nMissing runtime binary.",
                inner.display(),
                if cfg!(windows) {
                    "Canto-0243.exe"
                } else {
                    "Canto-0243.app"
                }
            ),
        );
        std::process::exit(1);
    }

    // Sidecars (lyrics.db, client/) must sit next to the launcher — not only inside .app.
    // Common failure: App Translocation or moving only the .app out of the extract folder.
    if !payload_has_sidecars(&root) {
        let hint = if cfg!(windows) {
            "找不到 lyrics.db（詞庫側車）。\n\n\
請完整解壓 Desktop zip，並從解壓後資料夾內雙擊 Canto-0243.exe（唔好只複製 .exe）。\n\
側車須同層：lyrics.db、client/、runtime/。\n\n\
Missing lyrics.db next to the launcher — keep the full extract folder together."
        } else {
            "找不到 lyrics.db（詞庫側車）。\n\n\
請確認已完整解壓 Desktop 套件，並用 Finder 把成個資料夾移去「文件」或「桌面」後再打開 Canto-0243.app（唔好只拖 .app）。\n\
或喺終端對套件資料夾執行：xattr -cr \"套件路徑\" 再雙擊。\n\n\
Missing lyrics.db next to the app — keep the full extract folder together."
        };
        show_fatal("Canto-0243", hint);
        std::process::exit(1);
    }

    // Clear quarantine on the real payload early so the next Finder launch is not translocated.
    clear_download_quarantine(&root);

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
        let mut respawned_after_install = false;
        let _ = proxy_t.send_event(UserEvent::Stage(1));

        loop {
            if done_t.load(Ordering::SeqCst) {
                return;
            }

            // Heuristic stages while PyApp bootstraps (no public byte % API).
            // Splash maps stage → estimated % only (ADR-0068 §12); no in-band crawl.
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
            if next > stage {
                stage = next;
                let _ = proxy_t.send_event(UserEvent::Stage(stage));
            }

            if product_http_ready() {
                if stage < 4 {
                    let _ = proxy_t.send_event(UserEvent::Stage(4));
                    thread::sleep(Duration::from_millis(200));
                }
                let _ = proxy_t.send_event(UserEvent::Complete);
                thread::sleep(Duration::from_millis(350));
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
                        // PyApp may exit 0 after install; product may need a second spawn.
                    }
                    Ok(None) => {}
                    Err(e) => {
                        let _ = proxy_t.send_event(UserEvent::Failed(format!("監控啟動失敗：{e}")));
                        return;
                    }
                }
            }

            if let Some(status) = child_exited {
                // Install finished (exit 0) but HTTP not up — re-launch once with env ready.
                if status.success()
                    && pyapp_install_ready()
                    && !product_http_ready()
                    && !respawned_after_install
                {
                    match spawn_inner(&root_t, &inner_t) {
                        Ok(c) => {
                            child = c;
                            child_exited = None;
                            respawned_after_install = true;
                            if stage < 4 {
                                stage = 4;
                                let _ = proxy_t.send_event(UserEvent::Stage(4));
                            }
                            continue;
                        }
                        Err(e) => {
                            let _ = proxy_t.send_event(UserEvent::Failed(format!(
                                "執行環境已就緒但無法重啟產品：{e}"
                            )));
                            return;
                        }
                    }
                }

                // Fail fast: signal kill / non-zero exit means bootstrap died.
                // Still allow a short grace if PyApp exits 0 after handoff (rare).
                let bad = !status.success();
                let grace_done = start.elapsed() > Duration::from_secs(if bad { 3 } else { 90 });
                if grace_done && !product_http_ready() && !pyapp_install_ready() {
                    let _ = proxy_t.send_event(UserEvent::Failed(format!(
                        "啟動未完成（結束代碼 {status}）。\n請確認網路後重試；仍失敗則再雙擊 Canto-0243.app／Canto-0243.exe。"
                    )));
                    return;
                }
                // Install finished but product not up yet — keep waiting until hard timeout.
                if grace_done && !product_http_ready() && pyapp_install_ready() && bad {
                    let _ = proxy_t.send_event(UserEvent::Failed(format!(
                        "執行環境已安裝但服務未就緒（結束代碼 {status}）。\n請再雙擊啟動一次。"
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
            Event::UserEvent(UserEvent::Complete) => {
                let _ = webview
                    .evaluate_script("window.setSplashComplete && window.setSplashComplete()");
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
    #[cfg(target_os = "macos")]
    {
        // Finder double-click has no terminal — use a system alert.
        let escape = |s: &str| s.replace('\\', "\\\\").replace('"', "\\\"");
        let script = format!(
            "display dialog \"{}\" with title \"{}\" buttons {{\"好\"}} default button 1 with icon stop",
            escape(text),
            escape(title)
        );
        let _ = Command::new("osascript")
            .args(["-e", &script])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status();
        eprintln!("{title}: {text}");
        return;
    }
    #[cfg(all(not(windows), not(target_os = "macos")))]
    {
        eprintln!("{title}: {text}");
    }
}
