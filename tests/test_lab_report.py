import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from lab_report import summarize

class ReportTests(unittest.TestCase):
    def test_mixed(self):
        self.assertEqual(summarize([{"name":"a","status":"success"},{"name":"b","status":"failure"},{"name":"c","status":"running"}]),
                         {"total":3,"success":1,"failure":1,"running":1,"all_passed":False})
    def test_all_success(self):
        self.assertTrue(summarize([{"name":"a","status":"success"}])["all_passed"])
    def test_empty_is_not_pass(self):
        self.assertFalse(summarize([])["all_passed"])
    def test_bad_root(self):
        with self.assertRaises(ValueError): summarize({})
    def test_bad_records(self):
        for item in [None, {}, {"name":" ","status":"success"},{"name":"a","status":[]},{"name":"a","status":"unknown"}]:
            with self.subTest(item=item), self.assertRaises(ValueError): summarize([item])
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            summarize([{"name":"a","status":"success"},{"name":" a ","status":"failure"}])
    def test_cli(self):
        script = Path(__file__).resolve().parents[1] / "lab_report.py"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.json"
            for data, code in [('[{"name":"a","status":"success"}]',0), ('[]',1), ('{',2), ('{}',2)]:
                path.write_text(data)
                result = subprocess.run([sys.executable,str(script),str(path)],capture_output=True,text=True)
                self.assertEqual(result.returncode, code, result.stderr)
                if code != 2: self.assertIn("total",json.loads(result.stdout))
                else: self.assertIn("error:",result.stderr)
            result = subprocess.run([sys.executable,str(script),str(path.parent/"missing.json")],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)


class MarkdownTests(unittest.TestCase):
    def test_markdown_summary_and_escape(self):
        from lab_report import render_markdown
        text = render_markdown([{'name':'中文|<b>\n*test*','status':'failure'}])
        self.assertIn('Failure: 1', text)
        self.assertIn('中文&#124;&lt;b&gt; &#42;test&#42;', text)
        self.assertIn('| failure |', text)
        self.assertTrue(text.endswith('\n'))

    def test_empty_markdown(self):
        from lab_report import render_markdown
        text = render_markdown([])
        self.assertIn('No tasks recorded.', text)
        self.assertIn('All passed: no', text)

    def test_export_cli_and_failures(self):
        script = Path(__file__).resolve().parents[1] / 'lab_report.py'
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, output = root/'input.json', root/'report.md'
            def run(target):
                return subprocess.run([sys.executable,str(script),str(source),'--markdown',str(target)],capture_output=True,text=True)
            for status, code in [('success',0),('failure',1),('running',1)]:
                source.write_text(json.dumps([{'name':'中文','status':status}]),encoding='utf-8')
                result = run(output)
                self.assertEqual(result.returncode,code,result.stderr)
                self.assertEqual(json.loads(result.stdout)['total'],1)
                self.assertIn('| 中文 | '+status+' |',output.read_text(encoding='utf-8'))
            before = source.read_bytes()
            self.assertEqual(run(source).returncode,2)
            self.assertEqual(source.read_bytes(),before)
            self.assertEqual(run(root/'missing'/'report.md').returncode,2)
            output.write_text('preserve',encoding='utf-8')
            source.write_text('{')
            self.assertEqual(run(output).returncode,2)
            self.assertEqual(output.read_text(),'preserve')


class HtmlTests(unittest.TestCase):
    def test_html_escapes_and_counts(self):
        from lab_report import render_html
        text = render_html([{'name':'中文<script>alert("x")</script>&','status':'failure'}, {'name':'next','status':'running'}])
        self.assertNotIn('<script>', text)
        self.assertIn('中文&lt;script&gt;', text)
        self.assertIn('&amp;', text)
        self.assertIn('Failure: <strong>1</strong>', text)
        self.assertIn('Running: <strong>1</strong>', text)
        self.assertIn('All passed: <strong>no</strong>', text)
        self.assertIn('<meta charset="utf-8">', text)
        self.assertIn('name="viewport"', text)

    def test_empty_html(self):
        from lab_report import render_html
        text = render_html([])
        self.assertIn('No tasks recorded.', text)
        self.assertIn('All passed: <strong>no</strong>', text)

    def test_export_formats_and_errors(self):
        script = Path(__file__).resolve().parents[1] / 'lab_report.py'
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, md, output = root/'input.json', root/'report.md', root/'report.html'
            def run(*extra):
                return subprocess.run([sys.executable,str(script),str(source),*map(str,extra)],capture_output=True,text=True)
            for status,code in [('success',0),('failure',1),('running',1)]:
                source.write_text(json.dumps([{'name':'中文','status':status}]),encoding='utf-8')
                result = run('--html',output,'--markdown',md)
                self.assertEqual(result.returncode,code,result.stderr)
                self.assertEqual(json.loads(result.stdout)['total'],1)
                self.assertIn('<td>中文</td>',output.read_text(encoding='utf-8'))
                self.assertIn('| 中文 |',md.read_text(encoding='utf-8'))
            before = source.read_bytes()
            self.assertEqual(run('--html',source).returncode,2)
            self.assertEqual(source.read_bytes(),before)
            before = md.read_bytes()
            self.assertEqual(run('--markdown',md,'--html',md).returncode,2)
            self.assertEqual(md.read_bytes(),before)
            self.assertEqual(run('--html',root/'missing'/'report.html').returncode,2)
            output.write_text('preserve')
            source.write_text('{')
            self.assertEqual(run('--html',output).returncode,2)
            self.assertEqual(output.read_text(),'preserve')

    def test_hardlink_input_protected(self):
        import os
        script = Path(__file__).resolve().parents[1] / 'lab_report.py'
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder)/'input.json', Path(folder)/'output.html'
            source.write_text('[]')
            os.link(source,output)
            result = subprocess.run([sys.executable,str(script),str(source),'--html',str(output)],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertEqual(source.read_text(),'[]')

if __name__ == '__main__':
    unittest.main()
