"""Launcher children must print CJK diagnostics on non-UTF-8 systems."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.launch.local_launch import _run_quiet, _spawn_detached


class LocalLaunchUtf8Tests(unittest.TestCase):
    def test_quiet_and_detached_children_override_non_utf8_locale(self):
        env = dict(os.environ, PYTHONUTF8="0", PYTHONCOERCECLOCALE="0", LC_ALL="C")
        env.pop("PYTHONIOENCODING", None)
        with TemporaryDirectory() as tmp, patch.dict(os.environ, env, clear=True):
            root = Path(tmp)
            code = (
                "import json,os,sys; from pathlib import Path; "
                # Exercise the actual encoding failure, without writing a warning
                # to the test runner's console or starting the backend/UI.
                "stream=open(os.devnull,'w',encoding=sys.stdout.encoding); "
                "stream.write('\\u274c \\u8b66\\u544a'); stream.close(); "
                "Path(sys.argv[1]).write_text(json.dumps({"
                "'utf8':sys.flags.utf8_mode,'encoding':sys.stdout.encoding}),encoding='utf-8')"
            )
            # Verify this environment does not already enable Python UTF-8 mode.
            control = subprocess.run(
                [sys.executable, "-c", "import sys; assert sys.flags.utf8_mode == 0"],
                check=False, capture_output=True,
            )
            self.assertEqual(control.returncode, 0, control.stderr)
            for spawn in (_run_quiet, _spawn_detached):
                with self.subTest(spawn=spawn.__name__):
                    result = root / f"{spawn.__name__}.json"
                    children = []
                    popen = subprocess.Popen

                    def track_child(*args, **kwargs):
                        child = popen(*args, **kwargs)
                        children.append(child)
                        return child

                    # Keep/reap our short diagnostic child; production deliberately
                    # lets detached backend processes outlive the launcher.
                    with patch("app.launch.local_launch.subprocess.Popen", side_effect=track_child):
                        rc = spawn(Path(sys.executable), root, ["-c", code, str(result)])
                    for child in children:
                        self.assertEqual(child.wait(timeout=10), 0)
                    if spawn is _run_quiet:
                        self.assertEqual(rc, 0)
                    self.assertTrue(result.is_file(), "Child failed before writing its UTF-8 result")
                    self.assertEqual(json.loads(result.read_text(encoding="utf-8")),
                                     {"utf8": 1, "encoding": "utf-8"})


if __name__ == "__main__":
    unittest.main()
