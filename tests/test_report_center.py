import tempfile
import unittest
from pathlib import Path
from report_center import build_report, render_html, render_markdown, safe_link, export

class CenterTests(unittest.TestCase):
    def test_states(self):
        self.assertEqual(build_report([], {})["state"], "暂无测试")
        self.assertFalse(build_report([], {})["all_passed"])
        for status in ("failure", "running", "skipped"):
            report = build_report([{"name": "a", "status": status}], {})
            self.assertFalse(report["all_passed"])
        self.assertTrue(build_report([{"name":"a","status":"success"}], {})["all_passed"])
    def test_invalid(self):
        for records in ([{}], [{"name":"a","status":[]}],
                        [{"name":"a","status":"success","reason":{}}],
                        [{"name":"a","status":"success"},{"name":" a ","status":"failure"}]):
            with self.subTest(records=records), self.assertRaises(ValueError):
                build_report(records, {})
    def test_host_and_scheme(self):
        for url in ("javascript:alert(1)", "https://github.com.evil/a",
                    "https://github.com@evil.com", "https://a@github.com",
                    "https://github.com:444/a", "https://github.com/\na"):
            with self.subTest(url=url): self.assertEqual(safe_link(url), "")
        self.assertEqual(safe_link("https://github.com/u/r/actions/runs/1"),
                         "https://github.com/u/r/actions/runs/1")
    def test_escape_all_fields(self):
        report = build_report([{"name":"<script>|test","status":"failure","reason":"<img src=x onerror=alert(1)>"}],
                              {"changes":"<script>evil</script>","branch":"<b>","run_url":"javascript:alert(1)"})
        for renderer in (render_html, render_markdown):
            text = renderer(report)
            self.assertNotIn("<script>", text)
            self.assertNotIn("<img ", text)
            self.assertNotIn("javascript:", text)
            self.assertIn("&lt;", text)
    def test_export(self):
        with tempfile.TemporaryDirectory() as folder:
            report = export([{"name":"真实中文","status":"success"}], {}, Path(folder)/"out")
            self.assertEqual(report["counts"]["success"], 1)
            for suffix in ("json", "md", "html"):
                self.assertIn("真实中文", (Path(folder)/"out"/("report."+suffix)).read_text())
    def test_context_validation(self):
        with self.assertRaises(ValueError):
            build_report([], {"changes":[]})
    def test_offline_mobile(self):
        text = render_html(build_report([], {}))
        self.assertIn('name="viewport"', text)
        self.assertIn('lang="zh-CN"', text)
        self.assertNotIn("<script", text)
        self.assertNotIn("<link", text)
