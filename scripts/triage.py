"""Evidence-based pending checklist; no model inference or automatic retries."""
import html
from report_center import escape_md, safe_link
from scripts.report_policy import normalize_policy

BAD = {"failure", "timed_out", "startup_failure"}

def direction(item):
    steps = " ".join(item.get("failed_steps", []))
    if "Check model authorization" in steps:
        return "模型授权检查未通过；核对原日志中的授权信息。"
    if "Test candidate validation" in steps:
        return "候选代码校验步骤失败；检查格式、大小及函数定义。"
    if any(word in steps.lower() for word in ("test", "regression", "smoke")):
        return "测试步骤失败；查看日志中的断言、异常或环境错误。"
    if any(word in steps.lower() for word in ("upload", "artifact", "package")):
        return "产物打包或上传步骤失败；检查输出路径及任务日志。"
    return "原因尚未判定；先检查失败步骤和原始日志。"

def build_triage(items, policy=None):
    rules = normalize_policy(policy)["paused_workflows"]
    groups = {}
    for item in items:
        key = (item.get("workflow_key") or str(item["id"]), item.get("branch") or str(item["id"]))
        groups.setdefault(key, []).append(item)
    pending = []
    paused = []
    for rows in groups.values():
        latest = rows[0]
        measurable = next((x for x in rows if x.get("status") == "completed"
                           and x.get("conclusion") in BAD | {"success"}), None)
        waiting = latest.get("status") != "completed"
        action_required = latest.get("conclusion") == "action_required"
        failed = measurable is not None and measurable.get("conclusion") in BAD
        if not failed and not waiting and not action_required:
            continue
        evidence = latest if action_required else measurable if failed else latest
        pending.append({"name": evidence["name"], "branch": evidence.get("branch", ""),
                        "id": evidence["id"], "url": evidence["url"],
                        "kind": "需要操作" if action_required else "失败待处理" if failed else "等待任务结果",
                        "newer_unverified": latest["id"] != evidence["id"],
                        "latest_url": latest["url"], "latest_state": latest.get("state", ""),
                        "direction": "GitHub 标记为需要操作，请打开任务页核对具体要求。" if action_required else direction(evidence) if failed else "任务尚未完成，暂不判断通过或失败。",
                        "failed_steps": evidence.get("failed_steps", []),
                        "log_links": evidence.get("log_links", []),
                        "notes": evidence.get("notes", [])})
        rule = next((r for r in rules if r["workflow_path"] == evidence.get("workflow_path")
                     and r["branch"] == evidence.get("branch")), None)
        if rule:
            entry = pending.pop()
            entry["pause_reason"] = rule["reason"]
            entry["original_conclusion"] = evidence.get("conclusion")
            paused.append(entry)
    return {"scope": f"覆盖本次已扫描的 {len(items)} 次历史运行（最多 100 次）；不代表整个仓库全部故障。",
            "evidence_note": "排查方向依据失败步骤名称，不是已确认根因；未自动重试或修改历史任务。",
            "items": pending, "paused": paused}

def render_md(data):
    lines = ["## 待处理清单", "", data["scope"], "", data["evidence_note"], ""]
    if not data["items"]:
        lines.append("当前需处理清单为空；已暂停实验单列，未覆盖的旧任务状态未知。")
    for item in data["items"]:
        lines.extend(["### " + item["kind"] + " · " + escape_md(item["name"]), "",
                      "- 分支：" + escape_md(item["branch"]),
                      "- 排查方向：" + escape_md(item["direction"])])
        if safe_link(item["url"]):
            lines.append(f'- [查看证据任务]({item["url"]})')
        if item["newer_unverified"]:
            lines.append("- 存在更新任务（" + escape_md(item["latest_state"]) + "），尚不能认定上述失败已恢复。")
            if safe_link(item["latest_url"]):
                lines.append(f'- [查看更新任务]({item["latest_url"]})')
        for link in item["log_links"]:
            if safe_link(link["url"]):
                lines.append(f'- <a href="{html.escape(link["url"], quote=True)}">日志：{escape_md(link["name"])}</a>')
        lines.append("")
    lines.extend(["## 已暂停实验", "", "暂停不代表通过或已修复；原失败结果仍保留。", ""])
    for item in data.get("paused", []):
        lines.extend(["- " + escape_md(item["name"]) + "：" + escape_md(item["pause_reason"]),
                      "  原结论：" + escape_md(str(item["original_conclusion"]))])
        if safe_link(item["url"]):
            lines.append(f'  [原任务证据]({item["url"]})')
    if not data.get("paused"):
        lines.append("本次扫描没有匹配的暂停实验。")
    return "\n".join(lines) + "\n"

def render_html(data):
    esc = lambda value: html.escape(str(value), quote=True)
    rows = []
    for item in data["items"]:
        links = f'<a href="{esc(safe_link(item["url"]))}">查看证据任务</a>' if safe_link(item["url"]) else ""
        for link in item["log_links"]:
            if safe_link(link["url"]):
                links += f' · <a href="{esc(link["url"])}">日志：{esc(link["name"])}</a>'
        note = ("存在更新任务（" + item["latest_state"] + "），尚不能认定已恢复。") if item["newer_unverified"] else ""
        rows.append(f'<article class="failure"><h3>{esc(item["kind"])} · {esc(item["name"])}</h3>'
                    f'<p>{esc(item["branch"])}</p><p>{esc(item["direction"])}</p>'
                    f'<p>{esc(note)}</p><nav>{links}</nav></article>')
    if not rows:
        rows = ["<p>当前需处理清单为空；已暂停实验单列，未覆盖的旧任务状态未知。</p>"]
    rows.append("<h3>已暂停实验</h3><p>暂停不代表通过或已修复；原失败结果仍保留。</p>")
    for item in data.get("paused", []):
        link = f'<a href="{esc(item["url"])}">原任务证据</a>' if safe_link(item["url"]) else ""
        rows.append(f'<article class="skipped"><h3>{esc(item["name"])}</h3><p>{esc(item["pause_reason"])}</p><p>原结论：{esc(item["original_conclusion"])}</p>{link}</article>')
    return ("<section><h2>待处理清单</h2><p class='meta'>" + esc(data["scope"])
            + "<br>" + esc(data["evidence_note"]) + "</p>" + "".join(rows) + "</section>")

