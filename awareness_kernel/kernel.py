"""Trusted broker: authoritative simulation adapter, validator, gateway and recovery."""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import time
from .records import CapabilityGraph, Fact, Intent, Node, Reality, Transition, stamp


CATALOG = {'java': 2, 'sdk': 4, 'builder': 1, 'compiler': 3,
           'portable_compiler': 3, 'packager': 2, 'cpu_runtime': 1, 'cuda': 8, 'emulator': 5}
CAPS = {'apk': ['java', 'sdk', 'builder'], 'native': ['compiler'],
        'report': ['cpu_runtime'], 'archive': ['packager'], 'emulator_test': ['emulator']}
OPERATIONAL = CAPS | {'native-portable': ['portable_compiler']}


def graph():
    nodes = {k: Node(k, 'installed-software', fact='pkg:' + k) for k in CATALOG}
    nodes['storage'] = Node('storage', 'physical-resource', fact='storage_available')
    for cap, deps in OPERATIONAL.items():
        nodes['cap:' + cap] = Node('cap:' + cap, 'operational-capability',
                                   deps + ['storage'], 'op:' + cap)
    alternatives = {cap: ['cap:' + cap] for cap in CAPS}
    alternatives['native'].append('cap:native-portable')
    return CapabilityGraph('simulation-graph', nodes, alternatives)


