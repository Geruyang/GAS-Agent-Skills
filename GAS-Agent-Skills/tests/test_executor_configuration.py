"""Check executor configuration and unobserved ownership without attesting live teams."""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verify_bundle import validate

NAMES = ('gas-centralized-development', 'gas-decentralized-development', 'gas-combined-development')
OFFSETS = dict(zip(NAMES, (3, 2, 5)))

class ExecutorConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='gas-executors-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in NAMES:
            shutil.copytree(ROOT / name, self.root / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))

    def mutate(self, name, relative, change, suffix, accepted=False):
        path = self.root / name / relative
        before = path.read_bytes()
        record = json.loads(before)
        change(record)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        try:
            result = validate(self.root, [name])
            if accepted:
                self.assertTrue(result['passed'], [x for x in result['checks'] if not x['passed']])
            else:
                self.assertTrue(any(not x['passed'] and x['check'].endswith(suffix) for x in result['checks']), suffix)
        finally:
            path.write_bytes(before)

    def team(self, record):
        # Supplying valid defaults also tests validators against older/missing templates.
        return record.setdefault('execution_team', {'executor_count': 1, 'count_source': 'default',
            'executor_roster': [], 'assignments': [], 'planned_distinct_subagents': 1 + OFFSETS[self.name]})

    def test_nonpositive_or_coerced_counts_rejected(self):
        for name in NAMES:
            self.name = name
            for value in (0, -1, True, 1.0, '3', None):
                with self.subTest(name=name, value=value):
                    self.mutate(name, 'templates/run.example.json', lambda r, v=value: self.team(r).update(executor_count=v), ':execution-team:count')

    def test_missing_or_malformed_team_rejected(self):
        for name in NAMES:
            for value in (None, [], True, 'team'):
                with self.subTest(name=name, value=value):
                    self.mutate(name, 'templates/run.example.json', lambda r, v=value: r.update(execution_team=v), ':execution-team:count')
            self.mutate(name, 'templates/run.example.json', lambda r: r.pop('execution_team', None), ':execution-team:count')

    def test_headcount_cannot_omit_executors_or_bridge(self):
        for name in NAMES:
            self.name = name
            self.mutate(name, 'templates/run.example.json', lambda r: self.team(r).update(planned_distinct_subagents=OFFSETS[name]), ':execution-team:headcount')

    def test_unknown_count_source_rejected(self):
        for name in NAMES:
            self.name = name
            self.mutate(name, 'templates/run.example.json', lambda r: self.team(r).update(count_source='implicit-confirmation'), ':execution-team:count-source')

    def test_example_cannot_invent_roster_or_assignments(self):
        for name in NAMES:
            self.name = name
            for field in ('executor_roster', 'assignments'):
                with self.subTest(name=name, field=field):
                    self.mutate(name, 'templates/run.example.json', lambda r, k=field: self.team(r).update({k: [{'executor_identity': 'fabricated'}]}), ':execution-team:unassigned-example')

    def test_runtime_cannot_invent_verification_ownership(self):
        for name in NAMES:
            for field in ('executor_identity', 'analysis_owner_identity'):
                with self.subTest(name=name, field=field):
                    self.mutate(name, 'templates/runtime.example.json', lambda r, k=field: r.setdefault('verification_ownership', {}).update({k: 'fabricated'}), ':verification-ownership:unobserved')

    def test_review_roles_cannot_gain_verification_code_permission(self):
        for name in NAMES:
            relative = 'templates/run.example.json' if name == NAMES[2] else 'templates/review.example.json'
            def change(record):
                if name == NAMES[0]:
                    record['reviewer_may_write_verification_code'] = True
                elif name == NAMES[1]:
                    record['review_boundary']['test_code_write_allowed'] = True
                else:
                    record['controls']['reviewers_write_test_code'] = True
            with self.subTest(name=name):
                self.mutate(name, relative, change, ':review-code-boundary')

    def test_three_executor_configuration_remains_unapproved_and_valid(self):
        for name in NAMES:
            def change(record):
                team = record['execution_team']
                team.update(executor_count=3, count_source='proposed', planned_distinct_subagents=3+OFFSETS[name])
                if 'planned_total_sessions' in team:
                    team['planned_total_sessions'] = 4+OFFSETS[name]
                if name == 'gas-centralized-development':
                    record['budget']['max_active_workers'] = 3
                elif name == 'gas-decentralized-development':
                    record['budget'].update(max_active_workers=3, max_active_agents=5)
                    record['governance']['agent_count'] = 5
                    record['dispatch']['method'] = 'peer-executor-self-claim'
            with self.subTest(name=name):
                self.mutate(name, 'templates/run.example.json', change, '', accepted=True)

if __name__ == '__main__':
    unittest.main()
