from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
import unittest
from unittest.mock import patch

from awareness_kernel import __version__
from awareness_kernel.cli import main
from awareness_kernel.kernel import Kernel


class PreviewTests(unittest.TestCase):
    def invoke(self, *args):
        stream = StringIO()
        with redirect_stdout(stream), patch.object(Kernel, 'submit', side_effect=AssertionError('execution forbidden')):
            status = main(list(args))
        self.assertEqual(status, 0)
        result = json.loads(stream.getvalue())
        self.assertFalse(result['execution_enabled'])
        self.assertEqual(result['gateway_outcome'], 'DISABLED_IN_DISTRIBUTION')
        return result

    def test_inspection_contains_snapshots_and_points(self):
        result = self.invoke('inspect', '--scenario', 'android')
        for key in ('point_a', 'point_b', 'reality_snapshot', 'intent_snapshot', 'capability_graph'):
            self.assertIn(key, result)
        self.assertEqual(result['reality_snapshot']['derived_capabilities']['apk'], 'cap:apk')

    def test_rejection_and_positive_authorization_never_execute(self):
        for scenario, component, requirement, expected in [
            ('android', 'sdk', 'apk', 'REJECTED_UNNECESSARY'),
            ('notebook', 'compiler', 'native', 'AUTHORIZED'),
        ]:
            result = self.invoke('simulate', '--scenario', scenario, '--operation', 'install',
                                 '--requirement', requirement, '--component', component)
            self.assertEqual(result['authorization_decision']['decision'], expected)
            self.assertTrue(result['verification_results']['state_unchanged'])
            self.assertEqual(result['verification_results']['postconditions'], 'NOT_EXECUTED')

    def test_resource_constraints_and_missing_compiler(self):
        result = self.invoke('simulate', '--scenario', 'notebook', '--operation', 'install',
                             '--requirement', 'native', '--component', 'compiler', '--storage', '1')
        self.assertEqual(result['authorization_decision']['decision'], 'REJECTED_INFEASIBLE')
        result = self.invoke('simulate', '--scenario', 'notebook', '--operation', 'build', '--requirement', 'native')
        self.assertEqual(result['authorization_decision']['decision'], 'REJECTED_INFEASIBLE')

    def test_graph_shares_storage(self):
        result = self.invoke('graph', '--requirement', 'native')
        self.assertIn('storage [shared reference]', result['tree'])
        self.assertEqual(len(result['capability_graph']['alternatives']['native']), 2)

    def test_selftest_checks_all_cases(self):
        result = self.invoke('selftest')
        self.assertTrue(result['passed'])
        self.assertEqual(len(result['checks']), 7)

    def test_execution_and_shell_flags_are_absent(self):
        for args in (['execute'], ['simulate', '--operation', 'shell', '--requirement', 'native'],
                     ['inspect', '--execute'], ['inspect', '--storage', '-1']):
            with self.subTest(args=args), redirect_stderr(StringIO()), self.assertRaises(SystemExit) as exc:
                main(args)
            self.assertEqual(exc.exception.code, 2)

    def test_version_label(self):
        stream = StringIO()
        with redirect_stdout(stream), self.assertRaises(SystemExit) as exc:
            main(['--version'])
        self.assertEqual(exc.exception.code, 0)
        self.assertIn(__version__, stream.getvalue())
        self.assertIn('EXPERIMENTAL DEVELOPER PREVIEW', stream.getvalue())
