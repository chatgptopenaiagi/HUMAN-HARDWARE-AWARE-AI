"""Reproduce deterministic scenarios and OS-enforced bypass tests on Windows."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from awareness_kernel.kernel import Kernel
from awareness_kernel.records import stamp
from awareness_kernel.windows_isolation import label_directory, propose


def run(result_dir=None):
    started = time.perf_counter()
    fixtures_path = ROOT / 'experiments/fixtures/genesis-1.1.json'
    fixtures = json.loads(fixtures_path.read_text(encoding='utf-8'))
    runtime = ROOT / 'experiments/.runtime' / ('run-' + uuid.uuid4().hex)
    runtime.mkdir(parents=True)
    results = Path(result_dir) if result_dir else ROOT / 'experiments/results/genesis-1.1'
    results.mkdir(parents=True, exist_ok=True)
    summary = {'schema_version': 1, 'timestamp': stamp(), 'python': platform.python_version(),
               'platform': platform.platform(), 'proposal_source': fixtures['source'],
               'fixture_sha256': hashlib.sha256(fixtures_path.read_bytes()).hexdigest(),
               'total_proposed_operations': 0, 'necessary_operations': 0, 'unnecessary_operations': 0,
               'obsolete_operations': 0, 'correct_authorizations': 0, 'correct_rejections': 0,
               'false_authorizations': 0, 'false_rejections': 0, 'wrong_rejection_reasons': 0,
               'successful_governed_operations': 0, 'prevented_unnecessary_operations': 0,
               'successful_bypass_attempts': 0, 'failed_bypass_attempts': 0,
               'bypass_errors': 0,
               'recovery_successes': 0, 'recovery_failures': 0, 'probe_seconds': 0,
               'gateway_seconds': 0, 'scenarios': {}, 'model_trial': 'NOT_PERFORMED',
               'model_tokens': None, 'energy_measurement': None}
    all_events, all_probes, clients, snapshots = [], [], {}, {}
    for case in fixtures['scenarios']:
        name = case['id']
        home, outbox = runtime / name / 'protected', runtime / name / 'outbox'
        label_directory(home, 'M')
        label_directory(outbox, 'L')
        kernel = Kernel(home, name, case['packages'], case['criteria'], physical_gpu=name == 'C')
        initial = deepcopy(kernel.state)
        original_intent = asdict(kernel.intent)
        initial_reality = asdict(kernel.reality)
        client = propose(case['steps'], outbox, state_path=kernel.path, broker_pid=os.getpid())
        clients[name] = client
        old = None
        if case.get('revise'):
            old = kernel.plan('build', 'emulator_test')
            kernel.intent.revise('Produce APK; omit emulator testing', case['revise'])
        events = []
        assert len(client['proposals']) == len(case['steps'])
        for index, step in enumerate(client['proposals']):
            oracle = case['steps'][index]
            p = old if oracle.get('old_intent') else kernel.plan(
                step['operation'], step['requirement'], step.get('component'))
            event = kernel.submit(p, fault=oracle.get('fault'))
            event['oracle'] = {k: oracle[k] for k in ('expected', 'necessity')}
            actual, expected = event['validator']['decision'], oracle['expected']
            summary['total_proposed_operations'] += 1
            summary[oracle['necessity'] + '_operations'] += 1
            if actual == 'AUTHORIZED':
                summary['correct_authorizations' if expected == 'AUTHORIZED' else 'false_authorizations'] += 1
            elif expected == 'AUTHORIZED':
                summary['false_rejections'] += 1
            elif actual == expected:
                summary['correct_rejections'] += 1
            else:
                summary['wrong_rejection_reasons'] += 1
            if event['gateway_outcome'] == 'EXECUTED' and event['verification'] == 'PASSED':
                summary['successful_governed_operations'] += 1
            if oracle['necessity'] == 'unnecessary' and event['gateway_outcome'] == 'BLOCKED':
                summary['prevented_unnecessary_operations'] += 1
                assert event['before'] == event['after']
            if event['recovery']:
                key = 'recovery_successes' if event['recovery']['result'] == 'RESTORED_VERIFIED' else 'recovery_failures'
                summary[key] += 1
            summary['gateway_seconds'] += event['elapsed_seconds']
            events.append(event)
        if name == 'C':
            # Hardware is represented separately from runtime capability.
            assert initial['physical_gpu'] is True
            assert not any(p['id'] in {'pkg:cuda', 'op:gpu'} for p in kernel.probes)
        summary['probe_seconds'] += kernel.probe_seconds
        summary['scenarios'][name] = {'objective_complete': kernel.complete(),
                                      'initial_state': initial, 'final_state': kernel.state,
                                      'active_requirements': kernel.intent.acceptance_criteria,
                                      'active_dependency_nodes': sorted(set().union(*(
                                          kernel.graph.closure(c) for c in kernel.intent.acceptance_criteria)))}
        snapshots[name] = {'initial_intent': original_intent, 'intent': asdict(kernel.intent),
                           'initial_reality': initial_reality, 'reality': asdict(kernel.reality),
                           'capability_graph': asdict(kernel.graph)}
        all_events += events
        all_probes += [dict(p, experiment=name) for p in kernel.probes]

    # E: real denied OS operations, not a mocked authorization response.
    home, outbox = runtime / 'E/protected', runtime / 'E/outbox'
    label_directory(home, 'M')
    label_directory(outbox, 'L')
    kernel = Kernel(home, 'E', ['java', 'sdk', 'builder'], ['apk'])
    before_bytes = kernel.path.read_bytes()
    attack = propose([], outbox, state_path=kernel.path, broker_pid=os.getpid(), bypass=True)
    attack['state_unchanged'] = before_bytes == kernel.path.read_bytes()
    for item in attack['attacks']:
        key = {'DENIED': 'failed_bypass_attempts', 'BYPASS_SUCCEEDED': 'successful_bypass_attempts'}.get(item['outcome'], 'bypass_errors')
        summary[key] += 1
    summary['gateway_enforcement'] = ('VERIFIED_WITHIN_BOUNDARY' if attack['state_unchanged']
                                      and summary['successful_bypass_attempts'] == 0
                                      and summary['bypass_errors'] == 0 else 'FAILED')

    # Equivalent injected proposal, no validator. This is NOT a model-behavior baseline.
    baseline = {'packages': ['java', 'sdk', 'builder'], 'storage': 50}
    baseline_path = outbox / 'unrestricted-state.json'
    baseline_path.write_text(json.dumps(baseline), encoding='utf-8')
    baseline_client = propose([fixtures['scenarios'][0]['steps'][0]], outbox,
                               state_path=kernel.path, broker_pid=os.getpid(), baseline_state=baseline_path)
    mechanical = {'source': 'deterministic injection, unrestricted simulated adapter',
                  'proposal': fixtures['scenarios'][0]['steps'][0],
                  **baseline_client['baseline'], 'client': baseline_client,
                  'persisted_state_matches': json.loads(baseline_path.read_text()) == baseline_client['baseline']['after'],
                  'claim': 'mechanical control only; not evidence of model propensity'}
    summary['elapsed_seconds'] = time.perf_counter() - started
    mirror = ROOT / f'experiments/.runtime/proposer-python-{sys.version_info.major}{sys.version_info.minor}'
    summary['reused_runtime_bytes'] = sum(f.stat().st_size for f in mirror.rglob('*') if f.is_file())
    summary['runtime_preparation'] = 'cached reused interpreter; cold staging time not measured'
    summary['status'] = ('VALIDATED_WITHIN_SIMULATED_BOUNDARY' if
        summary['gateway_enforcement'] == 'VERIFIED_WITHIN_BOUNDARY'
        and not any(summary[k] for k in ['false_authorizations', 'false_rejections', 'wrong_rejection_reasons'])
        and all(s['objective_complete'] for k, s in summary['scenarios'].items()
                if k != 'G-recovery-failure')
        and summary['scenarios']['G-recovery-failure']['final_state']['inconsistent'] else 'INCOMPLETE')
    for filename, value in [('summary.json', summary), ('bypass.json', attack),
                            ('clients.json', clients), ('snapshots.json', snapshots),
                            ('unrestricted-control.json', mechanical)]:
        (results / filename).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    (results / 'runtime-manifest.json').write_text((mirror / 'manifest.json').read_text(), encoding='utf-8')
    sources = (list((ROOT / 'awareness_kernel').glob('*.py'))
               + list((ROOT / 'tests').glob('*.py'))
               + [Path(__file__), fixtures_path, ROOT / 'genesis-1.1/EXPERIMENTAL-CONTRACT.md'])
    (results / 'source-manifest.json').write_text(json.dumps({
        str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        for p in sources}, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    for filename, records in [('events.jsonl', all_events), ('probes.jsonl', all_probes)]:
        (results / filename).write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in records), encoding='utf-8')
    (results / 'capability-tree.txt').write_text(kernel.graph.tree('apk') + '\n\n' + kernel.graph.tree('native') + '\n', encoding='utf-8')
    return summary


if __name__ == '__main__':
    result = run()
    print(json.dumps(result, indent=2))
    if result['status'] == 'INCOMPLETE':
        raise SystemExit(1)
