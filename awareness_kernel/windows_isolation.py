"""Windows-only low-integrity primary-token launcher. No global policy changes."""
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil
import zipfile
import hashlib
from contextlib import contextmanager


@contextmanager
def protect_broker():
    """Deny mutation/termination handles to this experiment process, then restore DACL."""
    kernel = C.WinDLL('kernel32', use_last_error=True)
    advapi = C.WinDLL('advapi32', use_last_error=True)
    kernel.GetCurrentProcess.restype = W.HANDLE
    kernel.LocalFree.argtypes = [C.c_void_p]
    advapi.GetSecurityInfo.argtypes = [W.HANDLE, C.c_int, W.DWORD, C.c_void_p,
                                     C.c_void_p, C.POINTER(C.c_void_p), C.c_void_p,
                                     C.POINTER(C.c_void_p)]
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        W.LPCWSTR, W.DWORD, C.POINTER(C.c_void_p), C.c_void_p]
    advapi.GetSecurityDescriptorDacl.argtypes = [C.c_void_p, C.POINTER(W.BOOL),
                                                C.POINTER(C.c_void_p), C.POINTER(W.BOOL)]
    advapi.SetSecurityInfo.argtypes = [W.HANDLE, C.c_int, W.DWORD, C.c_void_p,
                                     C.c_void_p, C.c_void_p, C.c_void_p]
    process = kernel.GetCurrentProcess()
    old_descriptor, old_dacl, descriptor, dacl = (C.c_void_p() for _ in range(4))
    present, defaulted = W.BOOL(), W.BOOL()
    code = advapi.GetSecurityInfo(process, 6, 4, None, None, C.byref(old_dacl), None,
                                 C.byref(old_descriptor))
    if code:
        raise C.WinError(code)
    try:
        # Deny new real handles, including query handles usable for token theft.
        # Trusted harness retains its existing pseudo handle and restores the DACL.
        if not advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                'D:(D;;0x001FFFFF;;;WD)(A;;GA;;;SY)(A;;GA;;;OW)', 1, C.byref(descriptor), None):
            raise C.WinError(C.get_last_error())
        if not advapi.GetSecurityDescriptorDacl(descriptor, C.byref(present), C.byref(dacl), C.byref(defaulted)):
            raise C.WinError(C.get_last_error())
        code = advapi.SetSecurityInfo(process, 6, 4, None, None, dacl, None)
        if code:
            raise C.WinError(code)
        try:
            yield
        finally:
            code = advapi.SetSecurityInfo(process, 6, 4, None, None, old_dacl, None)
            if code:
                raise C.WinError(code)
    finally:
        if descriptor:
            kernel.LocalFree(descriptor)
        if old_descriptor:
            kernel.LocalFree(old_descriptor)


def label_directory(path, level):
    path = Path(path).resolve()
    boundary = Path(__file__).resolve().parents[1] / 'experiments' / '.runtime'
    if not path.is_relative_to(boundary) or path == boundary:
        raise ValueError('integrity changes limited to disposable child directories')
    path.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(['icacls', str(path), '/setintegritylevel', f'(OI)(CI){level}'],
                            capture_output=True, text=True, check=True)
    if level == 'L':
        # The restricting SID must be allowed to use the low-integrity outbox.
        subprocess.run(['icacls', str(path), '/grant', '*S-1-5-32-545:(OI)(CI)M'],
                       capture_output=True, text=True, check=True)
    return result.stdout.strip()


