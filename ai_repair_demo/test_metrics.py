import unittest
from metrics import success_rate

class MetricsTests(unittest.TestCase):
    def test_empty(self): self.assertEqual(success_rate([]), 0.0)
    def test_excluded(self):
        self.assertEqual(success_rate(["cancelled", None, "skipped"]), 0.0)
    def test_mixed(self):
        self.assertEqual(success_rate(["success", "failure", "cancelled", None]), 50.0)
    def test_success(self): self.assertEqual(success_rate(["success"] * 2), 100.0)
    def test_failure(self): self.assertEqual(success_rate(["failure"]), 0.0)
    def test_rounding(self):
        self.assertEqual(success_rate(["success", "failure", "failure"]), 33.3)
