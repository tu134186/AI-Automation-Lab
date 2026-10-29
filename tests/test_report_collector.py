import io
import unittest
from scripts.run_report import Collector

class CollectorTests(unittest.TestCase):
    def test_failure_skip_and_error_are_recorded(self):
        class Sample(unittest.TestCase):
            def test_fail(self): self.fail("example failure")
            def test_error(self): raise RuntimeError("example error")
            @unittest.skip("example skipped")
            def test_skip(self): pass
        result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=Collector).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Sample))
        self.assertFalse(result.wasSuccessful())
        self.assertEqual([x["status"] for x in result.records].count("failure"), 2)
        self.assertEqual([x["status"] for x in result.records].count("skipped"), 1)
        self.assertIn("example failure", "\n".join(x["reason"] for x in result.records))
    def test_subtest_failure_does_not_pass_parent(self):
        class Sample(unittest.TestCase):
            def test_parts(self):
                for value in range(2):
                    with self.subTest(value=value): self.assertEqual(value, 0)
        result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=Collector).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Sample))
        self.assertFalse(result.wasSuccessful())
        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.records[0]["status"], "failure")
