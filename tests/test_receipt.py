import subprocess
import unittest
from pathlib import Path

class ReceiptTests(unittest.TestCase):
    def test_persistent_receipt_validation_and_write_scope(self):
        root=Path(__file__).resolve().parents[1]
        result=subprocess.run(["node","scripts/test_record_receipt.cjs"],cwd=root,
                              capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn("scoped writes: PASS",result.stdout)

