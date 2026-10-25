"""Atomic application-owned JSON state; human revisions never activate execution."""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time
import uuid

from .goals import TARGETS, OP_TARGETS, goal_graph, assess_all, graph_delta, scope_matches
from .records import Fact, Intent, Reality, Transition, stamp

SCHEMA = 1
FILENAME = 'awareness-state.json'
SCENARIO_CRITERIA = {'live': ['python_runtime'], 'android': ['apk'],
    'android-phone': ['apk', 'emulator_test', 'smartphone_install'], 'notebook': ['native'],
    'portable': ['native'], 'workstation': ['report'], 'archive': ['archive']}


class Workspace:
    def __init__(self, directory):
        self.workspace = Path(directory).resolve()
        self.path = self.workspace / FILENAME
        self.graph = goal_graph()

    @contextmanager
    def locked(self):
        self.workspace.mkdir(parents=True, exist_ok=True)
        lock = self.workspace / '.awareness.lock'
        if self.path.is_symlink() or lock.is_symlink():
            raise ValueError('application state and lock may not be symbolic links')
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise ValueError('workspace is locked; an interrupted writer may need human inspection. No lock was removed.') from exc
        try:
            with os.fdopen(fd, 'w') as stream:
                stream.write(json.dumps({'pid': os.getpid(), 'timestamp': stamp()}))
            yield self
        finally:
            lock.unlink()

    def initialize(self, scenario, objective, criteria=None, min_storage=1):
        if self.path.exists():
            raise ValueError('workspace already initialized; use intent-revise, never overwrite it')
        if scenario not in SCENARIO_CRITERIA or not objective.strip():
            raise ValueError('known scenario and nonempty human objective required')
        criteria = list(dict.fromkeys(criteria or SCENARIO_CRITERIA[scenario]))
        if (not criteria or any(c not in TARGETS for c in criteria)
                or not isinstance(min_storage, int) or isinstance(min_storage, bool) or min_storage < 1):
            raise ValueError('known nonempty criteria and positive storage constraint required')
        self.mode = 'live' if scenario == 'live' else 'simulated'
        self.scenario = scenario
        self.reality = Reality('reality-' + uuid.uuid4().hex,
                               'selected workspace volume and application runtime' if self.mode == 'live' else 'hypothetical fixture ' + scenario)
        self.intent = Intent('intent-' + uuid.uuid4().hex, objective.strip(), criteria,
            constraints={'min_storage': min_storage, 'storage_unit': 'bytes' if self.mode == 'live' else 'simulated-units',
                         'capability_targets': {k: TARGETS[k] for k in criteria}}, human_confirmed=criteria.copy())
        self.evidence, self.plans, self.events = {}, {}, []
        self.generation = 0
        self.history = [self._intent_record('Initial human-selected objective')]
        self.last_delta = None
        self.warnings = []
        if self.mode == 'simulated':
            self._fixture(scenario)
        self.events.append({'type': 'WORKSPACE_CREATED', 'timestamp': stamp(), 'mode': self.mode,
                            'intent_revision': 1, 'execution_status': 'NOT_EXECUTED'})
        return self

    def _fixture(self, scenario):
        packages = {'android': {'java', 'sdk', 'gradle', 'build_tools'},
                    'android-phone': {'java', 'sdk', 'gradle', 'build_tools', 'adb'},
                    'notebook': set(), 'portable': {'portable_compiler'},
                    'workstation': {'cpu_runtime'}, 'archive': set()}[scenario]
        for node in self.graph.nodes.values():
            if node.fact and node.fact.startswith('pkg:'):
                self.record_fixture(node.fact, node.fact[4:] in packages)
        self.record_fixture('storage', 50)
        self.record_fixture('storage_available', True)
        self.record_fixture('hardware:gpu', scenario == 'workstation')
        for key in OP_TARGETS:
            value = (key == 'op:apk' and scenario in {'android', 'android-phone'}
                     or key == 'op:native-portable' and scenario == 'portable'
                     or key == 'op:report' and scenario == 'workstation')
            if scenario == 'android-phone' and key in {'op:smartphone_install', 'op:emulator_test'}:
                continue
            self.record_fixture(key, bool(value))
        # Device connectivity intentionally remains unknown; no Android device is touched.

    def record_fixture(self, key, value, classification='VERIFIED', age=0):
        if self.mode != 'simulated':
            raise ValueError('fixture injection is not permitted in live state')
        evidence_id = 'fixture-' + uuid.uuid4().hex
        epoch = time.time() - age
        method = 'simulated-integration-test' if key.startswith('op:') else 'simulated-state-measurement'
        fact = Fact(key, value, classification, epoch, 3600, key, method=method,
                    context='explicit hypothetical fixture; not host inventory', result=value,
                    exit_status=0 if classification == 'VERIFIED' else 1, evidence_id=evidence_id)
        self.reality.facts[key] = fact
        self.evidence[evidence_id] = {'id': evidence_id, 'probe_id': method, 'target_fact': key,
            'start_timestamp': datetime.fromtimestamp(epoch, timezone.utc).isoformat(),
            'completion_timestamp': datetime.fromtimestamp(epoch, timezone.utc).isoformat(), 'observation_epoch': epoch,
            'result': value, 'exit_code': fact.exit_status, 'error_summary': None,
            'provenance': fact.context, 'freshness_expiration_epoch': epoch + fact.ttl_seconds,
            'affected_facts': [key], 'classification': classification, 'source_mode': 'simulated',
            'compatibility_target': OP_TARGETS.get(key)}

    def load(self):
        if self.path.is_symlink():
            raise ValueError('state file may not be a symbolic link')
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if data['schema_version'] != SCHEMA or data['graph_version'] != self.graph.version:
                raise ValueError('unsupported state or graph schema; no automatic migration performed')
            self.mode = data['mode']
            if self.mode not in {'live', 'simulated'}:
                raise ValueError('unknown evidence mode')
            self.scenario, self.generation = data['scenario'], data['generation']
            reality = data['reality']
            reality['facts'] = {k: Fact(**f) for k, f in reality['facts'].items()}
            self.reality = Reality(**reality)
            self.intent = Intent(**data['intent'])
            minimum = self.intent.constraints['min_storage']
            if (not self.intent.acceptance_criteria or any(k not in TARGETS for k in self.intent.acceptance_criteria)
                    or not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1):
                raise ValueError('invalid intent criteria or resource constraint')
            self.evidence, self.plans = data['evidence'], data['plans']
            self.history, self.events, self.last_delta = data['history'], data['events'], data['last_delta']
            self.warnings = [p.name for p in self.workspace.glob('.awareness-state-*.tmp')]
            return self
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError(f'invalid application state: {exc}; existing file preserved') from exc

    def save(self):
        self.generation += 1
        self.reality.derived_capabilities = {
            r: a['verified_satisfaction_path'] for r, a in assess_all(self).items()}
        data = {'schema_version': SCHEMA, 'graph_version': self.graph.version,
                'generation': self.generation, 'mode': self.mode, 'scenario': self.scenario,
                'reality': asdict(self.reality), 'intent': asdict(self.intent), 'evidence': self.evidence,
                'plans': self.plans, 'history': self.history, 'events': self.events, 'last_delta': self.last_delta}
        if self.path.is_symlink():
            raise ValueError('refusing symbolic-link state file')
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', prefix='.awareness-state-',
                                             suffix='.tmp', dir=self.workspace, delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(data, stream, indent=2, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except OSError:
            # Previous committed state remains authoritative. Report leftover pending file on reopen.
            raise

    def _intent_record(self, reason):
        result = asdict(self.intent)
        result['revision_history'] = []
        return result | {'reason': reason, 'authorized_by': 'human-cli', 'timestamp': stamp()}

    def revise(self, *, reason, objective=None, add=(), remove=(), exclude=(), include=(), narrow=None):
        if not reason.strip():
            raise ValueError('a nonempty human revision reason is required')
        before, assessments = asdict(self.intent), assess_all(self)
        criteria, exclusions = list(self.intent.acceptance_criteria), set(self.intent.exclusions)
        if narrow:
            old, new = narrow.split('=', 1) if '=' in narrow else ('', '')
            if old != 'native' or new != 'native_portable' or old not in criteria:
                raise ValueError('supported narrowing is native=native_portable on an active requirement')
            remove, add = list(remove) + [old], list(add) + [new]
        if any(k not in TARGETS for k in (*add, *remove, *exclude, *include)):
            raise ValueError('unknown capability requirement')
        if any(k not in criteria for k in remove):
            raise ValueError('cannot remove a criterion which is not active')
        exclusions.update(exclude)
        exclusions.difference_update(include)
        criteria = [k for k in criteria if k not in set(remove) | exclusions]
        for key in add:
            if key in exclusions:
                raise ValueError('explicitly include an excluded requirement before adding it')
            if key not in criteria:
                criteria.append(key)
        new_objective = objective.strip() if objective is not None else self.intent.objective
        if not criteria or not new_objective:
            raise ValueError('objective and at least one acceptance criterion must remain')
        if (criteria == self.intent.acceptance_criteria and sorted(exclusions) == sorted(self.intent.exclusions)
                and new_objective == self.intent.objective):
            raise ValueError('no objective change requested; no revision written')
        self.intent.revision += 1
        self.intent.timestamp = stamp()
        self.intent.objective, self.intent.acceptance_criteria = new_objective, criteria
        self.intent.exclusions = sorted(exclusions)
        self.intent.human_confirmed = criteria.copy()
        self.intent.constraints['capability_targets'] = {k: TARGETS[k] for k in criteria}
        invalidated = []
        for key, plan in self.plans.items():
            if plan['intent_revision'] != self.intent.revision:
                plan['authorization'] = 'REJECTED_STALE'
                invalidated.append(key)
        self.intent.revision_history.append({'previous_revision': before['revision'],
            'new_revision': self.intent.revision, 'previous_objective': before['objective'],
            'new_objective': new_objective, 'previous_criteria': before['acceptance_criteria'],
            'new_criteria': criteria.copy(), 'timestamp': stamp(), 'reason': reason,
            'authorized_by': 'human-cli'})
        self.history.append(self._intent_record(reason))
        self.last_delta = graph_delta(self, before, assessments, invalidated)
        self.events.append({'type': 'INTENT_REVISED', 'timestamp': stamp(),
                            'reason': reason, 'authorized_by': 'human-cli',
                            'delta': deepcopy(self.last_delta), 'execution_status': 'NOT_EXECUTED'})
        return self.last_delta

    def diff(self, old, new):
        previous = next((r for r in self.history if r['revision'] == old), None)
        current = next((r for r in self.history if r['revision'] == new), None)
        if not previous or not current:
            raise ValueError('requested intent revision does not exist')
        return {'previous': previous, 'current': current,
                'added_criteria': sorted(set(current['acceptance_criteria']) - set(previous['acceptance_criteria'])),
                'removed_criteria': sorted(set(previous['acceptance_criteria']) - set(current['acceptance_criteria'])),
                'unchanged_criteria': sorted(set(previous['acceptance_criteria']) & set(current['acceptance_criteria']))}

    def observations(self):
        result = []
        for evidence in self.evidence.values():
            fact = self.reality.facts.get(evidence['target_fact'])
            latest = bool(fact and fact.evidence_id == evidence['id'])
            expired = bool(latest and fact.classification in {'VERIFIED', 'OBSERVED'}
                           and (time.time() > fact.observed_at + fact.ttl_seconds
                                       or not scope_matches(self, fact.id, evidence)))
            result.append(dict(evidence, latest_for_fact=latest, historical=not latest or expired,
                current_state='STALE' if expired else fact.classification if latest else 'HISTORICAL'))
        return result

    def create_plan(self, requirement, operation='reuse', component=None):
        if requirement not in self.intent.acceptance_criteria:
            raise ValueError('plan requirement is not active')
        if operation not in {'install', 'build', 'reuse'}:
            raise ValueError('unsupported proposed operation')
        plan = Transition('plan-' + uuid.uuid4().hex, self.reality.id, self.reality.version,
            self.intent.id, self.intent.revision, self.graph.id, self.graph.version,
            {'operation': operation, 'requirement': requirement, 'component': component},
            sorted(self.graph.relevant(requirement) | {'storage'}), {'requirement': requirement},
            self.intent.constraints.copy(), [], risk='evaluation only', recovery='no execution permitted')
        self.plans[plan.id] = asdict(plan)
        return asdict(plan)

    def evaluate_plan(self, key):
        if key not in self.plans:
            raise ValueError('unknown transition plan identifier')
        plan = self.plans[key]
        references_valid = (plan['intent_id'] == self.intent.id and plan['intent_revision'] == self.intent.revision
            and plan['reality_id'] == self.reality.id and plan['reality_version'] == self.reality.version
            and plan['graph_id'] == self.graph.id and plan['graph_version'] == self.graph.version)
        req = plan['action']['requirement']
        assessment = assess_all(self).get(req)
        if not references_valid:
            decision, reason = 'REJECTED_STALE', 'plan references obsolete intent, reality or graph'
        elif not assessment:
            decision, reason = 'REJECTED_UNNECESSARY', 'requirement is no longer active'
        elif assessment['status'] == 'NEEDS_VERIFICATION':
            decision, reason = 'REJECTED_STALE', 'relevant evidence needs verification'
        elif assessment['status'] == 'ALREADY_SATISFIED':
            decision = 'REJECTED_UNNECESSARY' if plan['action']['operation'] == 'install' else 'AUTHORIZED'
            reason = 'existing verified path; installation unnecessary; any reuse remains not executed'
        else:
            decision, reason = 'REJECTED_INFEASIBLE', 'verified capability gap; no automatic installation plan inferred'
        return {'plan': plan, 'decision': decision, 'reason': reason, 'assessment': assessment,
                'execution_status': 'NOT_EXECUTED', 'execution_enabled': False}
