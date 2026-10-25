"""Goal sufficiency and intent deltas, reusing the original record and graph types."""
from dataclasses import asdict
import math
import os
from pathlib import Path
import sys
import time

from .kernel import graph as original_graph
from .records import Node, stamp
from . import __version__

TARGETS = {'apk': 'android-apk', 'native': 'windows-x64-native-binary', 'native_portable': 'windows-x64-native-binary',
           'report': 'cpu-report', 'archive': 'archive', 'emulator_test': 'android-emulator',
           'smartphone_install': 'android-device-install', 'python_runtime': 'application-runtime'}
OP_TARGETS = {**{'op:' + k: v for k, v in TARGETS.items() if k != 'native_portable'},
              'op:native-portable': 'windows-x64-native-binary'}


def execution_context():
    return {'executable': os.path.normcase(str(Path(sys.executable).resolve())),
            'python_version': sys.version, 'frozen': bool(getattr(sys, 'frozen', False)),
            'application_version': __version__}


def scope_matches(app, key, evidence):
    if app.mode != 'live':
        return True
    details = evidence.get('details', {})
    if key in {'runtime:available', 'op:python_runtime'}:
        return details.get('execution_context') == execution_context()
    if key in {'storage', 'storage_available'}:
        return details.get('resource_scope') == os.path.normcase(app.workspace.anchor)
    return True


def goal_graph():
    model = original_graph()
    for key, kind, fact in [('gradle', 'installed-software', 'pkg:gradle'),
                            ('build_tools', 'installed-software', 'pkg:build_tools'),
                            ('adb', 'installed-software', 'pkg:adb'),
                            ('device', 'physical-resource', 'device:connected'),
                            ('gpu', 'physical-resource', 'hardware:gpu'),
                            ('runtime', 'application-runtime', 'runtime:available')]:
        model.nodes[key] = Node(key, kind, fact=fact)
    model.nodes['cap:apk'].dependencies = ['java', 'sdk', 'gradle', 'build_tools', 'storage']
    model.nodes['cap:smartphone_install'] = Node('cap:smartphone_install', 'operational-capability',
        ['cap:apk', 'adb', 'device', 'storage'], 'op:smartphone_install')
    model.nodes['cap:python_runtime'] = Node('cap:python_runtime', 'operational-capability',
                                            ['runtime', 'storage'], 'op:python_runtime')
    model.alternatives['smartphone_install'] = ['cap:smartphone_install']
    model.alternatives['python_runtime'] = ['cap:python_runtime']
    model.alternatives['native_portable'] = ['cap:native-portable']
    model.id = 'goal-capability-graph'
    model.version = 2
    model.__post_init__()
    return model


def path_nodes(graph, root):
    result = set()
    def visit(key):
        if key not in result:
            result.add(key)
            for child in graph.nodes[key].dependencies:
                visit(child)
    visit(root)
    return result


def adequate(app, key, now=None):
    now = time.time() if now is None else now
    fact = app.reality.facts.get(key)
    if not fact or not fact.fresh(now):
        return False
    if key == 'storage':
        if (not isinstance(fact.value, (int, float)) or isinstance(fact.value, bool)
                or not math.isfinite(fact.value) or fact.value < 0):
            return False
    elif not isinstance(fact.value, bool):
        return False
    evidence = app.evidence.get(fact.evidence_id, {})
    if (evidence.get('source_mode') != app.mode or evidence.get('target_fact') != key
            or evidence.get('result') != fact.value or evidence.get('classification') != 'VERIFIED'
            or evidence.get('exit_code') != 0 or not scope_matches(app, key, evidence)):
        return False
    if key in OP_TARGETS and evidence.get('compatibility_target') != OP_TARGETS[key]:
        return False
    return True


def paths(app, requirement):
    result = []
    for root in app.graph.alternatives[requirement]:
        nodes = path_nodes(app.graph, root)
        facts = {app.graph.nodes[n].fact for n in nodes if app.graph.nodes[n].fact} | {'storage'}
        missing, blocked = [], []
        for key in sorted(facts):
            if not adequate(app, key):
                missing.append(key)
            elif key == 'storage':
                value = app.reality.facts[key].value
                if not isinstance(value, (int, float)) or isinstance(value, bool) or value < app.intent.constraints['min_storage']:
                    blocked.append(key)
            elif app.reality.facts[key].value is not True:
                blocked.append(key)
        if app.intent.constraints.get('capability_targets', {}).get(requirement) != TARGETS[requirement]:
            missing.append('compatibility:' + requirement)
        result.append({'root': root, 'nodes': sorted(nodes), 'facts': sorted(facts),
                       'needs_verification': missing, 'blocked_by': blocked,
                       'status': 'BLOCKED' if blocked else 'UNKNOWN' if missing else 'VERIFIED'})
    return result


