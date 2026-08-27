"""Run reproducible pinned Spatial Stringmol host/parasite controls."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from experiments.stringmol.configure_control import StringmolControlConfig, render_config


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_population(
    path: Path,
    parasite_species: int | None,
    host_species: int | None,
) -> dict[str, Any]:
    """Summarize upstream tick,species,count population rows."""

    with path.open(newline="", encoding="utf-8") as handle:
        raw = list(csv.reader(handle))
    rows = [
        {"tick": int(row[0]), "species": int(row[1]), "count": int(row[2])}
        for row in raw
        if len(row) == 3
    ]
    if not rows:
        raise ValueError(f"no population rows in {path}")
    ticks = sorted({int(row["tick"]) for row in rows})
    totals = {
        tick: sum(int(row["count"]) for row in rows if int(row["tick"]) == tick)
        for tick in ticks
    }
    result: dict[str, Any] = {
        "initial_total": totals[ticks[0]],
        "maximum_total": max(totals.values()),
        "final_total": totals[ticks[-1]],
        "final_tick": ticks[-1],
        "final_species_richness": sum(1 for row in rows if int(row["tick"]) == ticks[-1]),
    }
    if host_species is not None:
        host = [row for row in rows if int(row["species"]) == host_species]
        host_by_tick = {tick: 0 for tick in ticks}
        for row in host:
            host_by_tick[int(row["tick"])] = int(row["count"])
        result.update(
            {
                "host_species": host_species,
                "initial_host_count": host_by_tick[ticks[0]],
                "maximum_host_count": max(host_by_tick.values()),
                "final_host_count": host_by_tick[ticks[-1]],
            }
        )
    if parasite_species is not None:
        parasite = [row for row in rows if int(row["species"]) == parasite_species]
        count_by_tick = {tick: 0 for tick in ticks}
        for row in parasite:
            count_by_tick[int(row["tick"])] = int(row["count"])
        result.update(
            {
                "parasite_species": parasite_species,
                "initial_parasite_count": count_by_tick[ticks[0]],
                "maximum_parasite_count": max(count_by_tick.values()),
                "final_parasite_count": count_by_tick[ticks[-1]],
                "maximum_parasite_fraction": max(
                    count_by_tick[tick] / totals[tick] for tick in ticks
                ),
                "final_parasite_fraction": count_by_tick[ticks[-1]] / totals[ticks[-1]],
            }
        )
    return result


def run_one(
    *,
    source: Path,
    output_root: Path,
    control: StringmolControlConfig,
    lock: dict[str, Any],
    patch_paths: list[Path],
) -> Path:
    """Run or resume one pinned source/config/patch/seed combination."""

    run_dir = output_root / control.condition / f"seed_{control.seed}"
    manifest_path = run_dir / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("exit_status") == "success" and manifest.get("control") == asdict(control):
            return run_dir
        raise FileExistsError(f"refusing to overwrite mismatched Stringmol run: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=False)
    binary = source / "release" / "stringmol"
    matrix = source / "config" / "ALXII.mtx"
    if not binary.exists() or not matrix.exists():
        raise FileNotFoundError("run bootstrap.nu before launching Stringmol controls")
    config_path = run_dir / "control.conf"
    config_path.write_text(render_config(control, matrix), encoding="utf-8")
    protocol = {
        "source_lock": lock,
        "control": asdict(control),
        "config_sha256": sha256(config_path),
        "matrix_sha256": sha256(matrix),
        "binary_sha256": sha256(binary),
        "patches": [
            {"name": path.name, "sha256": sha256(path)} for path in patch_paths
        ],
    }
    (run_dir / "protocol.json").write_text(
        json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = {**protocol, "exit_status": "running"}
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    completed = subprocess.run(
        [str(binary.resolve()), "30", str(config_path.resolve())],
        cwd=run_dir,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    (run_dir / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (run_dir / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        manifest["exit_status"] = "failed"
        manifest["returncode"] = completed.returncode
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        raise RuntimeError(f"Stringmol failed in {run_dir}: {completed.returncode}")
    population_path = run_dir / "popdy001.dat"
    parasite_species = 2 if control.condition == "mixed" else (1 if control.condition == "parasite-only" else None)
    host_species = 1 if control.condition in {"host-only", "mixed"} else None
    summary = parse_population(population_path, parasite_species, host_species)
    warning = "impossible to configure using reproducible method" in completed.stdout
    summary["reproducible_loader_warning"] = warning
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    compact_outputs = [population_path, run_dir / "summary.json", run_dir / "control.conf"]
    manifest.update(
        {
            "exit_status": "success",
            "returncode": completed.returncode,
            "summary": summary,
            "compact_output_sha256": {
                path.name: sha256(path) for path in compact_outputs
            },
        }
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--start-seed", type=int, required=True)
    parser.add_argument("--n-seeds", type=int, required=True)
    parser.add_argument(
        "--conditions",
        nargs="+",
        choices=("host-only", "parasite-only", "mixed"),
        default=["host-only", "parasite-only", "mixed"],
    )
    parser.add_argument("--interaction-radius", type=int, choices=(0, 1), required=True)
    parser.add_argument("--placement-radius", type=int, choices=(0, 1), required=True)
    parser.add_argument("--nsteps", type=int, default=5_000)
    args = parser.parse_args()
    if args.n_seeds <= 0:
        raise ValueError("n-seeds must be positive")
    here = Path(__file__).resolve().parent
    source = here / "vendor" / "stringmol"
    lock_raw = json.loads((here / "source.lock.json").read_text(encoding="utf-8"))
    lock = cast(dict[str, Any], lock_raw)
    patch_paths = sorted((here / "patches").glob("*.patch"))
    paths: list[Path] = []
    for seed in range(args.start_seed, args.start_seed + args.n_seeds):
        for condition in args.conditions:
            control = StringmolControlConfig(
                condition=cast(Any, condition),
                seed=seed,
                interaction_radius=args.interaction_radius,
                placement_radius=args.placement_radius,
                nsteps=args.nsteps,
            )
            paths.append(
                run_one(
                    source=source,
                    output_root=args.output_root,
                    control=control,
                    lock=lock,
                    patch_paths=patch_paths,
                )
            )
    index = {
        "source_commit": lock["commit"],
        "run_dirs": [str(path) for path in paths],
    }
    index_path = args.output_root / "index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(index_path)


if __name__ == "__main__":
    main()
