#!/usr/bin/env python3
"""Offline checks for the delivered Skill examples and references, not a runtime gate.

Python 3.9+, standard library only. Does not invoke agents or modify the project.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

NAMES=('run','task','review','command','decision','release','supervision')
COMMON={'AUTH-01','AUTH-02','EVID-01','EVID-02','SAFE-01','BUDGET-01','FALLBACK-01','CHANGE-01'}
RULES=COMMON | {f'CEN-{i:02}' for i in range(1,8)}
TAGS={'reviewer-subordination','authorized-release','delegated-api-change','review-shopping','central-author-acceptance','all-role-fencing','fact-decision-separation','supervisor-scope','supervisor-safety','instruction-alignment','human-only-oversight','commander-delivery','supervision-not-verification'}

def validate(root: Path) -> dict:
    root=root.resolve()
    checks=[]
    def add(name,ok,detail=''):
        checks.append({'name':name,'ok':bool(ok),'detail':str(detail)})
    def text(rel):
        path=root/rel
        try:
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError('symlink/out-of-root reference')
            value=path.read_text(encoding='utf-8-sig')
            add('file:'+rel,True)
            return value
        except (OSError,UnicodeError,ValueError) as exc:
            add('file:'+rel,False,exc)
            return ''
    def obj(parent,key,label):
        value=parent.get(key)
        add(label+':'+key+'-object',isinstance(value,dict))
        return value if isinstance(value,dict) else {}
    def strings(parent,key,label):
        value=parent.get(key)
        valid=isinstance(value,list) and all(isinstance(v,str) for v in value)
        add('malformed-structure:'+label+':'+key,valid)
        return value if valid else []
    main=text('SKILL.md')
    protocol=text('references/protocol.md')
    for rel in ('README.zh-CN.md','CHANGELOG.md','scripts/validate_skill.py','tests/test_skill.py'):
        text(rel)
    fm=re.match(r'\A---\n(.*?)\n---\n',main,re.S)
    add('frontmatter',fm is not None)
    if fm:
        meta=dict(re.findall(r'^(name|description): (.+)$',fm.group(1),re.M))
        add('stable-name',meta.get('name')=='gas-centralized-development')
        description=meta.get('description','')
        add('description',description.startswith('Use when ') and len(description)<500)
        add('metadata-size',len(fm.group(1))<=1024)
    add('short-display-name','# 集权开发模式技能\n' in main)
    add('main-length',len(main.splitlines())<=120)
    for h in ('启动与适用边界','权责边界','执行流程','停止与升级','交付格式'):
        add('heading:'+h,'## '+h in main)
    defined=set(re.findall(r'^### ([A-Z]+-\d{2})：',protocol,re.M))
    referenced=set(re.findall(r'\b[A-Z]+-\d{2}\b',main+'\n'+protocol))
    add('defined-rules',RULES<=defined and referenced<=defined)
    for term in ('权限隔离','worktree','未执行','不自动','独立判断','管理接受'):
        add('boundary:'+term,term in main+protocol)
    for path in sorted(root.rglob('*.md')):
        if path.is_symlink():
            add('link:symlink:'+str(path),False)
            continue
        try:
            content=path.read_text(encoding='utf-8-sig')
        except (OSError,UnicodeError) as exc:
            add('file:'+path.relative_to(root).as_posix(),False,exc)
            continue
        for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)',content):
            if link.startswith(('http:','https:','#')):
                continue
            dest=(path.parent/link.split('#')[0]).resolve()
            add('link:'+path.name+':'+link,dest.is_relative_to(root) and dest.is_file())
    docs={}
    for name in NAMES:
        raw=text(f'templates/{name}.example.json')
        try:
            d=json.loads(raw)
            if not isinstance(d,dict):
                raise ValueError('root must be an object')
            docs[name]=d
            add(name+':json',True)
            add(name+':schema',type(d.get('schema_version')) is int and d.get('schema_version')==3)
            add(name+':example-only',d.get('example_only') is True)
        except (ValueError,TypeError) as exc:
            add(name+':json',False,exc)
            docs[name]={}
    run=docs['run']; task=docs['task']; review=docs['review']; command=docs['command']; decision=docs['decision']; delivery=docs['release']
    # Every declared nested contract remains an object even before it is populated.
    for record, fields in {'command':('scope','budget'), 'release':('target',),
                           'run':('dispatch',), 'task':('budget','test_plan','dispatch','integration','release')}.items():
        for key in fields:
            obj(docs[record],key,record)
    approval=obj(run,'approval','run')
    add('run:unapproved',approval.get('approved') is False and approval.get('record') is None)
    delegation=obj(run,'delegation','run')
    add('run:delegation-unapproved',delegation.get('approved') is False and delegation.get('authorization_ref') is None)
    add('run:technical-delegation','internal_api_changes' in strings(delegation,'technical_decisions','delegation'))
    scope=obj(run,'command_scope','run')
    add('run:all-roles',set(strings(scope,'roles','command_scope'))=={'executor','reviewer','supervisor'} and scope.get('authority')=='current-coordinator')
    add('run:supervision-actions',{'SUPERVISE','RECHECK_SUPERVISION'}<=set(strings(scope,'accepted_command_types','command_scope')))
    responsibility=obj(run,'delivery_responsibility','run')
    add('delivery:commander-owner',responsibility.get('owner_role')=='coordinator' and responsibility.get('separate_integrator_required') is False)
    supervision=obj(run,'supervision','run')
    add('supervision:target-roles',set(strings(supervision,'target_roles','supervision'))=={'executor','reviewer'})
    add('supervision:reports-to',supervision.get('reports_to')=='coordinator')
    add('supervision:human-oversight',supervision.get('commander_supervised_by')=='human-only')
    add('supervision:coverage',set(strings(supervision,'coverage_requirements','supervision'))=={'rule_compliance','unsafe_actions','instruction_alignment'})
    add('supervision:required',supervision.get('required_before_acceptance') is True and supervision.get('independence_required') is True)
    add('supervision:limited-authority',all(supervision.get(k) is False for k in ('can_modify_artifacts','can_assign_tasks','can_release')))
    pause=obj(supervision,'pause_authority','supervision')
    add('supervision:pause-ungranted',pause.get('granted') is False and pause.get('authorization_ref') is None and pause.get('task_ids')==[] and pause.get('coordinator_epoch') is None and pause.get('expires_at') is None and pause.get('revoked') is False)
    controls=obj(run,'controls','run')
    add('run:production-disabled',controls.get('production_release_enabled') is False)
    add('run:independent-review-required',controls.get('independent_review_required') is True)
    add('run:exact-commit-required',controls.get('require_exact_commit_checks') is True)
    add('run:unconfigured-gates',controls.get('mandatory_gates_configured') is False and controls.get('mandatory_gate_ids')==[])
    add('run:no-release-authorization',run.get('release_authorizations')==[])
    policy=obj(controls,'findings_policy','controls')
    add('run:non-waivable-blockers',policy.get('blocking_override_by_coordinator') is False and policy.get('review_history_append_only') is True)
    runtime=obj(run,'runtime','run')
    for key in ('subagents_verified','permission_isolation_verified','single_authority_verified','command_fencing_verified','idempotency_enforcement_verified','supervision_available_verified','budget_enforcement_verified','isolated_workspaces_verified'):
        add('runtime:'+key,runtime.get(key) is False)
    add('runtime:supervisor-unknown',runtime.get('supervisor_identity') is None and 'supervisor_identity' in runtime and 'integrator_identity' not in runtime)
    budget=obj(run,'budget','run')
    for key in ('max_active_workers','max_tool_calls_total','max_task_attempts','max_review_rounds','max_conflict_rounds'):
        add('budget:'+key,type(budget.get(key)) is int and budget[key]>0)
    reserves=[budget.get(k) for k in ('reserved_tool_calls_for_review','reserved_tool_calls_for_supervision')]
    add('budget:reserves-within-total',all(type(v) is int and v>=0 for v in reserves) and type(budget.get('max_tool_calls_total')) is int and sum(reserves)<=budget['max_tool_calls_total'])
    add('task:draft',task.get('state')=='DRAFT' and task.get('evidence')==[] and task.get('head_commit') is None)
    v=obj(task,'verification','task'); md=obj(task,'management_decision','task')
    add('task:two-records',v.get('status')=='NOT_RUN' and md.get('status')=='NOT_DECIDED')
    add('task:verification-unrun',v.get('required_checks_passed') is None and v.get('independent_review_satisfied') is False and v.get('review_refs')==[])
    ts=obj(task,'supervision','task')
    add('task:supervision-default',ts.get('required') is True and ts.get('status')=='NOT_RUN' and ts.get('report_refs')==[])
    required={'command_id','assignment_id','task_id','issued','issued_by','coordinator_epoch','recipient_identity','recipient_role','action','plan_version','contract_version','base_commit','head_commit','artifact_digest','issued_at','expires_at','revoked','acknowledged','acknowledged_at','supersedes_command_id','idempotency_key','scope','budget'}
    add('command-fields',required<=command.keys())
    add('command-unissued',command.get('issued') is False and command.get('acknowledged') is False and command.get('issued_by') is None)
    add('command:review-subordinate',command.get('recipient_role')=='reviewer' and command.get('action')=='REVIEW')
    add('review-not-management',review.get('record_type')=='verification' and 'release_authorized' not in review and 'decision' not in review)
    add('review:not-run',review.get('verdict')=='NOT_RUN' and review.get('checks')==[] and review.get('findings')==[])
    add('review-independent-default',review.get('independence_verified') is False and review.get('reviewer_identity') is None)
    add('review:unverified-default',review.get('required_checks_passed') is None and review.get('mandatory_gates_configured') is False)
    ra=obj(review,'review_assignment','review')
    add('review:assigned',{'command_id','assigned_by','coordinator_epoch','acknowledged'}<=ra.keys())
    add('decision-not-decided',decision.get('record_type')=='management_decision' and decision.get('decision')=='NOT_DECIDED' and decision.get('verification_refs')==[])
    ac=obj(decision,'acceptance_preconditions','decision')
    add('decision:unknown-preconditions',ac.get('required_checks_passed') is None and ac.get('independent_review_satisfied') is False and ac.get('unresolved_blocking_count') is None and ac.get('unresolved_major_risk_count') is None)
    add('decision:supervision-default',decision.get('supervision_refs')==[] and ac.get('supervision_satisfied') is False)
    add('decision:platform-approval-unknown',ac.get('platform_approvals_satisfied') is None)
    add('decision:history-fields',{'dissenting_review_refs','advisory_dispositions','blocking_dispositions'}<=decision.keys())
    dc=obj(delivery,'command','delivery'); da=obj(delivery,'authorization','delivery'); de=obj(delivery,'execution','delivery')
    dp=obj(delivery,'preconditions','delivery')
    add('delivery:three-inputs',{'command','authorization','verification_refs','management_decision_ref','target'}<=delivery.keys())
    add('delivery:unissued',dc.get('issued') is False and da.get('approved') is False)
    add('delivery:commander-recipient',delivery.get('record_type')=='commander_delivery_action' and dc.get('recipient_role')=='coordinator')
    add('delivery:commander-executor',de.get('executor_role')=='coordinator' and de.get('executor_identity') is None)
    add('delivery:supervision-default',delivery.get('supervision_refs')==[] and dp.get('supervision_satisfied') is False)
    add('delivery-not-run',de.get('status')=='NOT_RUN' and de.get('platform_receipt') is None and de.get('observed_artifact') is None)
    add('delivery:unknown-preconditions',dp.get('current_command_verified') is False and dp.get('required_checks_passed') is None and dp.get('authorization_matches_target') is False)
    add('delivery:independent-review-unverified',dp.get('independent_review_satisfied') is False)
    add('delivery:unknown-gates',all(k in dp and dp[k] is None for k in ('platform_approvals_satisfied','unresolved_blocking_count','unresolved_major_risk_count','budget_available')) and dp.get('idempotency_state_known') is False)
    action=delivery.get('action')
    add('delivery:verification-scope',action in ('PREPARE_INTEGRATION','MERGE','DEPLOY','ROLLBACK') and dp.get('verification_scope')==('accepted-source-tasks' if action=='PREPARE_INTEGRATION' else 'delivery-target'))
    add('delivery:idempotency',delivery.get('idempotency_key') is None and 'idempotency_key' in delivery and 'rollback_authorization_ref' in delivery)
    sr=docs['supervision']
    add('supervision:record-type',sr.get('record_type')=='supervision' and 'decision' not in sr and 'release_authorized' not in sr)
    add('supervision:not-run',sr.get('status')=='NOT_RUN' and all(sr.get(k)==[] for k in ('checks','findings','pause_actions')))
    add('supervision:identity-unknown',sr.get('supervisor_identity') is None and sr.get('independence_verified') is False and sr.get('reports_to_role')=='coordinator' and sr.get('reports_to_identity') is None)
    ss=obj(sr,'scope','supervision-report')
    add('supervision:report-targets',set(strings(ss,'target_roles','supervision-report'))=={'executor','reviewer'} and ss.get('subject_identities')==[] and ss.get('command_refs')==[])
    sa=obj(sr,'assignment','supervision-report')
    add('supervision:unassigned',{'command_id','assigned_by','acknowledged'}<=sa.keys() and sa.get('command_id') is None and sa.get('assigned_by') is None and sa.get('acknowledged') is False)
    sc=obj(sr,'coverage','supervision-report')
    add('supervision:coverage-not-run',set(sc)=={'rule_compliance','unsafe_actions','instruction_alignment'} and all(v=='NOT_RUN' for v in sc.values()))
    add('supervision:history',sr.get('prior_report_refs')==[] and sr.get('supersedes_report_id') is None and bool(sr.get('unverified_items')))
    for name,d in docs.items():
        add(name+':run-binding',d.get('run_id')==run.get('run_id') and bool(run.get('run_id')))
        add(name+':contract-binding',d.get('contract_version')==run.get('contract_version') and bool(run.get('contract_version')))
        if name not in ('run','task'):
            add(name+':task-binding',d.get('task_id')==task.get('id') and bool(task.get('id')))
    raw=text('evals/scenarios.json')
    try:
        s=json.loads(raw); cases=s.get('cases',[])
        add('scenarios:count',len(cases)>=48)
        ids=[c.get('id') for c in cases]
        add('scenarios:valid-ids',all(isinstance(i,str) and i.strip() for i in ids))
        add('scenarios:unique-ids',len(set(ids))==len(ids))
        add('scenarios:behavior-not-run',s.get('execution_status')=='NOT_RUN' and all(c.get('status')=='NOT_RUN' for c in cases))
        used={r for c in cases for r in c.get('rules',[])}
        add('scenarios:defined-rules',RULES<=used and used<=defined)
        tags={t for c in cases for t in c.get('tags',[])}
        add('scenarios:positive-scenarios',TAGS<=tags)
        add('scenarios:assertions',all(c.get('prompt') and c.get('expected_actions') and c.get('failure_actions') for c in cases))
        add('scenarios:combined-pressure',any(len(c.get('pressures',[]))>=3 for c in cases))
    except (ValueError,TypeError,AttributeError) as exc:
        add('scenarios:json',False,exc)
    failed=sum(not c['ok'] for c in checks)
    return {'scope':'static Skill package checks; not agent behavior or enforced runtime permissions','ok':failed==0,'check_count':len(checks),'failed_count':failed,'checks':checks}

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    result=validate(args.root)
    for item in result['checks']:
        if not item['ok']:
            print('FAIL',item['name'],item['detail'])
    print('Static checks: {}/{} passed'.format(result['check_count']-result['failed_count'],result['check_count']))
    print(result['scope'])
    if args.report:
        args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0 if result['ok'] else 1

if __name__=='__main__': sys.exit(main())
