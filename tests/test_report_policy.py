import copy
import unittest
from scripts.report_policy import normalize_policy
from scripts.triage import build_triage, render_md, render_html
from scripts.run_history import collect

POLICY={"schema":1,"paused_workflows":[{"workflow_path":".github/workflows/ai-repair.yml","branch":"test/bugfix-proof-20261029","reason":"暂不开通 API"}]}

def failed(ident=1, branch="test/bugfix-proof-20261029", path=".github/workflows/ai-repair.yml"):
    return {"id":ident,"name":"AI experiment","workflow_key":"1","workflow_path":path,
            "branch":branch,"url":f"https://github.com/u/r/actions/runs/{ident}",
            "status":"completed","conclusion":"failure","state":"失败"}

class PolicyTests(unittest.TestCase):
    def test_pause_preserves_raw_failure_and_evidence(self):
        rows=[failed()]
        result=build_triage(rows,POLICY)
        self.assertEqual(result["items"],[])
        self.assertEqual(result["paused"][0]["original_conclusion"],"failure")
        self.assertEqual(rows[0]["conclusion"],"failure")
        for render in (render_md,render_html):
            text=render(result)
            self.assertIn("已暂停实验",text)
            self.assertIn("failure",text)
            self.assertIn("暂不开通 API",text)
    def test_pause_does_not_apply_to_other_branch_or_workflow(self):
        for row in (failed(branch="other"),failed(path=".github/workflows/test.yml")):
            result=build_triage([row],POLICY)
            self.assertEqual(len(result["items"]),1)
            self.assertEqual(result["paused"],[])
    def test_missing_policy_never_hides_failure(self):
        self.assertEqual(len(build_triage([failed()])["items"]),1)
    def test_removing_pause_restores_active_item(self):
        self.assertEqual(len(build_triage([failed()],{"schema":1,"paused_workflows":[]})["items"]),1)
    def test_pause_does_not_inflate_success_rate(self):
        run=failed()
        run.update({"path":run["workflow_path"],"head_branch":run["branch"],"workflow_id":1})
        data=collect(lambda p:{"workflow_runs":[run]} if p.startswith("actions/runs?") else {},policy=POLICY)
        self.assertEqual(data["metrics"]["failed"],1)
        self.assertEqual(data["metrics"]["success_rate"],0.0)
        self.assertEqual(data["triage"]["items"],[])
        self.assertEqual(len(data["triage"]["paused"]),1)
    def test_invalid_or_duplicate_rules_rejected(self):
        for value in ([],{},{"schema":1,"paused_workflows":[{}]},
                      {"schema":1,"paused_workflows":POLICY["paused_workflows"]*2}):
            with self.subTest(value=value),self.assertRaises(ValueError):
                normalize_policy(value)
    def test_reason_is_escaped(self):
        policy=copy.deepcopy(POLICY)
        policy["paused_workflows"][0]["reason"]="<script>bad</script>"
        for render in (render_md,render_html):
            self.assertNotIn("<script>",render(build_triage([failed()],policy)))

