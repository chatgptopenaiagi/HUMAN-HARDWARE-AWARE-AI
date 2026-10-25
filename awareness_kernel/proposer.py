"""Standalone untrusted experiment client. Launched with -I -S -B and no handles."""
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import sys
import subprocess


def token_profile():
    kernel = C.WinDLL('kernel32', use_last_error=True)
    advapi = C.WinDLL('advapi32', use_last_error=True)
    kernel.GetCurrentProcess.restype = W.HANDLE
    kernel.CloseHandle.argtypes = [W.HANDLE]
    advapi.OpenProcessToken.argtypes = [W.HANDLE, W.DWORD, C.POINTER(W.HANDLE)]
    advapi.GetTokenInformation.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.POINTER(W.DWORD)]
    advapi.IsTokenRestricted.argtypes = [W.HANDLE]
    advapi.GetSidSubAuthorityCount.argtypes = [C.c_void_p]
    advapi.GetSidSubAuthorityCount.restype = C.POINTER(C.c_ubyte)
    advapi.GetSidSubAuthority.argtypes = [C.c_void_p, W.DWORD]
    advapi.GetSidSubAuthority.restype = C.POINTER(W.DWORD)
    handle, size = W.HANDLE(), W.DWORD()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 8, C.byref(handle)):
        raise C.WinError(C.get_last_error())
    try:
        advapi.GetTokenInformation(handle, 25, None, 0, C.byref(size))
        buffer = C.create_string_buffer(size.value)
        if not advapi.GetTokenInformation(handle, 25, buffer, size, C.byref(size)):
            raise C.WinError(C.get_last_error())
        sid = C.cast(buffer, C.POINTER(C.c_void_p))[0]
        count = advapi.GetSidSubAuthorityCount(sid)[0]
        rid = advapi.GetSidSubAuthority(sid, count - 1)[0]
        restricted = bool(advapi.IsTokenRestricted(handle))
        advapi.GetTokenInformation(handle, 11, None, 0, C.byref(size))
        groups = C.create_string_buffer(size.value)
        if not advapi.GetTokenInformation(handle, 11, groups, size, C.byref(size)):
            raise C.WinError(C.get_last_error())
        restricted_count = C.cast(groups, C.POINTER(W.DWORD))[0]
        return {'integrity_rid': rid, 'is_token_restricted': restricted,
                'restricting_sid_count': restricted_count}
    finally:
        kernel.CloseHandle(handle)


def attacks(path, broker_pid, output_dir):
    results = []

    def attempt(name, action):
        try:
            action()
            results.append({'attempt': name, 'outcome': 'BYPASS_SUCCEEDED'})
        except OSError as exc:
            denied = (exc.errno == 13 or exc.winerror == 5
                      or (name == 'descendant-process-creation' and exc.winerror == 1816))
            results.append({'attempt': name, 'outcome': 'DENIED' if denied else 'ERROR', 'winerror': exc.winerror,
                            'errno': exc.errno, 'message': str(exc)})

    def write():
        with path.open('w', encoding='utf-8') as stream:
            stream.write('{"bypassed":true}')

    def append():
        with path.open('a', encoding='utf-8') as stream:
            stream.write('tamper')

    attempt('truncate-write', write)
    attempt('append', append)
    attempt('delete', path.unlink)
    replacement = output_dir / 'replacement.json'
    replacement.write_text('{"bypassed":true}', encoding='utf-8')
    attempt('replace', lambda: os.replace(replacement, path))
    attempt('change-mode', lambda: os.chmod(path, 0o777))
    attempt('create-authoritative-sibling', lambda: (path.parent / 'state.new').write_text('tamper'))
    attempt('rename-protected-directory', lambda: path.parent.rename(path.parent.with_name(path.parent.name + '-moved')))
    kernel = C.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
    kernel.OpenProcess.restype = W.HANDLE
    kernel.CloseHandle.argtypes = [W.HANDLE]
    for name, rights in [('broker-terminate-access', 1), ('broker-memory-write-access', 0x28),
                         ('broker-handle-duplication', 0x40), ('broker-dacl-write', 0x40000),
                         ('broker-create-thread', 2)]:
        handle = kernel.OpenProcess(rights, False, broker_pid)
        if handle:
            kernel.CloseHandle(handle)
            results.append({'attempt': name, 'outcome': 'BYPASS_SUCCEEDED'})
        else:
            error = C.get_last_error()
            results.append({'attempt': name, 'outcome': 'DENIED' if error == 5 else 'ERROR', 'winerror': error})
    # Attempt token theft through otherwise permitted process-query access.
    advapi = C.WinDLL('advapi32', use_last_error=True)
    advapi.OpenProcessToken.argtypes = [W.HANDLE, W.DWORD, C.POINTER(W.HANDLE)]
    process = kernel.OpenProcess(0x1000, False, broker_pid)
    token = W.HANDLE()
    allowed = bool(process and advapi.OpenProcessToken(process, 0xB, C.byref(token)))
    error = C.get_last_error()
    results.append({'attempt': 'broker-primary-token-theft',
                    'outcome': 'BYPASS_SUCCEEDED' if allowed else 'DENIED', 'winerror': error})
    if token:
        kernel.CloseHandle(token)
    if process:
        kernel.CloseHandle(process)
    def spawn():
        child = subprocess.Popen([sys.executable, '-I', '-S', '-B', '-c', 'pass'])
        child.wait(timeout=3)
    attempt('descendant-process-creation', spawn)
    return results


if __name__ == '__main__':
    request = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    output = Path(sys.argv[2])
    response = {**token_profile(), 'proposals': request['proposals'],
                'proposal_source': 'deterministic injection; no model inference', 'attacks': []}
    if request['bypass']:
        response['attacks'] = attacks(Path(request['state']), request['broker_pid'], output.parent)
    if request.get('baseline_state'):
        baseline_path = Path(request['baseline_state'])
        baseline = json.loads(baseline_path.read_text(encoding='utf-8'))
        before = json.loads(json.dumps(baseline))
        baseline['packages'].append('sdk')
        baseline['storage'] -= 4
        baseline_path.write_text(json.dumps(baseline), encoding='utf-8')
        response['baseline'] = {'before': before, 'after': baseline,
                                'redundant_install_executed': True}
    output.write_text(json.dumps(response, indent=2), encoding='utf-8')
