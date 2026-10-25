"""Human-facing workspace commands. Only application state and allowlisted reads."""
import argparse
from dataclasses import asdict
import json
import time

from .goals import TARGETS, assessment, assess_all, scope_matches
from .probes import plan_probes, run_probes, definitions
from .records import stamp
from .workspace import Workspace, SCENARIO_CRITERIA

COMMANDS = {'workspace-init', 'workspace-show', 'assess', 'probe-plan', 'probe-run', 'probe-results',
            'intent-show', 'intent-revise', 'intent-history', 'intent-diff', 'graph-delta',
            'plan-create', 'plan-evaluate'}


def human(result):
    lines = ['EXPERIMENTAL DEVELOPER PREVIEW', 'SYSTEM MUTATIONS: DISABLED | PROPOSED ACTIONS: NOT EXECUTED']
    if 'intent' in result:
        i = result['intent']
        lines += [f'CURRENT INTENT r{i["revision"]}: {i["objective"]}',
                  'ACCEPTANCE CRITERIA: ' + ', '.join(i['acceptance_criteria']),
                  'EXCLUDED: ' + (', '.join(i['exclusions']) or 'none')]
    for requirement, a in result.get('assessments', {}).items():
        lines += [f'{requirement}: {a["status"]}', '  ' + a['explanation']]
        if a['verified_satisfaction_path']:
            lines.append('  PATH: ' + ' + '.join(a['verified_satisfaction_path']['nodes']))
        if a['needs_verification']:
            lines.append('  VERIFY: ' + ', '.join(a['needs_verification']))
    if 'probe_plan' in result:
        plan = result['probe_plan']
        lines += ['NEXT READ-ONLY PROBES: ' + (', '.join(plan['probes_to_run']) or 'none runnable')]
        for entry in plan['entries']:
            if entry['requirement_timing'] == 'REQUIRED_NOW':
                lines.append(f'  {entry["fact"]}: {entry["classification"]} ({entry["action"]})')
        lines.append('DELIBERATELY AVOIDED: ' + ', '.join(plan['avoided_facts']))
    if 'delta' in result and result['delta']:
        d = result['delta']
        lines += [f'INTENT REVISION {d["previous_revision"]} -> {d["current_revision"]}',
                  'REMOVED: ' + (', '.join(d['removed_requirements']) or 'none'),
                  'ADDED: ' + (', '.join(d['added_requirements']) or 'none'),
                  'UNCHANGED: ' + ', '.join(d['unchanged_requirements']),
                  'INVALIDATED PLANS: ' + (', '.join(d['invalidated_plans']) or 'none')]
    if 'plan' in result:
        lines.append('PLAN: ' + result['plan']['id'])
    if 'plan_evaluation' in result:
        lines += ['PLAN DECISION: ' + result['plan_evaluation']['decision'], result['plan_evaluation']['reason']]
    if 'probe_result' in result:
        for e in result['probe_result']['probe_records']:
            lines.append(f'OBSERVATION {e["target_fact"]}: {e["classification"]} ({e["result"]})')
    if 'history' in result:
        lines += [f'r{r["revision"]}: {r["objective"]} — {r["reason"]}' for r in result['history']]
    if 'comparison' in result:
        d = result['comparison']
        lines += ['REMOVED CRITERIA: ' + ', '.join(d['removed_criteria']),
                  'ADDED CRITERIA: ' + ', '.join(d['added_criteria'])]
    if 'probe_records' in result:
        lines += [f'{p["target_fact"]}: {p.get("current_state", p["classification"])} [{p["id"]}]' for p in result['probe_records']]
    if 'reality' in result:
        lines.append(f'CURRENT REALITY: {result["reality"]["id"]} v{result["reality"]["version"]} ({result["mode"]})')
    lines += ['Use --json for complete evidence, timestamps and version references.']
    return '\n'.join(lines)


