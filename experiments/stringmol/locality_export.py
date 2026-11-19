"""SM-XL001 portable regular-file export; original POSIX seals stay untouched."""
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
from experiments.stringmol.locality_pilot import CONTROL,RAW,inventory,record,save,preflight
from experiments.stringmol.analyze_lineage import require

DEST=Path('/run/media/jojo/Elements/bio-sim-results/verification/sm-xl001-exploration-v1')


def main() -> None:
    preflight()
    require((CONTROL/'diagnostic-v3/diagnostics.json').exists(), 'do not export incomplete analyses')
    require((CONTROL/'process-state-final.nuon').exists(), 'record actual stopped process state before export')
    require(not subprocess.check_output(['git','status','--porcelain'],text=True).strip(), 'commit source before final export')
    DEST.mkdir(parents=True,exist_ok=False)
    portable=DEST/'portable-control';portable.mkdir()
    manifest: list[dict[str, str | int]]=[]
    nodes: list[dict[str, str | int]]=[]
    for source in sorted(CONTROL.rglob('*')):
        relative=source.relative_to(CONTROL)
        mode=source.lstat().st_mode
        if stat.S_ISLNK(mode):
            nodes.append({'path':str(relative),'kind':'symlink','target':os.readlink(source)})
        elif stat.S_ISREG(mode):
            target=portable/relative;target.parent.mkdir(parents=True,exist_ok=True)
            before=record(source);shutil.copyfile(source,target)
            require(before==record(source)==record(target), f'export mismatch: {source}')
            manifest.append({'source':str(source),'portable':str(target.relative_to(DEST)),
                             'sha256':before['sha256'], 'bytes':before['bytes']})
        elif not stat.S_ISDIR(mode):
            nodes.append({'path':str(relative),'kind':'special','mode':mode})
    # Raw outputs already are ordinary Mac-readable files on Elements. Rehash
    # every file and compare immutable execution receipts, not just copy hashes.
    raw=inventory(RAW)
    for receipt_path in sorted(RAW.glob('*.receipt.json')):
        receipt=json.loads(receipt_path.read_text())
        directory=RAW/receipt_path.name.removesuffix('.receipt.json')
        require(inventory(directory)==receipt['inventory'], f'raw changed: {directory}')
    subprocess.run(['git','bundle','create',str(DEST/'source.bundle'),'explore/sm-xl001'],check=True)
    subprocess.run(['git','archive','--format=tar',f'--output={DEST / "source.tar"}','HEAD'],check=True)
    save(DEST/'checksums.json',{'controls':manifest,'raw_root':str(RAW),'raw':raw,'nonregular_nodes':nodes,
                             'source_bundle':record(DEST/'source.bundle'),'source_tar':record(DEST/'source.tar')})
    save(DEST/'VERIFIED.json',{'regular_control_files':len(manifest),'raw_files':len(raw),'nonregular_nodes':len(nodes),
                             'checksums':record(DEST/'checksums.json'),'all_checksums_verified':True,
                             'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                             'full_observer_off_gate':False,'population_interpretation_authorized':False})
    print(DEST/'VERIFIED.json')


if __name__=='__main__':main()
