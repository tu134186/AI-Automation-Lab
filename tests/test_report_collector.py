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

    def test_repeated_subtest_ids_keep_both_failures_exportable(self):
        from report_center import build_report
        class Sample(unittest.TestCase):
            def test_repeated(self):
                for _ in range(2):
                    with self.subTest(value=1): self.fail("repeated failure")
        result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=Collector).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Sample))
        self.assertEqual(len(result.records), 2)
        self.assertEqual(len({x["name"] for x in result.records}), 2)
        self.assertEqual(len({x["test_id"] for x in result.records}), 1)
        report = build_report(result.records, {})
        self.assertEqual(report["counts"]["failure"], 2)
        self.assertFalse(report["all_passed"])

    def test_repeated_test_execution_preserves_original_id(self):
        from report_center import build_report
        class Sample(unittest.TestCase):
            def test_ok(self): pass
        suite = unittest.TestSuite([Sample("test_ok"), Sample("test_ok")])
        result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=Collector).run(suite)
        report = build_report(result.records, {})
        self.assertEqual(report["total"], 2)
        self.assertEqual(len({x["test_id"] for x in result.records}), 1)
        self.assertTrue(report["all_passed"])


