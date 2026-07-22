fn main() {
    if std::env::var("CARGO_CFG_TARGET_OS").unwrap_or_default() == "windows" {
        let mut res = winresource::WindowsResource::new();
        // SSOT: generated from client/public/icon-512.png (PWA brand)
        res.set_icon("assets/app.ico");
        res.compile().expect("embed Windows app.ico");
    }
}
