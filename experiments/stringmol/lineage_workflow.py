"""Frozen SM-L001 build, isolation, immutable preparation and six-worker execution.

Commands are deliberately separate: preparation never executes the paired matrix.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

from experiments.stringmol.configure_control import HOST, StringmolControlConfig, inoculum, render_config

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PIN = "15dad84da126a4f887ba945c23a13e89e827f067"
PROTOCOL_PATH = "reports/sm_l001_native_reproduction_lineage_preregistration.md"
PROTOCOL_REVISION = "46c13846558a64fe61a6cae75945d0cd9994751b"
PROTOCOL_SHA256 = "cf093cb2ad26fecea39fea925da2944c6e6e1d4adc30b2ceaa72b6779a3e64b1"
ENV = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "TZ": "UTC"}
LOGS = {"lineage_events001.csv", "lineage_snapshots001.csv"}
PATCHES = [HERE / "patches" / name for name in (
    "0001-fix-neighbor-selection-and-add-locality-controls.patch",
    "0002-add-environment-gated-individual-lineage-observation.patch",
)]
FLAGS = {"CC": "g++ -O3 -Wall -Wunused -std=c++11", "C4C": "gcc -O3 -Wall -Wunused"}
IMPLEMENTATION = [HERE / n for n in ("lineage_workflow.py", "analyze_lineage.py", "configure_control.py", "source.lock.json")]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def record(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"not a regular file: {path}")
    data = path.read_bytes()
    return {"size": len(data), "sha256": digest(data)}


def inventory(directory: Path, exclude: frozenset[str] = frozenset()) -> dict[str, Any]:
    result = {}
    for p in sorted(directory.rglob("*")):
        name = p.relative_to(directory).as_posix()
        if p.is_symlink() or not (p.is_file() or p.is_dir()):
            raise ValueError(f"nonregular output: {p}")
        if p.is_file() and name not in exclude:
            result[name] = record(p)
    return result


def seal(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as f:
        f.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
    path.chmod(0o444)


def read(path: Path) -> Any:
    return json.loads(path.read_text())


def command(args: list[str], cwd: Path) -> bytes:
    return subprocess.run(args, cwd=cwd, env=ENV, check=True, capture_output=True).stdout


def protocol_pin() -> dict[str, Any]:
    """Verify the working protocol against independently pinned committed bytes."""
    committed = command(["git", "show", f"{PROTOCOL_REVISION}:{PROTOCOL_PATH}"], ROOT)
    if digest(committed) != PROTOCOL_SHA256:
        raise ValueError("committed SM-L001 protocol hash mismatch")
    path = ROOT / PROTOCOL_PATH
    expected = {"size": len(committed), "sha256": PROTOCOL_SHA256}
    if record(path) != expected or path.read_bytes() != committed:
        raise ValueError("SM-L001 protocol differs from committed preregistration")
    return {"path": PROTOCOL_PATH, "revision": PROTOCOL_REVISION, **expected, "bytes_hex": committed.hex()}


def source_state(source: Path) -> dict[str, Any]:
    names = command(["git", "ls-files", "-z"], source).decode().split("\0")
    return {
        "commit": command(["git", "rev-parse", "HEAD"], source).decode().strip(),
        "tree": command(["git", "rev-parse", "HEAD^{tree}"], source).decode().strip(),
        "status": command(["git", "status", "--porcelain", "--untracked-files=no"], source).decode(),
        "diff_sha256": digest(command(["git", "diff", "HEAD", "--binary"], source)),
        "tracked_files": {n: record(source / n) if (source / n).exists() else None for n in names if n},
    }


def build(root: Path, upstream: Path) -> Path:
    protocol = protocol_pin()
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    builds = {}
    for name, patches in (("baseline", PATCHES[:1]), ("observer", PATCHES)):
        source = root / name
        command(["git", "clone", "--no-hardlinks", "--no-checkout", str(upstream.resolve()), str(source)], root)
        command(["git", "checkout", "--detach", PIN], source)
        for patch in patches:
            command(["git", "apply", str(patch)], source)
        for folder in ("debug", "release", "output"):
            (source / folder).mkdir(exist_ok=True)
        with (root / f"{name}-tests.txt").open("wb") as f:
            tested = subprocess.run(["bash", "RunCatchTests.sh"], cwd=source / "tests", env=ENV, stdout=f, stderr=subprocess.STDOUT)
        if tested.returncode or b"All tests passed" not in (root / f"{name}-tests.txt").read_bytes():
            raise ValueError(f"upstream tests failed: {name}")
        with (root / f"{name}-build.txt").open("wb") as f:
            subprocess.run(["make", "all", *[f"{k}={v}" for k, v in FLAGS.items()]], cwd=source / "src", env=ENV, stdout=f, stderr=subprocess.STDOUT, check=True)
        builds[name] = {"source": str(source), "state": source_state(source), "binary": record(source / "release/stringmol"), "matrix": record(source / "config/ALXII.mtx"), "patch_order": [str(p) for p in patches]}
    manifest = {"builds": builds, "patches": [{"path": str(p), **record(p), "bytes_hex": p.read_bytes().hex()} for p in PATCHES], "flags": FLAGS, "environment": ENV,
                "compilers": {c: command([c, "--version"], root).decode() for c in ("gcc", "g++")},
                "logs": {p.name: record(p) for p in root.glob("*.txt")}}
    manifest["protocol_pin"] = protocol
    seal(root / "build.json", manifest)
    return root / "build.json"


def verify_build(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = read(path)
    if data.get("protocol_pin") != protocol_pin():
        raise ValueError("build protocol pin mismatch")
    if data["environment"] != ENV or data["flags"] != FLAGS:
        raise ValueError("build environment/flags mismatch")
    for saved, patch in zip(data["patches"], PATCHES, strict=True):
        if saved != {"path": str(patch), **record(patch), "bytes_hex": patch.read_bytes().hex()}:
            raise ValueError("patch mismatch")
    for name, info in data["builds"].items():
        source = Path(info["source"])
        if info["state"]["commit"] != PIN or source_state(source) != info["state"]:
            raise ValueError("source changed")
        if info["binary"] != record(source / "release/stringmol") or info["matrix"] != record(source / "config/ALXII.mtx"):
            raise ValueError("binary/matrix changed")
        expected = PATCHES[:1] if name == "baseline" else PATCHES
        if info["patch_order"] != [str(p) for p in expected]:
            raise ValueError("patch order mismatch")
    if set(data["builds"]) != {"baseline", "observer"}:
        raise ValueError("missing build")
    for name, expected_record in data["logs"].items():
        if record(path.parent / name) != expected_record:
            raise ValueError("build log changed")
    return data


def execute(binary: Path, config: Path, directory: Path, enabled: bool) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=False)
    env = {**ENV, **({"STRINGMOL_LINEAGE_LOG": "1"} if enabled else {})}
    with (directory / "stdout.txt").open("xb") as out, (directory / "stderr.txt").open("xb") as err:
        try:
            completed = subprocess.run([str(binary), "30", str(config)], cwd=directory, env=env, stdout=out, stderr=err, timeout=600, check=False)
            code: int | str = completed.returncode
        except subprocess.TimeoutExpired:
            code = "timeout"
        except OSError as exc:
            code = f"launch failure: {exc}"
    return {"exit_status": code, "files": inventory(directory)}


def loader_ok(directory: Path) -> bool:
    output = (directory / "stdout.txt").read_bytes() + (directory / "stderr.txt").read_bytes()
    return not any(s in output.lower() for s in (b"number of agents not specified", b"reproducible method", b"repclicable method", b"fallback", b"falling back"))


def parity(base: dict[str, Any], other: dict[str, Any], enabled: bool) -> None:
    files = other["files"].copy()
    if enabled:
        if not LOGS <= files.keys():
            raise ValueError("missing observer files")
        for name in LOGS:
            del files[name]
    if base["exit_status"] != 0 or other["exit_status"] != 0 or files != base["files"]:
        raise ValueError("observation isolation mismatch")


def isolation(build_path: Path, root: Path) -> Path:
    data = verify_build(build_path)
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    matrix = Path(data["builds"]["baseline"]["source"]) / "config/ALXII.mtx"
    config = root / "isolation.conf"
    config.write_text(render_config(StringmolControlConfig("host-only", 202619999, 0, 0, nsteps=500), matrix))
    config.chmod(0o444)
    results = {}
    for name, variant, enabled in (("baseline", "baseline", False), ("disabled", "observer", False), ("enabled", "observer", True), ("repeat", "observer", True)):
        binary = Path(data["builds"][variant]["source"]) / "release/stringmol"
        results[name] = execute(binary, config, root / name, enabled)
        seal(root / f"{name}-inventory.json", results[name])
        if not loader_ok(root / name):
            raise ValueError("loader warning in isolation")
        if name != "baseline":
            parity(results["baseline"], results[name], enabled)
    if results["enabled"] != results["repeat"]:
        raise ValueError("nondeterministic lineage")
    from experiments.stringmol.analyze_lineage import analyze_run
    summary = analyze_run(root / "enabled", expected_initial("host"), nsteps=500)
    seal(root / "isolation.json", {"passed": True, "build_manifest": str(build_path.resolve()), "build_record": record(build_path), "config": record(config), "runs": results, "observer_summary": summary})
    return root / "isolation.json"


def expected_initial(condition: str) -> list[dict[str, Any]]:
    sequence, label = (HOST, ord("Q")) if condition == "host" else ("B", ord("B"))
    return [{"id": i, "species": 1, "label": label, "x": x, "y": y, "sequence_hex": sequence.encode().hex().upper()} for i, (x, y) in enumerate(inoculum()[0])]


def verify_gate(path: Path, build_path: Path) -> None:
    gate = read(path)
    if gate["passed"] is not True or gate["build_record"] != record(build_path) or gate["config"] != record(path.parent / "isolation.conf"):
        raise ValueError("isolation provenance changed")
    for name, result in gate["runs"].items():
        if result["files"] != inventory(path.parent / name) or result != read(path.parent / f"{name}-inventory.json") or not loader_ok(path.parent / name):
            raise ValueError("isolation inventory changed")
    if set(gate["runs"]) != {"baseline", "disabled", "enabled", "repeat"}:
        raise ValueError("incomplete isolation")
    for name in ("disabled", "enabled", "repeat"):
        parity(gate["runs"]["baseline"], gate["runs"][name], name != "disabled")
    if gate["runs"]["enabled"] != gate["runs"]["repeat"]:
        raise ValueError("repeat mismatch")


def prepare(build_path: Path, gate_path: Path, root: Path) -> Path:
    protocol = protocol_pin()
    data = verify_build(build_path)
    verify_gate(gate_path, build_path)
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    source = Path(data["builds"]["observer"]["source"])
    entries = []
    for seed in range(202620000, 202620010):
        for condition in ("host", "inert"):
            config = root / f"{condition}-{seed}.conf"
            config.write_text(render_config(StringmolControlConfig("host-only" if condition == "host" else "inert", seed, 0, 0), source / "config/ALXII.mtx"))
            config.chmod(0o444)
            entries.append({"condition": condition, "seed": seed, "config": str(config), **record(config), "bytes_hex": config.read_bytes().hex(), "command": [str(source / "release/stringmol"), "30", str(config)], "directory": str(root / "runs" / condition / str(seed)), "expected_initial": expected_initial(condition)})
    manifest = {"protocol": "SM-L001", "workers": 6, "environment": {**ENV, "STRINGMOL_LINEAGE_LOG": "1"}, "build_manifest": str(build_path.resolve()), "build_record": record(build_path), "build": data, "isolation": str(gate_path.resolve()), "isolation_record": record(gate_path), "repository_state": source_state(ROOT), "implementation": {str(p): record(p) for p in IMPLEMENTATION}, "runs": entries}
    manifest["protocol_pin"] = protocol
    path = root / "preparation.json"
    seal(path, manifest)
    seal(root / "preparation.sha256.json", record(path))
    verify_preparation(path)
    return path


def verify_preparation(path: Path) -> dict[str, Any]:
    if path.stat().st_mode & 0o222 or record(path) != read(path.with_name("preparation.sha256.json")):
        raise ValueError("immutable input manifest changed")
    data: dict[str, Any] = read(path)
    if data["protocol"] != "SM-L001" or data["implementation"] != {str(p): record(p) for p in IMPLEMENTATION}:
        raise ValueError("prepared implementation changed")
    if data.get("protocol_pin") != protocol_pin():
        raise ValueError("prepared protocol pin mismatch")
    build_path = Path(data["build_manifest"])
    if record(build_path) != data["build_record"] or verify_build(build_path) != data["build"]:
        raise ValueError("build manifest changed")
    gate_path = Path(data["isolation"])
    if record(gate_path) != data["isolation_record"]:
        raise ValueError("isolation changed")
    verify_gate(gate_path, build_path)
    if data["workers"] != 6 or data["environment"] != {**ENV, "STRINGMOL_LINEAGE_LOG": "1"}:
        raise ValueError("execution protocol changed")
    pairs = [(r["condition"], r["seed"]) for r in data["runs"]]
    if pairs != [(c, s) for s in range(202620000, 202620010) for c in ("host", "inert")]:
        raise ValueError("matrix changed")
    source = Path(data["build"]["builds"]["observer"]["source"])
    for r in data["runs"]:
        config = Path(r["config"])
        expected = render_config(StringmolControlConfig("host-only" if r["condition"] == "host" else "inert", r["seed"], 0, 0), source / "config/ALXII.mtx").encode()
        if config.read_bytes() != expected or config.read_bytes().hex() != r["bytes_hex"] or record(config) != {k: r[k] for k in ("size", "sha256")}:
            raise ValueError("config changed")
        if r["command"] != [str(source / "release/stringmol"), "30", str(config)] or r["expected_initial"] != expected_initial(r["condition"]) or r["directory"] != str(path.parent / "runs" / r["condition"] / str(r["seed"])):
            raise ValueError("run inputs changed")
    return data


def run_matrix(path: Path) -> None:
    data = verify_preparation(path)
    # All directories are preflighted before any process launches; no selective retry.
    if (path.parent / "runs").exists() or (path.parent / "campaign.json").exists():
        raise FileExistsError("campaign already exists; complete unchanged matrix requires fresh preparation")
    seal(path.parent / "campaign.json", {"input_manifest": record(path), "workers": 6})

    def run(r: dict[str, Any]) -> dict[str, Any]:
        directory = Path(r["directory"])
        result = execute(Path(r["command"][0]), Path(r["config"]), directory, True)
        result["input_manifest"] = record(path)
        result["condition"] = r["condition"]
        result["seed"] = r["seed"]
        # Receipt is outside the inventoried directory, avoiding a self-hash exception.
        seal(directory.with_suffix(".inventory.json"), result)
        return result

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(run, data["runs"]))
    seal(path.parent / "campaign-results.json", results)
    verify_preparation(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "isolation", "prepare", "run"))
    parser.add_argument("--root", type=Path)
    parser.add_argument("--upstream", type=Path, default=HERE / "vendor/stringmol")
    parser.add_argument("--build", type=Path)
    parser.add_argument("--isolation", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    if args.action == "build" and args.root:
        print(build(args.root, args.upstream))
    elif args.action == "isolation" and args.build and args.root:
        print(isolation(args.build.resolve(), args.root))
    elif args.action == "prepare" and args.build and args.isolation and args.root:
        print(prepare(args.build.resolve(), args.isolation.resolve(), args.root))
    elif args.action == "run" and args.manifest:
        run_matrix(args.manifest.resolve())
    else:
        parser.error("missing required paths for action")


if __name__ == "__main__":
    main()
