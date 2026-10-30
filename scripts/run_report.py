"""Run real unittest results into JSON, Markdown and offline HTML."""
import io
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from report_center import export

class Collector(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []
        self.record_names = set()
        self.occurrences = {}
    def record(self, test, status, reason=""):
        test_id = str(test.id())
        occurrence = self.occurrences.get(test_id, 0) + 1
        name = test_id if occurrence == 1 else f"{test_id} [执行 {occurrence}]"
        while name in self.record_names:
            occurrence += 1
            name = f"{test_id} [执行 {occurrence}]"
        self.occurrences[test_id] = occurrence
        self.record_names.add(name)
        self.records.append({"name": name, "test_id": test_id, "status": status, "reason": reason})
    def addSuccess(self, test):
        super().addSuccess(test)
        self.record(test, "success")
    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.record(test, "failure", self._exc_info_to_string(err, test))
    def addError(self, test, err):
        super().addError(test, err)
        self.record(test, "failure", self._exc_info_to_string(err, test))
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.record(test, "skipped", reason)
    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.record(test, "skipped", "预期失败：" + self._exc_info_to_string(err, test))
    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.record(test, "failure", "预期失败的测试意外通过，请更新测试定义。")
    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.record(subtest, "failure", self._exc_info_to_string(err, test))

def main():
    os.chdir(ROOT)
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    sha = os.environ.get("GITHUB_SHA", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    changes = subprocess.run(["git", "show", "--format=%s", "--stat", "--no-renames", "HEAD"],
                             capture_output=True, text=True, timeout=15)
    context = {"repository": repo, "branch": os.environ.get("GITHUB_REF_NAME", "local"),
               "commit": sha, "changes": changes.stdout.strip() if changes.returncode == 0 else "本地验证，无 Git 修改记录",
               "run_url": f"https://github.com/{repo}/actions/runs/{run_id}" if repo and run_id else "",
               "commit_url": f"https://github.com/{repo}/commit/{sha}" if repo and sha else ""}
    output = ROOT / "reports"
    output.mkdir(exist_ok=True)
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Collector).run(suite)
    (output / "tests.log").write_text(stream.getvalue(), encoding="utf-8")
    print(stream.getvalue())
    smoke = subprocess.run([sys.executable, "scripts/self_check.py"], capture_output=True, text=True, timeout=30)
    records = [{"name": "源码基础检查", "status": "success" if smoke.returncode == 0 else "failure",
                "reason": "" if smoke.returncode == 0 else smoke.stdout + smoke.stderr}] + result.records
    report = export(records, context, output)
    return 0 if result.wasSuccessful() and report["all_passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())

