import unittest
from app import app

class TestNetworkHostInfo(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_host_info_endpoints_and_schema(self):
        # Both /api/host-info and /api/network/host-info must work
        for ep in ["/api/host-info", "/api/network/host-info"]:
            res = self.client.get(ep)
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertIn("lan_ip", data)
            self.assertIn("lan_url", data)
            self.assertIn("tailscale_ip", data)
            self.assertIn("tailscale_url", data)
            self.assertIn("active_url", data)
            self.assertIn("is_local", data)
            self.assertTrue(isinstance(data["lan_ip"], str))
            self.assertTrue(data["lan_url"].startswith("http"))

    def test_qr_endpoint(self):
        res = self.client.get("/api/qr?data=https%3A%2F%2Fexample.com", follow_redirects=False)
        self.assertIn(res.status_code, [200, 307])
        if res.status_code == 307:
            self.assertIn("api.qrserver.com", res.headers.get("Location", ""))

    def test_index_html_renders_dynamic_host_not_hardcoded(self):
        res = self.client.get("/", base_url="https://harvest.custom-domain.org:8443")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("harvest.custom-domain.org:8443", html)
        self.assertIn("apps-harvest-qr", html)
        self.assertIn('id="apps-modal-ip">https://harvest.custom-domain.org:8443</span>', html)

if __name__ == "__main__":
    unittest.main()
