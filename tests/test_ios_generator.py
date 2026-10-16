import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "tools" / "generate_ios_project.py"
FIXTURE = ROOT / "tests" / "fixtures" / "android-spec.json"


class IOSGeneratorTests(unittest.TestCase):
    def make_spec(self, directory, mutate=None):
        spec = json.loads(FIXTURE.read_text(encoding="utf-8"))
        spec.setdefault("ios", {})["bundleId"] = "mw.example.apex"
        if mutate:
            mutate(spec)
        path = Path(directory) / "spec.json"
        path.write_text(json.dumps(spec), encoding="utf-8")
        return path

    def test_generates_xcode_project_and_valid_plist(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = self.make_spec(tmp)
            out = Path(tmp) / "ios"
            result = subprocess.run(
                [sys.executable, str(GENERATOR), str(spec_path), str(out)],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((out / "project.yml").is_file())
            self.assertTrue((out / "App" / "AppMain.swift").is_file())
            plist = ET.parse(out / "App" / "Info.plist").getroot()
            self.assertEqual(plist.tag, "plist")
            self.assertIn("mw.example.apex", (out / "project.yml").read_text())

    def test_rejects_non_https_start_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = self.make_spec(tmp, lambda spec: spec["webview"].update(startUrl="http://example.com"))
            result = subprocess.run(
                [sys.executable, str(GENERATOR), str(spec_path), str(Path(tmp) / "ios")],
                text=True, capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("HTTPS required", result.stderr)

    def test_rejects_invalid_bundle_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = self.make_spec(tmp, lambda spec: spec["ios"].update(bundleId="bad bundle"))
            result = subprocess.run(
                [sys.executable, str(GENERATOR), str(spec_path), str(Path(tmp) / "ios")],
                text=True, capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid bundle id", result.stderr)


if __name__ == "__main__":
    unittest.main()