def workspace_main(argv):
    parser = argparse.ArgumentParser(description='Human-controlled goals, evidence and minimal read-only observation')
    sub = parser.add_subparsers(dest='command', required=True)
    for name in sorted(COMMANDS):
        cmd = sub.add_parser(name)
        cmd.add_argument('--workspace', required=True, help='explicit application-owned state directory')
        cmd.add_argument('--json', action='store_true', help='full machine-readable records')
        if name == 'workspace-init':
            cmd.add_argument('--scenario', choices=SCENARIO_CRITERIA, default='live')
            cmd.add_argument('--objective', required=True)
            cmd.add_argument('--criterion', choices=TARGETS, action='append')
            cmd.add_argument('--min-storage', type=int, default=1)
        elif name == 'assess':
            cmd.add_argument('--requirement', choices=TARGETS)
        elif name == 'probe-run':
            cmd.add_argument('--probe', choices=definitions(), action='append')
        elif name == 'intent-revise':
            cmd.add_argument('--objective')
            for option in ('add', 'remove', 'exclude', 'include'):
                cmd.add_argument('--' + option, choices=TARGETS, action='append', default=[])
            cmd.add_argument('--narrow', help='native=native_portable')
            cmd.add_argument('--reason', required=True)
            cmd.add_argument('--confirm', action='store_true', required=True, help='human confirms these exact changes')
        elif name == 'intent-diff':
            cmd.add_argument('--from-revision', type=int, required=True)
            cmd.add_argument('--to-revision', type=int, required=True)
        elif name == 'plan-create':
            cmd.add_argument('--requirement', choices=TARGETS, required=True)
            cmd.add_argument('--operation', choices=['install', 'build', 'reuse'], default='reuse')
            cmd.add_argument('--component')
        elif name == 'plan-evaluate':
            cmd.add_argument('--plan', required=True)
    args = parser.parse_args(argv)
    # Import lazily to avoid a CLI import cycle.
    from .cli import envelope
    try:
        app = Workspace(args.workspace)
        with app.locked():
            if args.command == 'workspace-init':
                app.initialize(args.scenario, args.objective, args.criterion, args.min_storage)
                app.save()
            else:
                app.load()
            payload = {'workspace': str(app.workspace), 'mode': app.mode,
                       'intent': asdict(app.intent), 'warnings': app.warnings,
                       'reality_scope': 'explicit hypothetical fixture' if app.mode == 'simulated' else 'read-only scoped live observations; not a machine-wide inventory',
                       'system_modifications': 'NONE', 'proposed_actions': 'NOT_EXECUTED'}
            if args.command in {'workspace-init', 'workspace-show', 'assess'}:
                payload['assessments'] = ({args.requirement: assessment(app, args.requirement)}
                    if args.command == 'assess' and args.requirement else assess_all(app))
                reality = asdict(app.reality)
                reality['derived_capabilities'] = {r: a['verified_satisfaction_path'] for r, a in payload['assessments'].items()}
                for fact in reality['facts'].values():
                    fact['current_state'] = ('STALE' if fact['classification'] in {'VERIFIED', 'OBSERVED'}
                        and (time.time() > fact['observed_at'] + fact['ttl_seconds']
                             or not scope_matches(app, fact['id'], app.evidence.get(fact['evidence_id'], {}))) else fact['classification'])
                payload['reality'] = reality
                payload['capability_graph'] = asdict(app.graph)
            if args.command == 'probe-plan':
                payload['probe_plan'] = plan_probes(app)
            elif args.command == 'probe-run':
                result = run_probes(app, args.probe)
                app.events.append({'type': 'READ_ONLY_OBSERVATIONS', 'timestamp': stamp(),
                                   'intent_revision': app.intent.revision, 'result': result})
                app.save()
                payload['probe_result'], payload['assessments'] = result, assess_all(app)
            elif args.command == 'probe-results':
                payload['probe_records'] = app.observations()
            elif args.command == 'intent-revise':
                payload['delta'] = app.revise(reason=args.reason, objective=args.objective,
                    add=args.add, remove=args.remove, exclude=args.exclude, include=args.include, narrow=args.narrow)
                app.save()
                payload['intent'] = asdict(app.intent)
                payload['assessments'], payload['probe_plan'] = assess_all(app), plan_probes(app)
            elif args.command == 'intent-history':
                payload['history'] = app.history
            elif args.command == 'intent-diff':
                payload['comparison'] = app.diff(args.from_revision, args.to_revision)
            elif args.command == 'graph-delta':
                payload['delta'] = app.last_delta
            elif args.command == 'plan-create':
                payload['plan'] = app.create_plan(args.requirement, args.operation, args.component)
                app.save()
            elif args.command == 'plan-evaluate':
                payload['plan_evaluation'] = app.evaluate_plan(args.plan)
                app.events.append({'type': 'PLAN_EVALUATED', 'timestamp': stamp(), 'result': payload['plan_evaluation']})
                app.save()
            result = envelope(**payload)
        print(json.dumps(result, indent=2, sort_keys=True) if args.json else human(result))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps(envelope(error=str(exc))) if args.json else 'Error: ' + str(exc))
        return 2