def reuse_python():
    """Mirror existing interpreter files locally; no install or source ACL changes."""
    target = Path(__file__).resolve().parents[1] / 'experiments/.runtime' / f'proposer-python-{sys.version_info.major}{sys.version_info.minor}'
    manifest = target / 'manifest.json'
    if manifest.exists():
        data = json.loads(manifest.read_text())
        if data['source_executable_sha256'] == hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest() and all(
                (target / name).exists() and hashlib.sha256((target / name).read_bytes()).hexdigest() == digest
                for name, digest in data['files'].items()):
            return target / 'python.exe'
        raise RuntimeError('cached reused runtime changed; investigate rather than silently repair')
    label_directory(target, 'M')
    prefix = Path(sys.base_prefix)
    shutil.copyfile(sys.executable, target / 'python.exe')
    for pattern in ('python*.dll', 'vcruntime*.dll'):
        for file in prefix.glob(pattern):
            shutil.copyfile(file, target / file.name)
    for name in ('ffi.dll', 'zlib.dll'):
        dependency = prefix / 'Library/bin' / name
        if dependency.exists():
            shutil.copyfile(dependency, target / name)
    (target / 'DLLs').mkdir(exist_ok=True)
    for file in (prefix / 'DLLs').iterdir():
        if file.suffix.lower() in {'.dll', '.pyd'}:
            shutil.copyfile(file, target / 'DLLs' / file.name)
    version = f'python{sys.version_info.major}{sys.version_info.minor}'
    ignored = {'site-packages', 'test', 'tests', '__pycache__', 'idlelib', 'tkinter', 'ensurepip', 'turtledemo'}
    with zipfile.ZipFile(target / (version + '.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        for folder, dirs, files in os.walk(prefix / 'Lib'):
            dirs[:] = [d for d in dirs if d not in ignored]
            for name in files:
                file = Path(folder) / name
                if file.suffix == '.py':
                    archive.write(file, file.relative_to(prefix / 'Lib').as_posix())
    (target / (version + '._pth')).write_text(version + '.zip\nDLLs\n.\n', encoding='utf-8')
    data = {'source_executable_sha256': hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
            'source': 'existing interpreter; repository-local reuse, not a new installation',
            'files': {str(f.relative_to(target)): hashlib.sha256(f.read_bytes()).hexdigest()
                      for f in target.rglob('*') if f.is_file()}}
    manifest.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return target / 'python.exe'


def launch_low(script, arguments, directory, timeout_ms=15000):
    if os.name != 'nt':
        raise RuntimeError('Windows token isolation unavailable; do not claim enforcement')
    kernel = C.WinDLL('kernel32', use_last_error=True)
    advapi = C.WinDLL('advapi32', use_last_error=True)

    class SIDATTR(C.Structure):
        _fields_ = [('Sid', C.c_void_p), ('Attributes', W.DWORD)]

    class STARTUP(C.Structure):
        _fields_ = [('cb', W.DWORD), ('reserved', W.LPWSTR), ('desktop', W.LPWSTR),
                    ('title', W.LPWSTR), ('x', W.DWORD), ('y', W.DWORD),
                    ('xs', W.DWORD), ('ys', W.DWORD), ('xc', W.DWORD), ('yc', W.DWORD),
                    ('fill', W.DWORD), ('flags', W.DWORD), ('show', W.WORD),
                    ('reserved2size', W.WORD), ('reserved2', C.c_void_p),
                    ('stdin', W.HANDLE), ('stdout', W.HANDLE), ('stderr', W.HANDLE)]

    class PROCESS(C.Structure):
        _fields_ = [('process', W.HANDLE), ('thread', W.HANDLE),
                    ('pid', W.DWORD), ('tid', W.DWORD)]

    class SECURITY(C.Structure):
        _fields_ = [('length', W.DWORD), ('descriptor', C.c_void_p), ('inherit', W.BOOL)]

    class BASIC_LIMITS(C.Structure):
        _fields_ = [('process_time', C.c_int64), ('job_time', C.c_int64), ('flags', W.DWORD),
                    ('min_working_set', C.c_size_t), ('max_working_set', C.c_size_t),
                    ('active_processes', W.DWORD), ('affinity', C.c_size_t),
                    ('priority', W.DWORD), ('scheduling', W.DWORD)]

    class IO_COUNTERS(C.Structure):
        _fields_ = [(name, C.c_uint64) for name in ('read_ops', 'write_ops', 'other_ops',
                                                  'read_bytes', 'write_bytes', 'other_bytes')]

    class EXTENDED_LIMITS(C.Structure):
        _fields_ = [('basic', BASIC_LIMITS), ('io', IO_COUNTERS),
                    ('process_memory', C.c_size_t), ('job_memory', C.c_size_t),
                    ('peak_process_memory', C.c_size_t), ('peak_job_memory', C.c_size_t)]

    kernel.GetCurrentProcess.restype = W.HANDLE
    kernel.CloseHandle.argtypes = [W.HANDLE]
    kernel.LocalFree.argtypes = [C.c_void_p]
    kernel.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
    kernel.GetExitCodeProcess.argtypes = [W.HANDLE, C.POINTER(W.DWORD)]
    kernel.TerminateProcess.argtypes = [W.HANDLE, W.UINT]
    kernel.CreateJobObjectW.argtypes = [C.c_void_p, W.LPCWSTR]
    kernel.CreateJobObjectW.restype = W.HANDLE
    kernel.SetInformationJobObject.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [W.HANDLE, W.HANDLE]
    kernel.ResumeThread.argtypes = [W.HANDLE]
    advapi.OpenProcessToken.argtypes = [W.HANDLE, W.DWORD, C.POINTER(W.HANDLE)]
    advapi.CreateRestrictedToken.argtypes = [W.HANDLE, W.DWORD, W.DWORD, C.c_void_p,
                                           W.DWORD, C.c_void_p, W.DWORD, C.c_void_p,
                                           C.POINTER(W.HANDLE)]
    advapi.ConvertStringSidToSidW.argtypes = [W.LPCWSTR, C.POINTER(C.c_void_p)]
    advapi.GetLengthSid.argtypes = [C.c_void_p]
    advapi.SetTokenInformation.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD]
    advapi.GetTokenInformation.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.POINTER(W.DWORD)]
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [W.LPCWSTR, W.DWORD, C.POINTER(C.c_void_p), C.c_void_p]
    advapi.GetSecurityDescriptorDacl.argtypes = [C.c_void_p, C.POINTER(W.BOOL), C.POINTER(C.c_void_p), C.POINTER(W.BOOL)]
    advapi.SetSecurityInfo.argtypes = [W.HANDLE, C.c_int, W.DWORD, C.c_void_p, C.c_void_p, C.c_void_p, C.c_void_p]
    advapi.CreateProcessAsUserW.argtypes = [W.HANDLE, W.LPCWSTR, W.LPWSTR, C.c_void_p,
                                          C.c_void_p, W.BOOL, W.DWORD, C.c_void_p,
                                          W.LPCWSTR, C.POINTER(STARTUP), C.POINTER(PROCESS)]

    def check(value):
        if not value:
            raise C.WinError(C.get_last_error())

    original, restricted, sid, restrict_sid = W.HANDLE(), W.HANDLE(), C.c_void_p(), C.c_void_p()
    everyone_sid = C.c_void_p()
    child_descriptor = C.c_void_p()
    process = PROCESS()
    job = W.HANDLE()
    try:
        check(advapi.OpenProcessToken(kernel.GetCurrentProcess(), 0xF01FF, C.byref(original)))
        check(advapi.ConvertStringSidToSidW('S-1-5-32-545', C.byref(restrict_sid)))
        check(advapi.ConvertStringSidToSidW('S-1-1-0', C.byref(everyone_sid)))
        class GROUPS(C.Structure):
            _fields_ = [('count', W.DWORD), ('groups', SIDATTR * 1)]
        size = W.DWORD()
        advapi.GetTokenInformation(original, 28, None, 0, C.byref(size))
        logon_buffer = C.create_string_buffer(size.value)
        check(advapi.GetTokenInformation(original, 28, logon_buffer, size, C.byref(size)))
        logon = C.cast(logon_buffer, C.POINTER(GROUPS)).contents.groups[0].Sid
        restriction = (SIDATTR * 3)(SIDATTR(restrict_sid, 0), SIDATTR(everyone_sid, 0), SIDATTR(logon, 0))
        check(advapi.CreateRestrictedToken(original, 1, 0, None, 0, None, 3,
                                           restriction, C.byref(restricted)))
        check(advapi.ConvertStringSidToSidW('S-1-16-4096', C.byref(sid)))
        label = SIDATTR(sid, 0x20)
        check(advapi.SetTokenInformation(restricted, 25, C.byref(label),
                                        C.sizeof(label) + advapi.GetLengthSid(sid)))
        check(advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            'D:(A;;GA;;;SY)(A;;GA;;;OW)(A;;GA;;;BU)', 1, C.byref(child_descriptor), None))
        present, defaulted, child_dacl = W.BOOL(), W.BOOL(), C.c_void_p()
        check(advapi.GetSecurityDescriptorDacl(child_descriptor, C.byref(present), C.byref(child_dacl), C.byref(defaulted)))
        check(advapi.SetTokenInformation(restricted, 6, C.byref(child_dacl), C.sizeof(child_dacl)))
        code = advapi.SetSecurityInfo(restricted, 6, 4, None, None, child_dacl, None)
        if code:
            raise C.WinError(code)
        child_security = SECURITY(C.sizeof(SECURITY), child_descriptor, False)
        startup = STARTUP()
        startup.cb = C.sizeof(startup)
        executable = str(reuse_python())
        command = C.create_unicode_buffer(subprocess.list2cmdline(
            [executable, '-I', '-S', '-B', str(Path(script).resolve()), *map(str, arguments)]))
        # Explicit allowlist; do not copy credentials from the parent environment.
        environment = C.create_unicode_buffer('\0'.join(
            f'{k}={v}' for k, v in sorted({'SystemRoot': os.environ['SystemRoot'],
                                          'TEMP': str(directory), 'TMP': str(directory),
                                          'DOTNET_EnableDiagnostics': '0',
                                          'POWERSHELL_TELEMETRY_OPTOUT': '1',
                                          'USERPROFILE': str(directory), 'LOCALAPPDATA': str(directory)}.items())) + '\0\0')
        job = kernel.CreateJobObjectW(None, None)
        check(job)
        limits = EXTENDED_LIMITS()
        limits.basic.flags = 0x2008  # KILL_ON_JOB_CLOSE | ACTIVE_PROCESS
        limits.basic.active_processes = 1
        check(kernel.SetInformationJobObject(job, 9, C.byref(limits), C.sizeof(limits)))
        ui = W.DWORD(0xFF)
        check(kernel.SetInformationJobObject(job, 4, C.byref(ui), C.sizeof(ui)))
        check(advapi.CreateProcessAsUserW(restricted, executable, command, C.byref(child_security), C.byref(child_security),
                                          False, 0x08000404, environment, str(directory),
                                          C.byref(startup), C.byref(process)))
        check(kernel.AssignProcessToJobObject(job, process.process))
        if kernel.ResumeThread(process.thread) == 0xFFFFFFFF:
            raise C.WinError(C.get_last_error())
        if kernel.WaitForSingleObject(process.process, timeout_ms) != 0:
            kernel.TerminateProcess(process.process, 124)
            kernel.WaitForSingleObject(process.process, 5000)
            raise TimeoutError('restricted proposer exceeded bounded runtime')
        code = W.DWORD()
        check(kernel.GetExitCodeProcess(process.process, C.byref(code)))
        if code.value:
            raise RuntimeError(f'restricted proposer failed: exit {code.value}')
        return {'pid': process.pid, 'exit_code': code.value, 'token': 'restricted-primary-low',
                'restricting_sids': ['S-1-5-32-545', 'S-1-1-0', 'current-logon-sid'],
                'job_active_process_limit': 1, 'job_kill_on_close': True,
                'job_ui_restrictions': 255,
                'inherited_handles': False}
    finally:
        if process.process:
            kernel.TerminateProcess(process.process, 125)  # harmless if already exited
        if job:
            kernel.CloseHandle(job)
        for handle in [process.thread, process.process, restricted, original]:
            if handle:
                kernel.CloseHandle(handle)
        if sid:
            kernel.LocalFree(sid)
        if restrict_sid:
            kernel.LocalFree(restrict_sid)
        if child_descriptor:
            kernel.LocalFree(child_descriptor)
        if everyone_sid:
            kernel.LocalFree(everyone_sid)


def propose(payload, outbox, *, state_path, broker_pid, bypass=False, baseline_state=None):
    """Untrusted process can emit proposals; it cannot supply authoritative evidence."""
    outbox = Path(outbox)
    request = outbox / 'request.json'
    output = outbox / 'response.json'
    request.write_text(json.dumps({'proposals': payload, 'state': str(state_path),
                                   'broker_pid': broker_pid, 'bypass': bypass,
                                   'baseline_state': str(baseline_state) if baseline_state else None}), encoding='utf-8')
    output.unlink(missing_ok=True)
    with protect_broker():
        details = launch_low(Path(__file__).with_name('proposer.py'), [request, output], outbox)
    response = json.loads(output.read_text(encoding='utf-8'))
    if (response['integrity_rid'] != 4096 or not response['is_token_restricted']
            or response['restricting_sid_count'] != 3):
        raise RuntimeError('proposer token profile differs from restricted low policy')
    return response | {'launch': details}