def assessment(app, requirement):
    if requirement not in app.intent.acceptance_criteria:
        raise ValueError('requirement is not active in the human intent')
    alternatives = paths(app, requirement)
    verified = next((p for p in alternatives if p['status'] == 'VERIFIED'), None)
    viable = [p for p in alternatives if p['status'] != 'BLOCKED']
    chosen = verified or min(viable or alternatives,
                             key=lambda p: (len(p['needs_verification']), len(p['facts']), p['root']))
    status = 'ALREADY_SATISFIED' if verified else 'NEEDS_VERIFICATION' if viable else 'ACTUAL_CAPABILITY_GAP'
    explanation = {
        'ALREADY_SATISFIED': 'Fresh operational evidence and resource constraints support an existing compatible path. No additional installation is required.',
        'NEEDS_VERIFICATION': 'Evidence is missing, expired, unsupported or inadequate. This is not proof that software is absent.',
        'ACTUAL_CAPABILITY_GAP': 'Every alternative has at least one currently verified blocking fact within this recorded scope. No installation is automatically proposed.',
    }[status]
    refs = [app.reality.facts[k].evidence_id for k in chosen['facts']
            if k in app.reality.facts and app.reality.facts[k].evidence_id]
    return {'requirement': requirement, 'status': status, 'intent_id': app.intent.id,
            'intent_revision': app.intent.revision, 'reality_id': app.reality.id,
            'reality_version': app.reality.version, 'capability_graph_version': app.graph.version,
            'verified_satisfaction_path': verified, 'selected_observation_path': chosen,
            'alternatives': alternatives,
            'resource_nodes': [n for n in chosen['nodes'] if app.graph.nodes[n].kind == 'physical-resource'],
            'software_nodes': [n for n in chosen['nodes'] if app.graph.nodes[n].kind in {'installed-software', 'application-runtime'}],
            'probe_evidence': [app.evidence[r] for r in refs if r in app.evidence],
            'freshness_status': 'FRESH_AND_ADEQUATE' if verified else 'INSUFFICIENT_FOR_SATISFACTION',
            'resource_constraints': app.intent.constraints,
            'additional_installation_required': False if verified else None,
            'missing_required_components': [] if verified else None,
            'needs_verification': chosen['needs_verification'],
            'verified_blockers': chosen['blocked_by'],
            'timestamp': stamp(), 'explanation': explanation, 'execution_status': 'NOT_EXECUTED'}


def assess_all(app):
    return {r: assessment(app, r) for r in app.intent.acceptance_criteria}


def graph_delta(app, previous_intent, previous_assessments, invalidated_plans):
    from .probes import plan_probes
    old, new = set(previous_intent['acceptance_criteria']), set(app.intent.acceptance_criteria)
    current = assess_all(app)
    old_nodes = set().union(*(app.graph.closure(r) for r in old)) if old else set()
    new_nodes = set().union(*(app.graph.closure(r) for r in new)) if new else set()
    observations = plan_probes(app)
    return {'previous_revision': previous_intent['revision'], 'current_revision': app.intent.revision,
            'unchanged_requirements': sorted(old & new), 'added_requirements': sorted(new - old),
            'removed_requirements': sorted(old - new), 'removed_active_nodes': sorted(old_nodes - new_nodes),
            'added_active_nodes': sorted(new_nodes - old_nodes),
            'newly_satisfied_paths': {r: a['verified_satisfaction_path'] for r, a in current.items()
                if a['status'] == 'ALREADY_SATISFIED' and previous_assessments.get(r, {}).get('status') != 'ALREADY_SATISFIED'},
            'currently_satisfied': [r for r, a in current.items() if a['status'] == 'ALREADY_SATISFIED'],
            'newly_missing_capabilities': [r for r, a in current.items()
                if a['status'] == 'ACTUAL_CAPABILITY_GAP' and previous_assessments.get(r, {}).get('status') != a['status']],
            'facts_requiring_observation': sorted({f for a in current.values() for f in a['needs_verification']}),
            'facts_requiring_refreshed_observations': [e['fact'] for e in observations['entries']
                                                      if e['classification'] == 'STALE_BUT_RELEVANT'],
            'next_recommended_observation': observations['probes_to_run'][0] if observations['probes_to_run'] else
                'No supported probe needed or available; inspect unverified operational evidence without installing software.',
            'invalidated_assumptions': ['plans pinned to prior human intent revision'],
            'invalidated_plans': invalidated_plans,
            'no_longer_justified_actions': [p['id'] for p in app.plans.values() if p['action']['requirement'] in old - new],
            'observations_retained': sorted(app.reality.facts),
            'observations_reused': [e['fact'] for e in observations['entries'] if e['classification'] == 'FRESH_AND_REUSABLE'],
            'machine_rescan_performed': False,
            'system_modifications': 'NONE', 'assessments': current}
