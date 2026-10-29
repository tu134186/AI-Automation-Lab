"""Bounded, read-only history collection for this repository's Actions runs."""
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from report_center import escape_md

REPOSITORY = "tu134186/AI-Automation-Lab"
LABELS = {"success": "通过", "failure": "失败", "cancelled": "已取消",
          "timed_out": "超时", "skipped": "跳过", "action_required": "需要处理",
          "neutral": "中立", "stale": "已失效", "startup_failure": "启动失败"}

def state(run):
    if run.get("status") != "completed":
        return "进行中" if run.get("status") == "in_progress" else "排队／等待"
    return LABELS.get(run.get("conclusion"), "结论未知")

def collect(get, current_run=""):
    payload = get("actions/runs?per_page=11")
    runs = [x for x in payload.get("workflow_runs", [])
            if str(x.get("id")) != str(current_run)][:10]
    items = []
    diagnostics = 0
    downloads = 0
    for run in runs:
        ident = run.get("id")
        if type(ident) is not int or ident <= 0:
            raise ValueError("无效任务 ID")
        base = f"https://github.com/{REPOSITORY}/actions/runs/{ident}"
        item = {"id": ident, "name": str(run.get("name") or "未命名任务"),
                "state": state(run), "status": run.get("status"),
                "conclusion": run.get("conclusion"), "branch": str(run.get("head_branch") or ""),
                "commit": str(run.get("head_sha") or ""),
                "created_at": str(run.get("created_at") or ""),
                "url": base, "failed_steps": [], "artifacts": [], "notes": []}
        if run.get("conclusion") in ("failure", "timed_out", "startup_failure") and diagnostics < 3:
            diagnostics += 1
            try:
                jobs = get(f"actions/runs/{ident}/jobs?per_page=100").get("jobs", [])
                for job in jobs:
                    if job.get("conclusion") not in ("failure", "timed_out", "startup_failure"):
                        continue
                    steps = [s.get("name", "未知步骤") for s in job.get("steps", [])
                             if s.get("conclusion") in ("failure", "timed_out")]
                    item["failed_steps"].append(str(job.get("name") or "未知 Job")
                                                + " → " + ("；".join(steps) if steps else "未提供失败步骤"))
                if not item["failed_steps"]:
                    item["notes"].append("GitHub 未返回失败步骤，请查看原任务日志。")
            except (HTTPError, URLError, ValueError):
                item["notes"].append("失败详情读取失败，请查看原任务日志。")
        elif run.get("conclusion") in ("failure", "timed_out", "startup_failure"):
            item["notes"].append("本次只展开最近 3 个失败任务，请查看原任务日志。")
        if run.get("status") == "completed" and downloads < 5:
            downloads += 1
            try:
                artifacts = get(f"actions/runs/{ident}/artifacts?per_page=100").get("artifacts", [])
                for artifact in artifacts:
                    aid = artifact.get("id")
                    if artifact.get("expired") or type(aid) is not int or aid <= 0:
                        continue
                    item["artifacts"].append({"name": str(artifact.get("name") or "下载产物"),
                                              "url": base + f"/artifacts/{aid}"})
                if not item["artifacts"]:
                    item["notes"].append("未返回有效产物：可能未上传、已过期或尚未完成上传。")
            except (HTTPError, URLError, ValueError):
                item["notes"].append("产物信息读取失败，请进入任务页查看。")
        elif run.get("status") == "completed":
            item["notes"].append("本次只查询最近 5 个已完成任务的产物。")
        items.append(item)
    return {"schema": 1, "repository": REPOSITORY,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "scope": "本仓库最近 10 次运行；排除本次运行；不是实时监控。",
            "runs": items}

def markdown(data):
    lines = ["## 最近云端任务", "", data["scope"], "",
             "采集时间（UTC）：" + data["collected_at"], ""]
    for item in data["runs"]:
        lines.extend(["### " + escape_md(item["name"]) + " · " + item["state"], "",
                      f"- 任务：[{item['id']}]({item['url']})",
                      "- 分支：" + escape_md(item["branch"]),
                      "- Commit：" + escape_md(item["commit"]),
                      "- 启动时间（UTC）：" + escape_md(item["created_at"])])
        for step in item["failed_steps"]:
            lines.append("- 失败步骤：" + escape_md(step))
        for artifact in item["artifacts"]:
            lines.append(f'- <a href="{html.escape(artifact["url"], quote=True)}">下载：{escape_md(artifact["name"])}</a>')
        for note in item["notes"]:
            lines.append("- " + note)
        lines.append("")
    if not data["runs"]:
        lines.append("没有返回历史任务，不能据此判断所有任务通过。")
    lines.append("")
    return "\n".join(lines)

def html_section(data):
    esc = lambda value: html.escape(str(value), quote=True)
    rows = []
    for item in data["runs"]:
        links = f'<a href="{esc(item["url"])}">任务 {item["id"]}</a>'
        for artifact in item["artifacts"]:
            links += f' · <a href="{esc(artifact["url"])}">下载：{esc(artifact["name"])}</a>'
        details = "\n".join(["失败步骤：" + x for x in item["failed_steps"]] + item["notes"])
        rows.append(f'<article><h3>{esc(item["name"])} · {esc(item["state"])}</h3>'
                    f'<div class="meta">{esc(item["branch"])} · {esc(item["commit"][:7])}<br>{esc(item["created_at"])}</div>'
                    f'<p>{links}</p><pre>{esc(details)}</pre></article>')
    return ('<section><h2>最近云端任务</h2><p class="meta">'
            + esc(data["scope"]) + "<br>采集时间（UTC）：" + esc(data["collected_at"]) + "</p>"
            + ("".join(rows) or "<p>没有返回历史任务，不能判断为全部通过。</p>") + "</section>")

def main():
    root = ROOT / "reports"
    root.mkdir(exist_ok=True)
    try:
        if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
            raise ValueError("只允许读取指定测试仓库")
        token = os.environ.get("GH_TOKEN", "")
        def get(path):
            request = Request(f"https://api.github.com/repos/{REPOSITORY}/{path}",
                              headers={"Accept": "application/vnd.github+json",
                                       "Authorization": "Bearer " + token,
                                       "X-GitHub-Api-Version": "2022-11-28"})
            with urlopen(request, timeout=15) as response:
                return json.load(response)
        data = collect(get, os.environ.get("GITHUB_RUN_ID", ""))
        (root / "history.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        (root / "history.md").write_text(markdown(data), encoding="utf-8")
        page = root / "report.html"
        if page.exists():
            page.write_text(page.read_text(encoding="utf-8").replace("<footer>", html_section(data) + "<footer>", 1),
                            encoding="utf-8")
        return 0
    except (HTTPError, URLError, OSError, ValueError) as error:
        label = f"HTTP {error.code}" if isinstance(error, HTTPError) else type(error).__name__
        (root / "history.md").write_text("## 历史采集失败\n\n" + label
                                        + "。本次未取得有效历史数据，请查看任务日志。\n", encoding="utf-8")
        print("History collection failed: " + label, file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
