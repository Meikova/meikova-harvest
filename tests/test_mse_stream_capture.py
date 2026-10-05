import unittest
import os
import subprocess

class TestMseStreamCapture(unittest.TestCase):
    def test_build_py_inject_script_contains_mse_hook(self):
        build_path = os.path.join(os.path.dirname(__file__), "..", "routes", "build.py")
        with open(build_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("SourceBuffer.prototype.appendBuffer", content)
        self.assertIn("MSE_CHUNK_CAPTURED", content)
        self.assertIn("getCapturedStreamBlob", content)
        self.assertIn("_realParent", content)
        self.assertIn("window._capturedMediaChunks", content)

    def test_main_js_mse_and_stream_player(self):
        js_path = os.path.join(os.path.dirname(__file__), "..", "static", "js", "main.js")
        with open(js_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("STREAM PLAYER", content)
        self.assertIn("getCapturedStreamBlob", content)
        self.assertIn("MSE_CHUNK_CAPTURED", content)
        self.assertIn("MediaRecorder", content)
        self.assertIn("showPlayerToast", content)

    def test_main_js_syntax_validity(self):
        js_path = os.path.join(os.path.dirname(__file__), "..", "static", "js", "main.js")
        res = subprocess.run(["node", "-c", js_path], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Node syntax check failed: {res.stderr}")

if __name__ == "__main__":
    unittest.main()
