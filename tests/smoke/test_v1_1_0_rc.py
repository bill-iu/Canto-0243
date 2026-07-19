"""Public seams for the one-off v1.1.0 local release candidate."""
from __future__ import annotations

import json
import hashlib
import http.server
import sqlite3
import subprocess
import sys
import tempfile
import tarfile
import threading
import unittest
import zipfile
import shutil
from functools import partial
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "v1_1_0_rc.py"
POWERSHELL = ROOT / "scripts" / "v1_1_0_rc.ps1"
PAGES_WORKFLOW = ROOT / ".github" / "workflows" / "pages-v1.1.0.yml"
EXPECTED_ARTIFACTS = (
    "lyrics.db",
    "dist/words-lexicon.json",
    "dist/canto-0243-portable.zip",
    "dist/portable-manifest-windows.json",
    "dist/canto-0243-pages-v1.1.0.tar.gz",
    "dist/v1.1.0-SHA256SUMS.txt",
)
EXPECTED_CHECKS = (
    "build-db",
    "project-pos",
    "rc-contract",
    "pos-self-checks",
    "portable-host-build",
    "pwa-build",
    "pages-package",
    "windows-portable",
    "relocated-portable-smoke",
)
COMMIT = "1" * 40


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def passed_check_args() -> tuple[str, ...]:
    return tuple(part for name in EXPECTED_CHECKS for part in ("--passed-check", name))


def seed_artifacts(root: Path) -> None:
    for index, relative in enumerate(EXPECTED_ARTIFACTS, 1):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"artifact-{index}\n".encode())
    db_sha = hashlib.sha256((root / "lyrics.db").read_bytes()).hexdigest()
    (root / "dist" / "portable-manifest-windows.json").write_text(
        json.dumps(
            {
                "tag": "v1.1.0",
                "platform": "windows",
                "lyrics_sha256": db_sha,
                "package_digest": "2" * 64,
            }
        ),
        encoding="utf-8",
    )
    zip_path = root / "dist" / "canto-0243-portable.zip"
    sidecar_bytes = (root / "dist" / "portable-manifest-windows.json").read_bytes()
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("lyrics.db", (root / "lyrics.db").read_bytes())
        archive.writestr("portable-manifest.json", sidecar_bytes)
    checksum_lines = []
    for relative in EXPECTED_ARTIFACTS[:-1]:
        checksum_lines.append(f"{hashlib.sha256((root / relative).read_bytes()).hexdigest()}  {relative}")
    (root / EXPECTED_ARTIFACTS[-1]).write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")


