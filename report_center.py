"""Chinese, dependency-free CI report renderer; legacy lab_report stays compatible."""
import html
import json
from collections import Counter
from urllib.parse import urlsplit

LABELS = {"success": "通过", "failure": "失败", "running": "进行中", "skipped": "跳过"}

def safe_link(value):
    if not isinstance(value, str):
        return ""
    try:
        url = urlsplit(value)
        if (url.scheme == "https" and url.hostname == "github.com"
                and url.port in (None, 443) and not url.username and not url.password
                and not any(c.isspace() or ord(c) < 32 for c in value)):
            return value
    except ValueError:
        pass
    return ""

def validate(records, context):
    if not isinstance(records, list) or not isinstance(context, dict):
        raise ValueError("任务必须为列表，上下文必须为对象")
    names = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("任务必须为对象")
        name = record.get("name")
        if not isinstance(name, str) or not name.strip() or name.strip() in names:
            raise ValueError("任务名称不能为空或重复")
        names.add(name.strip())
        if not isinstance(record.get("status"), str) or record["status"] not in LABELS:
            raise ValueError("无效任务状态")
        if not isinstance(record.get("reason", ""), str):
            raise ValueError("错误原因必须为文本")
    for key in ("repository", "branch", "commit", "run_url", "commit_url", "changes"):
        if not isinstance(context.get(key, ""), str):
            raise ValueError("上下文字段必须为文本")

def build_report(records, context):
    validate(records, context)
    counts = Counter(item["status"] for item in records)
    passed = bool(records) and counts["success"] == len(records)
    if not records:
        state = "暂无测试"
    elif counts["failure"]:
        state = "存在失败"
    elif counts["running"]:
        state = "尚未完成"
    elif counts["skipped"]:
        state = "完成，含跳过"
    else:
        state = "全部通过"
    return {"schema": 1, "state": state, "all_passed": passed,
            "total": len(records), "counts": {k: counts[k] for k in LABELS},
            "context": context, "tasks": records}

def escape_md(value):
    text = html.escape(value)
    for char, entity in (("\\", "&#92;"), ("|", "&#124;"), ("`", "&#96;"),
                         ("*", "&#42;"), ("_", "&#95;"), ("[", "&#91;"), ("]", "&#93;")):
        text = text.replace(char, entity)
    return text.replace("\r", "").replace("\n", "<br>")

def render_markdown(report):
    c = report["context"]
    lines = ["# 自动化测试报告", "", "**" + report["state"] + "**", "",
             " · ".join(f"{LABELS[k]}：{v}" for k, v in report["counts"].items()), "",
             f"- 仓库：{escape_md(c.get('repository', ''))}",
             f"- 分支：{escape_md(c.get('branch', ''))}",
             f"- Commit：{escape_md(c.get('commit', ''))}", ""]
    for key, label in (("run_url", "任务记录与报告下载"), ("commit_url", "本次修改")):
        url = safe_link(c.get(key))
        if url:
            # HTML links avoid Markdown destination delimiter injection.
            lines.append(f'<a href="{html.escape(url, quote=True)}">{label}</a>')
    lines.extend(["", "| 测试 | 状态 | 原因／详情 |", "| --- | --- | --- |"])
    for item in report["tasks"]:
        lines.append(f"| {escape_md(item['name'])} | {LABELS[item['status']]} | {escape_md(item.get('reason', ''))} |")
    if not report["tasks"]:
        lines.extend(["", "没有采集到测试，不能判断为通过。"])
    lines.extend(["", "## 修改记录", "", escape_md(c.get("changes", "未提供修改记录")), "",
                  "报告来自本次实际测试。跳过不计为通过；下载文件位于任务页底部 Artifacts。", ""])
    return "\n".join(lines)

def render_html(report):
    esc = lambda x: html.escape(str(x), quote=True)
    c = report["context"]
    cards = "".join(f'<div><b>{value}</b><span>{LABELS[key]}</span></div>'
                    for key, value in report["counts"].items())
    links = "".join(f'<a href="{esc(safe_link(c.get(key)))}">{label}</a>'
                    for key, label in (("run_url", "任务与下载"), ("commit_url", "查看修改"))
                    if safe_link(c.get(key)))
    rows = "".join(
        f'<article class="{item["status"]}"><h3>{esc(item["name"])}</h3>'
        f'<strong>{LABELS[item["status"]]}</strong>'
        + (f'<details open><summary>原因／详情</summary><pre>{esc(item["reason"])}</pre></details>'
           if item.get("reason") else "") + "</article>"
        for item in report["tasks"])
    if not rows:
        rows = "<p>没有采集到测试，不能判断为通过。</p>"
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>自动化测试报告</title>
<style>
:root{{color-scheme:light dark}}*{{box-sizing:border-box}}
body{{margin:0;background:#f2f5fa;color:#182438;font:16px/1.6 system-ui,sans-serif}}
main{{max-width:920px;margin:auto;padding:24px 16px}}h1{{font-size:25px;margin:4px 0}}
header,article,.changes{{background:#fff;border:1px solid #dce3ee;border-radius:16px;padding:20px;margin-bottom:14px}}
.kicker{{font-size:12px;letter-spacing:2px;color:#66758a}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:20px 0}}
.cards div{{background:#edf2fa;border-radius:12px;padding:12px;text-align:center}}
.cards b,.cards span{{display:block}}.cards b{{font-size:26px}}
nav{{display:flex;gap:10px;flex-wrap:wrap}}a{{color:#145ac0;overflow-wrap:anywhere}}
nav a{{background:#e8f0ff;padding:9px 16px;border-radius:10px;text-decoration:none}}
h3{{font-size:15px;overflow-wrap:anywhere;margin:0 0 8px}}
article{{border-left:5px solid #33875c}}article.failure{{border-left-color:#bd3546}}
article.running,article.skipped{{border-left-color:#a16a14}}
pre,.meta{{white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word}}
pre{{font:13px/1.65 ui-monospace,monospace}}.meta,footer{{font-size:13px;color:#586b82}}
@media(max-width:420px){{.cards{{grid-template-columns:repeat(2,1fr)}}header,article{{padding:16px}}}}
@media(prefers-color-scheme:dark){{body{{background:#111827;color:#e6edf8}}header,article,.changes{{background:#1b2638;border-color:#35445c}}.cards div{{background:#26364e}}nav a{{background:#263d62;color:#b9d5ff}}.meta,footer{{color:#b1bfd2}}}}
</style></head><body><main>
<header><div class="kicker">AUTOMATION LAB</div><h1>自动化测试报告</h1>
<p>{esc(report["state"])}</p><div class="cards">{cards}</div>
<div class="meta">{esc(c.get("repository",""))}\n分支：{esc(c.get("branch",""))}\nCommit：{esc(c.get("commit",""))}</div><nav>{links}</nav></header>
<h2>测试详情</h2>{rows}
<section class="changes"><h2>修改记录</h2><pre>{esc(c.get("changes","未提供修改记录"))}</pre></section>
<footer>本页无需联网或 JavaScript。报告来自本次实际测试；跳过不计为通过。下载请进入任务页底部 Artifacts。</footer>
</main></body></html>"""

def export(records, context, output):
    from pathlib import Path
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    report = build_report(records, context)
    (root / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "report.md").write_text(render_markdown(report), encoding="utf-8")
    (root / "report.html").write_text(render_html(report), encoding="utf-8")
    return report
