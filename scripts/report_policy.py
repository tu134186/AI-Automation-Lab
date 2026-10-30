"""Explicit report classification policy; never rewrites workflow conclusions."""
import json
from pathlib import Path
import re

def normalize_policy(policy=None):
    if policy is None:
        return {"schema": 1, "paused_workflows": []}
    if not isinstance(policy, dict) or policy.get("schema") != 1 or not isinstance(policy.get("paused_workflows"), list):
        raise ValueError("无效报告分类策略")
    entries = []
    seen = set()
    for item in policy["paused_workflows"]:
        if not isinstance(item, dict):
            raise ValueError("无效暂停条目")
        workflow, branch, reason = (item.get(k) for k in ("workflow_path", "branch", "reason"))
        if (not isinstance(workflow, str) or not re.fullmatch(r"\.github/workflows/[^/]+\.ya?ml", workflow)
                or not isinstance(branch, str) or not branch.strip()
                or not isinstance(reason, str) or not reason.strip()):
            raise ValueError("暂停条目必须明确工作流、分支和原因")
        key = (workflow, branch)
        if key in seen:
            raise ValueError("重复暂停条目")
        seen.add(key)
        entries.append({"workflow_path": workflow, "branch": branch, "reason": reason})
    return {"schema": 1, "paused_workflows": entries}

def load_policy(path):
    return normalize_policy(json.loads(Path(path).read_text(encoding="utf-8")))

