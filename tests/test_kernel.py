from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import time
import unittest

from awareness_kernel.kernel import Kernel, graph
from awareness_kernel.records import CapabilityGraph, Fact, Node


class KernelTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / 'experiments/.runtime'
        root.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=root)
        self.addCleanup(self.tmp.cleanup)

    def kernel(self, packages=(), criteria=('native',), storage=50):
        return Kernel(self.tmp.name, self.id(), packages, list(criteria), storage)

    def test_INV001_build_without_compiler_cannot_mutate(self):
        k = self.kernel()
        before = k.path.read_bytes()
        e = k.submit(k.plan('build', 'native'))
        self.assertEqual(e['validator']['decision'], 'REJECTED_INFEASIBLE')
        self.assertEqual(k.path.read_bytes(), before)

    def test_INV002_expired_evidence_blocks_mutation(self):
        k = self.kernel()
        k.reality.facts['storage'].observed_at -= 1000
        self.assertEqual(k.submit(k.plan('install', 'native', 'compiler'))['validator']['decision'], 'REJECTED_STALE')
        self.assertNotIn('compiler', k.state['packages'])

    def test_failed_probe_not_current_verified_claim(self):
        k = self.kernel()
        k.refresh({'storage'}, fail={'storage'})
        self.assertEqual(k.reality.facts['storage'].classification, 'PROBE_FAILED')
        self.assertEqual(k.validate(k.plan('install', 'native', 'compiler'))['decision'], 'REJECTED_STALE')

    def test_future_evidence_and_inadequate_method_result_not_fresh(self):
        for changes in [{'observed_at': time.time() + 1000}, {'evidence_id': ''},
                        {'exit_status': 1}, {'classification': 'OBSERVED'}, {'result': False}]:
            k = self.kernel()
            f = k.reality.facts['storage']
            for key, value in changes.items():
                setattr(f, key, value)
            self.assertFalse(f.fresh(time.time()))

    def test_all_evidence_states_are_serializable(self):
        for state in ('VERIFIED', 'OBSERVED', 'STALE', 'UNKNOWN', 'PROBE_FAILED', 'UNSUPPORTED'):
            f = Fact('x', None, state, time.time(), 60, 'software')
            self.assertEqual(json.loads(json.dumps(asdict(f)))['classification'], state)

    def test_INV003_redundant_sdk_install_rejected_but_reuse_runs(self):
        k = self.kernel(('java', 'sdk', 'builder'), ('apk',))
        before = deepcopy(k.state)
        e = k.submit(k.plan('install', 'apk', 'sdk'))
        self.assertEqual(e['validator']['decision'], 'REJECTED_UNNECESSARY')
        self.assertEqual(k.state, before)
        self.assertEqual(e['validator']['reuse_path'], 'cap:apk')
        self.assertEqual(k.submit(k.plan('reuse', 'apk'))['verification'], 'PASSED')
        self.assertTrue(k.complete())

    def test_package_presence_does_not_prove_operational_capability(self):
        k = self.kernel(('compiler',))
        k.refresh({'op:native'}, fail={'op:native'})
        self.assertIsNone(k.graph.verified_path('native', k.reality))
        self.assertNotEqual(k.validate(k.plan('build', 'native'))['decision'], 'AUTHORIZED')

    def test_INV004_invalidated_before_reverification(self):
        k = self.kernel()
        p = k.plan('install', 'native', 'compiler')
        observed_during_save = []
        save = k._save

        def watch():
            observed_during_save.append(k.reality.facts['op:native'].classification)
            save()

        k._save = watch
        e = k.submit(p)
        self.assertEqual(observed_during_save[0], 'STALE')
        self.assertIn('op:native', e['invalidation'])
        self.assertTrue(k.reality.facts['op:native'].fresh(time.time()))
        self.assertTrue(k.reality.facts['op:native'].value)
        self.assertEqual(k.validate(p)['decision'], 'REJECTED_STALE')

    def test_INV005_irrelevant_cuda_cannot_reach_state(self):
        k = self.kernel(('cpu_runtime',), ('report',))
        e = k.submit(k.plan('install', 'report', 'cuda'))
        self.assertEqual(e['validator']['decision'], 'REJECTED_UNNECESSARY')
        self.assertNotIn('cuda', k.state['packages'])
        self.assertNotIn('pkg:cuda', k.reality.facts)

    def test_irrelevant_stale_fact_does_not_trigger_probe_or_block(self):
        k = self.kernel()
        k.reality.facts['pkg:cuda'] = Fact('pkg:cuda', True, 'STALE', 0, 1, 'software')
        policy = k.reality.awareness(k.relevant())
        self.assertIn('pkg:cuda', policy['irrelevant_stale'])
        self.assertEqual(policy['needs_probe'], [])
        self.assertEqual(k.validate(k.plan('install', 'native', 'compiler'))['decision'], 'AUTHORIZED')

    def test_resource_limit_enforced(self):
        k = self.kernel(storage=2)
        e = k.submit(k.plan('install', 'native', 'compiler'))
        self.assertEqual(e['validator']['decision'], 'REJECTED_INFEASIBLE')
        self.assertEqual(k.state['packages'], [])

    def test_mutation_does_not_probe_irrelevant_stale_gpu_information(self):
        k = self.kernel()
        k.reality.facts['pkg:cuda'] = Fact('pkg:cuda', True, 'STALE', 0, 1, 'software')
        k.submit(k.plan('install', 'native', 'compiler'))
        self.assertEqual(k.reality.facts['pkg:cuda'].classification, 'STALE')
        self.assertNotIn('pkg:cuda', [p['id'] for p in k.probes])

    def test_privilege_and_pending_requirements_need_human(self):
        k = self.kernel()
        k.state['privilege'] = False
        k.refresh({'privilege'})
        self.assertEqual(k.validate(k.plan('install', 'native', 'compiler'))['decision'], 'REQUIRES_HUMAN_DECISION')
        k.state['privilege'] = True
        k.refresh({'privilege'})
        k.intent.assumed_pending.append('unconfirmed target')
        self.assertEqual(k.validate(k.plan('install', 'native', 'compiler'))['decision'], 'REQUIRES_HUMAN_DECISION')

    def test_unsupported_and_forged_plan_never_mutate(self):
        k = self.kernel()
        for operation in ('shell', 'delete', 'install-arbitrary-code'):
            self.assertEqual(k.submit(k.plan(operation, 'native'))['validator']['decision'], 'REJECTED_UNSUPPORTED')
        p = k.plan('install', 'native', 'compiler')
        p.required_resources['storage'] = 0
        self.assertEqual(k.submit(p)['validator']['decision'], 'REJECTED_UNSUPPORTED')
        self.assertEqual(k.state['packages'], [])

    def test_forged_postcondition_and_scope_rejected(self):
        k = self.kernel()
        for field, value in [('expected_postconditions', {'artifact': 'apk'}),
                             ('affected_scopes', []), ('preconditions', []), ('verification', [])]:
            p = k.plan('install', 'native', 'compiler')
            setattr(p, field, value)
            self.assertEqual(k.submit(p)['validator']['decision'], 'REJECTED_UNSUPPORTED')

    def test_INV006_missing_recovery_no_execution(self):
        k = self.kernel()
        p = k.plan('install', 'native', 'compiler')
        p.recovery = ''
        self.assertEqual(k.submit(p)['validator']['decision'], 'REQUIRES_HUMAN_DECISION')
        self.assertEqual(k.state['packages'], [])

    def test_recovery_restores_and_verifies_checkpoint_once(self):
        k = self.kernel()
        before = deepcopy(k.state)
        e = k.submit(k.plan('install', 'native', 'compiler'), fault='partial')
        self.assertEqual(e['gateway_outcome'], 'FAILED')
        self.assertNotEqual(e['failed_state'], before)
        self.assertEqual(e['recovery'], {'attempts': 1, 'result': 'RESTORED_VERIFIED'})
        self.assertEqual(k.state, before)
        self.assertEqual(json.loads(k.path.read_text()), before)
        self.assertFalse(k.reality.facts['op:native'].value)

    def test_failed_recovery_locks_subsequent_mutations(self):
        k = self.kernel()
        e = k.submit(k.plan('install', 'native', 'compiler'), fault='recovery-fails')
        self.assertEqual(e['recovery']['result'], 'FAILED_INCONSISTENT')
        before = k.path.read_bytes()
        blocked = k.submit(k.plan('build', 'native'))
        self.assertEqual(blocked['validator']['decision'], 'REJECTED_INFEASIBLE')
        self.assertEqual(k.path.read_bytes(), before)
        self.assertFalse(k.complete())
        self.assertTrue(all(f.classification == 'STALE' for f in k.reality.facts.values()))

    def test_failed_postcondition_probe_recovers(self):
        k = self.kernel()
        e = k.submit(k.plan('install', 'native', 'compiler'), fault='probe')
        self.assertEqual(e['verification'], 'FAILED')
        self.assertEqual(e['recovery']['result'], 'RESTORED_VERIFIED')
        self.assertNotIn('compiler', k.state['packages'])

    def test_real_restore_io_error_is_detectable_and_locks_memory(self):
        k = self.kernel()
        def disk_error():
            raise OSError('controlled write failure from adapter')
        k._save = disk_error
        e = k.submit(k.plan('install', 'native', 'compiler'))
        self.assertEqual(e['recovery']['result'], 'FAILED_INCONSISTENT')
        self.assertFalse(e['recovery']['lock_persisted'])
        self.assertTrue(k.state['inconsistent'])
        self.assertEqual(k.validate(k.plan('build', 'native'))['decision'], 'REJECTED_INFEASIBLE')

    def test_necessary_install_then_build_completes(self):
        k = self.kernel()
        self.assertEqual(k.submit(k.plan('install', 'native', 'compiler'))['verification'], 'PASSED')
        self.assertFalse(k.complete())
        self.assertEqual(k.submit(k.plan('build', 'native'))['verification'], 'PASSED')
        self.assertTrue(k.complete())

    def test_intent_revision_invalidates_old_plan_and_removes_path(self):
        k = self.kernel(('java', 'sdk', 'builder'), ('apk', 'emulator_test'))
        p = k.plan('install', 'emulator_test', 'emulator')
        k.intent.revise('APK without emulator', ['apk'])
        self.assertEqual(k.intent.revision, 2)
        self.assertEqual(k.intent.revision_history[0]['acceptance_criteria'], ['apk', 'emulator_test'])
        self.assertEqual(k.submit(p)['validator']['decision'], 'REJECTED_STALE')
        self.assertNotIn('pkg:emulator', k.relevant())
        revised = k.plan('reuse', 'apk')
        self.assertEqual(revised.intent_revision, 2)
        self.assertEqual(k.submit(revised)['verification'], 'PASSED')
        self.assertNotIn('emulator', k.state['packages'])

    def test_graph_or_reality_version_change_invalidates_plan(self):
        k = self.kernel()
        p = k.plan('install', 'native', 'compiler')
        k.graph.version += 1
        self.assertEqual(k.validate(p)['decision'], 'REJECTED_STALE')
        p = k.plan('install', 'native', 'compiler')
        k.refresh({'storage'})
        self.assertEqual(k.validate(p)['decision'], 'REJECTED_STALE')

    def test_graph_shared_dependencies_and_alternatives(self):
        k = self.kernel(('compiler',))
        g = k.graph
        g.nodes['cap:native-alt'] = Node('cap:native-alt', 'operational-capability', ['compiler', 'storage'], 'op:native')
        g.alternatives['native'].insert(0, 'cap:native-alt')
        self.assertEqual(g.verified_path('native', k.reality), 'cap:native-alt')
        self.assertEqual(list(g.nodes).count('compiler'), 1)
        self.assertIn('compiler [shared reference]', g.tree('native'))

    def test_graph_rejects_cycles_and_dangling_dependencies(self):
        with self.assertRaises(ValueError):
            CapabilityGraph('bad', {'a': Node('a', 'capability', ['a'])}, {})
        with self.assertRaises(ValueError):
            CapabilityGraph('bad', {'a': Node('a', 'capability', ['missing'])}, {})

    def test_existing_alternative_prevents_unneeded_primary_compiler(self):
        k = self.kernel(('portable_compiler',))
        self.assertEqual(k.graph.verified_path('native', k.reality), 'cap:native-portable')
        before = deepcopy(k.state)
        e = k.submit(k.plan('install', 'native', 'compiler'))
        self.assertEqual(e['validator']['decision'], 'REJECTED_UNNECESSARY')
        self.assertEqual(k.state, before)
        self.assertEqual(k.submit(k.plan('reuse', 'native'))['verification'], 'PASSED')
        self.assertTrue(k.complete())

    def test_three_records_and_events_round_trip(self):
        k = self.kernel()
        p = k.plan('install', 'native', 'compiler')
        for record in (k.reality, k.intent, k.graph, p):
            data = json.loads(json.dumps(asdict(record)))
            self.assertEqual(data['schema_version'], 1)
        e = k.submit(p)
        log = json.loads((Path(self.tmp.name) / 'events.jsonl').read_text().strip())
        self.assertEqual(log, e)
        for field in ('timestamp', 'experiment', 'plan', 'validator', 'before', 'after',
                      'verification', 'recovery', 'evidence_references'):
            self.assertIn(field, log)
        self.assertTrue(log['evidence_references'])
