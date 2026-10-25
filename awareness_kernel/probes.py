"""Allowlisted read-only observations; no tool subprocesses, SDK commands or downloads."""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import sys
import time
import uuid

from .goals import adequate, assessment, OP_TARGETS, execution_context, scope_matches
from .records import Fact, stamp


@dataclass(frozen=True)
class ProbeDefinition:
    id: str
    target_fact: str
    method: str
    expected_output_type: str
    supported_operating_systems: tuple = ('Windows', 'Linux', 'Darwin')
    execution_platform: str = 'current application process / bounded spawned read-only worker'
    required_privileges: str = 'current user; no elevation requested'
    expected_resource_cost: str = 'one bounded metadata query; no recursive scan'
    max_execution_seconds: float = 5.0
    max_output_bytes: int = 4096
    freshness_seconds: int = 60
    failure_behavior: str = 'PROBE_FAILED; never infer global software absence'
    evidence_classification: str = 'OBSERVED'
    runnable: bool = True


def definitions():
    result = {
        'storage': ProbeDefinition('storage', 'storage', 'shutil.disk_usage(selected workspace).free', 'integer free bytes', evidence_classification='VERIFIED'),
        'runtime': ProbeDefinition('runtime', 'runtime:available', 'current Python runtime and sys.version; not another installed environment', 'boolean plus version context', freshness_seconds=3600, evidence_classification='VERIFIED'),
    }
    for name in ('java', 'sdk', 'gradle', 'build_tools', 'adb', 'compiler', 'portable_compiler', 'cpu_runtime', 'packager', 'builder', 'emulator', 'cuda'):
        supported = name in {'java', 'sdk', 'gradle', 'build_tools', 'adb', 'compiler'}
        result['locate-' + name] = ProbeDefinition('locate-' + name, 'pkg:' + name,
            'scoped candidate existence only; no executable invocation', 'boolean candidate found; not operational proof',
            freshness_seconds=300, runnable=supported)
    for key in OP_TARGETS:
        if key != 'op:python_runtime':
            result[key] = ProbeDefinition(key, key,
                'no safe operational adapter in this preview', 'boolean operational capability',
                evidence_classification='UNSUPPORTED', runnable=False)
    result['device'] = ProbeDefinition('device', 'device:connected',
        'unsupported: adb devices may start a daemon; device is not contacted', 'boolean connection',
        evidence_classification='UNSUPPORTED', runnable=False)
    return result


def definition_for(fact):
    special = {'storage_available': 'storage', 'op:python_runtime': 'runtime'}
    defs = definitions()
    return defs.get(special.get(fact, fact)) or next((d for d in defs.values() if d.target_fact == fact), None)


def reusable_observation(app, key):
    """A fresh locator result is reusable knowledge, but not operational proof."""
    fact = app.reality.facts.get(key)
    if not fact or fact.classification != 'OBSERVED' or fact.exit_status != 0:
        return False
    evidence = app.evidence.get(fact.evidence_id, {})
    return (0 <= time.time() - fact.observed_at <= fact.ttl_seconds
            and evidence.get('source_mode') == app.mode and evidence.get('target_fact') == key
            and evidence.get('classification') == 'OBSERVED' and evidence.get('result') == fact.value
            and scope_matches(app, key, evidence))


