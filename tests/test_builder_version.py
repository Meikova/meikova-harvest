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

        # Empty string
        p.cfg._version = ''
        self.assertEqual(p._version_tuple(), (0, 0, 0))

if __name__ == '__main__':
    unittest.main()
