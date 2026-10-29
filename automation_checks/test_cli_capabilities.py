"""Offline CLI smoke checks; run from any working directory."""
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CliCapabilities(unittest.TestCase):
    def test_repository_config(self):
        config = json.loads((ROOT / "build-config.json").read_text())
        self.assertIsInstance(config, dict)

    def test_git_repository(self):
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )
        self.assertEqual(result.stdout.strip(), "true")

    def test_python_cli(self):
        subprocess.run([sys.executable, "--version"], check=True, capture_output=True)

    def test_node_cli(self):
        result = subprocess.run(
            ["node", "-e", "process.stdout.write(JSON.stringify({sum: 20 + 22}))"],
            check=True, capture_output=True, text=True,
        )
        self.assertEqual(json.loads(result.stdout), {"sum": 42})


if __name__ == "__main__":
    unittest.main(verbosity=2)
