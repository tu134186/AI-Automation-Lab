"""Build and verify a self-consistent delivery manifest without network access."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from report_center import build_report, render_markdown, render_html
from scripts.run_history import comparisons, markdown as history_md, html_section
from scripts.triage import build_triage, render_md as diagnosis_md
from scripts.report_policy import normalize_policy

def read_json(root, name):
    return json.loads((root / name).read_text(encoding="utf-8"))

def validate(root, sha, run_id=""):
    root = Path(root)
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("无效 Commit")
    required = {"report.json", "report.md", "report.html", "tests.log",
                "history.json", "history.md", "diagnosis.json", "diagnosis.md",
                f"AI-Automation-Lab-{sha[:7]}-source.zip"}
    for name in required:
        path = root / name
        if path.is_symlink() or not path.is_file() or not path.stat().st_size:
            raise ValueError("缺失、空文件或符号链接：" + name)
    report = read_json(root, "report.json")
    if report["context"].get("commit") != sha:
        raise ValueError("报告 Commit 与源码不一致")
    if build_report(report["tasks"], report["context"]) != report:
        raise ValueError("本次结果统计不一致")
    history = read_json(root, "history.json")
    scanned = history["scanned_runs"]
    if history["scanned_count"] != len(scanned) or len(scanned) > 100:
        raise ValueError("历史扫描数量不一致")
    if history["runs"] != scanned[:10]:
        raise ValueError("可见历史与扫描数据不一致")
    if run_id and any(str(item["id"]) == str(run_id) for item in scanned):
        raise ValueError("历史错误包含当前运行")
    if len({item["id"] for item in scanned}) != len(scanned):
        raise ValueError("历史存在重复任务")
    if history["metrics"] != comparisons(copy.deepcopy(scanned)):
        raise ValueError("历史统计不一致")
    diagnosis = read_json(root, "diagnosis.json")
    policy = normalize_policy(history.get("policy"))
    if diagnosis != history["triage"] or diagnosis != build_triage(scanned, policy):
        raise ValueError("诊断清单与历史证据不一致")
    texts = {"report.md": render_markdown(report), "history.md": history_md(history),
             "diagnosis.md": diagnosis_md(diagnosis),
             "report.html": render_html(report).replace("<footer>", html_section(history) + "<footer>", 1)}
    for name, expected in texts.items():
        if (root / name).read_text(encoding="utf-8") != expected:
            raise ValueError("可读报告与 JSON 数据不一致：" + name)
    source = root / f"AI-Automation-Lab-{sha[:7]}-source.zip"
    with zipfile.ZipFile(source) as archive:
        if archive.comment.decode("ascii") != sha or archive.testzip() is not None:
            raise ValueError("源码 ZIP 的 Commit 或完整性不匹配")
        names = archive.namelist()
        if "report_center.py" not in names or "scripts/run_history.py" not in names:
            raise ValueError("源码 ZIP 缺少报告核心文件")
        if json.loads(archive.read("report_policy.json")) != policy:
            raise ValueError("历史分类策略与源码 ZIP 不一致")
        if any(name.startswith("/") or ".." in Path(name).parts for name in names):
            raise ValueError("源码 ZIP 含不安全路径")
    return report, history

def hashes(root):
    result = {}
    for path in sorted(Path(root).iterdir()):
        if path.name in ("manifest.json", "SHA256SUMS.txt"):
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError("交付目录包含非普通文件")
        data = path.read_bytes()
        result[path.name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    return result

def create(root, sha, run_id=""):
    root = Path(root)
    report, history = validate(root, sha, run_id)
    text = ("# 交付一致性检查\n\n"
            f"- Commit：{sha}\n"
            f"- 本次测试状态：{report['state']}\n"
            f"- 检查记录：{report['total']}\n"
            f"- 历史扫描：{history['scanned_count']}\n"
            f"- 待处理任务：{len(history['triage']['items'])}\n"
            "- 报告统计、历史和诊断数据一致。\n"
            "- 源码 ZIP 完整性及内嵌 Commit 一致。\n"
            "- 文件 SHA-256 用于发现损坏或错包，不是数字签名。\n")
    (root / "delivery.md").write_text(text, encoding="utf-8")
    manifest = {"schema": 1, "commit": sha, "run_id": str(run_id),
                "test_state": report["state"], "files": hashes(root)}
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    sums = "".join(f"{entry['sha256']}  {name}\n" for name, entry in manifest["files"].items())
    (root / "SHA256SUMS.txt").write_text(sums, encoding="utf-8")
    verify(root, sha, run_id)
    return manifest

def verify(root, sha, run_id=""):
    root = Path(root)
    report, _ = validate(root, sha, run_id)
    manifest = read_json(root, "manifest.json")
    if (manifest.get("schema") != 1 or manifest.get("commit") != sha
            or manifest.get("run_id") != str(run_id) or manifest.get("test_state") != report["state"]):
        raise ValueError("交付标识不一致")
    if hashes(root) != manifest["files"]:
        raise ValueError("文件数量、大小或 SHA-256 不一致")
    expected = "".join(f"{entry['sha256']}  {name}\n" for name, entry in manifest["files"].items())
    if (root / "SHA256SUMS.txt").read_text(encoding="utf-8") != expected:
        raise ValueError("SHA256SUMS 清单不一致")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--commit", default=os.environ.get("GITHUB_SHA", ""))
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", ""))
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        if args.verify:
            verify(args.folder, args.commit, args.run_id)
        else:
            create(args.folder, args.commit, args.run_id)
        print("Delivery consistency and SHA-256 verification: PASS")
    except (ValueError, KeyError, OSError, zipfile.BadZipFile, UnicodeError) as error:
        print("Delivery validation failed: " + str(error), file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

