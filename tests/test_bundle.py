import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile
from test_delivery import fixture, SHA
from scripts.validate_delivery import create
from scripts.build_bundle import build_bundle, verify_bundle

class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.reports=self.root/"reports"
        self.reports.mkdir()
        fixture(self.reports)
        create(self.reports,SHA,"42")
    def test_complete_offline_bundle(self):
        package=build_bundle(self.reports,self.root/"bundle",SHA,"42")
        verify_bundle(package,SHA,"42")
        with zipfile.ZipFile(package) as archive:
            self.assertEqual(len(archive.namelist()),12)
        self.assertLess(package.stat().st_size,100000)
    def test_modified_zip_rejected(self):
        package=build_bundle(self.reports,self.root/"bundle",SHA,"42")
        with package.open("ab") as target: target.write(b"corrupt")
        with self.assertRaises(ValueError): verify_bundle(package,SHA,"42")
    def test_wrong_run_rejected_even_with_valid_checksum(self):
        package=build_bundle(self.reports,self.root/"bundle",SHA,"42")
        with self.assertRaises(ValueError): verify_bundle(package,SHA,"99")
    def test_unexpected_archive_entry_rejected(self):
        package=build_bundle(self.reports,self.root/"bundle",SHA,"42")
        with zipfile.ZipFile(package,"a") as archive: archive.writestr("../bad","x")
        package.with_suffix(".zip.sha256").write_text(hashlib.sha256(package.read_bytes()).hexdigest()+"  "+package.name+"\n")
        with self.assertRaises(ValueError): verify_bundle(package,SHA,"42")
    def test_bad_source_cannot_be_packaged(self):
        (self.reports/"report.html").write_text("old")
        with self.assertRaises(ValueError): build_bundle(self.reports,self.root/"bundle",SHA,"42")
    def test_cannot_overwrite_input_folder(self):
        with self.assertRaises(ValueError): build_bundle(self.reports,self.reports,SHA,"42")