def plan_probes(app):
    relevant, reasons = set(), {}
    for requirement in app.intent.acceptance_criteria:
        result = assessment(app, requirement)
        for fact in result['selected_observation_path']['facts']:
            relevant.add(fact)
            reasons.setdefault(fact, []).append(requirement)
    entries = []
    known = set(app.reality.facts) | {d.target_fact for d in definitions().values()} | {'storage_available', 'op:python_runtime'}
    for key in sorted(known | relevant):
        definition = definition_for(key)
        fact = app.reality.facts.get(key)
        if key not in relevant:
            status, action = 'IRRELEVANT_TO_CURRENT_OBJECTIVE', 'AVOID'
        elif adequate(app, key) or reusable_observation(app, key):
            status, action = 'FRESH_AND_REUSABLE', 'REUSE'
        elif fact and (fact.classification == 'STALE' or time.time() > fact.observed_at + fact.ttl_seconds
                       or (fact.classification in {'VERIFIED', 'OBSERVED'}
                           and not scope_matches(app, key, app.evidence.get(fact.evidence_id, {})))):
            status = 'STALE_BUT_RELEVANT'
            action = 'PROBE' if definition and definition.runnable and app.mode == 'live' else 'NO_SAFE_ADAPTER'
        elif (not definition or not definition.runnable or app.mode != 'live'):
            status, action = 'UNSUPPORTED_ON_DEVICE', 'NO_SAFE_ADAPTER'
        else:
            status, action = 'UNKNOWN_AND_RELEVANT', 'PROBE'
        entries.append({'fact': key, 'classification': status, 'action': action,
                        'evidence_state': fact.classification if fact else 'UNKNOWN',
                        'adequate_for_capability': adequate(app, key),
                        'requirement_timing': 'REQUIRED_NOW' if key in relevant else 'NOT_REQUIRED',
                        'reasons': reasons.get(key, []),
                        'definition': asdict(definition) if definition else None})
    runnable = sorted({e['definition']['id'] for e in entries if e['action'] == 'PROBE'})
    return {'entries': entries, 'relevant_facts': sorted(relevant), 'probes_to_run': runnable,
            'avoided_facts': [e['fact'] for e in entries if e['action'] == 'AVOID'],
            'expected_upper_wait_seconds': sum(definitions()[k].max_execution_seconds + 2 for k in runnable),
            'selection_policy': 'reuse a verified witness; otherwise choose one least-unknown viable alternative; deduplicate shared facts. Not a global optimality claim.',
            'system_modifications': 'NONE', 'execution_gateway': 'DISABLED'}


def _measure(probe_id, workspace):
    if probe_id == 'storage':
        return {'storage': shutil.disk_usage(workspace).free,
                'resource_scope': os.path.normcase(Path(workspace).anchor),
                'context': 'free bytes on the volume containing the selected workspace'}
    if probe_id == 'runtime':
        return {'runtime:available': True, 'op:python_runtime': True,
                'context': 'bundled application runtime' if getattr(sys, 'frozen', False) else 'current selected Python process',
                'version': sys.version[:256], 'execution_context': execution_context()}
    name = probe_id.removeprefix('locate-')
    candidates = []
    suffix = '.exe' if os.name == 'nt' else ''
    if name == 'sdk':
        candidates = [os.environ.get(k, '') for k in ('ANDROID_SDK_ROOT', 'ANDROID_HOME')]
    elif name == 'build_tools':
        candidates = [str(Path(os.environ[k]) / 'build-tools') for k in ('ANDROID_SDK_ROOT', 'ANDROID_HOME') if os.environ.get(k)]
    elif name == 'gradle':
        candidates = [str(Path(workspace) / 'gradlew.bat'), str(Path(workspace) / 'gradlew')]
    else:
        executable = {'compiler': 'cl', 'java': 'java', 'adb': 'adb'}[name]
        if name == 'java' and os.environ.get('JAVA_HOME'):
            candidates.append(str(Path(os.environ['JAVA_HOME']) / 'bin' / ('java' + suffix)))
        located = shutil.which(executable)
        if located:
            candidates.append(located)
    found = [p[:512] for p in candidates[:4] if p and len(p) <= 512 and Path(p).exists()]
    return {'pkg:' + name: bool(found), 'context': 'bounded PATH/environment/workspace candidates only',
            'candidates_found': found,
            'limitation': 'No candidate found does not prove absence elsewhere; no tool was run.'}


