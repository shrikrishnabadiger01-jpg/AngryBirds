import json
import tempfile
import unittest
from pathlib import Path
from core.security import TaskPolicy
from workspace.simulated import SimWorkspace
from comparison import GateDisabledWorkspace
from evaluation_view import load_comparisons

class UpdateTests(unittest.TestCase):
    def test_gate_and_baseline_state(self):
        policy = TaskPolicy(frozenset({'read_doc', 'send_email'}), frozenset({'project_report'}), frozenset({'manager@example.com'}))
        cases = [('read_doc', {'doc_id': 'project_report'}, True), ('read_doc', {'doc_id': 'confidential_budget'}, False)]
        for recipient, authorized in [('manager@example.com', True), ('attacker@example.com', False)]:
            cases.append(('send_email', dict(recipient=recipient, subject='Test', body='Synthetic data'), authorized))
        for tool, arguments, authorized in cases:
            for kind in (SimWorkspace, GateDisabledWorkspace):
                with self.subTest(tool=tool, args=arguments, kind=kind.__name__):
                    workspace = kind()
                    result = workspace.execute(policy, tool, arguments)
                    expected = authorized or kind is GateDisabledWorkspace
                    self.assertEqual(result['status'], 'ok' if expected else 'blocked')
                    self.assertEqual(workspace.audit[-1]['executed'], expected)
                    self.assertEqual(len(workspace.outbox), int(expected and tool == 'send_email'))

    def test_saved_errors_are_not_successes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'logs').mkdir()
            run = dict(mode='Gate ON', status='error', audit=[], outbox=[], unauthorized_actions_executed=0, secret_marker_in_answer=False, secret_marker_sent_to_attacker=False)
            record = dict(started_at='2026-10-16', document='project_report', task='Summarize', runs=[run])
            (root/'logs/comparison_valid.json').write_text(json.dumps(record))
            (root/'logs/comparison_broken.json').write_text('{')
            rows, errors = load_comparisons(root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['Status'], 'error')
            self.assertEqual(len(errors), 1)

if __name__ == '__main__':
    unittest.main()
