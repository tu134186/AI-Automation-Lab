import unittest
from validate_candidate import validate

class CandidateTests(unittest.TestCase):
    def test_valid(self):
        self.assertIn("success_rate", validate(b"def success_rate(x):\n return 0\n"))
    def test_empty(self):
        with self.assertRaises(ValueError): validate(b"")
    def test_large(self):
        with self.assertRaises(ValueError): validate(b"x" * 12001)
    def test_bad_syntax(self):
        with self.assertRaises(SyntaxError): validate(b"def success_rate(")
    def test_missing_function(self):
        with self.assertRaises(ValueError): validate(b"x = 1")
    def test_utf8(self):
        with self.assertRaises(UnicodeDecodeError): validate(b"\xff")
