import unittest
from scripts.triage import build_triage, render_md, render_html
from scripts.run_history import collect

def item(ident, result, status="completed", branch="main", workflow="1"):
    return {"id":ident,"name":"job","url":f"https://github.com/u/r/actions/runs/{ident}",
            "workflow_key":workflow,"branch":branch,"status":status,"conclusion":result,"state":status,
            "failed_steps":[],"log_links":[],"notes":[]}

class TriageTests(unittest.TestCase):
    def test_recovered_old_failure_not_pending(self):
        self.assertEqual(build_triage([item(2,"success"),item(1,"failure")])["items"],[])
    def test_latest_failure_only_once(self):
        records = build_triage([item(3,"failure"),item(2,"failure"),item(1,"success")])["items"]
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]["id"],3)
    def test_cancelled_run_does_not_erase_failure(self):
        records = build_triage([item(2,"cancelled"),item(1,"failure")])["items"]
        self.assertEqual(records[0]["id"],1)
        self.assertTrue(records[0]["newer_unverified"])
    def test_running_run_does_not_claim_fixed(self):
        records = build_triage([item(2,None,"in_progress"),item(1,"failure")])["items"]
        self.assertEqual(records[0]["kind"],"失败待处理")
        self.assertTrue(records[0]["newer_unverified"])
    def test_running_after_success_is_waiting(self):
        records = build_triage([item(2,None,"queued"),item(1,"success")])["items"]
        self.assertEqual(records[0]["kind"],"等待任务结果")
    def test_action_required_not_hidden(self):
        self.assertEqual(build_triage([item(2,"action_required"),item(1,"success")])["items"][0]["kind"],"需要操作")
    def test_branches_and_workflows_isolated(self):
        records = build_triage([item(3,"success"),item(2,"failure",branch="other"),
                                item(1,"failure",workflow="2")])["items"]
        self.assertEqual(len(records),2)
    def test_escape_untrusted_names_and_reject_bad_links(self):
        record = item(1,"failure")
        record["name"]="<script>bad</script>"
        record["url"]="javascript:alert(1)"
        record["log_links"]=[{"name":"<img>","url":"javascript:bad"}]
        for render in (render_md,render_html):
            text = render(build_triage([record]))
            self.assertNotIn("<script>",text)
            self.assertNotIn("javascript:",text)
    def test_failed_job_url_uses_numeric_id_only(self):
        def get(path):
            if path.startswith("actions/runs?"):
                return {"workflow_runs":[{"id":5,"name":"test","status":"completed","conclusion":"failure"}]}
            if "/jobs?" in path:
                return {"jobs":[{"id":71,"name":"unit","conclusion":"failure","steps":[]}]}
            return {}
        result=collect(get)
        self.assertTrue(result["runs"][0]["log_links"][0]["url"].endswith("/job/71"))
    def test_empty_scope_not_all_clear(self):
        self.assertIn("未覆盖",render_md(build_triage([])))

