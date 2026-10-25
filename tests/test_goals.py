from copy import deepcopy
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from awareness_kernel.goals import assessment, assess_all
from awareness_kernel.kernel import Kernel
from awareness_kernel.probes import plan_probes, run_probes, definitions, bounded_measure, _measure
from awareness_kernel.workspace import Workspace, FILENAME


class GoalTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / '.preview-work'
        root.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=root)
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def app(self, scenario='android', criteria=None):
        app = Workspace(self.folder).initialize(scenario, 'Human-selected test objective', criteria)
        app.save()
        return app

    def test_A_already_satisfied_links_operational_evidence(self):
        app = self.app()
        result = assessment(app, 'apk')
        self.assertEqual(result['status'], 'ALREADY_SATISFIED')
        self.assertFalse(result['additional_installation_required'])
        self.assertIn('storage', result['resource_nodes'])
        self.assertIn('gradle', result['software_nodes'])
        self.assertTrue(any(e['target_fact'] == 'op:apk' for e in result['probe_evidence']))
        for field in ('intent_id', 'intent_revision', 'reality_version', 'capability_graph_version',
                      'freshness_status', 'resource_constraints', 'timestamp', 'explanation'):
            self.assertIn(field, result)

    def test_B_alternative_not_primary_compiler_is_sufficient(self):
        app = self.app('portable')
        result = assessment(app, 'native')
        self.assertEqual(result['status'], 'ALREADY_SATISFIED')
        self.assertEqual(result['verified_satisfaction_path']['root'], 'cap:native-portable')
        p = app.create_plan('native', 'install', 'compiler')
        self.assertEqual(app.evaluate_plan(p['id'])['decision'], 'REJECTED_UNNECESSARY')
        self.assertNotIn('pkg:compiler', plan_probes(app)['relevant_facts'])

    def test_C_cpu_goal_never_plans_gpu_or_cuda_probes(self):
        app = self.app('workstation')
        plan = plan_probes(app)
        self.assertTrue(app.reality.facts['hardware:gpu'].value)
        self.assertNotIn('hardware:gpu', plan['relevant_facts'])
        self.assertNotIn('pkg:cuda', plan['relevant_facts'])
        self.assertIn('pkg:cuda', plan['avoided_facts'])

    def test_D_phone_goal_has_shared_android_dependencies(self):
        app = self.app('live', ['apk', 'smartphone_install'])
        plan = plan_probes(app)
        for key in ('pkg:java', 'pkg:sdk', 'pkg:gradle', 'pkg:build_tools', 'pkg:adb', 'device:connected', 'storage'):
            self.assertIn(key, plan['relevant_facts'])
        self.assertEqual(plan['relevant_facts'].count('pkg:java'), 1)
        self.assertNotIn('locate-cuda', plan['probes_to_run'])
        self.assertNotIn('device', plan['probes_to_run'])

    def test_E_human_revision_preserves_build_and_invalidates_emulator_plan(self):
        app = self.app('android-phone')
        p = app.create_plan('emulator_test', 'build')
        before = asdict(app.reality)
        delta = app.revise(reason='Human explicitly omits emulator test', remove=['emulator_test'])
        self.assertEqual(app.intent.revision, 2)
        self.assertEqual(app.evaluate_plan(p['id'])['decision'], 'REJECTED_STALE')
        self.assertIn('emulator_test', delta['removed_requirements'])
        self.assertIn('apk', delta['currently_satisfied'])
        self.assertNotIn('pkg:emulator', plan_probes(app)['relevant_facts'])
        self.assertEqual(asdict(app.reality), before)
        self.assertIn(p['id'], delta['no_longer_justified_actions'])
        self.assertEqual(app.history[-1]['reason'], 'Human explicitly omits emulator test')

    def test_F_stale_operation_never_satisfied_by_package_presence(self):
        app = self.app()
        app.reality.facts['op:apk'].observed_at -= 4000
        self.assertEqual(assessment(app, 'apk')['status'], 'NEEDS_VERIFICATION')
        entry = next(e for e in plan_probes(app)['entries'] if e['fact'] == 'op:apk')
        self.assertEqual(entry['classification'], 'STALE_BUT_RELEVANT')

    def test_G_failed_measurement_is_unknown_not_global_absence(self):
        app = self.app('live', ['python_runtime'])
        with patch('awareness_kernel.probes.bounded_measure', return_value={'ok': False, 'error': 'controlled failure'}):
            result = run_probes(app, ['runtime'])
        self.assertTrue(all(e['classification'] == 'PROBE_FAILED' for e in result['probe_records']))
        self.assertIsNone(app.reality.facts['runtime:available'].value)
        self.assertTrue(all(e['current_state'] == 'PROBE_FAILED' for e in app.observations()))
        self.assertEqual(assessment(app, 'python_runtime')['status'], 'NEEDS_VERIFICATION')
        self.assertNotEqual(assessment(app, 'python_runtime')['status'], 'ACTUAL_CAPABILITY_GAP')

    def test_H_history_evidence_and_ids_survive_reload(self):
        app = self.app('android-phone')
        p = app.create_plan('emulator_test')
        app.revise(reason='Omit emulator', remove=['emulator_test'])
        app.save()
        reopened = Workspace(self.folder).load()
        self.assertEqual(reopened.intent.id, app.intent.id)
        self.assertEqual(reopened.intent.revision, 2)
        self.assertEqual(reopened.evidence, app.evidence)
        self.assertEqual(reopened.history, app.history)
        self.assertEqual(reopened.evaluate_plan(p['id'])['decision'], 'REJECTED_STALE')

    def test_H_real_process_restart_through_cli(self):
        def cli(*args):
            command = [sys.executable, '-m', 'awareness_kernel', *args, '--workspace', str(self.folder), '--json']
            result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=True)
            return json.loads(result.stdout)
        initial = cli('workspace-init', '--scenario', 'android-phone', '--objective', 'Build APK and test emulator')
        revised = cli('intent-revise', '--remove', 'emulator_test', '--reason', 'Human omits emulator', '--confirm')
        reloaded = cli('workspace-show')
        self.assertEqual(reloaded['intent']['id'], initial['intent']['id'])
        self.assertEqual(reloaded['intent'], revised['intent'])
        self.assertEqual(reloaded['intent']['revision'], 2)

    def test_I_supported_reads_never_call_execution_gateway_or_change_environment(self):
        app = self.app('live', ['python_runtime'])
        original = dict(os.environ)
        with patch.object(Kernel, 'submit', side_effect=AssertionError('gateway forbidden')):
            result = run_probes(app)
        self.assertEqual(dict(os.environ), original)
        self.assertTrue(all(e['classification'] == 'VERIFIED' for e in result['probe_records']))
        self.assertEqual(assessment(app, 'python_runtime')['status'], 'ALREADY_SATISFIED')
        self.assertEqual(plan_probes(app)['probes_to_run'], [])
        self.assertTrue(all(e['source_mode'] == 'live' for e in result['probe_records']))

    def test_wrong_artifact_compatibility_does_not_satisfy(self):
        app = self.app()
        app.evidence[app.reality.facts['op:apk'].evidence_id]['compatibility_target'] = 'unrelated-output'
        self.assertEqual(assessment(app, 'apk')['status'], 'NEEDS_VERIFICATION')

    def test_unknown_alternative_prevents_false_global_gap(self):
        app = self.app('notebook')
        app.reality.facts.pop('pkg:portable_compiler')
        app.reality.facts.pop('op:native-portable')
        self.assertEqual(assessment(app, 'native')['status'], 'NEEDS_VERIFICATION')

    def test_malformed_fact_is_not_verified_blocker_or_satisfaction(self):
        app = self.app()
        app.reality.facts['op:apk'].value = 'not-a-boolean'
        app.reality.facts['op:apk'].result = 'not-a-boolean'
        app.evidence[app.reality.facts['op:apk'].evidence_id]['result'] = 'not-a-boolean'
        self.assertEqual(assessment(app, 'apk')['status'], 'NEEDS_VERIFICATION')

    def test_changed_target_contract_requires_new_compatible_evidence(self):
        app = self.app('portable')
        app.intent.constraints['capability_targets']['native'] = 'linux-arm-native-binary'
        self.assertEqual(assessment(app, 'native')['status'], 'NEEDS_VERIFICATION')

    def test_nonfinite_storage_is_not_adequate_resource_evidence(self):
        app = self.app()
        app.reality.facts['storage'].value = float('nan')
        app.reality.facts['storage'].result = float('nan')
        app.evidence[app.reality.facts['storage'].evidence_id]['result'] = float('nan')
        self.assertNotEqual(assessment(app, 'apk')['status'], 'ALREADY_SATISFIED')

    def test_all_verified_absent_alternatives_establish_scoped_gap(self):
        app = self.app('notebook')
        result = assessment(app, 'native')
        self.assertEqual(result['status'], 'ACTUAL_CAPABILITY_GAP')
        self.assertIsNone(result['additional_installation_required'])

    def test_storage_constraint_can_block_otherwise_verified_path(self):
        app = self.app()
        app.intent.constraints['min_storage'] = 100
        self.assertEqual(assessment(app, 'apk')['status'], 'ACTUAL_CAPABILITY_GAP')

    def test_no_reprobe_when_all_relevant_evidence_is_fresh(self):
        app = self.app('live', ['python_runtime'])
        run_probes(app)
        with patch('awareness_kernel.probes.bounded_measure', side_effect=AssertionError('unnecessary probe')):
            self.assertEqual(run_probes(app)['probe_records'], [])

    def test_runtime_evidence_is_bound_to_actual_application_context(self):
        app = self.app('live', ['python_runtime'])
        run_probes(app)
        record = app.evidence[app.reality.facts['op:python_runtime'].evidence_id]
        record['details']['execution_context']['executable'] = 'another-application-context'
        self.assertEqual(assessment(app, 'python_runtime')['status'], 'NEEDS_VERIFICATION')
        self.assertIn('runtime', plan_probes(app)['probes_to_run'])
        current = next(e for e in app.observations() if e['id'] == record['id'])
        self.assertEqual(current['current_state'], 'STALE')

    def test_storage_evidence_cannot_transfer_to_another_volume_scope(self):
        app = self.app('live', ['python_runtime'])
        run_probes(app)
        record = app.evidence[app.reality.facts['storage'].evidence_id]
        record['details']['resource_scope'] = 'different-volume'
        self.assertEqual(assessment(app, 'python_runtime')['status'], 'NEEDS_VERIFICATION')
        self.assertIn('storage', plan_probes(app)['probes_to_run'])

    def test_irrelevant_or_unsupported_probe_explicitly_rejected(self):
        app = self.app('live', ['python_runtime'])
        for probe in ('locate-cuda', 'locate-adb', 'device', 'arbitrary-shell'):
            with self.assertRaises(ValueError):
                run_probes(app, [probe])

    def test_fresh_locator_observation_reused_without_promoting_capability(self):
        app = self.app('live', ['native'])
        with patch('awareness_kernel.probes.bounded_measure', return_value={
                'ok': True, 'result': {'pkg:compiler': False, 'context': 'controlled PATH-only observation'}}):
            run_probes(app, ['locate-compiler'])
        entry = next(e for e in plan_probes(app)['entries'] if e['fact'] == 'pkg:compiler')
        self.assertEqual(entry['classification'], 'FRESH_AND_REUSABLE')
        self.assertFalse(entry['adequate_for_capability'])
        self.assertNotIn('locate-compiler', plan_probes(app)['probes_to_run'])
        self.assertEqual(assessment(app, 'native')['status'], 'NEEDS_VERIFICATION')

    def test_simulated_state_cannot_be_promoted_using_live_probes(self):
        app = self.app()
        with self.assertRaises(ValueError):
            run_probes(app)

    def test_probe_definitions_have_contract_and_bounded_worker(self):
        required = {'id', 'target_fact', 'method', 'execution_platform', 'required_privileges',
                    'expected_resource_cost', 'max_execution_seconds', 'max_output_bytes',
                    'freshness_seconds', 'supported_operating_systems', 'failure_behavior', 'evidence_classification'}
        self.assertTrue(all(required <= asdict(p).keys() for p in definitions().values()))
        result = bounded_measure(replace(definitions()['storage'], max_execution_seconds=0), self.folder)
        self.assertFalse(result['ok'])
        self.assertIn('deadline', result['error'])

    def test_real_read_only_worker_failure_is_preserved_not_absence(self):
        app = self.app('live', ['python_runtime'])
        actual_measure = bounded_measure
        with patch('awareness_kernel.probes.bounded_measure',
                   side_effect=lambda d, w: actual_measure(d, self.folder / 'deliberately-nonexistent-probe-target')):
            result = run_probes(app, ['storage'])
        self.assertTrue(result['probe_records'])
        self.assertTrue(all(e['classification'] == 'PROBE_FAILED' for e in result['probe_records']))
        self.assertIn('FileNotFoundError', result['probe_records'][0]['error_summary'])
        self.assertEqual(assessment(app, 'python_runtime')['status'], 'NEEDS_VERIFICATION')
        app.save()
        self.assertEqual(Workspace(self.folder).load().reality.facts['storage'].classification, 'PROBE_FAILED')

    def test_path_locator_is_observation_not_operational_absence(self):
        with patch('awareness_kernel.probes.shutil.which', return_value=None):
            result = _measure('locate-adb', self.folder)
        self.assertFalse(result['pkg:adb'])
        self.assertIn('does not prove absence', result['limitation'])
        self.assertEqual(definitions()['locate-adb'].evidence_classification, 'OBSERVED')

    def test_revisions_add_exclude_include_and_narrow(self):
        app = self.app('portable')
        app.revise(reason='Choose portable target explicitly', narrow='native=native_portable')
        self.assertEqual(app.intent.acceptance_criteria, ['native_portable'])
        self.assertEqual(assessment(app, 'native_portable')['status'], 'ALREADY_SATISFIED')
        app.revise(reason='Also require CPU report', add=['report'])
        app.revise(reason='Exclude report', exclude=['report'])
        self.assertEqual(app.intent.exclusions, ['report'])
        app.revise(reason='Restore report', include=['report'], add=['report'])
        self.assertEqual(app.intent.revision, 5)
        self.assertIn('report', app.diff(1, 5)['added_criteria'])

    def test_noop_empty_reason_and_empty_criteria_do_not_revise(self):
        app = self.app()
        for kwargs in ({'reason': ''}, {'reason': 'No changes'}, {'reason': 'Empty goal', 'remove': ['apk']}):
            before = asdict(app.intent)
            with self.assertRaises(ValueError):
                app.revise(**kwargs)
            self.assertEqual(asdict(app.intent), before)

    def test_adding_verified_requirement_records_new_satisfied_path(self):
        app = self.app('portable')
        delta = app.revise(reason='Add explicit portable criterion', add=['native_portable'])
        self.assertIn('native_portable', delta['newly_satisfied_paths'])

    def test_reality_refresh_invalidates_existing_plan(self):
        app = self.app()
        p = app.create_plan('apk')
        app.reality.version += 1
        self.assertEqual(app.evaluate_plan(p['id'])['decision'], 'REJECTED_STALE')

    def test_atomic_write_failure_preserves_prior_state_and_reports_pending(self):
        app = self.app()
        previous = app.path.read_bytes()
        app.revise(reason='Change objective', objective='Produce a documented APK')
        with patch('awareness_kernel.workspace.os.replace', side_effect=OSError('controlled interrupted replace')):
            with self.assertRaises(OSError):
                app.save()
        self.assertEqual(app.path.read_bytes(), previous)
        reopened = Workspace(self.folder).load()
        self.assertEqual(reopened.intent.revision, 1)
        self.assertTrue(reopened.warnings)

    def test_state_schema_and_lock_fail_closed(self):
        app = self.app()
        with app.locked(), self.assertRaises(ValueError):
            with Workspace(self.folder).locked():
                pass
        data = json.loads(app.path.read_text())
        data['schema_version'] = 999
        app.path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            Workspace(self.folder).load()

    def test_initialization_never_overwrites_existing_state(self):
        app = self.app()
        old = app.path.read_bytes()
        with self.assertRaises(ValueError):
            app.initialize('notebook', 'Another objective')
        self.assertEqual(app.path.read_bytes(), old)

    def test_derived_cached_capability_not_used_after_evidence_expires(self):
        app = self.app()
        app.reality.facts['op:apk'].observed_at -= 4000
        app.save()
        loaded = Workspace(self.folder).load()
        self.assertIsNone(loaded.reality.derived_capabilities['apk'])
        self.assertEqual(assessment(loaded, 'apk')['status'], 'NEEDS_VERIFICATION')

    def test_expired_latest_probe_is_visibly_stale_and_historical(self):
        app = self.app()
        app.reality.facts['op:apk'].observed_at -= 4000
        record = next(r for r in app.observations() if r['id'] == app.reality.facts['op:apk'].evidence_id)
        self.assertTrue(record['latest_for_fact'])
        self.assertTrue(record['historical'])
        self.assertEqual(record['current_state'], 'STALE')
        self.assertEqual(record['classification'], 'VERIFIED')  # Original observation is retained.
