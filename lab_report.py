"""Dependency-free task result summary CLI."""
import argparse
import json
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

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--markdown", type=Path, metavar="PATH",
                        help="also export a UTF-8 Markdown report")
    args = parser.parse_args()
    try:
        records = json.loads(args.input.read_text(encoding="utf-8"))
        report = summarize(records)
        if args.markdown:
            if args.markdown.resolve() == args.input.resolve():
                raise ValueError("Markdown output must differ from input")
            args.markdown.write_text(render_markdown(records), encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["all_passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
