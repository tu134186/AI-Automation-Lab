"""Run identical tests on the seeded parent and repaired head, retaining logs."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parent
baseline = subprocess.check_output(
    ["git", "show", "HEAD^:bugfix_demo/task_metrics.py"], text=True)
with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    (temp / "task_metrics.py").write_text(baseline)
    (temp / "test_task_metrics.py").write_text(
        (root / "test_task_metrics.py").read_text())
    before = subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "test_task_metrics"],
        cwd=temp, text=True, capture_output=True)
after = subprocess.run(
    [sys.executable, "-m", "unittest", "-v", "test_task_metrics"],
    cwd=root, text=True, capture_output=True)
before_log = before.stdout + before.stderr
after_log = after.stdout + after.stderr
(root / "before.log").write_text(before_log)
(root / "after.log").write_text(after_log)
expected = ("FAILED (failures=1, errors=1)" in before_log
            and "Ran 6 tests" in before_log)
passed = before.returncode != 0 and expected and after.returncode == 0
report = (
    "# 自动修复 BUG 验证\n\n"
    "这是人工植入故障、由本次助手修复的演示；不是无人值守自动修复服务。\n\n"
    "- 场景：GitHub 任务成功率，取消、跳过和未完成任务不计入分母。\n"
    "- 故障：空列表除零；取消任务错误计入分母。\n"
    f"- 修复前退出码：{before.returncode}（预期：1 个断言失败、1 个异常）。\n"
    f"- 修复后退出码：{after.returncode}（预期：6 项全部通过）。\n"
    f"- 总结：{'PASS' if passed else 'FAIL'}\n"
    f"- Commit：{os.environ.get('GITHUB_SHA', 'local')}\n\n"
    "## 修复前\n\n```text\n" + before_log + "\n```\n\n"
    "## 修复后\n\n```text\n" + after_log + "\n```\n")
(root / "report.md").write_text(report)
print(report)
if not passed:
    raise SystemExit(1)
