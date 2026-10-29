import unittest
from scripts.run_history import comparisons

def item(ident, result, branch="main", workflow="1", status="completed"):
    return {"id":ident, "url":f"https://github.com/u/r/actions/runs/{ident}",
            "workflow_key":workflow, "branch":branch, "status":status, "conclusion":result}

class ComparisonTests(unittest.TestCase):
    def test_new_and_recovered_failures(self):
        for current, previous, expected in (
                ("failure","success","新增失败"),("success","failure","恢复通过"),
                ("failure","timed_out","持续失败"),("success","success","持续通过")):
            rows = [item(2,current),item(1,previous)]
            comparisons(rows)
            self.assertEqual(rows[0]["comparison"],expected)
            self.assertTrue(rows[0]["previous_run_url"].endswith("/1"))
    def test_different_workflows_or_branches_not_compared(self):
        for previous in (item(1,"failure",branch="other"),item(1,"failure",workflow="2")):
            rows = [item(2,"success"),previous]
            comparisons(rows)
            self.assertEqual(rows[0]["comparison"],"暂无可比较记录")
    def test_skip_cancelled_and_running_for_prior_result(self):
        rows = [item(4,"success"),item(3,"cancelled"),item(2,None,status="in_progress"),item(1,"failure")]
        metrics = comparisons(rows)
        self.assertEqual(rows[0]["comparison"],"恢复通过")
        self.assertEqual(metrics["measurable"],2)
        self.assertEqual(metrics["excluded"],2)
        self.assertEqual(metrics["success_rate"],50.0)
    def test_no_completed_results_not_zero_percent_success(self):
        self.assertIsNone(comparisons([item(1,None,status="queued")])["success_rate"])
        self.assertIsNone(comparisons([])["success_rate"])
    def test_missing_identity_not_compared(self):
        rows = [item(2,"success",workflow=""),item(1,"failure",workflow="")]
        comparisons(rows)
        self.assertEqual(rows[0]["comparison"],"暂无可比较记录")
    def test_unknown_conclusion_excluded(self):
        metrics = comparisons([item(1,"future_value")])
        self.assertEqual(metrics["measurable"],0)
