"""Negative tests for illustrative contracts, not runtime enforcement."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verify_bundle import validate

NAME = 'gas-decentralized-development'


class SeparationContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gas-separation-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / NAME, self.root / NAME)

    def mutate(self, file, change):
        path = self.root / NAME / 'templates' / (file + '.example.json')
        value = json.loads(path.read_text(encoding='utf-8-sig'))
        change(value)
        path.write_text(json.dumps(value), encoding='utf-8')

    def assert_bad(self, suffix):
        report = validate(self.root, [NAME])
        self.assertTrue(any(not c['passed'] and c['check'].endswith(suffix)
                            for c in report['checks']), report)

    def test_current_examples_valid(self):
        report = validate(self.root, [NAME])
        self.assertTrue(report['passed'], report)

    def test_fourth_governing_role_rejected(self):
        self.mutate('run', lambda d: d.setdefault('governance', {}).setdefault('roles', {}).update(supervisor={}))
        self.assert_bad(':separation:three-roles')

    def test_missing_separation_configuration_rejected(self):
        self.mutate('run', lambda d: d.pop('governance', None))
        self.assert_bad(':separation:three-roles')

    def test_extra_implementation_worker_rejected(self):
        self.mutate('run', lambda d: d['budget'].update(max_active_workers=2))
        self.assert_bad(':separation:single-executor')

    def test_dispatch_cannot_restore_multiple_worker_race(self):
        self.mutate('run', lambda d: d['dispatch'].update(method='atomic-self-claim'))
        self.assert_bad(':dispatch-distinction')

    def test_malformed_governance_fails_without_crash(self):
        for value in (None, [], True, 'invalid', 4):
            with self.subTest(value=value):
                self.mutate('run', lambda d: d.update(governance=value))
                self.assert_bad(':separation:three-roles')

    def test_self_review_role_rejected(self):
        self.mutate('review', lambda d: d.update(reviewer_role='executor'))
        self.assert_bad(':separation:independent-arbiter')

    def test_missing_dispute_record_rejected(self):
        path = self.root / NAME / 'templates/dispute.example.json'
        if path.exists():
            path.unlink()
        self.assert_bad(':separation:dispute-json')

    def test_missing_dispute_epochs_rejected(self):
        self.mutate('dispute', lambda d: d['resolution'].pop('decided_by_epoch', None))
        self.assert_bad(':separation:dispute-epochs')

    def test_fabricated_dispute_epoch_rejected(self):
        self.mutate('dispute', lambda d: d.update(raised_by_epoch=2))
        self.assert_bad(':separation:dispute-epochs')

    def test_fabricated_release_rejected(self):
        path = self.root / NAME / 'templates/release.example.json'
        path.write_text(json.dumps({'example_only': True, 'status': 'RELEASED', 'actor_role': 'executor'}), encoding='utf-8')
        self.assert_bad(':separation:release-not-run')

    def test_missing_intent_review_rejected(self):
        self.mutate('run', lambda d: d['contract'].pop('intent_review', None))
        self.assert_bad(':separation:intent-review-not-run')

    def test_fabricated_human_consent_rejected(self):
        self.mutate('dispute', lambda d: d.setdefault('intent_change', {}).update(human_decision='APPROVED'))
        self.assert_bad(':separation:intent-change-not-approved')

    def test_missing_rule_reconsideration_rejected(self):
        self.mutate('dispute', lambda d: d.pop('rule_reconsideration', None))
        self.assert_bad(':separation:rule-reconsideration-not-decided')


if __name__ == '__main__':
    unittest.main()
