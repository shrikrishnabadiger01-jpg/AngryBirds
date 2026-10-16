import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
from google.genai import types
from agent.approval import ApprovalRun
from agent.runner import run_agent
from core.security import TaskPolicy
from workspace.simulated import SimWorkspace

EMAIL = dict(recipient='manager@example.com', subject='Milestone update', body='Synthetic summary')

def response(*calls):
    parts = [types.Part(function_call=types.FunctionCall(name=name, args=args)) for name, args in calls]
    if not parts:
        parts = [types.Part.from_text(text='Finished.')]
    return SimpleNamespace(candidates=[SimpleNamespace(content=types.Content(role='model', parts=parts))])

class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.patch = patch('agent.runner.genai.Client')
        self.client = self.patch.start().return_value
        self.env = patch('agent.runner.dotenv_values', return_value={'GEMINI_API_KEY':'test-only'})
        self.env.start()
        self.addCleanup(self.patch.stop)
        self.addCleanup(self.env.stop)
        self.policy = TaskPolicy(frozenset({'read_doc','send_email'}), frozenset({'project_report'}), frozenset({'manager@example.com'}))

    def session(self, responses):
        self.client.models.generate_content.side_effect = responses
        return ApprovalRun('Summarize and email manager', 'project_report', self.policy, SimWorkspace())

    def test_approve_exactly_once_and_preserve_batched_tools(self):
        s = self.session([response(('read_doc', {'doc_id':'project_report'}), ('send_email', EMAIL)), response()])
        s.start()
        self.assertEqual(s.status, 'awaiting_approval')
        self.assertEqual(s.workspace.outbox, [])
        self.assertEqual(len(s.workspace.audit), 1)
        token = s.pending['token']
        s.proposal()['recipient'] = 'attacker@example.com'
        s.resolve(token, True)
        self.assertEqual(s.workspace.outbox, [EMAIL])
        self.assertEqual(s.status, 'completed')
        with self.assertRaises(ValueError): s.resolve(token, True)
        self.assertEqual(len(s.workspace.outbox), 1)
        self.client.close.assert_called_once()

    def test_denial_prevents_repeated_email_proposals(self):
        s = self.session([response(('send_email', EMAIL)), response(('send_email', {**EMAIL,'body':'Another'})), response()])
        s.start();s.resolve(s.pending['token'], False)
        self.assertEqual(s.status, 'completed')
        self.assertEqual(s.workspace.outbox, [])
        self.assertEqual([e['decision'] for e in s.workspace.audit], ['DENY','DENY'])

    def test_forbidden_recipient_never_requests_approval(self):
        s=self.session([response(('send_email', {**EMAIL,'recipient':'attacker@example.com'})),response()])
        s.start()
        self.assertEqual(s.status,'completed')
        self.assertEqual(s.workspace.audit[0]['decision'],'BLOCK')
        self.assertEqual(s.workspace.outbox,[])

    def test_wrong_token_and_expiration(self):
        s=self.session([response(('send_email',EMAIL)),response()]);s.start()
        with self.assertRaises(ValueError):s.resolve('another-run-token',True)
        self.assertEqual(s.workspace.outbox,[])
        s.pending['expires']=0;s.resolve(s.pending['token'],True)
        self.assertEqual(s.workspace.outbox,[])
        self.assertEqual(s.approvals[0]['decision'],'expired')

    def test_payload_change_cancels(self):
        s=self.session([response(('send_email',EMAIL))]);s.start()
        s.pending['payload']='{}'
        with self.assertRaises(ValueError):s.resolve(s.pending['token'],True)
        self.assertEqual(s.status,'cancelled')
        self.assertEqual(s.workspace.outbox,[])

    def test_rechecks_run_limit_after_approval(self):
        s=self.session([response(('send_email',EMAIL)),response()]);s.start()
        s.workspace.execute(self.policy,'send_email',{**EMAIL,'body':'Already sent'})
        s.resolve(s.pending['token'],True)
        self.assertEqual(len(s.workspace.outbox),1)
        self.assertEqual(s.workspace.audit[-1]['decision'],'BLOCK')

    def test_model_error_after_send_does_not_replay(self):
        s=self.session([response(('send_email',EMAIL)),RuntimeError('Temporary model failure')]);s.start()
        token=s.pending['token']
        with self.assertRaises(RuntimeError):s.resolve(token,True)
        self.assertEqual(len(s.workspace.outbox),1)
        with self.assertRaises(ValueError):s.resolve(token,True)

    def test_legacy_evaluation_remains_noninteractive(self):
        self.client.models.generate_content.side_effect=[response(('send_email',EMAIL)),response()]
        w=SimWorkspace()
        self.assertEqual(run_agent('Email','project_report',self.policy,w),'Finished.')
        self.assertEqual(w.outbox,[EMAIL])

if __name__=='__main__':unittest.main()