def _worker(probe_id, workspace, connection):
    try:
        data = {'ok': True, 'result': _measure(probe_id, workspace)}
    except Exception as exc:
        data = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:512]}'}
    raw = json.dumps(data).encode('utf-8')
    if len(raw) > 4096:
        raw = b'{"ok":false,"error":"probe output limit exceeded"}'
    try:
        connection.send_bytes(raw)
    finally:
        connection.close()


def bounded_measure(definition, workspace):
    context = multiprocessing.get_context('spawn')
    reader, writer = context.Pipe(duplex=False)
    worker = context.Process(target=_worker, args=(definition.id, str(workspace), writer), daemon=True)
    started = time.monotonic()
    try:
        worker.start()
        writer.close()
        remaining = definition.max_execution_seconds - (time.monotonic() - started)
        if remaining <= 0 or not reader.poll(remaining):
            return {'ok': False, 'error': 'read-only probe deadline exceeded'}
        return json.loads(reader.recv_bytes(definition.max_output_bytes))
    except (OSError, EOFError, ValueError, RuntimeError) as exc:
        return {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:512]}'}
    finally:
        if worker.pid:
            worker.join(timeout=0.2)
            if worker.is_alive():
                worker.terminate()
                worker.join(timeout=1)
            if worker.is_alive():
                worker.kill()
                worker.join(timeout=1)
        reader.close()
        writer.close()


def run_probes(app, requested=None):
    if app.mode != 'live':
        raise ValueError('simulated evidence cannot be refreshed with host probes; create a live workspace')
    plan = plan_probes(app)
    selected = plan['probes_to_run'] if requested is None else requested
    if any(k not in plan['probes_to_run'] for k in selected):
        raise ValueError('probe is irrelevant, fresh, unknown or unsupported; inspect probe-plan first')
    records = []
    for key in dict.fromkeys(selected):
        definition = definitions()[key]
        start, epoch = stamp(), time.time()
        output = bounded_measure(definition, app.workspace)
        completed = stamp()
        values = output.get('result', {}) if output.get('ok') else {definition.target_fact: None}
        if key == 'storage':
            values['storage_available'] = values.get('storage', 0) > 0 if output.get('ok') else None
        if key == 'runtime' and not output.get('ok'):
            values['op:python_runtime'] = None
        fact_keys = [k for k in values if k in {definition.target_fact, 'storage_available', 'op:python_runtime'}]
        for fact_key in fact_keys:
            classification = definition.evidence_classification if output.get('ok') else 'PROBE_FAILED'
            evidence_id = 'probe-' + uuid.uuid4().hex
            value = values[fact_key]
            fact = Fact(fact_key, value, classification, epoch, definition.freshness_seconds,
                        fact_key, method=definition.method, context=values.get('context', 'read-only worker'),
                        result=value, exit_status=0 if output.get('ok') else 1, evidence_id=evidence_id)
            app.reality.facts[fact_key] = fact
            evidence = {'id': evidence_id, 'probe_id': key, 'target_fact': fact_key,
                        'definition': asdict(definition), 'start_timestamp': start,
                        'completion_timestamp': completed, 'result': value,
                        'exit_code': fact.exit_status, 'error_summary': output.get('error'),
                        'provenance': values.get('context', 'bounded read-only worker'),
                        'details': {k: v for k, v in values.items() if k not in fact_keys},
                        'freshness_expiration': datetime.fromtimestamp(epoch + fact.ttl_seconds, timezone.utc).isoformat(),
                        'affected_facts': fact_keys, 'classification': classification, 'source_mode': 'live',
                        'compatibility_target': OP_TARGETS.get(fact_key)}
            app.evidence[evidence_id] = evidence
            records.append(evidence)
        app.reality.version += 1
    return {'probe_records': records, 'planned_probe_ids': selected, 'system_modifications': 'NONE',
            'execution_gateway': 'DISABLED', 'scope_note': 'Read-only worker processes; no located software executed.'}
