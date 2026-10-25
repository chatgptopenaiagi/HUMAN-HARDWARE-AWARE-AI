"""Inspection and evaluation only. Never calls Kernel.submit or a shell gateway."""
import argparse
from dataclasses import asdict
import json
from tempfile import TemporaryDirectory

from . import __version__
from .kernel import CAPS, CATALOG, Kernel, graph

LABEL = 'EXPERIMENTAL DEVELOPER PREVIEW'
SCENARIOS = {
    'android': (['java', 'sdk', 'builder'], ['apk'], False),
    'notebook': ([], ['native'], False),
    'workstation': (['cpu_runtime'], ['report'], True),
    'archive': ([], ['archive'], False),
    'portable': (['portable_compiler'], ['native'], False),
}


def envelope(**values):
    return {'product': LABEL, 'version': __version__,
            'reality_scope': 'simulated fixture; not workstation inventory',
            'execution_enabled': False,
            'gateway_outcome': 'DISABLED_IN_DISTRIBUTION', **values}


def inspect_kernel(kernel):
    return {
        'point_a': {'existing_observed_capabilities': kernel.reality.derived_capabilities,
                    'simulated_resources': kernel.state},
        'point_b': {'required_capabilities': kernel.intent.acceptance_criteria},
        'reality_snapshot': asdict(kernel.reality),
        'intent_snapshot': asdict(kernel.intent),
        'capability_graph': asdict(kernel.graph),
        'verification_results': {
            'fixture_probes': 'PASSED', 'action_postconditions': 'NOT_EXECUTED',
            'packaged_execution_isolation': 'UNVERIFIED_EXECUTION_DISABLED',
            'awareness': kernel.reality.awareness(kernel.relevant())},
    }


def evaluate(kernel, operation, requirement, component):
    before = json.dumps(kernel.state, sort_keys=True)
    plan = kernel.plan(operation, requirement, component)
    decision = kernel.validate(plan)
    # This is a feasibility result, never an execution ticket.
    plan.authorization = decision['decision']
    inspection = inspect_kernel(kernel)
    inspection['verification_results'].update(
        state_unchanged=before == json.dumps(kernel.state, sort_keys=True), postconditions='NOT_EXECUTED')
    return envelope(transition_plan=asdict(plan), authorization_decision=decision, **inspection)


def make_kernel(directory, scenario, storage=50):
    packages, criteria, gpu = SCENARIOS[scenario]
    return Kernel(directory, 'preview-' + scenario, list(packages), list(criteria), storage, gpu)


def selftest():
    cases = [
        ('android', 'install', 'apk', 'sdk', 'REJECTED_UNNECESSARY'),
        ('android', 'reuse', 'apk', None, 'AUTHORIZED'),
        ('notebook', 'build', 'native', None, 'REJECTED_INFEASIBLE'),
        ('notebook', 'install', 'native', 'compiler', 'AUTHORIZED'),
        ('workstation', 'install', 'report', 'cuda', 'REJECTED_UNNECESSARY'),
        ('archive', 'install', 'archive', 'packager', 'AUTHORIZED'),
        ('portable', 'install', 'native', 'compiler', 'REJECTED_UNNECESSARY'),
    ]
    results = []
    for scenario, op, req, component, expected in cases:
        with TemporaryDirectory(prefix='awareness-preview-') as folder:
            kernel = make_kernel(folder, scenario)
            report = evaluate(kernel, op, req, component)
            actual = report['authorization_decision']['decision']
            results.append({'scenario': scenario, 'operation': op, 'expected': expected,
                            'actual': actual, 'passed': actual == expected and report['verification_results']['state_unchanged']})
    return envelope(checks=results, passed=all(r['passed'] for r in results),
                    verification_results={'postconditions': 'NOT_EXECUTED',
                                          'packaged_execution_isolation': 'UNVERIFIED_EXECUTION_DISABLED'})


def nonnegative(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError('storage must be nonnegative simulated units')
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=LABEL + ': inspect and evaluate simulated capabilities; execution disabled.')
    parser.add_argument('--version', action='version', version=f'{LABEL} {__version__}')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('selftest', help='check seven evaluation cases; no actions executed')
    g = sub.add_parser('graph', help='inspect authoritative graph or a tree projection')
    g.add_argument('--requirement', choices=sorted(CAPS), default='native')
    g.add_argument('--format', choices=['json', 'tree'], default='json')
    for name in ('inspect', 'simulate'):
        command = sub.add_parser(name)
        command.add_argument('--scenario', choices=sorted(SCENARIOS), default='android')
        command.add_argument('--storage', type=nonnegative, default=50)
        if name == 'simulate':
            command.add_argument('--operation', choices=['install', 'build', 'reuse'], required=True)
            command.add_argument('--requirement', choices=sorted(CAPS), required=True)
            command.add_argument('--component', choices=sorted(CATALOG))
    args = parser.parse_args(argv)
    if args.command == 'graph':
        model = graph()
        if args.format == 'tree':
            print(LABEL + ' ' + __version__ + '\n' + model.tree(args.requirement))
            return 0
        result = envelope(capability_graph=asdict(model), tree=model.tree(args.requirement))
    elif args.command == 'selftest':
        result = selftest()
    else:
        with TemporaryDirectory(prefix='awareness-preview-') as folder:
            kernel = make_kernel(folder, args.scenario, args.storage)
            result = (envelope(**inspect_kernel(kernel)) if args.command == 'inspect'
                      else evaluate(kernel, args.operation, args.requirement, args.component))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get('passed', True) else 1
