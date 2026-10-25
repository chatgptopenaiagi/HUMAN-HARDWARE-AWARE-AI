"""Exercise installed entry points from a disposable directory outside the checkout."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory


def verify(python, exe=None):
    checks = []
    root = Path(__file__).resolve().parents[1]
    with TemporaryDirectory(prefix='awareness-independent-') as directory:
        folder = Path(directory)
        assert not folder.is_relative_to(root)
        env = {k: v for k, v in os.environ.items() if k not in {'PYTHONPATH', 'PYTHONHOME'}}
        targets = {'wheel': [str(Path(python).with_name('awareness-kernel.exe'))]}
        if exe:
            copied = folder / 'AwarenessKernel.exe'
            shutil.copyfile(exe, copied)
            targets['exe'] = [str(copied)]
        identity = subprocess.run([str(python), '-I', '-c',
            'import awareness_kernel,json,sys; print(json.dumps({"module":awareness_kernel.__file__,"prefix":sys.prefix,"base_prefix":sys.base_prefix}))'],
            cwd=folder, env=env, capture_output=True, text=True, timeout=60, check=True)
        origin = json.loads(identity.stdout)
        assert 'site-packages' in origin['module']
        assert origin['prefix'] != origin['base_prefix']
        before = sorted(p.name for p in folder.iterdir())
        cases = [
            (['--version'], None), (['--help'], None),
            (['graph', '--requirement', 'native'], None),
            (['graph', '--requirement', 'native', '--format', 'tree'], None),
            (['inspect', '--scenario', 'android'], None),
            (['inspect', '--scenario', 'workstation'], None),
            (['simulate', '--scenario', 'android', '--operation', 'install', '--requirement', 'apk', '--component', 'sdk'], 'REJECTED_UNNECESSARY'),
            (['simulate', '--scenario', 'notebook', '--operation', 'install', '--requirement', 'native', '--component', 'compiler'], 'AUTHORIZED'),
            (['simulate', '--scenario', 'notebook', '--operation', 'build', '--requirement', 'native'], 'REJECTED_INFEASIBLE'),
            (['simulate', '--scenario', 'workstation', '--operation', 'install', '--requirement', 'report', '--component', 'cuda'], 'REJECTED_UNNECESSARY'),
            (['simulate', '--scenario', 'portable', '--operation', 'install', '--requirement', 'native', '--component', 'compiler'], 'REJECTED_UNNECESSARY'),
            (['simulate', '--scenario', 'notebook', '--storage', '1', '--operation', 'install', '--requirement', 'native', '--component', 'compiler'], 'REJECTED_INFEASIBLE'),
            (['selftest'], None), (['execute'], 'USAGE_ERROR'),
        ]
        for target, command in targets.items():
            target_env = dict(env)
            if target == 'exe':
                target_env['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32')
            for args, expected in cases:
                run = subprocess.run(command + args, cwd=folder, env=target_env,
                                     capture_output=True, text=True, timeout=60)
                passed = run.returncode == (2 if expected == 'USAGE_ERROR' else 0)
                if expected != 'USAGE_ERROR' and args[0] not in ('--version', '--help') and 'tree' not in args:
                    try:
                        data = json.loads(run.stdout)
                        passed &= (data['execution_enabled'] is False and data['gateway_outcome'] == 'DISABLED_IN_DISTRIBUTION')
                        if expected:
                            passed &= data['authorization_decision']['decision'] == expected
                            passed &= data['verification_results']['state_unchanged']
                            passed &= data['verification_results']['postconditions'] == 'NOT_EXECUTED'
                        if args[0] == 'selftest':
                            passed &= data['passed'] and len(data['checks']) == 7
                        if args[0] == 'inspect':
                            passed &= all(k in data for k in ('point_a', 'point_b', 'capability_graph', 'reality_snapshot', 'intent_snapshot'))
                    except (ValueError, KeyError):
                        passed = False
                elif expected != 'USAGE_ERROR':
                    passed &= 'EXPERIMENTAL DEVELOPER PREVIEW' in run.stdout
                checks.append({'target': target, 'args': args, 'expected': expected,
                               'exit_code': run.returncode, 'passed': bool(passed),
                               'stdout': run.stdout, 'stderr': run.stderr})
        module_run = subprocess.run([str(python), '-I', '-m', 'awareness_kernel', 'selftest'],
                                    cwd=folder, env=env, capture_output=True, text=True, timeout=60)
        module_passed = module_run.returncode == 0 and json.loads(module_run.stdout)['passed']
        checks.append({'target': 'wheel-python-module', 'passed': module_passed, 'stdout': module_run.stdout})
        unchanged = sorted(p.name for p in folder.iterdir()) == before
        return {'working_directory_outside_repository': True, 'installed_origin': origin,
                'exe_test_path_contains_no_python': bool(exe), 'cwd_files_unchanged': unchanged,
                'checks': checks, 'passed': all(c['passed'] for c in checks) and unchanged,
                'packaged_execution_isolation': 'UNVERIFIED_EXECUTION_DISABLED'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--python', required=True, type=Path)
    parser.add_argument('--exe', type=Path)
    parser.add_argument('--results', required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.python.resolve(), args.exe.resolve() if args.exe else None)
    args.results.parent.mkdir(parents=True, exist_ok=True)
    args.results.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': result['passed'], 'checks': len(result['checks'])}))
    raise SystemExit(0 if result['passed'] else 1)
