"""Reproducible single-run, replicate, and parameter-sweep orchestration."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import itertools
import json
import multiprocessing
import tomllib
from pathlib import Path
from typing import Any

import pandas as pd
import tomli_w

from analysis.report import write_batch_stage0_report, write_stage0_report
from soup.config import Config
from soup.simulation import Simulation


def config_hash(config: Config) -> str:
    """Return the same stable short hash used in run directory names."""

    encoded = tomli_w.dumps(config.to_dict()).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:12]


def _completed_run(config: Config) -> Path | None:
    parent = Path(config.run.output_dir)
    if not parent.exists():
        return None
    suffix = f"_{config_hash(config)}_{config.run.seed}"
    for candidate in sorted(parent.iterdir()):
        if not candidate.is_dir() or not candidate.name.endswith(suffix):
            continue
        manifest_path = candidate / "manifest.json"
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("exit_status") == "success":
            return candidate
    return None


def _run_one(config: Config) -> str:
    existing = _completed_run(config)
    if existing is not None:
        return str(existing)
    return str(Simulation(config).run())


def run_replicates(base: Config, n_seeds: int, start_seed: int, processes: int) -> list[Path]:
    """Run or resume sequential seeds, optionally in spawned worker processes."""

    if n_seeds <= 0:
        raise ValueError("n_seeds must be positive")
    configs: list[Config] = []
    for seed in range(start_seed, start_seed + n_seeds):
        values = base.to_dict()
        values["run"]["seed"] = seed
        clone_path = Path(base.run.output_dir) / f".replicate_{seed}.toml"
        clone_path.parent.mkdir(parents=True, exist_ok=True)
        clone_path.write_text(tomli_w.dumps(values), encoding="utf-8")
        configs.append(Config.load(clone_path))
        clone_path.unlink()
    if processes == 1:
        return [Path(_run_one(config)) for config in configs]
    context = multiprocessing.get_context("spawn")
    with context.Pool(processes=processes) as pool:
        return [Path(value) for value in pool.map(_run_one, configs)]


def _set_parameter(config: Config, path: str, value: object) -> None:
    parts = path.split(".")
    if len(parts) != 2:
        raise ValueError(f"parameter path must be section.field, got {path!r}")
    section_name, field_name = parts
    if not hasattr(config, section_name):
        raise ValueError(f"unknown config section {section_name!r}")
    section = getattr(config, section_name)
    if not dataclasses.is_dataclass(section) or not hasattr(section, field_name):
        raise ValueError(f"unknown config field {path!r}")
    setattr(section, field_name, value)


def run_sweep(spec_path: Path) -> Path:
    """Execute a TOML Cartesian grid with deterministic seeds and resume support."""

    with spec_path.open("rb") as handle:
        spec = tomllib.load(handle)
    sweep = spec.get("sweep")
    parameters = spec.get("parameters", {})
    if not isinstance(sweep, dict) or not isinstance(parameters, dict):
        raise ValueError("sweep spec needs [sweep] and [parameters] tables")
    base_path = (spec_path.parent / str(sweep["base_config"])).resolve()
    name = str(sweep["name"])
    n_seeds = int(sweep.get("n_seeds", 1))
    start_seed = int(sweep.get("start_seed", 0))
    processes = int(sweep.get("processes", 1))
    output_root = Path(str(sweep.get("output_dir", "sweeps"))) / name
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "spec.toml").write_bytes(spec_path.read_bytes())

    parameter_names = sorted(parameters)
    value_lists: list[list[object]] = []
    for key in parameter_names:
        values = parameters[key]
        if not isinstance(values, list) or not values:
            raise ValueError(f"sweep parameter {key!r} must be a nonempty array")
        value_lists.append(values)

    index_rows: list[dict[str, Any]] = []
    for combination in itertools.product(*value_lists):
        base = Config.load(base_path)
        for key, value in zip(parameter_names, combination, strict=True):
            _set_parameter(base, key, value)
        base.run.output_dir = str(output_root / "runs")
        base.validate()
        paths = run_replicates(base, n_seeds, start_seed, processes)
        for seed, path in zip(range(start_seed, start_seed + n_seeds), paths, strict=True):
            row: dict[str, Any] = {
                "config_hash": path.name.rsplit("_", 2)[-2],
                "seed": seed,
                "run_dir": str(path),
            }
            row.update(dict(zip(parameter_names, combination, strict=True)))
            index_rows.append(row)
    index_path = output_root / "index.parquet"
    pd.DataFrame(index_rows).sort_values(parameter_names + ["seed"]).to_parquet(index_path, index=False, compression="zstd")
    return index_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="run one TOML configuration")
    run_parser.add_argument("config", type=Path)
    run_parser.add_argument("--report", action="store_true")

    replicate_parser = subparsers.add_parser("replicates", help="run sequential seeded replicates")
    replicate_parser.add_argument("config", type=Path)
    replicate_parser.add_argument("--n-seeds", type=int, required=True)
    replicate_parser.add_argument("--start-seed", type=int, default=0)
    replicate_parser.add_argument("--processes", type=int, default=1)
    replicate_parser.add_argument("--batch-report", type=Path)

    sweep_parser = subparsers.add_parser("sweep", help="run a TOML Cartesian sweep")
    sweep_parser.add_argument("spec", type=Path)

    args = parser.parse_args()
    if args.command == "run":
        run_dir = Path(_run_one(Config.load(args.config)))
        if args.report:
            print(write_stage0_report(run_dir))
        else:
            print(run_dir)
    elif args.command == "replicates":
        run_dirs = run_replicates(Config.load(args.config), args.n_seeds, args.start_seed, args.processes)
        for run_dir in run_dirs:
            print(run_dir)
        if args.batch_report is not None:
            print(write_batch_stage0_report(run_dirs, args.batch_report))
    else:
        print(run_sweep(args.spec))


if __name__ == "__main__":
    main()