class Kernel:
    def __init__(self, directory, experiment, packages, criteria, storage=50, physical_gpu=False):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'state.json'
        self.experiment = experiment
        self.state = {'packages': sorted(packages), 'storage': storage, 'privilege': True,
                      'artifacts': [], 'inconsistent': False, 'physical_gpu': physical_gpu}
        self.intent = Intent(experiment + '-intent', 'Produce ' + ', '.join(criteria), criteria,
                             human_confirmed=list(criteria),
                             constraints={'resource_boundary': 'simulated units'})
        self.reality = Reality(experiment + '-reality', 'disposable simulated ' + experiment)
        self.graph = graph()
        self.events, self.probes = [], []
        self.sequence = 0
        self.probe_seconds = 0.0
        self._save()
        self.refresh(self.relevant())

    def _save(self):
        # Higher-integrity directory is required by the Windows isolation adapter.
        temporary = self.path.with_suffix('.new')
        temporary.write_text(json.dumps(self.state, sort_keys=True), encoding='utf-8')
        temporary.replace(self.path)

    def relevant(self, requirement=None):
        criteria = [requirement] if requirement else self.intent.acceptance_criteria
        result = {'storage', 'privilege', 'storage_available'}
        for criterion in criteria:
            result |= self.graph.relevant(criterion)
        return result

    def _value(self, key):
        if key.startswith('pkg:'):
            return key[4:] in self.state['packages']
        if key.startswith('op:'):
            # An integration probe, separate from a package-presence probe.
            return all(k in self.state['packages'] for k in OPERATIONAL[key[3:]])
        if key.startswith('artifact:'):
            return key[9:] in self.state['artifacts']
        if key == 'storage_available':
            return self.state['storage'] > 0
        return self.state[key]

    @staticmethod
    def scope(key):
        return 'software' if key.startswith(('pkg:', 'op:')) else key

    def refresh(self, keys, fail=()):
        start = time.perf_counter()
        self.reality.version += 1
        for key in sorted(keys):
            evidence = f'{self.experiment}-probe-{len(self.probes) + 1}'
            ok = key not in fail
            value = self._value(key) if ok else None
            fact = Fact(key, value, 'VERIFIED' if ok else 'PROBE_FAILED', time.time(),
                        60, self.scope(key), result=value, exit_status=0 if ok else 1,
                        evidence_id=evidence)
            self.reality.facts[key] = fact
            self.probes.append(asdict(fact))
        self.reality.derived_capabilities = {
            c: self.graph.verified_path(c, self.reality)
            for c in self.intent.acceptance_criteria}
        self.probe_seconds += time.perf_counter() - start

    def plan(self, operation, requirement, component=None):
        self.sequence += 1
        action = {'operation': operation, 'requirement': requirement, 'component': component}
        cost = CATALOG.get(component, 0) if operation == 'install' else 0
        post = ({'package': component} if operation == 'install'
                else {'artifact': requirement})
        scopes = ['software', 'storage', 'storage_available'] if operation == 'install' else ['artifact:' + requirement]
        return Transition(f'{self.experiment}-plan-{self.sequence}', self.reality.id,
                          self.reality.version, self.intent.id, self.intent.revision,
                          self.graph.id, self.graph.version, action,
                          sorted(self.relevant(requirement)), post, {'storage': cost}, scopes,
                          verification=sorted(self.relevant(requirement)) + ['artifact:' + requirement])

    def validate(self, p):
        a = p.action
        op, req, component = a.get('operation'), a.get('requirement'), a.get('component')
        keys = self.relevant(req) if req in CAPS else set()
        evidence = [self.reality.facts[k].evidence_id for k in sorted(keys)
                    if k in self.reality.facts]

        def result(code, reason, **details):
            return {'decision': code, 'reason': reason, 'requirement': req,
                    'evidence': evidence, **details}

        if op not in {'install', 'build', 'reuse'} or req not in CAPS:
            return result('REJECTED_UNSUPPORTED', 'operation or requirement outside adapter')
        if self.state['inconsistent']:
            return result('REJECTED_INFEASIBLE', 'environment inconsistent; mutations locked')
        if (p.intent_id != self.intent.id or p.intent_revision != self.intent.revision
                or p.reality_id != self.reality.id or p.reality_version != self.reality.version
                or p.graph_id != self.graph.id or p.graph_version != self.graph.version):
            return result('REJECTED_STALE', 'referenced record version obsolete')
        if req not in self.intent.acceptance_criteria or req in self.intent.exclusions:
            return result('REJECTED_UNNECESSARY', 'not connected to active objective')
        if self.intent.assumed_pending or req not in self.intent.human_confirmed:
            return result('REQUIRES_HUMAN_DECISION', 'unconfirmed requirements')
        policy = self.reality.awareness(keys)
        if policy['needs_probe']:
            return result('REJECTED_STALE', 'relevant evidence unavailable or expired', awareness=policy)
        if not self.reality.facts['privilege'].value:
            return result('REQUIRES_HUMAN_DECISION', 'required simulated privilege unavailable')
        path = self.graph.verified_path(req, self.reality)
        if op == 'install':
            if component not in CATALOG:
                return result('REJECTED_UNSUPPORTED', 'component outside fixed catalog')
            if component not in self.graph.closure(req):
                return result('REJECTED_UNNECESSARY', 'component outside requirement path', reuse_path=path)
            if path:
                return result('REJECTED_UNNECESSARY', 'verified existing path satisfies requirement', reuse_path=path)
            if self.reality.facts['pkg:' + component].value:
                return result('REJECTED_UNNECESSARY', 'component already present; duplicate install cannot repair capability')
            cost, post = CATALOG[component], {'package': component}
            scopes = ['software', 'storage', 'storage_available']
        else:
            cost, post, scopes = 0, {'artifact': req}, ['artifact:' + req]
            if not path:
                return result('REJECTED_INFEASIBLE', 'no verified operational path')
            if req in self.state['artifacts']:
                return result('REJECTED_UNNECESSARY', 'acceptance artifact already verified')
        if (p.required_resources != {'storage': cost} or p.expected_postconditions != post
                or p.affected_scopes != scopes or set(p.preconditions) != keys
                or set(p.verification) != keys | {'artifact:' + req}):
            return result('REJECTED_UNSUPPORTED', 'plan differs from fixed adapter contract')
        if self.reality.facts['storage'].value < cost:
            return result('REJECTED_INFEASIBLE', 'insufficient measured simulated storage')
        if p.recovery != 'restore-checkpoint-once':
            return result('REQUIRES_HUMAN_DECISION', 'unsupported recovery; irreversible effects not accepted by this adapter')
        return result('AUTHORIZED', 'traceable feasible transition; reuse evaluated', reuse_path=path)

    def submit(self, p, *, fault=None):
        """Only trusted harness may inject faults; proposals cannot name Python or shell code."""
        start = time.perf_counter()
        before = deepcopy(self.state)
        decision = self.validate(p)
        p.authorization = decision['decision']
        event = {'timestamp': stamp(), 'experiment': self.experiment,
                 'intent_version': self.intent.revision, 'reality_snapshot_version': self.reality.version,
                 'capability_graph_version': self.graph.version, 'transition_plan_version': p.version,
                 'plan': asdict(p), 'proposed_operation': p.action, 'evidence_references': decision['evidence'],
                 'validator': decision, 'gateway_outcome': 'BLOCKED', 'before': before,
                 'verification': 'NOT_RUN', 'recovery': None, 'invalidation': []}
        if decision['decision'] == 'AUTHORIZED':
            event['gateway_outcome'] = 'EXECUTED'
            self.reality.invalidate(p.affected_scopes)
            event['invalidation'] = [k for k, f in self.reality.facts.items() if f.classification == 'STALE']
            try:
                a = p.action
                if a['operation'] == 'install':
                    self.state['storage'] -= CATALOG[a['component']]
                    self.state['packages'].append(a['component'])
                    self.state['packages'].sort()
                else:
                    self.state['artifacts'].append(a['requirement'])
                self._save()
                if fault in {'partial', 'recovery-fails'}:
                    raise RuntimeError('controlled interruption after partial state write')
                keys = self.relevant() | {'artifact:' + a['requirement']}
                # Unrelated stale observations remain stale; do not inspect everything.
                self.refresh(keys, fail={'op:' + a['requirement']} if fault == 'probe' else ())
                target = 'pkg:' + a['component'] if a['operation'] == 'install' else 'artifact:' + a['requirement']
                if (not self.reality.facts[target].fresh(time.time())
                        or self.reality.facts[target].value is not True
                        or any(self.reality.facts[k].classification == 'PROBE_FAILED' for k in keys)):
                    raise RuntimeError('postcondition probe failed')
                event['verification'] = 'PASSED'
            except (RuntimeError, OSError) as exc:
                event['gateway_outcome'] = 'FAILED'
                event['verification'] = 'FAILED'
                event['failure'] = str(exc)
                event['failed_state'] = deepcopy(self.state)
                self.reality.invalidate(p.affected_scopes)
                event['failure_evidence'] = asdict(self.reality)
                event['recovery'] = self.recover(before, fault == 'recovery-fails')
        event['after'] = deepcopy(self.state)
        event['reality_after'] = asdict(self.reality)
        event['elapsed_seconds'] = time.perf_counter() - start
        self.events.append(event)
        with (self.directory / 'events.jsonl').open('a', encoding='utf-8') as log:
            log.write(json.dumps(event, sort_keys=True) + '\n')
        return event

    def recover(self, checkpoint, fail=False):
        # One restore attempt, one verification, no retry loop.
        try:
            if fail:
                raise RuntimeError('controlled rollback failure')
            self.state = deepcopy(checkpoint)
            self._save()
            keys = self.relevant() | {'artifact:' + c for c in self.intent.acceptance_criteria}
            self.refresh(keys)
            persisted = json.loads(self.path.read_text(encoding='utf-8'))
            if persisted == checkpoint and all(self.reality.facts[k].fresh(time.time()) for k in keys):
                return {'attempts': 1, 'result': 'RESTORED_VERIFIED'}
            raise RuntimeError('rollback verification mismatch')
        except (OSError, RuntimeError) as exc:
            failure = str(exc)
        self.state['inconsistent'] = True
        self.reality.invalidate({f.scope for f in self.reality.facts.values()})
        persisted = True
        try:
            self._save()
        except OSError:
            persisted = False
        return {'attempts': 1, 'result': 'FAILED_INCONSISTENT', 'failure': failure,
                'lock_persisted': persisted}

    def complete(self):
        return (not self.state['inconsistent'] and all(
            (f := self.reality.facts.get('artifact:' + c)) and f.fresh(time.time()) and f.value is True
            for c in self.intent.acceptance_criteria))
