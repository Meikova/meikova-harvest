import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from build_tool.packager import BuildConfig, Packager, sanitize_version

class TestBuilderVersion(unittest.TestCase):
    def test_sanitize_version(self):
        self.assertEqual(sanitize_version('.1.2.0'), '1.2.0')
        self.assertEqual(sanitize_version('v.1.2.0'), '1.2.0')
        self.assertEqual(sanitize_version('v1.2.0'), '1.2.0')
        self.assertEqual(sanitize_version('1.2.0'), '1.2.0')
        self.assertEqual(sanitize_version('1.2'), '1.2.0')
        self.assertEqual(sanitize_version(''), '1.0.0')
        self.assertEqual(sanitize_version(None), '1.0.0')

    def test_build_config_version_property(self):
        cfg = BuildConfig()
        cfg.version = '.1.2.0'
        self.assertEqual(cfg.version, '1.2.0')
        self.assertEqual(cfg.to_dict()['version'], '1.2.0')

        cfg_from = BuildConfig.from_dict({'version': '.1.2.0'})
        self.assertEqual(cfg_from.version, '1.2.0')

    def test_packager_version_tuple(self):
        cfg = BuildConfig()
        cfg.version = '.1.2.0'
        p = Packager(cfg)
        self.assertEqual(p._version_tuple(), (1, 2, 0))

        # Direct assignment of dirty version
        p.cfg._version = '.1.2.0'
        self.assertEqual(p._version_tuple(), (1, 2, 0))

    def test_hidden_imports_complete(self):
        from build_tool.packager import PYINSTALLER_SPEC
        required_submodules = [
            'routes.pages', 'routes.cookies', 'routes.info', 'routes.download',
            'routes.build', 'routes.extension', 'routes.convert',
            'tasks.download', 'tasks.convert',
            'extractors.generic', 'extractors.torrent',
            'utils.security', 'utils.dns_bypass', 'utils.ffmpeg', 'utils.helpers', 'utils.ytdl',
            'requests', 'mutagen', 'edge_tts', 'quickjs', 'curl_cffi',
        ]
        for mod in required_submodules:
            self.assertIn(f"'{mod}'", PYINSTALLER_SPEC, f"Missing {mod} in PYINSTALLER_SPEC hiddenimports")

    def test_obfuscation_defaults_safe(self):
        from build_tool.obfuscator import ObfuscationConfig, _LICENSE_HEADER_TEMPLATE
        cfg = ObfuscationConfig()
        self.assertFalse(cfg.scramble_names, "scramble_names must default to False to prevent AST corruption")
        self.assertFalse(cfg.encode_strings, "encode_strings must default to False to prevent AST corruption")
        self.assertFalse(cfg.inject_dead_code, "inject_dead_code must default to False to prevent IndentationError")
        self.assertFalse(cfg.pyarmor_mix_str, "pyarmor_mix_str must default to False to prevent PyArmor license limits")
        self.assertFalse(cfg.antidebug, "antidebug must default to False to prevent false positive process kills")
        self.assertNotIn("import tkinter", _LICENSE_HEADER_TEMPLATE, "tkinter must not be imported in license guard")

    def test_version_consistency(self):
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent

        with open(root / 'electron' / 'package.json', 'r', encoding='utf-8') as f:
            pkg_v = json.load(f)['version']
        with open(root / 'electron' / 'config.json', 'r', encoding='utf-8') as f:
            cfg_v = json.load(f)['version']
        with open(root / 'update.json', 'r', encoding='utf-8') as f:
            upd_v = json.load(f)['version']
        cfg_obj = BuildConfig()

        self.assertEqual(pkg_v, '2.0.2')
        self.assertEqual(cfg_v, '2.0.2')
        self.assertEqual(upd_v, '2.0.2')
        self.assertEqual(cfg_obj.version, '2.0.2')

    def test_packager_datas_excludes_downloads(self):
        from build_tool.packager import PYINSTALLER_SPEC
        self.assertNotIn("downloads', 'downloads'", PYINSTALLER_SPEC, "Static downloads folder must not be in datas")

if __name__ == '__main__':
    unittest.main()

