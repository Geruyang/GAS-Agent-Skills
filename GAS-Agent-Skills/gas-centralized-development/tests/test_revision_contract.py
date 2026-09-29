"""Static acceptance tests for the requested v3 contract, not agent behavior."""
import json
import os
import unittest
from pathlib import Path

ROOT = Path(os.environ.get('SKILL_ROOT', str(Path(__file__).resolve().parents[1])))

class RevisionContract(unittest.TestCase):
    def text(self, path):
        p=ROOT/path
        self.assertTrue(p.is_file(), f'missing: {path}')
        return p.read_text(encoding='utf-8-sig')
    def doc(self, path):
        return json.loads(self.text(path))
    def test_identity_stable_display_short(self):
        text=self.text('SKILL.md')
        self.assertIn('name: gas-centralized-development',text)
        self.assertIn('# 集权开发模式技能',text)
    def test_all_roles_under_one_command(self):
        r=self.doc('templates/run.example.json')
        self.assertEqual(r.get('schema_version'),3)
        self.assertEqual(set(r.get('command_scope',{}).get('roles',[])),{'executor','reviewer','supervisor'})
        self.assertEqual(r['command_scope']['authority'],'current-coordinator')
    def test_delegated_technical_decisions(self):
        r=self.doc('templates/run.example.json')
        d=r.get('delegation',{})
        self.assertIn('internal_api_changes',d.get('technical_decisions',[]))
        self.assertIs(d.get('approved'),False)
        self.assertIn('CHANGE-01',self.text('references/protocol.md'))
    def test_review_records_not_manager_decision(self):
        r=self.doc('templates/review.example.json')
        self.assertEqual(r.get('record_type'),'verification')
        self.assertIn('review_assignment',r)
        self.assertNotIn('release_authorized',r)
        d=self.doc('templates/decision.example.json')
        self.assertEqual(d['record_type'],'management_decision')
        self.assertEqual(d['decision'],'NOT_DECIDED')
    def test_reviewer_not_unbounded_veto(self):
        p=self.text('references/protocol.md')
        for x in ['ADVISORY','BLOCKING','UNRESOLVED_RISK','CEN-04']:
            self.assertIn(x,p)
    def test_release_requires_hub_order_and_authorization(self):
        d=self.doc('templates/release.example.json')
        for x in ['command','authorization','verification_refs','execution']:
            self.assertIn(x,d)
        self.assertIs(d['command']['issued'],False)
        self.assertEqual(d['execution']['status'],'NOT_RUN')
    def test_fencing_covers_review_and_release(self):
        d=self.doc('templates/command.example.json')
        for x in ['coordinator_epoch','recipient_role','expires_at','acknowledged','idempotency_key']:
            self.assertIn(x,d)
        self.assertEqual(d['recipient_role'],'reviewer')
    def test_author_can_accept_but_not_independently_review(self):
        self.assertIn('指挥者兼任作者时，可以在独立验证后做管理接受',self.text('references/protocol.md'))
    def test_positive_cases_and_anti_review_shopping(self):
        s=self.doc('evals/scenarios.json')
        tags={t for c in s['cases'] for t in c.get('tags',[])}
        for tag in ['reviewer-subordination','authorized-release','delegated-api-change','review-shopping','central-author-acceptance']:
            self.assertIn(tag,tags)
    def test_existing_entries_safe(self):
        for name in ['run','task','review','command','decision','release','supervision']:
            r=self.doc(f'templates/{name}.example.json')
            self.assertIs(r.get('example_only'),True)
            self.assertEqual(r.get('schema_version'),3)

    def test_prepare_does_not_require_nonexistent_artifact(self):
        self.assertIn('PREPARE_INTEGRATION 不要求尚不存在的候选产物已经通过',self.text('references/protocol.md'))

if __name__=='__main__': unittest.main(verbosity=2)
