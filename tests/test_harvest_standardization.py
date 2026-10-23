"""Verification test suite for Meikova Harvest standardization (Playbook Part 3 & Golden Invariants).
Tests:
1. HttpOnly cookies on auth responses (prevent XSS token theft).
2. Rate limiting sliding window on login and register.
3. TLS verification default in app.py.
4. Electron webPreferences security configuration.
5. Accessibility prefers-reduced-motion in styles.css.
"""
import unittest
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from utils.ratelimit import check_rate_limit, reset_rate_limit, LIMITS

class TestHarvestStandardization(unittest.TestCase):

    def test_ratelimiter_sliding_window(self):
        test_ip = "203.0.113.199" # Documentation test IP (non-local)
        reset_rate_limit(test_ip, "login")
        
        # Should allow up to LIMITS["login"][0] requests
        max_allowed = LIMITS["login"][0]
        for i in range(max_allowed):
            allowed, msg = check_rate_limit(test_ip, "login")
            self.assertTrue(allowed, f"Request {i+1} should be allowed")
            self.assertEqual(msg, "")
        
        # Next request must be rate limited
        allowed, msg = check_rate_limit(test_ip, "login")
        self.assertFalse(allowed, "Exceeding limit must be blocked")
        self.assertIn("Quá nhiều lần", msg)
        
        # Reset should allow request again
        reset_rate_limit(test_ip, "login")
        allowed, msg = check_rate_limit(test_ip, "login")
        self.assertTrue(allowed, "Reset should restore access")

    def test_httponly_cookies_in_auth_routes(self):
        auth_file = os.path.join(BASE_DIR, "routes", "auth.py")
        with open(auth_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # There should be NO httponly=False
        matches_false = re.findall(r'resp\.set_cookie\([^)]*httponly\s*=\s*False', content)
        self.assertEqual(len(matches_false), 0, f"Found {len(matches_false)} cookies with httponly=False")
        
        # All session_token cookies must have httponly=True
        matches_true = re.findall(r'resp\.set_cookie\(["\']session_token["\'][^)]*httponly\s*=\s*True', content)
        self.assertGreater(len(matches_true), 4, "Must have at least 5 session_token cookies with httponly=True")

    def test_electron_web_security_enabled(self):
        main_js = os.path.join(BASE_DIR, "electron", "main.js")
        with open(main_js, "r", encoding="utf-8") as f:
            content = f.read()
        
        # webSecurity should be true
        self.assertIn("webSecurity:      true", content)
        self.assertNotIn("webSecurity:      false", content)

    def test_app_py_tls_verification(self):
        app_py = os.path.join(BASE_DIR, "app.py")
        with open(app_py, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Line 231 should be verify=True
        self.assertIn("headers=headers, verify=True, timeout=10,", content)

    def test_prefers_reduced_motion_in_css(self):
        css_file = os.path.join(BASE_DIR, "static", "css", "styles.css")
        with open(css_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        self.assertIn("@media (prefers-reduced-motion: reduce)", content)
        self.assertIn("animation-duration: 0.01ms !important;", content)

if __name__ == "__main__":
    unittest.main()
