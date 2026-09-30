"""Frozen SM-C001 fresh builds and independently sealed mechanics gates.

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

from experiments.stringmol.configure_control import StringmolControlConfig, render_config
from experiments.stringmol import lineage_workflow as lineage
from experiments.stringmol.analyze_conservation import initial_material, analyze_run
from experiments.stringmol.analyze_lineage import require

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PIN = "15dad84da126a4f887ba945c23a13e89e827f067"
PROTOCOL_PATH = "reports/sm_c001_stringmol_conservation_boundary_preregistration.md"
PROTOCOL_REVISION = "9cc31a3fd36c79ff42966ad091fac63f33f16e03"
PROTOCOL_SHA256 = "e352f3a1798a77c8f5a5ab254023b9e74c1e8e4c8daddce2dd83bd64ceb4e537"
ENV = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "TZ": "UTC"}
LOGS = {"lineage_events001.csv", "lineage_snapshots001.csv"}
PATCHES = [HERE / "patches" / name for name in (
    "0001-fix-neighbor-selection-and-add-locality-controls.patch",
    "0002-add-environment-gated-individual-lineage-observation.patch",
    "0003-add-exact-spatial-symbol-conservation.patch",
)]
FLAGS = {"CC": "g++ -O3 -Wall -Wunused -std=c++11", "C4C": "gcc -O3 -Wall -Wunused"}
IMPLEMENTATION = [HERE / n for n in ("conservation_workflow.py", "analyze_conservation.py", "lineage_workflow.py", "analyze_lineage.py", "configure_control.py", "source.lock.json")] + [ROOT / "tests" / n for n in ("test_stringmol_conservation.py", "stringmol_conservation_directed.cpp", "test_stringmol_lineage.py", "test_stringmol_control.py")]
CONSERVATION_LOGS = {"conservation001.csv", "conservation_buffers001.csv"}
# Exact release inputs from the pinned Makefile, including the simulator main.
RELEASE_OBJECTS = frozenset("SMspp agent alignment hsort lodepng mathutil memoryutil microbial_ga mt19937-2 opcodes params randutil rules setupSM sm_spatial stringPM stringmanip stringmol".split())


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
        raise ValueError("committed SM-C001 protocol hash mismatch")
    path = ROOT / PROTOCOL_PATH
    expected = {"size": len(committed), "sha256": PROTOCOL_SHA256}
    if record(path) != expected or path.read_bytes() != committed:
        raise ValueError("SM-C001 protocol differs from committed preregistration")
    return {"path": PROTOCOL_PATH, "revision": PROTOCOL_REVISION, **expected, "bytes_hex": committed.hex(), "inherited": lineage.protocol_pin()}


def source_state(source: Path) -> dict[str, Any]:
    names = command(["git", "ls-files", "-z"], source).decode().split("\0")
    return {
        "commit": command(["git", "rev-parse", "HEAD"], source).decode().strip(),
        "tree": command(["git", "rev-parse", "HEAD^{tree}"], source).decode().strip(),
        "status": command(["git", "status", "--porcelain", "--untracked-files=no"], source).decode(),
        "diff_sha256": digest(command(["git", "diff", "HEAD", "--binary"], source)),
        "tracked_files": {n: record(source / n) if (source / n).exists() else None for n in names if n},
        "source_files": inventory(source / "src") if (source / "src").exists() else {},
    }


def release_objects(source: Path) -> dict[str, Any]:
    paths = sorted((source / "release").glob("*.o"))
    require({p.stem for p in paths} == RELEASE_OBJECTS, "release object input set changed")
    return {p.name: record(p) for p in paths}


def verify_release_objects(source: Path, expected: dict[str, Any]) -> None:
    require(release_objects(source) == expected, "release object bytes changed")


def build(root: Path, upstream: Path) -> Path:
    protocol = protocol_pin()
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    builds = {}
    for name, patches in (("baseline", PATCHES[:2]), ("observer", PATCHES)):
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
        builds[name] = {"source": str(source), "state": source_state(source), "binary": record(source / "release/stringmol"), "release_objects": release_objects(source), "matrix": record(source / "config/ALXII.mtx"), "patch_order": [str(p) for p in patches]}
    manifest = {"builds": builds, "patches": [{"path": str(p), **record(p), "bytes_hex": p.read_bytes().hex()} for p in PATCHES], "flags": FLAGS, "environment": ENV,
                "compilers": {c: command([c, "--version"], root).decode() for c in ("gcc", "g++")},
                "logs": {p.name: record(p) for p in root.glob("*.txt")}}
    manifest["protocol_pin"] = protocol
    manifest["implementation"] = {str(p): record(p) for p in IMPLEMENTATION}
    seal(root / "build.json", manifest)
    return root / "build.json"


def verify_build(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = read(path)
    if data.get("protocol_pin") != protocol_pin():
        raise ValueError("build protocol pin mismatch")
    if data["implementation"] != {str(p): record(p) for p in IMPLEMENTATION}:
        raise ValueError("build implementation changed")
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
        verify_release_objects(source, info["release_objects"])
        expected = PATCHES[:2] if name == "baseline" else PATCHES
        if info["patch_order"] != [str(p) for p in expected]:
            raise ValueError("patch order mismatch")
    if set(data["builds"]) != {"baseline", "observer"}:
        raise ValueError("missing build")
    for name, expected_record in data["logs"].items():
        if record(path.parent / name) != expected_record:
            raise ValueError("build log changed")
    return data


def environment(mode: str | None = None, amount: int = 0, *, logging: bool = True, flag: str | None = None) -> dict[str, str]:
    env = {**ENV, **({"STRINGMOL_LINEAGE_LOG": "1"} if logging else {})}
    if mode is not None:
        env.update(STRINGMOL_CONSERVATION=flag or "1", STRINGMOL_POOL_MODE=mode, STRINGMOL_POOL_AMOUNT=str(amount))
    return env


def execute(binary: Path, config: Path, directory: Path, env: dict[str, str]) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=False)
    with (directory / "stdout.txt").open("xb") as out, (directory / "stderr.txt").open("xb") as err:
        try:
            process = subprocess.run([str(binary), "30", str(config)], cwd=directory, env=env, stdout=out, stderr=err, timeout=600, check=False)
            code: int | str = process.returncode
        except subprocess.TimeoutExpired:
            code = "timeout"
        except OSError as exc:
            code = f"launch failure: {exc}"
    return {"exit_status": code, "files": inventory(directory)}


def parity(base: dict[str, Any], other: dict[str, Any], extra: set[str] | None = None) -> None:
    extra = extra or set()
    require(base["exit_status"] == other["exit_status"] == 0, "compatibility process failure")
    require(set(other["files"]) == set(base["files"]) | extra and not set(base["files"]) & extra, "compatibility filename set")
    require({k: v for k, v in other["files"].items() if k not in extra} == base["files"], "compatibility output bytes")


def directed_linkage(build_path: Path, data: dict[str, Any], root: Path) -> dict[str, Any]:
    info = data["builds"]["observer"]
    source = Path(info["source"])
    # This check is local to the link boundary, in addition to verify_build.
    verify_release_objects(source, info["release_objects"])
    fixture = ROOT / "tests/stringmol_conservation_directed.cpp"
    objects = {str(source / "release" / name): value for name, value in sorted(info["release_objects"].items()) if name != "stringmol.o"}
    args = ["g++", "-std=c++11", "-O2", "-Wall", "-I", str(source / "src"), str(fixture), *objects, "-o", str(root / "directed-test")]
    return {"build_manifest": str(build_path.resolve()), "build_record": record(build_path),
            "objects": objects, "fixture": record(fixture), "command": args, "environment": ENV}


def directed(build_path: Path, root: Path) -> dict[str, Any]:
    data = verify_build(build_path)
    linkage = directed_linkage(build_path, data, root)
    binary = root / "directed-test"
    command(linkage["command"], root)
    # Refuse a receipt if any build or linked input changed during compilation.
    require(directed_linkage(build_path, verify_build(build_path), root) == linkage, "directed linkage changed during build")
    result = subprocess.run([str(binary)], cwd=root, env=ENV, capture_output=True, check=False)
    (root / "directed.stdout").write_bytes(result.stdout)
    (root / "directed.stderr").write_bytes(result.stderr)
    require(result.returncode == 0 and b"SM-C001 directed gates passed\n" in result.stdout, "directed mechanics failed")
    return {"linkage": linkage, "binary": record(binary), "exit_status": result.returncode,
            "stdout": record(root / "directed.stdout"), "stderr": record(root / "directed.stderr")}


def verify_directed(receipt: dict[str, Any], build_path: Path, root: Path) -> None:
    linkage = directed_linkage(build_path, verify_build(build_path), root)
    require(receipt["exit_status"] == 0 and receipt["linkage"] == linkage, "directed linkage receipt changed")
    for key, filename in (("binary", "directed-test"), ("stdout", "directed.stdout"), ("stderr", "directed.stderr")):
        require(receipt[key] == record(root / filename), "directed artifact changed")


def validation(root: Path) -> dict[str, Any]:
    python = ROOT / ".venv/bin/python"
    tests = ["tests/test_stringmol_conservation.py", "tests/test_stringmol_lineage.py", "tests/test_stringmol_control.py"]
    commands = {
        "pytest": [str(python), "-m", "pytest", "-q", *tests],
        "mypy": [str(python), "-m", "mypy", "experiments/stringmol/conservation_workflow.py", "experiments/stringmol/analyze_conservation.py",
                 "experiments/stringmol/lineage_workflow.py", "experiments/stringmol/analyze_lineage.py", *tests],
    }
    results = {}
    for name, args in commands.items():
        completed = subprocess.run(args, cwd=ROOT, env=ENV, capture_output=True, check=False)
        log = root / f"{name}.txt"
        log.write_bytes(completed.stdout + completed.stderr)
        require(completed.returncode == 0, f"focused {name} failed: {log}")
        results[name] = {"command": args, "exit_status": completed.returncode, "log": record(log)}
    return results


def gates(build_path: Path, root: Path, lineage_build: Path, lineage_gate: Path) -> Path:
    data = verify_build(build_path)
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    sources = {k: Path(v["source"]) for k, v in data["builds"].items()}
    lineage.verify_build(lineage_build)
    lineage.verify_gate(lineage_gate, lineage_build)
    inherited = {"build": str(lineage_build.resolve()), "build_record": record(lineage_build),
                 "gate": str(lineage_gate.resolve()), "gate_record": record(lineage_gate)}
    checks = validation(root)
    fixture = directed(build_path, root)
    results: dict[str, Any] = {}
    configs = {}
    summaries = {}
    for kind, seed in (("disabled", 202620998), ("uniform", 202620999)):
        config = root / f"{kind}.conf"
        config.write_text(render_config(StringmolControlConfig("host-only", seed, 0, 0, nsteps=500), sources["baseline"] / "config/ALXII.mtx"))
        config.chmod(0o444)
        configs[kind] = record(config)
        variants = [("baseline", "baseline", environment()),
                    ("absent", "observer", environment()),
                    ("zero", "observer", environment("histogram", 16, flag="0")),
                    ("repeat", "observer", environment()),
                    ("no-lineage", "observer", environment(logging=False))] if kind == "disabled" else [
                    ("baseline", "baseline", environment()),
                    ("enabled", "observer", environment("uniform", 1000000)),
                    ("repeat", "observer", environment("uniform", 1000000)),
                    ("no-lineage", "observer", environment("uniform", 1000000, logging=False))]
        for name, source, env in variants:
            ident = kind + "-" + name
            directory = root / ident
            result = execute(sources[source] / "release/stringmol", config, directory, env)
            require(lineage.loader_ok(directory), "loader failure in gate")
            results[ident] = {**result, "environment": env, "command": [str(sources[source] / "release/stringmol"), "30", str(config)]}
            seal(root / f"{ident}-inventory.json", results[ident])
        base = results[kind + "-baseline"]
        if kind == "disabled":
            for name in ("absent", "zero", "repeat"):
                parity(base, results[kind + "-" + name])
            parity(results[kind + "-no-lineage"], results[kind + "-absent"], LOGS)
            from experiments.stringmol.analyze_lineage import analyze_run as analyze_lineage
            summaries[kind] = analyze_lineage(root / "disabled-absent", lineage.expected_initial("host"), nsteps=500)
        else:
            parity(base, results[kind + "-enabled"], CONSERVATION_LOGS)
            parity(results[kind + "-enabled"], results[kind + "-repeat"])
            parity(results[kind + "-no-lineage"], results[kind + "-enabled"], LOGS)
            for name in ("enabled", "repeat"):
                summary = analyze_run(root / f"uniform-{name}", lineage.expected_initial("host"), "uniform", 1000000, nsteps=500)
                require(summary["end_conservation"]["scarcity_blocked"] == 0, "no-scarcity blocked copy")
                summaries[kind + "-" + name] = summary
    seal(root / "gates.json", {"passed": True, "build_manifest": str(build_path.resolve()), "build_record": record(build_path),
                               "configs": configs, "runs": results, "directed": fixture, "summaries": summaries, "validation": checks, "lineage": inherited})
    return root / "gates.json"


def verify_gate(path: Path, build_path: Path) -> None:
    gate = read(path)
    require(gate["passed"] is True and gate["build_record"] == record(build_path), "gate build provenance")
    inherited = gate["lineage"]
    lb, lg = Path(inherited["build"]), Path(inherited["gate"])
    require(record(lb) == inherited["build_record"] and record(lg) == inherited["gate_record"], "inherited lineage provenance changed")
    lineage.verify_build(lb)
    lineage.verify_gate(lg, lb)
    for name in ("pytest", "mypy"):
        require(gate["validation"][name]["exit_status"] == 0 and gate["validation"][name]["log"] == record(path.parent / f"{name}.txt"), "focused validation changed")
    build_data = read(build_path)
    source = Path(build_data["builds"]["baseline"]["source"])
    for k, seed in (("disabled", 202620998), ("uniform", 202620999)):
        config = path.parent / f"{k}.conf"
        require(config.read_text() == render_config(StringmolControlConfig("host-only", seed, 0, 0, nsteps=500), source / "config/ALXII.mtx"), "gate config protocol mismatch")
        require(gate["configs"][k] == record(path.parent / f"{k}.conf"), "gate config changed")
    expected_names = {"disabled-" + n for n in ("baseline", "absent", "zero", "repeat", "no-lineage")} | {"uniform-" + n for n in ("baseline", "enabled", "repeat", "no-lineage")}
    require(set(gate["runs"]) == expected_names, "gate runs missing")
    for name, result in gate["runs"].items():
        require(result == read(path.parent / f"{name}-inventory.json") and result["files"] == inventory(path.parent / name), "gate inventory changed")
        require(lineage.loader_ok(path.parent / name), "gate loader warning")
        kind, variant = name.split("-", 1)
        env = environment(logging=variant != "no-lineage")
        if kind == "uniform" and variant != "baseline":
            env = environment("uniform", 1000000, logging=variant != "no-lineage")
        elif name == "disabled-zero":
            env = environment("histogram", 16, flag="0")
        binary_source = Path(build_data["builds"]["baseline" if variant == "baseline" else "observer"]["source"])
        require(result["environment"] == env and result["command"] == [str(binary_source / "release/stringmol"), "30", str(path.parent / f"{kind}.conf")], "gate environment/command mismatch")
    r = gate["runs"]
    for n in ("absent", "zero", "repeat"):
        parity(r["disabled-baseline"], r["disabled-" + n])
    parity(r["disabled-no-lineage"], r["disabled-absent"], LOGS)
    parity(r["uniform-baseline"], r["uniform-enabled"], CONSERVATION_LOGS)
    parity(r["uniform-enabled"], r["uniform-repeat"])
    parity(r["uniform-no-lineage"], r["uniform-enabled"], LOGS)
    for n in ("enabled", "repeat"):
        summary = analyze_run(path.parent / f"uniform-{n}", lineage.expected_initial("host"), "uniform", 1000000, nsteps=500)
        require(summary == gate["summaries"]["uniform-" + n] and summary["end_conservation"]["scarcity_blocked"] == 0, "gate reconstruction changed")
    verify_directed(gate["directed"], build_path, path.parent)


def run_input(source: Path, root: Path, seed: int, condition: str) -> dict[str, Any]:
    config = root / f"{condition}-{seed}.conf"
    amount = 16 if condition == "m16" else 0
    expected = lineage.expected_initial("host")
    return {"condition": condition, "seed": seed, "amount": amount, "config": str(config),
            "command": [str(source / "release/stringmol"), "30", str(config)], "directory": str(root / "runs" / condition / str(seed)),
            "environment": environment("histogram", amount), "expected_initial": expected,
            "initial_material": initial_material(expected, "histogram", amount)}


def prepare(build_path: Path, gate_path: Path, root: Path) -> Path:
    data = verify_build(build_path)
    verify_gate(gate_path, build_path)
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    source = Path(data["builds"]["observer"]["source"])
    entries = []
    for seed in range(202621000, 202621010):
        for condition in ("m16", "m0"):
            entry = run_input(source, root, seed, condition)
            config = Path(entry["config"])
            config.write_text(render_config(StringmolControlConfig("host-only", seed, 0, 0), source / "config/ALXII.mtx"))
            config.chmod(0o444)
            entries.append({**entry, **record(config), "bytes_hex": config.read_bytes().hex()})
    path = root / "preparation.json"
    seal(path, {"protocol": "SM-C001", "protocol_pin": protocol_pin(), "workers": 6,
                "build_manifest": str(build_path.resolve()), "build_record": record(build_path), "build": data,
                "gates": str(gate_path.resolve()), "gate_record": record(gate_path), "repository_state": source_state(ROOT),
                "implementation": {str(p): record(p) for p in IMPLEMENTATION}, "runs": entries})
    seal(root / "preparation.sha256.json", record(path))
    verify_preparation(path)
    return path


def verify_preparation(path: Path) -> dict[str, Any]:
    require(not path.stat().st_mode & 0o222 and record(path) == read(path.with_name("preparation.sha256.json")), "immutable preparation changed")
    data: dict[str, Any] = read(path)
    require(data["protocol"] == "SM-C001" and data["protocol_pin"] == protocol_pin(), "prepared protocol pin mismatch")
    require(data["implementation"] == {str(p): record(p) for p in IMPLEMENTATION}, "prepared implementation changed")
    build_path, gate_path = Path(data["build_manifest"]), Path(data["gates"])
    require(record(build_path) == data["build_record"] and verify_build(build_path) == data["build"], "prepared build changed")
    require(record(gate_path) == data["gate_record"], "prepared gates changed")
    verify_gate(gate_path, build_path)
    require(data["workers"] == 6, "worker limit changed")
    require([(r["condition"], r["seed"]) for r in data["runs"]] == [(c, s) for s in range(202621000, 202621010) for c in ("m16", "m0")], "matrix changed")
    source = Path(data["build"]["builds"]["observer"]["source"])
    for r in data["runs"]:
        config = Path(r["config"])
        expected = render_config(StringmolControlConfig("host-only", r["seed"], 0, 0), source / "config/ALXII.mtx").encode()
        require(not config.stat().st_mode & 0o222 and config.read_bytes() == expected, "prepared config changed")
        require(r == {**run_input(source, path.parent, r["seed"], r["condition"]), **record(config), "bytes_hex": expected.hex()}, "run input changed")
    return data


def run_matrix(path: Path) -> None:
    data = verify_preparation(path)
    require(not (path.parent / "runs").exists() and not (path.parent / "campaign.json").exists(), "campaign already exists; no resume or selective retry")
    seal(path.parent / "campaign.json", {"input_manifest": record(path), "workers": 6})

    def run(r: dict[str, Any]) -> dict[str, Any]:
        directory = Path(r["directory"])
        result = execute(Path(r["command"][0]), Path(r["config"]), directory, r["environment"])
        result.update(input_manifest=record(path), condition=r["condition"], seed=r["seed"])
        seal(directory.with_suffix(".inventory.json"), result)
        return result

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(run, data["runs"]))
    seal(path.parent / "campaign-results.json", results)
    verify_preparation(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "gates", "prepare", "run"))
    parser.add_argument("--root", type=Path)
    parser.add_argument("--upstream", type=Path, default=HERE / "vendor/stringmol")
    parser.add_argument("--build", type=Path)
    parser.add_argument("--gates", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--lineage-build", type=Path)
    parser.add_argument("--lineage-gate", type=Path)
    args = parser.parse_args()
    if args.action == "build" and args.root:
        print(build(args.root, args.upstream))
    elif args.action == "gates" and args.build and args.root and args.lineage_build and args.lineage_gate:
        print(gates(args.build.resolve(), args.root, args.lineage_build.resolve(), args.lineage_gate.resolve()))
    elif args.action == "prepare" and args.build and args.gates and args.root:
        print(prepare(args.build.resolve(), args.gates.resolve(), args.root))
    elif args.action == "run" and args.manifest:
        run_matrix(args.manifest.resolve())
    else:
        parser.error("missing required paths for action")


if __name__ == "__main__":
    main()
