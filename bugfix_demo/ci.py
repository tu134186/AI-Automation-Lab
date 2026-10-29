"""Run real regression tests; propagate failures to GitHub Actions."""
import os
from pathlib import Path
import subprocess
import sys
root = Path(__file__).resolve().parent
result = subprocess.run(
    [sys.executable, "-m", "unittest", "-v", "test_task_metrics"],
    cwd=root, capture_output=True, text=True)
log = result.stdout + result.stderr
(root / "tests.log").write_text(log, encoding="utf-8")
status = "PASS" if result.returncode == 0 else "FAIL"
report = (
    "# 云端回归测试\n\n"
    f"- 结果：{status}\n"
    f"- 退出码：{result.returncode}\n"
    f"- Commit：{os.environ.get('GITHUB_SHA', 'local')}\n"
    "- 本任务直接运行测试，失败会使整个任务失败。\n"
    "- 故障样本由助手植入；修复由当前对话中的助手执行。\n\n"
    "~~~text\n" + log + "\n~~~\n")
(root / "report.md").write_text(report, encoding="utf-8")
print(report)
sys.exit(result.returncode)
