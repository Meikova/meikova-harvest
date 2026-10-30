import json
import os
import unittest
from PIL import Image

TARGET_HEX = "#11151B"
TARGET_RGB = (17, 21, 27)

class TestHarvestPWAManifest(unittest.TestCase):
    def test_harvest_pwa_manifests(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        static_dir = os.path.join(base_dir, "static")

        manifest_files = [
            os.path.join(static_dir, "manifest.json"),
            os.path.join(static_dir, "site.webmanifest")
        ]

        for mf in manifest_files:
            self.assertTrue(os.path.exists(mf), f"Manifest file missing: {mf}")
            with open(mf, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertEqual(data.get("background_color", "").upper(), TARGET_HEX)
            self.assertEqual(data.get("theme_color", "").upper(), TARGET_HEX)

            icons = data.get("icons", [])
            self.assertGreaterEqual(len(icons), 4, "Must have at least 4 icons (any-192, maskable-192, any-512, maskable-512)")

            for icon in icons:
                src = icon["src"]
                self.assertFalse(src.endswith(".svg"), f"SVG prohibited in manifest icons: {src}")
                self.assertNotIn("logo.png", src, f"logo.png prohibited in manifest icons: {src}")
                self.assertNotIn("apple-touch-icon", src, f"apple-touch-icon prohibited in manifest icons: {src}")

                # Resolve local path
                clean_src = src.replace("/static/", "").lstrip("/\\")
                img_path = os.path.join(static_dir, clean_src)
                self.assertTrue(os.path.exists(img_path), f"Icon file missing: {img_path}")

                im = Image.open(img_path)
                w, h = im.size
                corners = [
                    im.getpixel((0, 0)),
                    im.getpixel((w - 1, 0)),
                    im.getpixel((0, h - 1)),
                    im.getpixel((w - 1, h - 1))
                ]

                if icon.get("purpose") == "any":
                    for c in corners:
                        if im.mode == "RGBA":
                            self.assertEqual(c[3], 255, f"Corner has transparency: {c}")
                            self.assertEqual(c[:3], TARGET_RGB, f"Corner RGB mismatch: {c[:3]}")
                        else:
                            self.assertEqual(c, TARGET_RGB, f"Corner RGB mismatch: {c}")

if __name__ == "__main__":
    unittest.main()

