"""Bounded, rule-based unattended repair for one verified laboratory bug."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
BROKEN = "def success_rate(conclusions):\n    \"\"\"Percentage of finished success/failure tasks that succeeded.\"\"\"\n    return round(100 * conclusions.count(\"success\") / len(conclusions), 1)\n"
FIXED = "def success_rate(conclusions):\n    \"\"\"Return success percentage among completed success/failure tasks only.\"\"\"\n    finished = [value for value in conclusions if value in (\"success\", \"failure\")]\n    if not finished:\n        return 0.0\n    return round(100 * finished.count(\"success\") / len(finished), 1)\n"

def run_tests():
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "test_task_metrics"],
        cwd=ROOT, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout + result.stderr

def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()

def main():
    report = ["# 无人值守定向修复", "",
              "引擎：已验证规则；未调用 AI 模型。最多修复一次。", ""]
    code, log = run_tests()
    (ROOT / "before.log").write_text(log, encoding="utf-8")
    report.append(f"- 初始测试：{'FAIL' if code else 'PASS'}")
    success = False
    try:
        if code == 0:
            report.append("- 无需修复。")
            success = True
            return
        source = ROOT / "task_metrics.py"
        if (source.read_text() != BROKEN
            or "ZeroDivisionError" not in log
            or "AssertionError: 25.0 != 50.0" not in log
            or "FAILED (failures=1, errors=1)" not in log):
            raise RuntimeError("未知故障，规则不匹配，停止修改。")
        report.append("- 匹配：空列表除零、取消任务被计入分母。")
        source.write_text(FIXED, encoding="utf-8")
        try:
            code, after = run_tests()
            (ROOT / "after.log").write_text(after, encoding="utf-8")
            if code:
                raise RuntimeError("修复后测试失败，撤回本次修改。")
        except BaseException:
            source.write_text(BROKEN, encoding="utf-8")
            raise
        report.append("- 复测：6 项全部通过。")
        if os.environ.get("GITHUB_REF") != "refs/heads/test/bugfix-proof-20261029":
            raise RuntimeError("不是授权的测试分支，禁止提交。")
        if git("diff", "--name-only") != "bugfix_demo/task_metrics.py":
            raise RuntimeError("出现规则范围以外的跟踪文件修改，禁止提交。")
        git("config", "user.name", "github-actions[bot]")
        git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
        git("add", "--", "bugfix_demo/task_metrics.py")
        git("commit", "-m", "fix(bot): repair verified task metrics regression")
        git("push", "origin", "HEAD:refs/heads/test/bugfix-proof-20261029")
        sha = git("rev-parse", "HEAD")
        report.append(f"- 自动提交：{sha}")
        report.append("- 自动提交由 GITHUB_TOKEN 完成，不触发递归工作流。")
        success = True
    except Exception as error:
        report.append("- 停止原因：" + str(error))
        raise
    finally:
        report.append(f"- 最终结果：{'PASS' if success else 'FAIL'}")
        report.extend(["", "## 初始日志", "", "~~~text", log, "~~~"])
        if (ROOT / "after.log").exists():
            report.extend(["", "## 复测日志", "", "~~~text",
                           (ROOT / "after.log").read_text(), "~~~"])
        text = "\n".join(report) + "\n"
        (ROOT / "report.md").write_text(text, encoding="utf-8")
        print(text)

if __name__ == "__main__":
    main()
