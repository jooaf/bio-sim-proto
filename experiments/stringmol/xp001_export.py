"""Checksum-verified ordinary Elements export; original POSIX evidence stays intact."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
from typing import TypedDict

class FileRecord(TypedDict):
    path: str
    bytes: int
    sha256: str
from experiments.stringmol import xp001 as x
from experiments.stringmol.xp001_safety import require

DEST=Path('/run/media/jojo/Elements/bio-sim-results/verification/sm-xp001-exploration-v1')

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()

def export() -> None:
    x.preflight()
    DEST.mkdir()
    portable=DEST/'posix-controls'; portable.mkdir()
    records: list[FileRecord] = []
    special: list[dict[str, str | int]] = []
    for source in sorted(x.EVIDENCE.rglob('*')):
        rel=source.relative_to(x.EVIDENCE); target=portable/rel
        mode=source.lstat().st_mode
        if stat.S_ISLNK(mode):
            special.append({'path':str(rel),'kind':'symlink','target':os.readlink(source)})
        elif stat.S_ISDIR(mode):
            target.mkdir(exist_ok=True)
        elif stat.S_ISREG(mode):
            target.parent.mkdir(parents=True,exist_ok=True)
            before=sha(source);shutil.copyfile(source,target)
            require(sha(target)==before==sha(source), 'export checksum mismatch')
            records.append({'path':str(rel),'bytes':source.stat().st_size,'sha256':before})
        else:
            special.append({'path':str(rel),'kind':'special','mode':mode})
    x.save(DEST/'posix-controls-checksums.json',records)
    x.save(DEST/'posix-special-metadata.json',special)
    raw: list[FileRecord] = []
    for source in sorted(x.RAW.rglob('*')):
        if source.is_file():
            raw.append({'path':str(source.relative_to(x.RAW)),'bytes':source.stat().st_size,'sha256':sha(source)})
    x.save(DEST/'raw-checksums.json',raw)
    # Verify the entire ordinary raw export in a second read.
    for record in raw:
        require(sha(x.RAW/record['path'])==record['sha256'], 'raw checksum mismatch')
    archive=DEST/'source.tar'
    subprocess.run(['git','archive','--format=tar',f'--output={archive}','HEAD','experiments/stringmol',
                    'tests/test_sm_xp001.py','tests/stringmol_xp001_reaction.cpp',
                    'reports/sm_xp001_development_plan.md','reports/sm_xp001_reaction_recovery_plan.md',
                    'reports/sm_xp001_population_launch.md','reports/sm_xp001_results.md'],cwd=x.ROOT,check=True)
    receipt={'verified':True,'posix_regular_files':len(records),'posix_bytes':sum(r['bytes'] for r in records),
             'raw_regular_files':len(raw),'raw_bytes':sum(r['bytes'] for r in raw),
             'special_metadata_entries':len(special),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=x.ROOT,text=True).strip(),
             'source_archive_sha256':sha(archive),'manifest_sha256':{name:sha(DEST/name) for name in
                ['posix-controls-checksums.json','posix-special-metadata.json','raw-checksums.json']}}
    x.save(DEST/'EXPORT-VERIFIED.json',receipt)
    print(json.dumps(receipt,sort_keys=True))

if __name__=='__main__':
    export()
