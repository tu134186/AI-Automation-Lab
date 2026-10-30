import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile
from report_center import export
from scripts.run_history import collect, markdown, html_section
from scripts.triage import render_md
from scripts.validate_delivery import create, verify

SHA = "a" * 40

def fixture(root, sha=SHA):
    export([{"name":"test","status":"success"}], {"commit":sha}, root)
    (root/"tests.log").write_text("one real fixture check")
    history = collect(lambda _: {})
    (root/"history.json").write_text(json.dumps(history))
    (root/"history.md").write_text(markdown(history))
    (root/"diagnosis.json").write_text(json.dumps(history["triage"]))
    (root/"diagnosis.md").write_text(render_md(history["triage"]))
    page=root/"report.html"
    page.write_text(page.read_text().replace("<footer>",html_section(history)+"<footer>",1))
    with zipfile.ZipFile(root/f"AI-Automation-Lab-{sha[:7]}-source.zip","w") as archive:
        archive.comment=sha.encode()
        archive.writestr("report_center.py","x=1")
        archive.writestr("scripts/run_history.py","x=1")
        archive.writestr("report_policy.json",json.dumps({"schema":1,"paused_workflows":[]}))

class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        fixture(self.root)
    def test_valid_delivery_and_standalone_verify(self):
        manifest=create(self.root,SHA,"42")
        verify(self.root,SHA,"42")
        self.assertIn("delivery.md",manifest["files"])
        self.assertEqual(len(manifest["files"]),10)
    def test_damaged_or_added_file_detected(self):
        create(self.root,SHA)
        (self.root/"tests.log").write_text("changed")
        with self.assertRaises(ValueError): verify(self.root,SHA)
        create(self.root,SHA)
        (self.root/"extra.txt").write_text("unexpected")
        with self.assertRaises(ValueError): verify(self.root,SHA)
    def test_wrong_commit_rejected(self):
        with self.assertRaises(ValueError): create(self.root,"b"*40)
    def test_diagnosis_mismatch_rejected(self):
        (self.root/"diagnosis.json").write_text('{"items":[]}')
        with self.assertRaises(ValueError): create(self.root,SHA)
    def test_false_test_summary_rejected(self):
        path=self.root/"report.json"
        data=json.loads(path.read_text())
        data["counts"]["failure"]=1
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError): create(self.root,SHA)
    def test_source_commit_mismatch_rejected(self):
        path=self.root/f"AI-Automation-Lab-{SHA[:7]}-source.zip"
        with zipfile.ZipFile(path,"a") as archive: archive.comment=b"b"*40
        with self.assertRaises(ValueError): create(self.root,SHA)
    def test_checksum_list_tamper_detected(self):
        create(self.root,SHA)
        (self.root/"SHA256SUMS.txt").write_text("wrong")
        with self.assertRaises(ValueError): verify(self.root,SHA)
    def test_missing_file_rejected(self):
        (self.root/"report.html").unlink()
        with self.assertRaises(ValueError): create(self.root,SHA)
    def test_readable_report_mismatch_rejected(self):
        (self.root/"report.html").write_text("<html>old report</html>")
        with self.assertRaises(ValueError): create(self.root,SHA)
    def test_real_git_archive_has_verifiable_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory)/"repo"
            repo.mkdir()
            def git(*args):
                return subprocess.check_output(["git","-C",str(repo),*args],stderr=subprocess.DEVNULL,text=True).strip()
            git("init","-q")
            (repo/"scripts").mkdir()
            (repo/"report_center.py").write_text("x=1")
            (repo/"scripts/run_history.py").write_text("x=1")
            (repo/"report_policy.json").write_text(json.dumps({"schema":1,"paused_workflows":[]}))
            git("add",".")
            git("-c","user.name=Fixture","-c","user.email=fixture@example.invalid","commit","-qm","fixture")
            sha=git("rev-parse","HEAD")
            other=Path(directory)/"reports"
            other.mkdir()
            fixture(other,sha)
            git("archive","--format=zip","-o",str(other/f"AI-Automation-Lab-{sha[:7]}-source.zip"),"HEAD")
            create(other,sha)
            verify(other,sha)

