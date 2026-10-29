import unittest
from scripts.run_history import collect, markdown, html_section

def record(ident, conclusion="success", workflow=1):
    return {"id":ident,"name":"workflow","status":"completed","conclusion":conclusion,
            "workflow_id":workflow,"head_branch":"main","head_sha":"abc"}

class WiderHistoryTests(unittest.TestCase):
    def test_old_unresolved_failure_survives_report_noise(self):
        rows = [record(i) for i in range(30, 10, -1)] + [record(10,"failure",2)]
        calls=[]
        def get(path):
            calls.append(path)
            return {"workflow_runs":rows} if path.startswith("actions/runs?") else {}
        data=collect(get)
        self.assertEqual(len(data["runs"]),10)
        self.assertEqual(data["scanned_count"],21)
        self.assertEqual(data["triage"]["items"][0]["id"],10)
        self.assertTrue(any("/10/jobs?" in path for path in calls))
        self.assertIn("待处理清单",markdown(data))
        self.assertIn("待处理清单",html_section(data))
        self.assertEqual(data["metrics"]["failed"],1)
    def test_old_recovered_failure_is_not_pending(self):
        rows=[record(50,"success",2)]+[record(i) for i in range(49,10,-1)]+[record(10,"failure",2)]
        data=collect(lambda path: {"workflow_runs":rows} if path.startswith("actions/runs?") else {})
        self.assertEqual(data["triage"]["items"],[])
    def test_unresolved_failure_gets_priority_over_resolved_history(self):
        rows=[record(50)]+[record(i,"failure") for i in range(49,40,-1)]+[record(1,"failure",2)]
        calls=[]
        def get(path):
            calls.append(path)
            return {"workflow_runs":rows} if path.startswith("actions/runs?") else {}
        data=collect(get)
        self.assertTrue(any("/1/jobs?" in path for path in calls))
        self.assertLessEqual(sum("/jobs?" in path for path in calls),3)
        self.assertLessEqual(sum("/artifacts?" in path for path in calls),5)
        self.assertEqual(len(data["triage"]["items"]),1)
    def test_scan_bounded_and_current_excluded(self):
        rows=[record(i) for i in range(200,0,-1)]
        data=collect(lambda path: {"workflow_runs":rows} if path.startswith("actions/runs?") else {},"200")
        self.assertEqual(data["scanned_count"],100)
        self.assertNotIn(200,[x["id"] for x in data["scanned_runs"]])
        self.assertEqual(data["scanned_runs"][-1]["id"],100)
    def test_comparison_can_find_prior_outside_visible_ten(self):
        rows=[record(30,"success",2)]+[record(i) for i in range(29,10,-1)]+[record(10,"failure",2)]
        data=collect(lambda path: {"workflow_runs":rows} if path.startswith("actions/runs?") else {})
        self.assertEqual(data["runs"][0]["comparison"],"恢复通过")

