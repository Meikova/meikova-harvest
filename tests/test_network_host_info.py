import unittest
from app import app

class TestNetworkHostInfo(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_host_info_endpoint(self):
        res = self.client.get("/api/network/host-info")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("lan_ip", data)
        self.assertIn("lan_origin", data)
        self.assertIn("public_origin", data)
        self.assertIn("is_local", data)
        self.assertTrue(isinstance(data["lan_ip"], str))
        self.assertTrue(data["lan_origin"].startswith("http"))

    def test_index_html_renders_dynamic_host_not_hardcoded(self):
        # When request comes from custom domain
        res = self.client.get("/", base_url="https://harvest.custom-domain.org:8443")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("harvest.custom-domain.org:8443", html)
        self.assertIn("apps-harvest-qr", html)
        # Should not have hardcoded onrender in apps-modal-ip when accessed from custom domain
        self.assertIn('id="apps-modal-ip">https://harvest.custom-domain.org:8443</span>', html)

if __name__ == "__main__":
    unittest.main()
