"""Development-only native test tooling; no simulation/assay launch API."""
import hashlib
import os
from pathlib import Path
import subprocess

SANITIZERS = os.environ.get('SM_ADMISSION_SANITIZERS', '0')
if SANITIZERS not in ('0', '1'):
    raise ValueError('SM_ADMISSION_SANITIZERS must be 0 or 1')


def sanitizer_flags() -> list[str]:
    directory = os.environ.get('SM_ADMISSION_SANITIZER_LIBDIR')
    if SANITIZERS == '0':
        if directory:
            raise ValueError('Sanitizer library override requires instrumentation')
        return []
    flags = ['-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer', '-g']
    if directory:
        lib = Path(directory).resolve(strict=True)
        for name in ('libasan.so', 'libubsan.so'):
            if not (lib / name).is_file():
                raise ValueError(f'Missing sanitizer runtime: {lib / name}')
        flags.extend(['-L', str(lib), '-Xlinker', '-rpath', '-Xlinker', str(lib)])
    return flags


def runtime_environment() -> dict[str, str]:
    env = dict(os.environ)
    if SANITIZERS == '1':
        env.pop('LSAN_OPTIONS', None)
        env['ASAN_OPTIONS'] = 'detect_leaks=1:halt_on_error=1:strict_string_checks=1'
        env['UBSAN_OPTIONS'] = 'halt_on_error=1:print_stacktrace=1'
    return env


def verify_linkage(binary: Path) -> None:
    if SANITIZERS != '1':
        return
    result = subprocess.run(['ldd', str(binary)], check=True, capture_output=True, text=True, timeout=10)
    (binary.parent / 'linkage.txt').write_text(result.stdout, encoding='utf-8')
    directory = os.environ.get('SM_ADMISSION_SANITIZER_LIBDIR')
    for name in ('libasan.so', 'libubsan.so'):
        matches = [line.partition('=>')[2].rsplit(' (', 1)[0].strip()
                   for line in result.stdout.splitlines() if line.strip().startswith(name + '.')]
        if len(matches) != 1 or not Path(matches[0]).is_file():
            raise ValueError(f'Missing runtime linkage: {result.stdout}')
        if directory and Path(matches[0]).resolve() != (Path(directory) / name).resolve():
            raise ValueError(f'Unexpected runtime linkage: {result.stdout}')


def verify_native_agent(source: Path) -> None:
    pins = {'agent.cpp': '81218d2c1083e24c8b10c916a482664d309ccbdfbfd8cedc054c1e5f5b68b1a1',
            'agent.h': '0066da3fb8233ddb5f7b8abb43e79cc5b47f407eca4126a569eb00e2d0f89941'}
    for name, expected in pins.items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Native agent implementation changed: {name}')
