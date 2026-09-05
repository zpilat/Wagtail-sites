"""Run the theme script without Node.js or third-party browser dependencies."""

import html
import json
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from unittest import skipUnless

from django.conf import settings
from django.test import SimpleTestCase


BROWSER = shutil.which("chromium") or shutil.which("google-chrome")


@skipUnless(BROWSER, "Theme tests require Chromium or Google Chrome on PATH")
class ThemeScriptTests(SimpleTestCase):
    def test_theme_behaviour(self):
        source = (Path(settings.PROJECT_DIR) / "static/js/mysite.js").read_text()
        tests = Path(__file__).with_name("theme_tests.js").read_text()
        with TemporaryDirectory(prefix="wagtail-theme-tests-") as directory:
            page = Path(directory) / "tests.html"
            page.write_text(
                '<!doctype html><meta charset="utf-8"><body><script>'
                f"const themeSource = {json.dumps(source)};\n{tests}"
                "</script></body>"
            )
            result = subprocess.run(
                [
                    BROWSER,
                    "--headless",
                    "--disable-gpu",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-background-networking",
                    f"--user-data-dir={directory}/profile",
                    "--dump-dom",
                    page.as_uri(),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        body = re.search(r"<body>(.*?)</body>", result.stdout, re.DOTALL)
        self.assertIsNotNone(body, result.stdout)
        results = json.loads(html.unescape(body.group(1)))
        self.assertEqual(len(results), 10)
        for case in results:
            with self.subTest(case=case["name"]):
                self.assertTrue(case["passed"], case.get("error"))
