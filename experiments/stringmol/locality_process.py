"""Single-attempt process evidence. Reservations precede every attempted launch."""
from pathlib import Path
from typing import TypedDict
import json
import os
import subprocess
import time


class FileRecord(TypedDict):
    sha256: str
    bytes: int


class ProcessResult(TypedDict):
    command: list[str]
    environment: dict[str, str]
    cwd: str
    timeout: float
    started: float
    finished: float
    seconds: float
    exit_code: int | str
    exception: dict[str, str] | None
    inventory: dict[str, FileRecord]
    collection_complete: bool
    inventory_error: dict[str, str] | None


class InventoryError(RuntimeError):
    """Process outcome retained, but incomplete evidence cannot qualify success."""


def execute(command: list[str], *, cwd: Path, environment: dict[str, str],
            receipt: Path, stdout: Path, stderr: Path, timeout: float,
            output_root: Path) -> ProcessResult:
    # Open exclusively and leave a reservation even if output setup itself fails.
    with receipt.open('x') as evidence:
        started = time.time()
        base = dict(command=command, environment=environment, cwd=str(cwd),
                    timeout=timeout, started=started, state='reserved')
        json.dump(base, evidence, sort_keys=True); evidence.flush(); os.fsync(evidence.fileno())
        code: int | str = 'SETUP_ERROR'
        exception = None
        try:
            with stdout.open('xb') as out, stderr.open('xb') as err:
                p = subprocess.run(command, cwd=cwd, env=environment, stdout=out,
                                   stderr=err, timeout=timeout)
                code = p.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            code = 'TIMEOUT' if isinstance(exc, subprocess.TimeoutExpired) else 'OSERROR'
            exception = {'type': type(exc).__name__, 'message': str(exc), 'repr': repr(exc)}
        finished = time.time()
        result: ProcessResult = dict(command=command, environment=environment, cwd=str(cwd),
            timeout=timeout, started=started, finished=finished, seconds=finished-started,
            exit_code=code, exception=exception, inventory={},
            collection_complete=False, inventory_error=None)

        def persist() -> None:
            evidence.seek(0); json.dump(result, evidence, sort_keys=True, indent=2)
            evidence.write('\n'); evidence.truncate(); evidence.flush(); os.fsync(evidence.fileno())

        # Persist the known process outcome before any collection can fail.
        persist()
        try:
            # Import lazily to avoid a controller import cycle. The sink retains
            # records already hashed if a later file cannot be collected.
            from experiments.stringmol.locality_pilot import inventory
            result['inventory'] = inventory(output_root, collected=result['inventory'])
            result['collection_complete'] = True
        except Exception as exc:
            result['inventory_error'] = {'type': type(exc).__name__, 'message': str(exc), 'repr': repr(exc)}
            if receipt.is_relative_to(output_root):
                result['inventory'].pop(str(receipt.relative_to(output_root)), None)
            persist()
            raise InventoryError('inventory incomplete; process receipt retained; no retry') from exc
        if receipt.is_relative_to(output_root):
            result['inventory'].pop(str(receipt.relative_to(output_root)), None)
        persist()
    return result
