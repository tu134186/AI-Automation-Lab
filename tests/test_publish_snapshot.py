import subprocess
import unittest
from pathlib import Path

class PublishSnapshotTests(unittest.TestCase):
    def test_snapshot_validation_and_publication_guards(self):
        root=Path(__file__).resolve().parents[1]
        result=subprocess.run(["node","scripts/test_publish_report.cjs"],cwd=root,
                              capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn("checks: PASS",result.stdout)

