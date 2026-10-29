import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from lab_report import summarize

class ReportTests(unittest.TestCase):
    def test_mixed(self):
        self.assertEqual(summarize([{"name":"a","status":"success"},{"name":"b","status":"failure"},{"name":"c","status":"running"}]),
                         {"total":3,"success":1,"failure":1,"running":1,"all_passed":False})
    def test_all_success(self):
        self.assertTrue(summarize([{"name":"a","status":"success"}])["all_passed"])
    def test_empty_is_not_pass(self):
        self.assertFalse(summarize([])["all_passed"])
    def test_bad_root(self):
        with self.assertRaises(ValueError): summarize({})
    def test_bad_records(self):
        for item in [None, {}, {"name":" ","status":"success"},{"name":"a","status":[]},{"name":"a","status":"unknown"}]:
            with self.subTest(item=item), self.assertRaises(ValueError): summarize([item])
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            summarize([{"name":"a","status":"success"},{"name":" a ","status":"failure"}])
    def test_cli(self):
        script = Path(__file__).resolve().parents[1] / "lab_report.py"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.json"
            for data, code in [('[{"name":"a","status":"success"}]',0), ('[]',1), ('{',2), ('{}',2)]:
                path.write_text(data)
                result = subprocess.run([sys.executable,str(script),str(path)],capture_output=True,text=True)
                self.assertEqual(result.returncode, code, result.stderr)
                if code != 2: self.assertIn("total",json.loads(result.stdout))
                else: self.assertIn("error:",result.stderr)
            result = subprocess.run([sys.executable,str(script),str(path.parent/"missing.json")],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)

if __name__ == "__main__":
    unittest.main()
