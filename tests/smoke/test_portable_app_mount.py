"""Smoke: portable product UI mount at /app (CANTO_APP_UI / dist-portable)."""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from main import inject_app_index_meta, require_app_ui_dir, resolve_favicon


class PortableAppMountTests(unittest.TestCase):
    def test_workbench_index_routes_are_registered_before_static_mount(self):
        from main import app

        paths = [getattr(route, "path", None) for route in app.routes]
        self.assertIn("/app/workbench/", paths)
        self.assertLess(paths.index("/app/workbench/"), paths.index("/app"))

    def test_require_app_ui_dir_missing_raises_clear_error(self):
        missing = Path("definitely-missing-canto-app-ui-dir")
        with self.assertRaises(RuntimeError) as ctx:
            require_app_ui_dir(missing)
        msg = str(ctx.exception)
        self.assertIn("build:portable", msg)
        self.assertIn("Portable UI not found", msg)

    def test_require_app_ui_dir_ok_with_temp_index(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            ui = Path(tmp)
            (ui / "index.html").write_text("<!doctype html><html><head></head></html>", encoding="utf-8")
            self.assertEqual(require_app_ui_dir(ui), ui)

    def test_require_app_ui_dir_respects_env(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            ui = Path(tmp)
            (ui / "index.html").write_text("<html><head></head></html>", encoding="utf-8")
            with patch.dict(os.environ, {"CANTO_APP_UI": str(ui)}):
                self.assertEqual(require_app_ui_dir(), ui)

    def test_inject_meta_lexicon_and_portable(self):
        html = "<html><head>\n<title>t</title></head></html>"
        with patch("main.lexicon_version", return_value="test-ver"):
            out = inject_app_index_meta(html, portable=True)
        self.assertIn('name="canto-lexicon-version" content="test-ver"', out)
        self.assertIn('name="canto-portable" content="1"', out)

    def test_inject_meta_skips_portable_when_not_set(self):
        html = "<html><head></head></html>"
        with patch("main.lexicon_version", return_value="v"):
            out = inject_app_index_meta(html, portable=False)
        self.assertIn("canto-lexicon-version", out)
        self.assertNotIn("canto-portable", out)

    def test_app_index_route_with_fixture_dir(self):
        """TestClient GET /app/index.html when CANTO_APP_UI points at a minimal fixture.

        Smoke/tests that need the live /app route must either build portable
        (client/dist-portable) or set CANTO_APP_UI to a fixture dir before
        process start. Here we call the route handler directly to avoid
        lifespan DB preload.
        """
        import tempfile

        from main import serve_app_index

        with tempfile.TemporaryDirectory() as tmp:
            ui = Path(tmp)
            (ui / "index.html").write_text(
                "<!doctype html><html><head><title>fixture</title></head></html>",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"CANTO_APP_UI": str(ui), "PORTABLE": "1"}):
                with patch("main.lexicon_version", return_value="fixture-ver"):
                    # Avoid TestClient lifespan (DB preload); call handler directly.
                    import asyncio

                    resp = asyncio.run(serve_app_index())
            self.assertEqual(resp.status_code, 200)
            body = resp.body.decode("utf-8")
            self.assertIn("fixture-ver", body)
            self.assertIn("canto-portable", body)
            self.assertIn("fixture", body)

    def test_resolve_favicon_prefers_app_ui_dir(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            ui = Path(tmp)
            fav = ui / "favicon.ico"
            fav.write_bytes(b"ico")
            self.assertEqual(resolve_favicon(ui), fav)

    def test_resolve_favicon_falls_back_to_icon_32(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            ui = Path(tmp)
            icon = ui / "icon-32.png"
            icon.write_bytes(b"png")
            self.assertEqual(resolve_favicon(ui), icon)

    def test_resolve_favicon_none_when_missing(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            ui = Path(tmp)
            with patch("main.SHARED_DIR", Path("definitely-missing-shared-dir")):
                self.assertIsNone(resolve_favicon(ui))

    def test_root_favicon_404_when_no_asset(self):
        import asyncio
        import tempfile

        from main import root_favicon

        with tempfile.TemporaryDirectory() as tmp:
            ui = Path(tmp)
            with patch("main.SHARED_DIR", Path("definitely-missing-shared-dir")):
                with patch("main.APP_UI_DIR", ui):
                    with self.assertRaises(Exception) as ctx:
                        asyncio.run(root_favicon())
                    self.assertEqual(getattr(ctx.exception, "status_code", None), 404)


if __name__ == "__main__":
    unittest.main()
