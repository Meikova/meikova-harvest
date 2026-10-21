# -*- coding: utf-8 -*-
import os
import sys
import unittest
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import HarvestDbAdapter

class TestTursoHarvest(unittest.TestCase):
    def test_local_fallback(self):
        # When TURSO_DATABASE_URL is unset
        db_path = os.path.join(os.path.dirname(__file__), "test_temp.db")
        if os.path.exists(db_path):
            os.remove(db_path)
            
        old_url = os.environ.pop("TURSO_DATABASE_URL", None)
        old_token = os.environ.pop("TURSO_AUTH_TOKEN", None)
        adapter = None
        try:
            adapter = HarvestDbAdapter(db_path)
            self.assertFalse(adapter.is_turso)
            adapter.execute("CREATE TABLE IF NOT EXISTS probe (id TEXT PRIMARY KEY, val INT)")
            adapter.execute("INSERT INTO probe VALUES (?, ?)", ("k1", 100))
            row = adapter.fetchone("SELECT val FROM probe WHERE id = ?", ("k1",))
            self.assertEqual(row[0], 100)
        finally:
            if adapter:
                adapter.close()
            if old_url: os.environ["TURSO_DATABASE_URL"] = old_url
            if old_token: os.environ["TURSO_AUTH_TOKEN"] = old_token
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except Exception:
                    pass

    def test_turso_cloud_connection(self):
        # Configure Turso credentials directly for test
        os.environ["TURSO_DATABASE_URL"] = "https://meikova-harvest-m3ik18dp.aws-ap-northeast-1.turso.io"
        os.environ["TURSO_AUTH_TOKEN"] = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTI1ODkxNDYsImlkIjoiMDFhMTVlYTMtOTQwMS03NWM3LThiZTUtNWYxZjM3ZGY4OTM5Iiwia2lkIjoibk13eDJZSGtEaHVvYl81SXZkM1FQVzhpVi1ZT0poeHdUbmpIMXo5dl9iMCIsInJpZCI6ImM1N2FkOWMzLTQ3MzctNGU4ZS04MGUzLTBiN2QyM2M0NmY3NiJ9.oyOtljcDbKwSgzyDwq-yHNlc-aczemegxNalqiiyL-6zNzEMfij_TO2AII259aPQQh3xbV5cKK5gDBkCNrg5Bw"
        
        db_path = os.path.join(os.path.dirname(__file__), "test_temp2.db")
        adapter = HarvestDbAdapter(db_path)
        try:
            self.assertTrue(adapter.is_turso)
            
            test_id = f"test_task_{int(time.time()*1000)}"
            payload = json.dumps({"title": "Test Cloud Task", "status": "completed"})
            
            adapter.execute(
                "INSERT INTO downloads (download_id, data, timestamp, sync_status) VALUES (?, ?, ?, ?)",
                (test_id, payload, time.time(), "synced")
            )
            
            row = adapter.fetchone("SELECT download_id, data FROM downloads WHERE download_id = ?", (test_id,))
            self.assertIsNotNone(row)
            self.assertEqual(row[0], test_id)
            data = json.loads(row[1])
            self.assertEqual(data["title"], "Test Cloud Task")
            
            # Clean up
            adapter.execute("DELETE FROM downloads WHERE download_id = ?", (test_id,))
            check = adapter.fetchone("SELECT download_id FROM downloads WHERE download_id = ?", (test_id,))
            self.assertIsNone(check)
            print("test_turso_cloud_connection: OK")
        finally:
            adapter.close()
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except Exception:
                    pass

if __name__ == "__main__":
    unittest.main()
