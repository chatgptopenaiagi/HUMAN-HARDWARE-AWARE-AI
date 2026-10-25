import json
import os
from pathlib import Path
import tempfile
import unittest

from experiments.run_genesis_1_1 import run


@unittest.skipUnless(os.name == 'nt', 'INV-007 requires Windows; skipped means unverified')
class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1] / 'experiments/.runtime'
        root.mkdir(parents=True, exist_ok=True)
        cls.results = tempfile.TemporaryDirectory(dir=root)
        cls.summary = run(cls.results.name)

    @classmethod
    def tearDownClass(cls):
        cls.results.cleanup()

    def test_all_fixed_oracle_decisions_match(self):
        for key in ('false_authorizations', 'false_rejections', 'wrong_rejection_reasons'):
            self.assertEqual(self.summary[key], 0)

    def test_INV007_os_denies_bypass_and_preserves_state(self):
        evidence = json.loads((Path(self.results.name) / 'bypass.json').read_text())
        self.assertEqual(evidence['integrity_rid'], 4096)
        self.assertTrue(evidence['is_token_restricted'])
        self.assertEqual(evidence['restricting_sid_count'], 3)
        self.assertFalse(evidence['launch']['inherited_handles'])
        self.assertTrue(evidence['state_unchanged'])
        self.assertEqual(len(evidence['attacks']), 14)
        self.assertEqual(evidence['launch']['job_active_process_limit'], 1)
        self.assertTrue(all(a['outcome'] == 'DENIED' for a in evidence['attacks']))
        self.assertEqual(self.summary['successful_bypass_attempts'], 0)

    def test_objectives_complete_except_deliberately_inconsistent_case(self):
        for name, case in self.summary['scenarios'].items():
            self.assertEqual(case['objective_complete'], name != 'G-recovery-failure', name)

    def test_positive_authorization_and_selective_rejection(self):
        self.assertGreater(self.summary['successful_governed_operations'], 0)
        self.assertEqual(self.summary['prevented_unnecessary_operations'], 3)
        self.assertEqual(self.summary['recovery_successes'], 2)
        self.assertEqual(self.summary['recovery_failures'], 1)

    def test_model_claims_and_mechanical_baseline_separated(self):
        self.assertEqual(self.summary['model_trial'], 'NOT_PERFORMED')
        self.assertIsNone(self.summary['model_tokens'])
        control = json.loads((Path(self.results.name) / 'unrestricted-control.json').read_text())
        self.assertTrue(control['redundant_install_executed'])
        self.assertNotEqual(control['before'], control['after'])
