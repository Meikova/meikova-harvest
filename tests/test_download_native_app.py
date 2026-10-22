import unittest
from app import app

class TestDownloadNativeApp(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_native_app_platforms_redirect(self):
        platform_targets = {
            "win-setup": (".exe", "setup"),
            "win-portable": (".exe", "portable"),
            "dmg": (".dmg", ""),
            "appimage": (".appimage", ""),
            "deb": (".deb", ""),
            "tar": (".tar.gz", ""),
            "msi": (".msi", "")
        }
        for target, (ext, keyword) in platform_targets.items():
            res = self.client.get(f"/api/download/app/{target}")
            self.assertIn(res.status_code, [200, 307], f"Failed for target {target}")
            if res.status_code == 307:
                location = res.headers.get("Location", "").lower()
                self.assertIn("github.com/meikova/meikova-harvest-tool/releases", location)
                self.assertTrue(location.endswith(ext) or ext in location, f"Target {target} redirected to {location} which does not have ext {ext}")
                if keyword:
                    self.assertIn(keyword, location, f"Target {target} redirected to {location} without keyword {keyword}")

    def test_native_app_extension_zip(self):
        res = self.client.get("/api/download/app/extension")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "application/zip")
        self.assertIn("MeikovaHarvest-Extension.zip", res.headers.get("Content-Disposition", ""))

    def test_invalid_target_404(self):
        res = self.client.get("/api/download/app/nonexistent-target")
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data.get("code"), "APP_TARGET_NOT_SUPPORTED")

if __name__ == "__main__":
    unittest.main()
