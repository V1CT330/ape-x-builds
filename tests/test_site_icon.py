import io
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools.fetch_site_icon import save_icons, validate_url


class SiteIconTests(unittest.TestCase):
    def test_rejects_http_icon_urls(self):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            validate_url("http://example.com/favicon.ico", ["example.com"])

    def test_rejects_disallowed_icon_host(self):
        with self.assertRaisesRegex(ValueError, "allowlist"):
            validate_url("https://evil.example/favicon.ico", ["example.com"])

    def test_rejects_private_ip_icon_urls(self):
        with self.assertRaisesRegex(ValueError, "private or reserved"):
            validate_url("https://127.0.0.1/favicon.ico", ["127.0.0.1"])

    def test_converts_logo_to_android_launcher_resources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = io.BytesIO()
            Image.new("RGBA", (64, 32), (20, 80, 140, 255)).save(source, format="PNG")
            save_icons(source.getvalue(), root)
            self.assertTrue((root / "app/src/main/res/drawable-nodpi/ic_site_logo.png").is_file())
            self.assertTrue((root / "app/src/main/res/mipmap-mdpi/ic_launcher.png").is_file())
            self.assertTrue((root / "app/src/main/res/mipmap-xxxhdpi/ic_launcher.png").is_file())
            adaptive = (root / "app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml").read_text()
            self.assertIn("@drawable/ic_site_logo", adaptive)


if __name__ == "__main__":
    unittest.main(verbosity=2)
