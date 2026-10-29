import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from lab_report import write_reports

class TransactionalExportTests(unittest.TestCase):
    def test_invalid_second_destination_preserves_first_report(self):
        script=Path(__file__).resolve().parents[1]/"lab_report.py"
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/"tasks.json";md=root/"report.md"
            source.write_text('[{"name":"a","status":"success"}]')
            for html in (root/"missing/report.html", root/"directory"):
                if html.name=="directory": html.mkdir()
                md.write_text("previous-report")
                result=subprocess.run([sys.executable,str(script),str(source),"--markdown",str(md),"--html",str(html)],capture_output=True,text=True)
                self.assertEqual(result.returncode,2)
                self.assertEqual(md.read_text(),"previous-report")
                self.assertEqual(list(root.glob(".lab-report-*")),[])
    def test_second_replace_failure_rolls_back_existing_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);a=root/"a.md";b=root/"b.html"
            a.write_text("old-a");b.write_text("old-b")
            replace=os.replace
            def fail_second(src,dst):
                if Path(dst)==b and "backup" not in Path(src).name:
                    raise PermissionError("simulated second commit failure")
                return replace(src,dst)
            with patch("lab_report.os.replace",side_effect=fail_second):
                with self.assertRaises(PermissionError):
                    write_reports([(a,"new-a"),(b,"new-b")])
            self.assertEqual(a.read_text(),"old-a")
            self.assertEqual(b.read_text(),"old-b")
            self.assertEqual(list(root.glob(".lab-report-*")),[])
    def test_second_failure_removes_new_first_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);a=root/"a.md";b=root/"b.html"
            replace=os.replace
            def fail_second(src,dst):
                if Path(dst)==b: raise PermissionError("simulated")
                return replace(src,dst)
            with patch("lab_report.os.replace",side_effect=fail_second):
                with self.assertRaises(PermissionError): write_reports([(a,"a"),(b,"b")])
            self.assertFalse(a.exists())
            self.assertFalse(b.exists())
    def test_success_preserves_output_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/"real.md";link=root/"link.md"
            target.write_text("old");link.symlink_to(target)
            write_reports([(link,"new")])
            self.assertTrue(link.is_symlink())
            self.assertEqual(target.read_text(),"new")
    def test_failed_rollback_retains_backup_for_recovery(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);a=root/"a.md";b=root/"b.html"
            a.write_text("old-a");b.write_text("old-b")
            replace=os.replace
            def fail(src,dst):
                if Path(dst)==b or "backup" in Path(src).name: raise PermissionError("simulated")
                return replace(src,dst)
            with patch("lab_report.os.replace",side_effect=fail):
                with self.assertRaisesRegex(OSError,"rollback incomplete"):
                    write_reports([(a,"new-a"),(b,"new-b")])
            backups=list(root.glob(".lab-report-backup-*"))
            self.assertTrue(any(p.read_text()=="old-a" for p in backups))

