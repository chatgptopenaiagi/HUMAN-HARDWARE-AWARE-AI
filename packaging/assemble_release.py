"""Assemble verified preview artifacts, notices, inventories and checksums."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
VERSION = '0.1.2.dev1'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def assemble():
    wheel = DIST / f'human_hardware_awareness_kernel-{VERSION}-py3-none-any.whl'
    sdist = DIST / f'human_hardware_awareness_kernel-{VERSION}.tar.gz'
    exe = DIST / 'AwarenessKernel.exe'
    acceptance = json.loads((ROOT / 'genesis-1.2/evidence/artifact-acceptance.json').read_text())
    assert acceptance['passed']
    with zipfile.ZipFile(wheel) as archive:
        assert archive.testzip() is None
        wheel_names = archive.namelist()
        for name in wheel_names:
            assert name.startswith(('awareness_kernel/', f'human_hardware_awareness_kernel-{VERSION}.dist-info/'))
            if name.endswith('.py'):
                assert archive.read(name).replace(b'\r\n', b'\n') == (ROOT / name).read_bytes().replace(b'\r\n', b'\n')
        metadata = archive.read(f'human_hardware_awareness_kernel-{VERSION}.dist-info/METADATA').decode()
        assert 'Requires-Dist:' not in metadata
    with tarfile.open(sdist) as archive:
        source_names = archive.getnames()
        assert all(not m.issym() and not m.islnk() and not m.name.startswith('/')
                   and '..' not in Path(m.name).parts for m in archive.getmembers())
        assert not any(any(part in name for part in ('.preview-work/', '.runtime/', '__pycache__/')) for name in source_names)
    analysis = ast.literal_eval((ROOT / '.preview-work/pyinstaller/AwarenessKernel/Analysis-00.toc').read_text())
    binary_names = sorted({entry[0] for part in analysis if isinstance(part, list)
                           for entry in part if isinstance(entry, tuple) and len(entry) > 2
                           and entry[-1] in {'BINARY', 'EXTENSION'}})
    notices = {
        'THIRD-PARTY/CPython-LICENSE.txt': (Path(sys.base_prefix) / 'LICENSE_PYTHON.txt').read_bytes(),
        'THIRD-PARTY/zlib-LICENSE.txt': (Path(sys.base_prefix) / 'Library/share/doc/zlib/zlib/LICENSE').read_bytes(),
    }
    copying = next((ROOT / '.preview-work/venv/Lib/site-packages').glob('pyinstaller-*.dist-info/licenses/COPYING.txt'))
    notices['THIRD-PARTY/PyInstaller-COPYING.txt'] = copying.read_bytes()
    notices['THIRD-PARTY/README.txt'] = (
        'Bundled components: CPython, PyInstaller bootloader, zlib, and Microsoft Visual C++/Universal C runtimes.\n'
        'Python, PyInstaller (including its bootloader exception), and zlib notices accompany this archive.\n'
        'Microsoft runtime terms: https://visualstudio.microsoft.com/license-terms/vs2022-cruntime/\n'
        'No third-party package is required by the Python wheel; the EXE embeds its runtime.\n'
        'The project has not selected an open-source license. This is an experimental private developer preview.\n'
    ).encode()
    bundle = DIST / f'AwarenessKernel-{VERSION}-windows-x64.zip'
    with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.write(exe, 'AwarenessKernel.exe')
        for filename in ('README.md', 'SECURITY.md', 'BUILD-REPORT.md'):
            archive.write(ROOT / 'genesis-1.2' / filename, filename)
        for name, content in notices.items():
            archive.writestr(name, content)
    with TemporaryDirectory(prefix='awareness-extract-') as directory, zipfile.ZipFile(bundle) as archive:
        assert archive.testzip() is None
        archive.extractall(directory)
        unpacked = Path(directory) / 'AwarenessKernel.exe'
        assert digest(unpacked.read_bytes()) == digest(exe.read_bytes())
        env = {k: v for k, v in os.environ.items() if k not in {'PYTHONPATH', 'PYTHONHOME'}}
        env['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32')
        result = subprocess.run([str(unpacked), 'selftest'], cwd=directory, env=env,
                                capture_output=True, text=True, timeout=60, check=True)
        assert json.loads(result.stdout)['passed']
    inventory = {'wheel_files': wheel_names, 'sdist_files': source_names,
                 'exe_binary_dependencies': binary_names, 'zip_extraction_selftest': 'PASSED',
                 'packaged_execution': 'DISABLED', 'files': {}}
    for artifact in (wheel, sdist, exe, bundle):
        inventory['files'][artifact.name] = {'bytes': artifact.stat().st_size, 'sha256': digest(artifact.read_bytes())}
    checksums = ''.join(f'{item["sha256"]}  {name}\n' for name, item in inventory['files'].items())
    (DIST / 'SHA256SUMS.txt').write_text(checksums, encoding='utf-8')
    (ROOT / 'genesis-1.2/SHA256SUMS.txt').write_text(checksums, encoding='utf-8')
    (ROOT / 'genesis-1.2/evidence/artifact-inventory.json').write_text(json.dumps(inventory, indent=2) + '\n', encoding='utf-8')
    sources = [ROOT / 'pyproject.toml', ROOT / 'MANIFEST.in', *sorted((ROOT / 'awareness_kernel').glob('*.py')),
               *sorted((ROOT / 'packaging').glob('*')), ROOT / 'tests/test_preview.py']
    (ROOT / 'genesis-1.2/evidence/source-manifest.json').write_text(json.dumps({
        p.relative_to(ROOT).as_posix(): digest(p.read_bytes().replace(b'\r\n', b'\n'))
        for p in sources if p.is_file()}, indent=2) + '\n', encoding='utf-8')
    print(checksums)


if __name__ == '__main__':
    assemble()
