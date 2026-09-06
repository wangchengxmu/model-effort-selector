import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from inspect_project import inspect_project


class ProjectEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'README.md').write_text('A kinetics manuscript with experimental concentration data.', encoding='utf-8')
        (self.root / 'analysis.py').write_text('def rate(c, k):\n    return k * c\n', encoding='utf-8')

    def test_reads_real_content_and_focus(self):
        report = inspect_project(self.root, ['analysis.py'])
        self.assertIn('return k * c', report['excerpts'][0]['excerpt'])
        self.assertEqual(report['excerpts'][0]['path'], 'analysis.py')
        self.assertIn('kinetics', report['excerpts'][1]['excerpt'])
        self.assertTrue(report['interpretation_required'])

    def test_sensitive_and_hidden_files_excluded(self):
        for name in ('.env', 'credentials.json', 'access-token.txt'):
            (self.root / name).write_text('DO_NOT_READ', encoding='utf-8')
        (self.root / 'node_modules').mkdir()
        (self.root / 'node_modules' / 'README.md').write_text('DO_NOT_READ', encoding='utf-8')
        report = inspect_project(self.root)
        self.assertNotIn('DO_NOT_READ', json.dumps(report))
        self.assertEqual({x['path'] for x in report['inventory']}, {'README.md', 'analysis.py'})

    def test_sensitive_excerpt_not_returned(self):
        secret = 'ghp_' + 'a' * 30
        (self.root / 'README.md').write_text(secret, encoding='utf-8')
        report = inspect_project(self.root)
        self.assertEqual(report['excerpts'], [])
        self.assertNotIn(secret, json.dumps(report))

    def test_focus_cannot_escape_or_read_credentials(self):
        for focus in ('../outside.txt', str(self.root / 'analysis.py'), '.env', 'missing.md'):
            with self.subTest(focus=focus), self.assertRaises(ValueError):
                inspect_project(self.root, [focus])

    def test_symlink_not_followed(self):
        with tempfile.TemporaryDirectory() as other:
            secret = Path(other) / 'private.md'
            secret.write_text('OUTSIDE_PROJECT', encoding='utf-8')
            try:
                (self.root / 'linked.md').symlink_to(secret)
            except OSError:
                self.skipTest('This host does not permit creating test symlinks')
            self.assertNotIn('OUTSIDE_PROJECT', json.dumps(inspect_project(self.root)))
            with self.assertRaises(ValueError):
                inspect_project(self.root, ['linked.md'])

    def test_limits_and_truncation(self):
        (self.root / 'README.md').write_text('x' * 9000, encoding='utf-8')
        report = inspect_project(self.root, max_entries=1, excerpt_bytes=64)
        self.assertLessEqual(len(report['inventory']), 1)
        self.assertTrue(report['inventory_truncated'])
        if report['excerpts']:
            self.assertLessEqual(len(report['excerpts'][0]['excerpt']), 64)
            self.assertTrue(report['excerpts'][0]['truncated'])

    def test_no_project_execution_or_writes(self):
        marker = self.root / 'executed.txt'
        (self.root / 'analysis.py').write_text("raise RuntimeError('Do not execute this file')", encoding='utf-8')
        before = {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        inspect_project(self.root, ['analysis.py'])
        self.assertFalse(marker.exists())
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()})

    def run_selector(self, *args):
        script = str(Path(__file__).with_name('select_model.py'))
        proc = subprocess.run([sys.executable, script, '--workload', 'scientific-writing', '--results', *args], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_folder_inventory_is_not_a_final_recommendation(self):
        result = self.run_selector('--project', str(self.root))
        self.assertEqual(result['status'], 'needs_project_review')
        self.assertIsNone(result['model'])
        self.assertIn('kinetics', result['project_context']['excerpts'][0]['excerpt'])

    def test_explicit_review_assertion_and_generic_disclosure(self):
        result = self.run_selector('--project', str(self.root), '--focus', 'analysis.py', '--project-reviewed')
        self.assertEqual(result['status'], 'recommended')
        self.assertEqual(result['evidence_basis'], 'project_review_asserted_by_caller')
        self.assertEqual(self.run_selector()['evidence_basis'], 'task_flags_only')

    def test_empty_folder_cannot_claim_reviewed(self):
        with tempfile.TemporaryDirectory() as empty:
            result = self.run_selector('--project', empty, '--project-reviewed')
            self.assertEqual(result['status'], 'needs_project_review')
            self.assertIsNone(result['model'])


if __name__ == '__main__':
    unittest.main()
