"""Versioned records, evidence freshness, intent revisions and capability DAG."""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import time


def stamp():
    return datetime.now(timezone.utc).isoformat()


STATES = {'VERIFIED', 'OBSERVED', 'STALE', 'UNKNOWN', 'PROBE_FAILED', 'UNSUPPORTED'}


@dataclass
class Fact:
    id: str
    value: object
    classification: str
    observed_at: float
    ttl_seconds: float
    scope: str
    method: str = 'simulated-state-adapter'
    context: str = 'trusted local broker; simulated environment only'
    result: object = None
    exit_status: int | None = 0
    evidence_id: str = ''

    def __post_init__(self):
        if self.classification not in STATES:
            raise ValueError('unknown evidence classification')

    def fresh(self, now):
        return (self.classification == 'VERIFIED' and self.exit_status == 0
                and bool(self.evidence_id) and self.result == self.value
                and 0 <= now - self.observed_at <= self.ttl_seconds)


@dataclass
class Reality:
    id: str
    target: str
    schema_version: int = 1
    version: int = 1
    created_at: str = field(default_factory=stamp)
    facts: dict = field(default_factory=dict)
    derived_capabilities: dict = field(default_factory=dict)

    def awareness(self, relevant, now=None):
        now = time.time() if now is None else now
        fresh = sorted(k for k in relevant if k in self.facts and self.facts[k].fresh(now))
        return {'relevant': sorted(relevant), 'fresh': fresh,
                'needs_probe': sorted(set(relevant) - set(fresh)),
                'irrelevant_stale': sorted(k for k, f in self.facts.items()
                                          if k not in relevant and not f.fresh(now))}

    def invalidate(self, scopes):
        self.version += 1
        for f in self.facts.values():
            if f.scope in scopes:
                f.classification = 'STALE'
        self.derived_capabilities.clear()


@dataclass
class Intent:
    id: str
    objective: str
    acceptance_criteria: list
    exclusions: list = field(default_factory=list)
    constraints: dict = field(default_factory=dict)
    human_confirmed: list = field(default_factory=list)
    assumed_pending: list = field(default_factory=list)
    revision: int = 1
    timestamp: str = field(default_factory=stamp)
    revision_history: list = field(default_factory=list)
    schema_version: int = 1

    def revise(self, objective, criteria):
        self.revision_history.append(asdict(self) | {'revision_history': []})
        self.revision += 1
        self.objective = objective
        self.acceptance_criteria = list(criteria)
        self.human_confirmed = list(criteria)
        self.timestamp = stamp()


@dataclass
class Node:
    id: str
    kind: str
    dependencies: list = field(default_factory=list)
    fact: str | None = None


@dataclass
class CapabilityGraph:
    id: str
    nodes: dict
    # requirement -> alternative capability paths (OR); dependencies within a node are AND
    alternatives: dict
    version: int = 1
    schema_version: int = 1

    def __post_init__(self):
        visiting, visited = set(), set()

        def visit(key):
            if key in visiting:
                raise ValueError('capability cycle')
            if key in visited:
                return
            if key not in self.nodes:
                raise ValueError('missing graph node: ' + key)
            visiting.add(key)
            for child in self.nodes[key].dependencies:
                visit(child)
            visiting.remove(key)
            visited.add(key)

        for key in self.nodes:
            visit(key)
        for paths in self.alternatives.values():
            for key in paths:
                visit(key)

    def closure(self, requirement):
        found = set()

        def visit(key):
            if key not in found:
                found.add(key)
                for child in self.nodes[key].dependencies:
                    visit(child)

        for key in self.alternatives.get(requirement, []):
            visit(key)
        return found

    def relevant(self, requirement):
        return {self.nodes[k].fact for k in self.closure(requirement) if self.nodes[k].fact}

    def verified_path(self, requirement, reality, now=None):
        now = time.time() if now is None else now

        def usable(key):
            node = self.nodes[key]
            fact = reality.facts.get(node.fact) if node.fact else None
            return ((node.fact is None or (fact and fact.fresh(now) and fact.value is True))
                    and all(usable(child) for child in node.dependencies))

        return next((k for k in self.alternatives.get(requirement, []) if usable(k)), None)

    def tree(self, requirement):
        lines, seen = [requirement + ' (alternatives)'], set()

        def visit(key, depth):
            shared = key in seen
            lines.append('  ' * depth + key + (' [shared reference]' if shared else ''))
            if not shared:
                seen.add(key)
                for child in self.nodes[key].dependencies:
                    visit(child, depth + 1)

        for key in self.alternatives.get(requirement, []):
            visit(key, 1)
        return '\n'.join(lines)


@dataclass
class Transition:
    id: str
    reality_id: str
    reality_version: int
    intent_id: str
    intent_revision: int
    graph_id: str
    graph_version: int
    action: dict
    preconditions: list
    expected_postconditions: dict
    required_resources: dict
    affected_scopes: list
    risk: str = 'contained simulated-state change'
    recovery: str = 'restore-checkpoint-once'
    irreversible_accepted: bool = False
    authorization: str = 'PROPOSED'
    verification: list = field(default_factory=list)
    version: int = 1
    schema_version: int = 1
