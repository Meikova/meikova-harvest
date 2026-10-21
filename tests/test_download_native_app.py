import unittest
from app import app

class TestDownloadNativeApp(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_native_app_redirects_or_serves(self):
        # win-setup should redirect to release base or serve file
        res = self.client.get("/api/download/app/win-setup")
        self.assertIn(res.status_code, [200, 307])
        if res.status_code == 307:
            self.assertIn("github.com/Meikova/meikova-harvest-tool/releases", res.headers.get("Location", ""))

    def test_native_app_extension_zip(self):
        res = self.client.get("/api/download/app/extension")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "application/zip")
        self.assertIn("MeikovaHarvest-Extension.zip", res.headers.get("Content-Disposition", ""))

    def test_invalid_target_404(self):
        res = self.client.get("/api/download/app/nonexistent-target")
        self.assertEqual(res.status_code, 404)

if __name__ == "__main__":
    unittest.main()
