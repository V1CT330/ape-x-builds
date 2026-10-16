#!/usr/bin/env python3
"""Smoke tests for the Android and iOS project generators."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = {
    "application": {
        "name": "Ape X Test",
        "applicationId": "mw.apex.smoketest",
        "versionName": "1.0.0",
        "versionCode": 1,
        "minSdk": 24,
        "targetSdk": 35,
    },
    "webview": {
        "startUrl": "https://example.com",
        "allowedHosts": [],
        "externalLinks": "browser",
    },
    "appearance": {"themeColor": "#123456", "orientation": "portrait"},
    "ios": {"bundleId": "mw.apex.smoketest", "minimumOS": "15.0"},
}


class GeneratorSmokeTests(unittest.TestCase):
    def run_generator(self, script, spec):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            spec_path = tmp / "spec.json"
            output = tmp / "out"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / script), str(spec_path), str(output)],
                text=True,
                capture_output=True,
                check=False,
            )
            return result, output

    def test_android_generates_required_files_and_defaults_host(self):
        result, output = self.run_generator("tools/generate_project.py", SPEC)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((output / "app/build.gradle").is_file())
        self.assertTrue((output / "app/src/main/AndroidManifest.xml").is_file())
        self.assertTrue((output / "app/src/main/res/mipmap/ic_launcher.xml").is_file())
        activity = output / "app/src/main/java/mw/apex/smoketest/MainActivity.java"
        self.assertTrue(activity.is_file())
        self.assertIn('"example.com"', activity.read_text(encoding="utf-8"))

    def test_android_rejects_http_start_url(self):
        spec = json.loads(json.dumps(SPEC))
        spec["webview"]["startUrl"] = "http://example.com"
        result, _ = self.run_generator("tools/generate_project.py", spec)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HTTPS", result.stderr)

    def test_ios_generates_project_sources(self):
        result, output = self.run_generator("tools/generate_ios_project.py", SPEC)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((output / "project.yml").is_file())
        self.assertTrue((output / "App/AppMain.swift").is_file())
        self.assertTrue((output / "App/Info.plist").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
