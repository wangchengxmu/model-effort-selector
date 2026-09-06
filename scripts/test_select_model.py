import itertools
import json
from pathlib import Path
import subprocess
import sys
import unittest

from select_model import ASTRA, CATALOG, LUNA, SOL, SPARK, TERRA, WORKLOADS, Task, recommend


class SelectorTests(unittest.TestCase):
    def pair(self, task):
        result = recommend(task)
        return result['model'], result['reasoning_effort']

    def test_realistic_workloads(self):
        cases = [
            (Task('extraction'), (LUNA, 'low')),
            (Task('extraction', 'integrated'), (LUNA, 'medium')),
            (Task('writing'), (LUNA, 'low')),
            (Task('coding', 'integrated'), (TERRA, 'medium')),
            (Task('synthesis', 'integrated'), (SOL, 'high')),
            (Task('scientific-writing', results=True, calculations=True), (ASTRA, 'medium')),
            (Task('scientific-writing', 'integrated', results=True, calculations=True), (ASTRA, 'high')),
            (Task('analysis', figures=True), (ASTRA, 'medium')),
            (Task('analysis', 'integrated', figures=True), (ASTRA, 'high')),
            (Task('architecture'), (ASTRA, 'medium')),
            (Task('debugging', 'hard'), (ASTRA, 'high')),
            (Task('analysis', deep_reasoning=True), (ASTRA, 'xhigh')),
            (Task('debugging', reasoning_blocked=True), (ASTRA, 'xhigh')),
            (Task('coding', priority='speed'), (SPARK, 'medium')),
        ]
        for task, expected in cases:
            with self.subTest(task=task):
                self.assertEqual(self.pair(task), expected)

    def test_missing_evidence_not_xhigh(self):
        self.assertEqual(self.pair(Task('analysis', deep_reasoning=True, evidence_missing=True)), (ASTRA, 'high'))

    def test_calculations_alone_do_not_raise_effort(self):
        for workload in WORKLOADS:
            self.assertEqual(self.pair(Task(workload)), self.pair(Task(workload, calculations=True)))

    def test_consequences_do_not_force_high(self):
        self.assertEqual(self.pair(Task('admin', critical=True)), (ASTRA, 'medium'))

    def test_explicit_legacy_baseline_and_effort(self):
        for model in CATALOG:
            self.assertEqual(self.pair(Task('coding', model=model, effort='medium')), (model, 'medium'))

    def test_unavailable_is_not_silent_downgrade(self):
        result = recommend(Task('analysis', deep_reasoning=True), [LUNA])
        self.assertEqual(result['status'], 'recommended_pair_unavailable')
        self.assertIsNone(result['model'])
        self.assertIsNone(result['reasoning_effort'])

    def test_reject_bad_inputs(self):
        for task, available in [(Task('other'), None), (Task('coding', model='imaginary'), None),
                                (Task('coding', model=LUNA, effort='ultra'), None),
                                (Task('coding'), []), (Task('coding'), ['unknown']),
                                (Task('coding', model=ASTRA), [LUNA])]:
            with self.subTest(task=task, available=available), self.assertRaises(ValueError):
                recommend(task, available)

    def test_all_flag_combinations_return_supported_pair(self):
        count = 0
        for workload, complexity, priority in itertools.product(WORKLOADS, ('routine', 'integrated', 'hard'), ('economy', 'balanced', 'quality', 'speed')):
            for flags in itertools.product((False, True), repeat=7):
                result = recommend(Task(workload, complexity, priority, *flags))
                self.assertIn(result['reasoning_effort'], CATALOG[result['model']])
                self.assertNotIn(result['reasoning_effort'], ('max', 'ultra'))
                self.assertFalse(result['dispatch_performed'])
                if flags[-1]:
                    self.assertNotEqual(result['reasoning_effort'], 'xhigh')
                count += 1
        self.assertEqual(count, 13824)

    def test_cli_json_and_error(self):
        script = str(Path(__file__).with_name('select_model.py'))
        result = subprocess.run([sys.executable, script, '--workload', 'scientific-writing', '--complexity', 'integrated', '--results', '--calculations'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['reasoning_effort'], 'high')
        invalid = subprocess.run([sys.executable, script, '--workload', 'coding', '--available', ''], capture_output=True, text=True)
        self.assertNotEqual(invalid.returncode, 0)
        self.assertEqual(invalid.stdout, '')


if __name__ == '__main__':
    unittest.main()
