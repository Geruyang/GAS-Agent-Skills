"""Mutation tests for the static checker. They do not test model behavior."""
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class StaticCheckerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'gas-centralized-development'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns('__pycache__'))
    def validate(self):
        path=ROOT/'scripts/validate_skill.py'
        self.assertTrue(path.is_file(), 'static checker not implemented')
        spec=importlib.util.spec_from_file_location('validate_skill',path)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.validate(self.root)
    def edit(self, name, fn):
        p=self.root/name
        obj=json.loads(p.read_text(encoding='utf-8'))
        fn(obj)
        p.write_text(json.dumps(obj,ensure_ascii=False),encoding='utf-8')
    def rejected(self, fragment):
        result=self.validate()
        self.assertFalse(result['ok'])
        failures=[c['name'] for c in result['checks'] if not c['ok']]
        self.assertTrue(any(fragment in n for n in failures), failures)
    def test_valid_bundle(self):
        result=self.validate()
        self.assertTrue(result['ok'], [c for c in result['checks'] if not c['ok']])
    def test_missing_decision(self):
        (self.root/'templates/decision.example.json').unlink()
        self.rejected('decision')
    def test_invalid_json(self):
        (self.root/'templates/run.example.json').write_text('{',encoding='utf-8')
        self.rejected('run')
    def test_wrong_schema(self):
        self.edit('templates/task.example.json',lambda x:x.update(schema_version=1))
        self.rejected('schema')
    def test_live_example(self):
        self.edit('templates/run.example.json',lambda x:x.update(example_only=False))
        self.rejected('example-only')
    def test_fake_approval(self):
        self.edit('templates/run.example.json',lambda x:x['approval'].update(approved=True))
        self.rejected('unapproved')
    def test_production_default(self):
        self.edit('templates/run.example.json',lambda x:x['controls'].update(production_release_enabled=True))
        self.rejected('production-disabled')
    def test_missing_review_role(self):
        self.edit('templates/run.example.json',lambda x:x['command_scope'].update(roles=['executor','integrator']))
        self.rejected('all-roles')
    def test_missing_delegation(self):
        self.edit('templates/run.example.json',lambda x:x['delegation'].update(technical_decisions=[]))
        self.rejected('technical-delegation')
    def test_granted_delegation(self):
        self.edit('templates/run.example.json',lambda x:x['delegation'].update(approved=True))
        self.rejected('delegation-unapproved')
    def test_missing_command_epoch(self):
        self.edit('templates/command.example.json',lambda x:x.pop('coordinator_epoch'))
        self.rejected('command-fields')
    def test_live_command(self):
        self.edit('templates/command.example.json',lambda x:x.update(issued=True))
        self.rejected('command-unissued')
    def test_fake_independence(self):
        self.edit('templates/review.example.json',lambda x:x.update(independence_verified=True))
        self.rejected('review-independent-default')
    def test_review_claims_release_power(self):
        self.edit('templates/review.example.json',lambda x:x.update(release_authorized=True))
        self.rejected('review-not-management')
    def test_accept_without_execution(self):
        self.edit('templates/decision.example.json',lambda x:x.update(decision='ACCEPT'))
        self.rejected('decision-not-decided')
    def test_fake_release_receipt(self):
        self.edit('templates/release.example.json',lambda x:x['execution'].update(status='SUCCEEDED',platform_receipt='fake'))
        self.rejected('delivery-not-run')
    def test_invalid_rule_reference(self):
        self.edit('evals/scenarios.json',lambda x:x['cases'][0]['rules'].append('FAKE-99'))
        self.rejected('defined-rules')
    def test_missing_positive_scenario(self):
        self.edit('evals/scenarios.json',lambda x:[c.update(tags=[]) for c in x['cases']])
        self.rejected('positive-scenarios')
    def test_fake_behavior_pass(self):
        self.edit('evals/scenarios.json',lambda x:x['cases'][0].update(status='PASS'))
        self.rejected('behavior-not-run')
    def test_broken_link(self):
        p=self.root/'SKILL.md'
        p.write_text(p.read_text(encoding='utf-8')+'\n[broken](references/missing.md)\n',encoding='utf-8')
        self.rejected('link')
    def test_missing_protocol_rule(self):
        p=self.root/'references/protocol.md'
        p.write_text(p.read_text(encoding='utf-8').replace('### CEN-06：','### NOTE：'),encoding='utf-8')
        self.rejected('defined-rules')
    def test_cross_record_task_mismatch(self):
        self.edit('templates/review.example.json',lambda x:x.update(task_id='OTHER'))
        self.rejected('task-binding')
    def test_malformed_nested_object(self):
        self.edit('templates/run.example.json',lambda x:x.update(controls=[]))
        self.rejected('controls')
    def test_boolean_not_integer_budget(self):
        self.edit('templates/run.example.json',lambda x:x['budget'].update(max_tool_calls_total=True))
        self.rejected('budget')

    def test_null_roles_rejected_without_crash(self):
        self.edit('templates/run.example.json',lambda x:x['command_scope'].update(roles=None))
        self.rejected('malformed-structure')
    def test_nonstring_role_rejected_without_crash(self):
        self.edit('templates/run.example.json',lambda x:x['command_scope'].update(roles=[{}]))
        self.rejected('malformed-structure')
    def test_null_delegation_rejected_without_crash(self):
        self.edit('templates/run.example.json',lambda x:x['delegation'].update(technical_decisions=None))
        self.rejected('malformed-structure')

if __name__=='__main__': unittest.main(verbosity=2)
