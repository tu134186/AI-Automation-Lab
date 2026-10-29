import unittest
from task_metrics import success_rate

class SuccessRateTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(success_rate([]), 0.0)

    def test_cancelled_only(self):
        self.assertEqual(success_rate(["cancelled", None, "skipped"]), 0.0)

    def test_mixed(self):
        self.assertEqual(success_rate(["success", "failure", "cancelled", None]), 50.0)

    def test_all_success(self):
        self.assertEqual(success_rate(["success", "success"]), 100.0)

    def test_all_failed(self):
        self.assertEqual(success_rate(["failure"]), 0.0)

    def test_rounding(self):
        self.assertEqual(success_rate(["success", "failure", "failure"]), 33.3)

if __name__ == "__main__":
    unittest.main()
