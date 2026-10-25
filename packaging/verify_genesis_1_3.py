"""Independent installed-wheel and frozen-EXE acceptance; A-I evidence per target."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from verify_artifacts import verify as legacy_verify


def verify_goals(python, exe=None):
    results = {}
    with tempfile.TemporaryDirectory(prefix='awareness-g13-independent-') as directory:
        root = Path(directory)
        repo = Path(__file__).resolve().parents[1]
        assert not root.is_relative_to(repo)
        env = {k: v for k, v in os.environ.items() if k not in {'PYTHONPATH', 'PYTHONHOME'}}
        targets = {'wheel': [str(Path(python).with_name('awareness-kernel.exe'))]}
        if exe:
            copied = root / 'AwarenessKernel.exe'
            shutil.copyfile(exe, copied)
            targets['exe'] = [str(copied)]
        for target, command in targets.items():
            workspace_root = root / (target + ' workspaces with spaces')
            workspace_root.mkdir()
            environment = dict(env)
            if target == 'exe':
                environment['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32')
            commands, scenarios = [], []

            def invoke(name, workspace, *arguments, expected_exit=0, human=False):
                args = [name, '--workspace', str(workspace), *arguments]
                if not human:
                    args.append('--json')
                result = subprocess.run(command + args, cwd=root, env=environment,
                    capture_output=True, text=True, timeout=40)
                record = {'args': args, 'exit_code': result.returncode,
                          'stdout': result.stdout, 'stderr': result.stderr,
                          'passed': result.returncode == expected_exit}
                commands.append(record)
                if result.returncode != expected_exit:
                    raise AssertionError(json.dumps(record))
                if human:
                    assert 'SYSTEM MUTATIONS: DISABLED' in result.stdout
                    return result.stdout
                data = json.loads(result.stdout)
                assert data['execution_enabled'] is False
                assert data['gateway_outcome'] == 'DISABLED_IN_DISTRIBUTION'
                return data

            def initialize(name, scenario, *criteria):
                ws = workspace_root / name
                args = ['--scenario', scenario, '--objective', 'Human acceptance objective: ' + name]
                for criterion in criteria:
                    args += ['--criterion', criterion]
                return ws, invoke('workspace-init', ws, *args)

            def record(identifier, initial, expected, actual, passed, explanation, evidence=None):
                scenarios.append({'scenario': identifier, 'target': target,
                    'input_intent': initial['intent'], 'starting_reality_snapshot': initial['reality'],
                    'capability_graph': initial['capability_graph'], 'expected': expected, 'actual': actual,
                    'relevant_evidence': evidence, 'explanation': explanation,
                    'execution_status': 'NOT_EXECUTED', 'passed': bool(passed)})

            # A: evidence-backed sufficiency is distinct from an unnecessary action decision.
            ws, initial = initialize('A', 'android')
            a = invoke('assess', ws)['assessments']['apk']
            p = invoke('plan-create', ws, '--requirement', 'apk', '--operation', 'install', '--component', 'sdk')['plan']
            action = invoke('plan-evaluate', ws, '--plan', p['id'])['plan_evaluation']
            record('A', initial, 'ALREADY_SATISFIED', a['status'],
                a['status'] == 'ALREADY_SATISFIED' and a['probe_evidence']
                and action['decision'] == 'REJECTED_UNNECESSARY', a['explanation'], a)

            ws, initial = initialize('B', 'portable')
            b = invoke('assess', ws)['assessments']['native']
            record('B', initial, 'ALREADY_SATISFIED through portable compiler', b['status'],
                b['status'] == 'ALREADY_SATISFIED' and b['verified_satisfaction_path']['root'] == 'cap:native-portable', b['explanation'], b)

            ws, initial = initialize('C', 'workstation')
            c = invoke('probe-plan', ws)['probe_plan']
            record('C', initial, 'No GPU/CUDA probes', c['probes_to_run'],
                'hardware:gpu' not in c['relevant_facts'] and 'pkg:cuda' not in c['relevant_facts'],
                'Simulated dedicated GPU is irrelevant to the CPU report requirement.', c)

            ws, initial = initialize('D', 'live', 'apk', 'smartphone_install')
            d = invoke('probe-plan', ws)['probe_plan']
            required = {'pkg:java', 'pkg:sdk', 'pkg:gradle', 'pkg:build_tools', 'pkg:adb', 'device:connected', 'storage'}
            record('D', initial, 'Android facts considered, unrelated GPU excluded', d['relevant_facts'],
                required <= set(d['relevant_facts']) and 'pkg:cuda' not in d['relevant_facts']
                and 'device' not in d['probes_to_run'],
                'Live plan only; no device, wrapper, SDK or tool command executed.', d)

            ws, initial = initialize('E-H', 'android-phone')
            p = invoke('plan-create', ws, '--requirement', 'emulator_test', '--operation', 'build')['plan']
            revised = invoke('intent-revise', ws, '--remove', 'emulator_test', '--objective', 'APK and phone installation only',
                             '--reason', 'Human explicitly removes emulator testing', '--confirm')
            old = invoke('plan-evaluate', ws, '--plan', p['id'])['plan_evaluation']
            delta = invoke('graph-delta', ws)['delta']
            next_probes = invoke('probe-plan', ws)['probe_plan']
            record('E', initial, 'Intent r2, old plan stale, APK retained', old['decision'],
                revised['intent']['revision'] == 2 and old['decision'] == 'REJECTED_STALE'
                and 'emulator_test' in delta['removed_requirements'] and 'apk' in delta['currently_satisfied']
                and 'pkg:emulator' not in next_probes['relevant_facts'],
                'Human revision preserves evidence and removes only the obsolete dependency branch.', delta)
            restart_input = deepcopy(initial)
            saved_state = json.loads((ws / 'awareness-state.json').read_text())
            restart_input['intent'], restart_input['reality'] = saved_state['intent'], saved_state['reality']
            reopened = invoke('workspace-show', ws)
            history = invoke('intent-history', ws)['history']
            diff = invoke('intent-diff', ws, '--from-revision', '1', '--to-revision', '2')['comparison']
            record('H', restart_input, 'History and evidence preserved across process exits', reopened['intent']['revision'],
                reopened['intent']['id'] == initial['intent']['id'] and reopened['intent']['revision'] == 2
                and len(history) == 2 and diff['removed_criteria'] == ['emulator_test']
                and reopened['reality']['id'] == initial['reality']['id'],
                'Every invocation is a fresh process. Stable identifiers and prior evidence remain saved.',
                {'history': history, 'comparison': diff, 'reality': reopened['reality']})
            invoke('intent-show', ws, human=True)

            ws, initial = initialize('F', 'android')
            path = ws / 'awareness-state.json'
            state = json.loads(path.read_text())
            state['reality']['facts']['op:apk']['observed_at'] -= 4000
            path.write_text(json.dumps(state), encoding='utf-8')
            stale_input = deepcopy(initial)
            stale_input['reality'] = deepcopy(state['reality'])
            f = invoke('assess', ws)['assessments']['apk']
            record('F', stale_input, 'NEEDS_VERIFICATION', f['status'], f['status'] == 'NEEDS_VERIFICATION',
                   'Harness explicitly expires hypothetical integration evidence; no host capability claim.', f)

            ws, initial = initialize('G', 'android')
            path = ws / 'awareness-state.json'
            state = json.loads(path.read_text())
            fact = state['reality']['facts']['op:apk']
            fact.update(classification='PROBE_FAILED', value=None, result=None, exit_status=1)
            failure = state['evidence'][fact['evidence_id']]
            failure.update(classification='PROBE_FAILED', result=None, exit_code=1,
                           error_summary='Explicit injected fixture probe failure; not a live hardware measurement')
            path.write_text(json.dumps(state), encoding='utf-8')
            failed_input = deepcopy(initial)
            failed_input['reality'] = deepcopy(state['reality'])
            g = invoke('assess', ws)['assessments']['apk']
            record('G', failed_input, 'NEEDS_VERIFICATION, not global absence', g['status'],
                   g['status'] == 'NEEDS_VERIFICATION' and g['status'] != 'ACTUAL_CAPABILITY_GAP',
                   'Distribution tests replay a declared failed fixture observation. Actual worker errors/deadlines are tested by the source suite.', g)

            ws, initial = initialize('I', 'live', 'python_runtime')
            before_env = dict(os.environ)
            before_plan = invoke('probe-plan', ws)['probe_plan']
            observed = invoke('probe-run', ws)['probe_result']
            observed_ids = set(observed['planned_probe_ids'])
            i = invoke('assess', ws)['assessments']['python_runtime']
            after_plan = invoke('probe-plan', ws)['probe_plan']
            saved = invoke('probe-results', ws)['probe_records']
            invoke('probe-run', ws, '--probe', 'locate-cuda', expected_exit=2)
            only_app_files = sorted(p.name for p in ws.iterdir()) == ['awareness-state.json']
            record('I', initial, 'Read-only runtime/storage observations; gateway disabled', i['status'],
                i['status'] == 'ALREADY_SATISFIED' and observed_ids == {'runtime', 'storage'}
                and all(r['classification'] == 'VERIFIED' and r['source_mode'] == 'live' for r in saved)
                and not after_plan['probes_to_run'] and only_app_files and before_env == dict(os.environ),
                'Actual bounded workers measured the application runtime and selected volume. No tool execution or mutation endpoint. This is not a forensic audit of the whole OS.',
                {'initial_probe_plan': before_plan, 'results': saved, 'assessment': i, 'files_only_in_selected_workspace': only_app_files})
            results[target] = {'scenarios': scenarios, 'commands': commands,
                               'passed': all(s['passed'] for s in scenarios) and all(c['passed'] for c in commands),
                               'working_directory_outside_repository': True, 'new_dependencies': [],
                               'observation_workers_tested': True, 'execution_gateway': 'DISABLED'}
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--python', required=True, type=Path)
    parser.add_argument('--exe', type=Path)
    parser.add_argument('--results', required=True, type=Path)
    args = parser.parse_args()
    python, exe = args.python.resolve(), args.exe.resolve() if args.exe else None
    legacy = legacy_verify(python, exe)
    goals = verify_goals(python, exe)
    result = {'legacy_preview_acceptance': legacy, 'goal_acceptance': goals,
              'passed': legacy['passed'] and all(g['passed'] for g in goals.values()),
              'packaged_mutation_gateway': 'DISABLED', 'supported_read_only_workers': 'TESTED'}
    args.results.parent.mkdir(parents=True, exist_ok=True)
    args.results.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': result['passed'], 'legacy_checks': len(legacy['checks']),
                      'goal_scenarios': {k: len(g['scenarios']) for k, g in goals.items()},
                      'commands': {k: len(g['commands']) for k, g in goals.items()}}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
