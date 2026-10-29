#!/usr/bin/env python3
"""Dependency-free smoke check for the isolated automation lab."""
from pathlib import Path
import json
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
required = ["README.md", "AGENTS.md", "scripts/self_check.py"]
missing = [name for name in required if not (root / name).is_file()]
tools = {name: bool(shutil.which(name)) for name in ("git", "gh", "python3", "node")}
result = {"ok": not missing, "missing_files": missing, "available_commands": tools}
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result["ok"] else 1)
