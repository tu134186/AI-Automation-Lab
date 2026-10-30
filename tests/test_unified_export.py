import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError
from report_center import export
from scripts.run_history import collect, export_history, main

class UnifiedExportTests(unittest.TestCase):
    def test_report_center_rejects_output_aliases(self):
        import os
        for alias_type in ("symlink","hardlink"):
            with self.subTest(alias_type=alias_type), tempfile.TemporaryDirectory() as folder:
                root=Path(folder);target=root/"report.md";alias=root/"report.json"
                target.write_text("previous")
                if alias_type=="symlink": alias.symlink_to(target)
                else: os.link(target,alias)
                with self.assertRaises(ValueError): export([{"name":"a","status":"success"}],{},root)
                self.assertEqual(target.read_text(),"previous")
                self.assertEqual(alias.read_text(),"previous")
    def test_report_center_failure_preserves_old_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/"report.json").write_text("previous-json")
            (root/"report.md").write_text("previous-md")
            (root/"report.html").mkdir()
            with self.assertRaises(ValueError):
                export([{"name":"a","status":"success"}],{},root)
            self.assertEqual((root/"report.json").read_text(),"previous-json")
            self.assertEqual((root/"report.md").read_text(),"previous-md")
    def test_history_failure_preserves_all_old_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            names=["diagnosis.json","diagnosis.md","history.json"]
            for name in names: (root/name).write_text("previous-"+name)
            (root/"history.md").mkdir()
            with self.assertRaises(ValueError): export_history(collect(lambda _:{}),root)
            for name in names: self.assertEqual((root/name).read_text(),"previous-"+name)
    def test_history_refresh_replaces_one_block(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            export([{"name":"a","status":"success"}],{},root)
            first=collect(lambda _:{})
            export_history(first,root)
            second=collect(lambda _:{})
            second["collected_at"]="second-refresh"
            export_history(second,root)
            text=(root/"report.html").read_text()
            self.assertEqual(text.count("<!-- REPORT_HISTORY_START -->"),1)
            self.assertEqual(text.count("<!-- REPORT_HISTORY_END -->"),1)
            self.assertIn("second-refresh",text)
            self.assertNotIn(first["collected_at"],text)
            self.assertEqual(json.loads((root/"history.json").read_text())["collected_at"],"second-refresh")
    def test_invalid_html_block_preserves_history(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/"history.json").write_text("previous")
            original="<html><!-- REPORT_HISTORY_START --><footer></html>"
            (root/"report.html").write_text(original)
            with self.assertRaises(ValueError): export_history(collect(lambda _:{}),root)
            self.assertEqual((root/"history.json").read_text(),"previous")
            self.assertEqual((root/"report.html").read_text(),original)
    def test_collection_error_uses_separate_note(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);reports=root/"reports";reports.mkdir()
            (root/"report_policy.json").write_text('{"schema":1,"paused_workflows":[]}')
            (reports/"history.md").write_text("previous-history")
            with patch("scripts.run_history.ROOT",root), patch.dict("os.environ",{"GITHUB_REPOSITORY":"tu134186/AI-Automation-Lab"}), patch("scripts.run_history.collect",side_effect=URLError("simulated")), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(),1)
            self.assertEqual((reports/"history.md").read_text(),"previous-history")
            self.assertIn("不能视为本次结果",(reports/"history-error.md").read_text())

