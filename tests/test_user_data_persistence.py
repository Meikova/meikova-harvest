import os
import sys
import unittest
import tempfile
import shutil
import sqlite3

class TestUserDataPersistence(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="etd_test_userdata_")
        self.old_env_userdata = os.environ.get("EVERYTHING_USER_DATA")
        self.old_env_appdata = os.environ.get("APPDATA")

    def tearDown(self):
        if self.old_env_userdata is not None:
            os.environ["EVERYTHING_USER_DATA"] = self.old_env_userdata
        else:
            os.environ.pop("EVERYTHING_USER_DATA", None)

        if self.old_env_appdata is not None:
            os.environ["APPDATA"] = self.old_env_appdata
        else:
            os.environ.pop("APPDATA", None)

        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_get_user_data_dir_from_env(self):
        mock_user_dir = os.path.join(self.test_dir, "custom_user_data")
        os.environ["EVERYTHING_USER_DATA"] = mock_user_dir
        
        import config
        resolved_dir = config.get_user_data_dir()
        self.assertEqual(os.path.abspath(resolved_dir), os.path.abspath(mock_user_dir))
        self.assertTrue(os.path.isdir(resolved_dir))

    def test_get_user_data_dir_windows_appdata_fallback(self):
        os.environ.pop("EVERYTHING_USER_DATA", None)
        mock_appdata = os.path.join(self.test_dir, "AppData", "Roaming")
        os.makedirs(mock_appdata, exist_ok=True)
        os.environ["APPDATA"] = mock_appdata

        import config
        resolved_dir = config.get_user_data_dir()
        expected = os.path.join(mock_appdata, "EveryThingDownloader")
        self.assertEqual(os.path.abspath(resolved_dir), os.path.abspath(expected))
        self.assertTrue(os.path.isdir(resolved_dir))

    def test_auto_migration_legacy_data(self):
        # Create legacy structure
        legacy_dir = os.path.join(self.test_dir, "legacy_downloads")
        os.makedirs(legacy_dir, exist_ok=True)
        legacy_db = os.path.join(legacy_dir, "downloads.db")
        
        # Write dummy data to legacy DB
        conn = sqlite3.connect(legacy_db)
        conn.execute("CREATE TABLE downloads (download_id TEXT PRIMARY KEY, data TEXT, timestamp REAL)")
        conn.execute("INSERT INTO downloads VALUES ('task_123', '{\"status\": \"completed\"}', 12345)")
        conn.commit()
        conn.close()

        # Create target new user data dir
        target_user_dir = os.path.join(self.test_dir, "target_userdata")
        os.makedirs(target_user_dir, exist_ok=True)

        import config
        migrated = config.migrate_legacy_user_data(legacy_dir, target_user_dir)
        self.assertTrue(migrated)

        # Verify target DB has the data
        target_db = os.path.join(target_user_dir, "downloads.db")
        self.assertTrue(os.path.exists(target_db))
        conn2 = sqlite3.connect(target_db)
        cursor = conn2.cursor()
        cursor.execute("SELECT download_id, data FROM downloads WHERE download_id = 'task_123'")
        row = cursor.fetchone()
        conn2.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "task_123")

if __name__ == "__main__":
    unittest.main()
