import unittest
from urllib.error import HTTPError
from scripts.run_history import collect, state, markdown, html_section

def run(ident, conclusion="success", status="completed", **extra):
    return {"id":ident,"name":"任务","conclusion":conclusion,"status":status,
            "head_branch":"feature/test","head_sha":"abc","created_at":"2026-10-29T00:00:00Z",**extra}

class HistoryTests(unittest.TestCase):
    def test_statuses_never_treat_cancelled_or_unknown_as_success(self):
        self.assertEqual(state(run(1, "cancelled")), "已取消")
        self.assertEqual(state(run(1, None, "in_progress")), "进行中")
        self.assertEqual(state(run(1, None, "queued")), "排队／等待")
        self.assertEqual(state(run(1, None)), "结论未知")
    def test_bounds_and_current_run_excluded(self):
        calls = []
        def get(path):
            calls.append(path)
            if path.startswith("actions/runs?"):
                return {"workflow_runs":[run(i, "failure") for i in range(11, 0, -1)]}
            return {}
        result = collect(get, "11")
        self.assertEqual(len(result["runs"]), 10)
        self.assertNotIn(11, [x["id"] for x in result["runs"]])
        self.assertEqual(sum("/jobs?" in p for p in calls), 3)
        self.assertEqual(sum("/artifacts?" in p for p in calls), 5)
        self.assertEqual(len(calls), 9)
    def test_failure_steps_and_only_live_artifacts(self):
        def get(path):
            if path.startswith("actions/runs?"): return {"workflow_runs":[run(7, "failure")]}
            if "/jobs?" in path:
                return {"jobs":[{"name":"generate","conclusion":"failure",
                                 "steps":[{"name":"Check model authorization","conclusion":"failure"}]}]}
            return {"artifacts":[{"id":1,"name":"expired","expired":True},
                                 {"id":2,"name":"report","expired":False}]}
        item = collect(get)["runs"][0]
        self.assertIn("Check model authorization", item["failed_steps"][0])
        self.assertEqual(len(item["artifacts"]), 1)
        self.assertTrue(item["artifacts"][0]["url"].endswith("/artifacts/2"))
    def test_partial_failure_stays_visible(self):
        def get(path):
            if path.startswith("actions/runs?"): return {"workflow_runs":[run(1, "failure")]}
            raise HTTPError("https://api.github.com",403,"forbidden",{},None)
        item = collect(get)["runs"][0]
        self.assertEqual(item["state"], "失败")
        self.assertEqual(len(item["notes"]), 2)
        self.assertEqual(item["artifacts"], [])
    def test_escapes_remote_content(self):
        def get(path):
            if path.startswith("actions/runs?"):
                return {"workflow_runs":[run(1, name="<script>alert(1)</script>|x")]}
            return {}
        data = collect(get)
        for render in (markdown, html_section):
            value = render(data)
            self.assertNotIn("<script>", value)
            self.assertIn("&lt;script&gt;", value)
    def test_invalid_run_id_rejected(self):
        with self.assertRaises(ValueError):
            collect(lambda _: {"workflow_runs":[run("javascript:alert(1)")]})
    def test_empty_history_does_not_claim_pass(self):
        data = collect(lambda _: {})
        self.assertIn("不能", markdown(data))
        self.assertIn("不能", html_section(data))
