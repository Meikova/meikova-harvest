# -*- coding: utf-8 -*-
"""
Meikova Harvest - Cloudflared Tunnel Manager Test Suite
Tests:
- Tunnel Manager status and discovery
- Lifecycle state transitions (idle, running, stopped)
- API endpoint integration: /api/tunnel/status, /api/host-info
"""

import sys
import unittest
from pathlib import Path

HARVEST_ROOT = Path(__file__).resolve().parent.parent
if str(HARVEST_ROOT) not in sys.path:
    sys.path.insert(0, str(HARVEST_ROOT))

from utils.tunnel_manager import CloudflaredTunnelManager, tunnel_manager
from app import app


class TestHarvestTunnelManager(unittest.TestCase):
    def setUp(self):
        self.mgr = CloudflaredTunnelManager()
        self.client = app.test_client()

    def tearDown(self):
        self.mgr.stop()

    def test_initial_status_structure(self):
        st = self.mgr.get_status()
        self.assertFalse(st["running"])
        self.assertEqual(st["status"], "idle")
        self.assertIsNone(st["url"])
        self.assertIsNone(st["error"])
        self.assertIn("installed", st)
        self.assertIn("platform", st)
        self.assertIn("installCommand", st)
        self.assertIsInstance(st["installCommand"], str)
        self.assertGreater(len(st["installCommand"]), 0)

    def test_find_cloudflared(self):
        bin_path = self.mgr.find_cloudflared()
        if bin_path:
            self.assertIsInstance(bin_path, str)
            self.assertTrue(Path(bin_path).exists())

    def test_lifecycle_offline_state(self):
        # Simulate running state
        self.mgr.status = "running"
        self.mgr.tunnel_url = "https://mock-harvest-test.trycloudflare.com"
        st = self.mgr.get_status()
        self.assertTrue(st["running"])
        self.assertEqual(st["url"], "https://mock-harvest-test.trycloudflare.com")

        # Stop
        st2 = self.mgr.stop()
        self.assertFalse(st2["running"])
        self.assertIsNone(st2["url"])
        self.assertEqual(st2["status"], "idle")

    def test_api_tunnel_status_endpoint(self):
        resp = self.client.get("/api/tunnel/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("running", data)
        self.assertIn("status", data)
        self.assertIn("installCommand", data)

    def test_api_host_info_includes_tunnel(self):
        resp = self.client.get("/api/host-info")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("tunnel", data)
        self.assertIn("active_url", data)


if __name__ == "__main__":
    unittest.main()
