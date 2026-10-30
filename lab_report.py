"""Dependency-free task result summary CLI."""
import argparse
import json
import html
import os
import shutil
import stat
import tempfile
from pathlib import Path

STATUSES = ("success", "failure", "running")

def summarize(records):
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    counts = dict.fromkeys(STATUSES, 0)
    names = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"record {index} must be an object")
        name = record.get("name")
        status = record.get("status")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"record {index} needs a non-empty name")
        name = name.strip()
        if name in names:
            raise ValueError(f"duplicate task name: {name}")
        if not isinstance(status, str) or status not in STATUSES:
            raise ValueError(f"record {index} has an invalid status")
        names.add(name)
        counts[status] += 1
    return {"total": len(records), **counts,
            "all_passed": bool(records) and counts["success"] == len(records)}

def render_markdown(records):
    report = summarize(records)
    def escape(value):
        import html
        return (html.escape(value.strip()).replace("\\", "&#92;")
                .replace("|", "&#124;").replace("\r", " ").replace("\n", " ")
                .replace("`", "&#96;").replace("*", "&#42;")
                .replace("_", "&#95;").replace("[", "&#91;").replace("]", "&#93;"))
    lines = ["# Task Report", "", f"Total: {report['total']}",
             f"Success: {report['success']}", f"Failure: {report['failure']}",
             f"Running: {report['running']}",
             f"All passed: {'yes' if report['all_passed'] else 'no'}", "",
             "| Task | Status |", "| --- | --- |"]
    lines.extend(f"| {escape(item['name'])} | {item['status']} |" for item in records)
    if not records:
        lines.extend(["", "No tasks recorded."])
    return "\n".join(lines) + "\n"

def render_html(records):
    report = summarize(records)
    rows = "".join(
        f"<tr><td>{html.escape(item['name'].strip())}</td>"
        f"<td>{item['status']}</td></tr>" for item in records)
    if not records:
        rows = '<tr><td colspan="2">No tasks recorded.</td></tr>'
    summary = "".join(
        f"<li>{key.capitalize()}: <strong>{report[key]}</strong></li>"
        for key in ("total", "success", "failure", "running"))
    passed = "yes" if report["all_passed"] else "no"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Task Report</title>
<style>
body{{font:16px system-ui,sans-serif;max-width:900px;margin:40px auto;padding:0 20px;color:#182438;background:#f5f7fb}}
main{{background:white;padding:24px;border-radius:16px}}
ul{{display:flex;flex-wrap:wrap;gap:24px;padding:0;list-style:none}}
table{{width:100%;border-collapse:collapse;table-layout:fixed}}
th,td{{text-align:left;padding:12px;border-bottom:1px solid #dce2eb;overflow-wrap:anywhere;white-space:pre-wrap}}
th{{background:#edf2fa}}
</style>
</head>
<body><main>
<h1>Task Report</h1>
<ul>{summary}</ul>
<p>All passed: <strong>{passed}</strong></p>
<table><caption>Task results</caption><thead><tr><th scope="col">Task</th><th scope="col">Status</th></tr></thead>
<tbody>{rows}</tbody></table>
</main></body>
</html>
"""

def write_reports(outputs):
    """Stage every output before replacing files; roll back a failed commit."""
    staged = []
    committed = []
    preserve_backups = False
    targets = []
    try:
        for path, text in outputs:
            target = path.resolve()
            if target.exists() and not target.is_file():
                raise ValueError("output must be a regular file")
            for previous in targets:
                if target == previous or (target.exists() and previous.exists() and target.samefile(previous)):
                    raise ValueError("output paths must not alias one another")
            targets.append(target)
            descriptor, temporary = tempfile.mkstemp(prefix=".lab-report-", dir=target.parent)
            os.close(descriptor)
            entry = {"target": target, "staged": Path(temporary), "backup": None}
            staged.append(entry)
            entry["staged"].write_text(text, encoding="utf-8")
            if target.exists():
                descriptor, backup = tempfile.mkstemp(prefix=".lab-report-backup-", dir=target.parent)
                os.close(descriptor)
                entry["backup"] = Path(backup)
                shutil.copy2(target, backup)
                os.chmod(entry["staged"], stat.S_IMODE(target.stat().st_mode))
        for entry in staged:
            os.replace(entry["staged"], entry["target"])
            committed.append(entry)
    except BaseException:
        errors = []
        for entry in reversed(committed):
            try:
                if entry["backup"] is None:
                    entry["target"].unlink()
                else:
                    os.replace(entry["backup"], entry["target"])
            except OSError as error:
                errors.append(str(error))
        if errors:
            preserve_backups = True
            raise OSError("output rollback incomplete: " + "; ".join(errors))
        raise
    finally:
        for entry in staged:
            for path in (entry["staged"], entry["backup"] if not preserve_backups else None):
                if path is not None:
                    try:
                        path.unlink(missing_ok=True)
                    except OSError:
                        pass

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--markdown", type=Path, metavar="PATH",
                        help="also export a UTF-8 Markdown report")
    parser.add_argument("--html", type=Path, metavar="PATH",
                        help="also export a standalone UTF-8 HTML report")
    args = parser.parse_args()
    try:
        records = json.loads(args.input.read_text(encoding="utf-8"))
        report = summarize(records)
        outputs = [(path, renderer) for path, renderer in
                   ((args.markdown, render_markdown), (args.html, render_html)) if path]
        paths = [args.input] + [path for path, _ in outputs]
        for index, path in enumerate(paths):
            for other in paths[:index]:
                if path.resolve() == other.resolve() or (
                        path.exists() and other.exists() and path.samefile(other)):
                    raise ValueError("input and output paths must differ")
        write_reports([(path, renderer(records)) for path, renderer in outputs])
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["all_passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())

