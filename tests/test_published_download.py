import base64
import hashlib
from pathlib import Path
import tempfile
import unittest
from test_delivery import fixture, SHA
from scripts.validate_delivery import create
from scripts.build_bundle import build_bundle
from scripts.verify_published import get_file, verify_published

SNAPSHOT="c"*40

def response(data, encoding="base64"):
    return {"type":"file","size":len(data),"sha":hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest(),
            "encoding":encoding,"content":base64.b64encode(data).decode() if encoding=="base64" else ""}

class PublishedDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);reports=root/"reports";reports.mkdir()
        fixture(reports);create(reports,SHA,"42")
        archive=build_bundle(reports,root/"bundle",SHA,"42")
        data=archive.read_bytes()
        self.files={"complete-delivery.zip":data,"complete-delivery.zip.sha256":(hashlib.sha256(data).hexdigest()+"  complete-delivery.zip\n").encode()}
    def test_real_bundle_round_trip(self):
        result=verify_published(self.files.__getitem__,SHA,SNAPSHOT,"42")
        self.assertTrue(result["verified"])
        self.assertEqual(result["files"],12)
    def test_corrupt_remote_bytes_rejected(self):
        self.files["complete-delivery.zip"]+=b"bad"
        with self.assertRaises(ValueError):verify_published(self.files.__getitem__,SHA,SNAPSHOT,"42")
    def test_wrong_source_or_run_rejected(self):
        for source,run in (("b"*40,"42"),(SHA,"99")):
            with self.subTest(source=source,run=run),self.assertRaises(ValueError):
                verify_published(self.files.__getitem__,source,SNAPSHOT,run)
    def test_contents_api_verifies_git_blob_hash(self):
        data=b"remote fixture"
        self.assertEqual(get_file(lambda _:response(data),SNAPSHOT,"complete-delivery.zip"),data)
        bad=response(data);bad["sha"]="f"*40
        with self.assertRaises(ValueError):get_file(lambda _:bad,SNAPSHOT,"complete-delivery.zip")
    def test_large_file_metadata_uses_git_blob_fallback(self):
        data=b"fixture";meta=response(data,"none");calls=[]
        def get(endpoint):
            calls.append(endpoint)
            return meta if endpoint.startswith("contents/") else response(data)
        self.assertEqual(get_file(get,SNAPSHOT,"complete-delivery.zip"),data)
        self.assertEqual(len(calls),2)
        self.assertTrue(calls[1].startswith("git/blobs/"))
    def test_mutable_ref_and_unapproved_filename_rejected(self):
        for snapshot,name in (("reports-latest","complete-delivery.zip"),(SNAPSHOT,"other.txt")):
            with self.subTest(snapshot=snapshot,name=name),self.assertRaises(ValueError):
                get_file(lambda _:None,snapshot,name)