def seed_synced_main_repo(base: Path) -> tuple[Path, str]:
    remote = base / "remote.git"
    repo = base / "repo"
    commands = [
        (["git", "init", "--bare", str(remote)], base),
        (["git", "clone", str(remote), str(repo)], base),
        (["git", "checkout", "-b", "main"], repo),
    ]
    for command, cwd in commands:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise AssertionError(result.stderr or result.stdout)
    (repo / "tracked.txt").write_text("fixture\n", encoding="utf-8")
    for command in (
        ["git", "add", "tracked.txt"],
        ["git", "-c", "user.name=RC Test", "-c", "user.email=rc@example.invalid", "commit", "-m", "fixture"],
        ["git", "push", "-u", "origin", "main"],
        ["git", "branch", "dev"],
        ["git", "push", "origin", "dev"],
    ):
        result = subprocess.run(command, cwd=repo, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise AssertionError(result.stderr or result.stdout)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return repo, commit


class V110RcManifestTest(unittest.TestCase):
    def test_manifest_create_and_verify_are_fixed_to_v1_1_0(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            seed_artifacts(root)
            manifest = root / "dist" / "v1.1.0-rc-manifest.json"

            created = run_cli(
                "create-manifest",
                "--tag",
                "v1.1.0",
                "--root",
                str(root),
                "--source-commit",
                COMMIT,
                *passed_check_args(),
                "--output",
                str(manifest),
            )
            self.assertEqual(created.returncode, 0, created.stderr or created.stdout)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(payload["tag"], "v1.1.0")
            self.assertEqual(payload["source_commit"], COMMIT)
            self.assertEqual(tuple(item["path"] for item in payload["artifacts"]), EXPECTED_ARTIFACTS)
            self.assertEqual(
                tuple(item["name"] for item in payload["checks"] if item["status"] == "pass"),
                EXPECTED_CHECKS,
            )

            verified = run_cli(
                "verify-manifest",
                "--tag",
                "v1.1.0",
                "--root",
                str(root),
                "--source-commit",
                COMMIT,
                "--manifest",
                str(manifest),
            )
            self.assertEqual(verified.returncode, 0, verified.stderr or verified.stdout)

            wrong_tag = run_cli(
                "verify-manifest",
                "--tag",
                "v1.1.1",
                "--root",
                str(root),
                "--source-commit",
                COMMIT,
                "--manifest",
                str(manifest),
            )
            self.assertNotEqual(wrong_tag.returncode, 0)
            self.assertIn("v1.1.0 only", wrong_tag.stderr + wrong_tag.stdout)

    def test_manifest_rejects_portable_built_from_another_database(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            seed_artifacts(root)
            sidecar = root / "dist" / "portable-manifest-windows.json"
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
            payload["lyrics_sha256"] = "f" * 64
            sidecar.write_text(json.dumps(payload), encoding="utf-8")

            result = run_cli(
                "create-manifest",
                "--tag",
                "v1.1.0",
                "--root",
                str(root),
                "--source-commit",
                COMMIT,
                *passed_check_args(),
                "--output",
                str(root / "dist" / "v1.1.0-rc-manifest.json"),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("portable lyrics_sha256", result.stderr + result.stdout)

    def test_manifest_rejects_a_zip_with_stale_portable_contents(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            seed_artifacts(root)
            with zipfile.ZipFile(root / "dist" / "canto-0243-portable.zip", "w") as archive:
                archive.writestr("lyrics.db", b"stale database\n")
                archive.writestr(
                    "portable-manifest.json",
                    (root / "dist" / "portable-manifest-windows.json").read_bytes(),
                )
            result = run_cli(
                "create-manifest",
                "--tag",
                "v1.1.0",
                "--root",
                str(root),
                "--source-commit",
                COMMIT,
                *passed_check_args(),
                "--output",
                str(root / "dist" / "v1.1.0-rc-manifest.json"),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("portable zip lyrics.db", result.stderr + result.stdout)

    def test_verify_file_checks_a_download_against_the_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            seed_artifacts(root)
            manifest = root / "dist" / "v1.1.0-rc-manifest.json"
            created = run_cli(
                "create-manifest",
                "--tag",
                "v1.1.0",
                "--root",
                str(root),
                "--source-commit",
                COMMIT,
                *passed_check_args(),
                "--output",
                str(manifest),
            )
            self.assertEqual(created.returncode, 0, created.stderr or created.stdout)
            downloaded = root / "downloaded.db"
            downloaded.write_bytes((root / "lyrics.db").read_bytes())

            verified = run_cli(
                "verify-file",
                "--manifest",
                str(manifest),
                "--artifact-path",
                "lyrics.db",
                "--source-commit",
                COMMIT,
                "--file",
                str(downloaded),
            )
            self.assertEqual(verified.returncode, 0, verified.stderr or verified.stdout)
            downloaded.write_bytes(b"tampered\n")
            rejected = run_cli(
                "verify-file",
                "--manifest",
                str(manifest),
                "--artifact-path",
                "lyrics.db",
                "--source-commit",
                COMMIT,
                "--file",
                str(downloaded),
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("artifact integrity mismatch", rejected.stderr + rejected.stdout)

    def test_remote_retry_only_allows_identical_or_missing_assets(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "candidate"
            remote = Path(raw) / "remote"
            remote.mkdir()
            seed_artifacts(root)
            manifest = root / "dist" / "v1.1.0-rc-manifest.json"
            created = run_cli(
                "create-manifest",
                "--tag",
                "v1.1.0",
                "--root",
                str(root),
                "--source-commit",
                COMMIT,
                *passed_check_args(),
                "--output",
                str(manifest),
            )
            self.assertEqual(created.returncode, 0, created.stderr or created.stdout)
            shutil.copy2(root / "lyrics.db", remote / "lyrics.db")

            checked = run_cli(
                "verify-remote-assets",
                "--root",
                str(root),
                "--remote-dir",
                str(remote),
                "--manifest",
                str(manifest),
                "--source-commit",
                COMMIT,
            )
            self.assertEqual(checked.returncode, 0, checked.stderr or checked.stdout)
            missing = json.loads(checked.stdout)["missing"]
            self.assertIn("v1.1.0-rc-manifest.json", missing)
            self.assertNotIn("lyrics.db", missing)

            (remote / "unexpected.bin").write_bytes(b"no\n")
            extra = run_cli(
                "verify-remote-assets",
                "--root",
                str(root),
                "--remote-dir",
                str(remote),
                "--manifest",
                str(manifest),
                "--source-commit",
                COMMIT,
            )
            self.assertNotEqual(extra.returncode, 0)
            self.assertIn("unexpected remote asset", extra.stderr + extra.stdout)

    def test_pack_pages_binds_the_same_v1_1_0_database(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            db = root / "lyrics.db"
            db.write_bytes(b"candidate database\n")
            pages = root / "client" / "dist"
            (pages / "workbench").mkdir(parents=True)
            (pages / "index.html").write_text("release", encoding="utf-8")
            (pages / "workbench" / "index.html").write_text("workbench", encoding="utf-8")
            (pages / "lyrics.db").write_bytes(db.read_bytes())
            (pages / "lexicon-manifest.json").write_text(
                json.dumps(
                    {
                        "lexiconVersion": "v1.1.0",
                        "dbFile": "lyrics.db",
                        "byteSize": db.stat().st_size,
                        "sha256": hashlib.sha256(db.read_bytes()).hexdigest(),
                        "preferCompressed": False,
                    }
                ),
                encoding="utf-8",
            )
            output = root / "dist" / "canto-0243-pages-v1.1.0.tar.gz"

            packed = run_cli(
                "pack-pages",
                "--tag",
                "v1.1.0",
                "--root",
                str(root),
                "--source-dir",
                str(pages),
                "--output",
                str(output),
            )
            self.assertEqual(packed.returncode, 0, packed.stderr or packed.stdout)
            with tarfile.open(output, "r:gz") as archive:
                names = {name.removeprefix("./") for name in archive.getnames()}
                extracted = root / "extracted-pages"
                archive.extractall(extracted)
            self.assertIn("index.html", names)
            self.assertIn("lyrics.db", names)
            verified_pages = run_cli(
                "verify-pages",
                "--tag",
                "v1.1.0",
                "--root",
                str(root),
                "--source-dir",
                str(extracted),
            )
            self.assertEqual(
                verified_pages.returncode,
                0,
                verified_pages.stderr or verified_pages.stdout,
            )

            (pages / "lyrics.db").write_bytes(b"wrong database\n")
            page_manifest = json.loads((pages / "lexicon-manifest.json").read_text(encoding="utf-8"))
            page_manifest["byteSize"] = (pages / "lyrics.db").stat().st_size
            page_manifest["sha256"] = hashlib.sha256((pages / "lyrics.db").read_bytes()).hexdigest()
            (pages / "lexicon-manifest.json").write_text(json.dumps(page_manifest), encoding="utf-8")
            rejected = run_cli(
                "pack-pages",
                "--tag",
                "v1.1.0",
                "--root",
                str(root),
                "--source-dir",
                str(pages),
                "--output",
                str(output),
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("Pages lyrics.db", rejected.stderr + rejected.stdout)

    def test_live_smoke_proves_db_search_and_three_axis_pos(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            db = root / "lyrics.db"
            connection = sqlite3.connect(db)
            try:
                connection.execute("CREATE TABLE words (char TEXT)")
                connection.execute("INSERT INTO words VALUES (?)", ("鼻青眼腫",))
                connection.commit()
            finally:
                connection.close()
            db_sha = hashlib.sha256(db.read_bytes()).hexdigest()
            (root / "lexicon-manifest.json").write_text(
                json.dumps(
                    {
                        "lexiconVersion": "v1.1.0",
                        "dbFile": "lyrics.db",
                        "byteSize": db.stat().st_size,
                        "sha256": db_sha,
                    }
                ),
                encoding="utf-8",
            )
            (root / "project-pos-index.json").write_text(
                json.dumps(
                    {
                        "literals": {
                            "鼻青眼腫": {
                                "pos": ["a"],
                                "trust": "high",
                                "gate": ["a"],
                                "show": ["a"],
                                "family": "chengyu",
                                "voice": "passive",
                            }
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (root / "index.html").write_text("<html>v1.1.0</html>", encoding="utf-8")

            handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                result = run_cli(
                    "live-smoke",
                    "--root",
                    str(root),
                    "--base-url",
                    f"http://127.0.0.1:{server.server_port}/",
                )
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["search"], "鼻青眼腫")
            self.assertEqual(payload["pos"]["voice"], "passive")


class V110RcPowerShellSeamTest(unittest.TestCase):
    def test_plan_is_fixed_and_publish_contains_no_build_steps(self) -> None:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(POWERSHELL),
                "-Mode",
                "Plan",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        plan = json.loads(result.stdout)
        self.assertEqual(plan["tag"], "v1.1.0")
        self.assertEqual(tuple(plan["artifacts"]), EXPECTED_ARTIFACTS)
        self.assertIn("python -m ingest build-db", plan["build_commands"])
        publish = "\n".join(plan["publish_commands"]).lower()
        for forbidden in ("npm", "vite", "build-db", "export_words", "build-portable", "pack-pages"):
            self.assertNotIn(forbidden, publish)
        self.assertIn("verify-manifest", publish)
        self.assertIn("gh release upload v1.1.0", publish)
        self.assertEqual(
            tuple(plan["finalize_checks"]),
            ("pages-v1.1.0 workflow completed successfully", "live Pages DB/search/POS smoke"),
        )
        source = POWERSHELL.read_text(encoding="utf-8")
        self.assertNotIn('"--tags"', source)
        self.assertIn("fetch_rime_lexicon_data.py", source)
        for required in (
            "tests/smoke/test_v1_1_0_rc.py",
            "pos-meta-self-check.ts",
            "pos-filter-self-check.ts",
            "build:portable",
            "Test-RelocatedPortable",
        ):
            self.assertIn(required, source)

    def test_preflight_rejects_a_non_main_repository(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            initialized = subprocess.run(
                ["git", "init", "--initial-branch=dev"],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            (repo / "tracked.txt").write_text("fixture\n", encoding="utf-8")
            for command in (
                ["git", "add", "tracked.txt"],
                ["git", "-c", "user.name=RC Test", "-c", "user.email=rc@example.invalid", "commit", "-m", "fixture"],
            ):
                result = subprocess.run(command, cwd=repo, capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(POWERSHELL),
                    "-Mode",
                    "Preflight",
                    "-Repository",
                    str(repo),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("main", result.stderr + result.stdout)
            self.assertNotIn("not implemented", result.stderr + result.stdout)

            build = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(POWERSHELL),
                    "-Mode",
                    "Build",
                    "-Repository",
                    str(repo),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(build.returncode, 0)
            self.assertIn("main", build.stderr + build.stdout)
            self.assertNotIn("not implemented", build.stderr + build.stdout)

            upload = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(POWERSHELL),
                    "-Mode",
                    "UploadDraft",
                    "-Repository",
                    str(repo),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(upload.returncode, 0)
            self.assertIn("main", upload.stderr + upload.stdout)
            self.assertNotIn("not implemented", upload.stderr + upload.stdout)

            finalize = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(POWERSHELL),
                    "-Mode",
                    "Finalize",
                    "-Repository",
                    str(repo),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(finalize.returncode, 0)
            self.assertIn("PagesVerified", finalize.stderr + finalize.stdout)

    def test_verify_accepts_a_synced_main_and_intact_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            repo, commit = seed_synced_main_repo(base)
            candidate = base / "candidate"
            seed_artifacts(candidate)
            manifest = candidate / "dist" / "v1.1.0-rc-manifest.json"
            created = run_cli(
                "create-manifest",
                "--tag",
                "v1.1.0",
                "--root",
                str(candidate),
                "--source-commit",
                commit,
                *passed_check_args(),
                "--output",
                str(manifest),
            )
            self.assertEqual(created.returncode, 0, created.stderr or created.stdout)

            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(POWERSHELL),
                    "-Mode",
                    "Verify",
                    "-Repository",
                    str(repo),
                    "-CandidateRoot",
                    str(candidate),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            status = json.loads(result.stdout)
            self.assertEqual(status["tag"], "v1.1.0")
            self.assertEqual(status["source_commit"], commit)
            self.assertTrue(status["verified"])


class V110PagesDeploymentSeamTest(unittest.TestCase):
    def test_pages_deploys_the_accepted_archive_without_rebuilding(self) -> None:
        source = PAGES_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", source)
        self.assertIn("gh release download v1.1.0", source)
        self.assertIn("canto-0243-pages-v1.1.0.tar.gz", source)
        self.assertIn("verify-file", source)
        self.assertIn("--source-commit \"$(git rev-parse HEAD)\"", source)
        self.assertIn("actions/upload-pages-artifact@", source)
        self.assertIn("actions/deploy-pages@", source)
        lowered = source.lower()
        for forbidden in (
            "actions/setup-node",
            "npm ci",
            "npm run build",
            "vite",
            "python -m ingest",
            "fetch_rime_data",
        ):
            self.assertNotIn(forbidden, lowered)
        self.assertNotIn('tags:\n      - "v*.*.*"', source)
        general = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
        self.assertIn("target_tag", general)
        self.assertNotIn('tags:\n      - "v*.*.*"', general)


if __name__ == "__main__":
    unittest.main()
