"""Deterministic analysis of the frozen AC-P001 viability screen (no assay retuning).

Run with RUNS_ROOT --output-dir OUTPUT. Outputs never default to reports/.
Integrity errors invalidate support; unreadable outcomes remain unknown, not zero.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections.abc import Collection
from pathlib import Path
from typing import Any, Callable, cast
from zipfile import BadZipFile

import numpy as np
import pandas as pd
from numpy.typing import NDArray

SEEDS = tuple(range(202612000, 202612010))
EPOCHS, POPULATION, CALLBACK = 100_000, 32_768, 100
SPEC = {
    "version": "paper-selfrep-v1-top1024-abundance-lex-ties",
    "entropy_threshold": 1.0, "consecutive_callbacks": 10,
    "candidate_limit": 1024,
    "candidate_order": "descending abundance; lexicographic stable ties",
    "evaluator_seed": 0, "qualification_score": 64,
    "checkpoint_policy": "first contemporaneous qualifying callback",
}
CATEGORIES = ("execution_scarcity_blocked", "execution_friction_blocked",
              "mutation_scarcity_blocked", "mutation_friction_blocked")


def require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def validate_config(
    config: dict[str, Any], *, pool_multiplier: int = 16, allowed_seeds: Collection[int] = SEEDS
) -> None:
    expected = {
        "phase": 1, "population_size": POPULATION, "tape_length": 64,
        "epochs": EPOCHS, "mutation_rate": 1 / 4096, "pool_multiplier": pool_multiplier,
        "callback_interval": CALLBACK, "max_steps": 8192,
        "pairing_mode": "paper_splitmix64_shuffled_disjoint",
        "execution_mode": "serial_exact_global_pool",
        "functional_observation": True, "functional_observation_spec": SPEC,
        "friction_hash_domain": "splitmix64(seed_xor_0xAC1001_plus_changing_write_counter)",
    }
    for key, value in expected.items():
        require(config.get(key) == value, f"unregistered config: {key}")
    require(config.get("seed") in allowed_seeds, "unregistered seed")
    require(not config.get("initial_soup") and config.get("epoch_offset", 0) == 0,
            "runs must be independently initialized")
    require(config.get("pool_mode", "histogram_matched") == "histogram_matched", "unregistered pool mode")
    require(config.get("friction_rejection_rate", 0) == 0, "unexpected friction")
    require(not config.get("pool_exclude_top") and not config.get("pool_exclude_symbols"),
            "unexpected exclusion parameter")


def verify_artifacts(root: Path, manifest: dict[str, Any]) -> None:
    required = {"config.json", "aggregate.csv", "writes.csv", "symbols.csv", "functional_scores.csv"}
    checksums = manifest.get("artifact_checksums", {})
    files = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and p.name != "manifest.json"}
    require(required <= files and set(checksums) == files, "incomplete checksum inventory")
    require({"aggregate.csv", "writes.csv", "symbols.csv", "functional_scores.csv", "functional_assays"}
            <= set(manifest.get("artifacts", [])), "incomplete artifact inventory")
    for name in manifest["artifacts"]:
        require((root / name).resolve().is_relative_to(root.resolve()), "artifact outside run")
        require((root / name).exists(), f"missing artifact: {name}")
    require((root / "functional_assays").is_dir(), "missing assay directory")
    for name, digest in sorted(checksums.items()):
        require((root / name).resolve().is_relative_to(root.resolve()), "checksum artifact outside run")
        require(sha256(root / name) == digest, f"checksum mismatch: {name}")


def bool_column(series: pd.Series[Any]) -> NDArray[np.bool_]:
    require(series.isin([True, False, "True", "False"]).all(), f"invalid boolean: {series.name}")
    return series.astype(str).eq("True").to_numpy()


def validate_function(root: Path, aggregate: pd.DataFrame, functional: pd.DataFrame,
                      manifest: dict[str, Any]) -> tuple[int | None, list[dict[str, Any]]]:
    streak = 0
    eligible: list[int] = []
    for row in aggregate.to_dict("records"):
        entropy = float(row["high_order_entropy"])
        require(math.isfinite(entropy), "nonfinite entropy")
        streak = streak + 1 if entropy >= 1 else 0
        require(row["functional_entropy_streak"] == streak, "incorrect entropy streak")
        if streak >= 10:
            eligible.append(int(row["epoch"]))
    require(functional["epoch"].tolist() == eligible, "eligible callback assays missing/extra")
    require(np.array_equal(bool_column(aggregate["functional_scoring_performed"]),
                           aggregate["epoch"].isin(eligible)), "scoring eligibility mismatch")
    unscored = aggregate.loc[~aggregate["epoch"].isin(eligible)]
    for key in ("functional_candidate_count", "functional_max_score", "functional_score_64_count"):
        require(unscored[key].isna().all(), "unevaluated score must be missing")
    require(not bool_column(unscored["functional_origin_qualified"]).any(), "unscored origin")
    expected_files = {f"epoch_{epoch:06d}.npz" for epoch in eligible}
    require({p.name for p in (root / "functional_assays").iterdir()} == expected_files,
            "assay file inventory mismatch")
    qualified: list[int] = []
    witnesses: list[dict[str, Any]] = []
    indexed = aggregate.set_index("epoch")
    for row in functional.to_dict("records"):
        epoch = int(row["epoch"])
        # Callback uniqueness is checked before this scalar row lookup.
        a = cast("pd.Series[Any]", indexed.loc[epoch])
        with np.load(root / "functional_assays" / f"epoch_{epoch:06d}.npz", allow_pickle=False) as assay:
            candidates, counts, scores = assay["candidates"], assay["abundances"], assay["scores"]
            n = min(1024, int(a["distinct_tapes"]))
            require(candidates.dtype == np.uint8 and candidates.shape == (n, 64), "invalid candidates")
            require(counts.shape == scores.shape == (n,) and n > 0, "invalid assay arrays")
            require(np.issubdtype(counts.dtype, np.integer) and (counts > 0).all(), "invalid abundances")
            require(np.issubdtype(scores.dtype, np.integer) and ((scores >= 0) & (scores <= 64)).all(), "invalid scores")
            keys = [(-int(c), tape.tobytes()) for c, tape in zip(counts, candidates, strict=True)]
            require(keys == sorted(keys) and len({key[1] for key in keys}) == n, "candidate order/uniqueness")
            for key, value in (("evaluator_seed", 0), ("local_epoch", epoch), ("absolute_epoch", epoch),
                               ("observation_version", SPEC["version"])):
                require(assay[key].tolist() == [value], f"assay {key} mismatch")
            hits = np.flatnonzero(scores == 64)
            for key, value in (("candidate_count", n), ("max_score", int(scores.max())),
                               ("score_64_count", len(hits)), ("origin_qualified", bool(len(hits)))):
                require(row[key] == value and a[f"functional_{key}"] == value, f"assay summary mismatch: {key}")
            require(row["absolute_epoch"] == epoch and row["entropy_streak"] == a["functional_entropy_streak"],
                    "functional epoch/streak mismatch")
            if len(hits):
                qualified.append(epoch)
                first = int(hits[0])
                require(row["witness_rank"] == first and row["witness_abundance"] == counts[first]
                        and row["witness_hex"] == candidates[first].tobytes().hex(), "witness mismatch")
                for rank in hits:
                    tape = candidates[rank]
                    witnesses.append({"epoch": epoch, "rank": int(rank), "abundance": int(counts[rank]),
                                      "tape_hex": tape.tobytes().hex(),
                                      "composition": json.dumps(np.bincount(tape, minlength=256).tolist(), separators=(",", ":"))})
            else:
                require(all(pd.isna(row[k]) for k in ("witness_rank", "witness_abundance", "witness_hex")), "unexpected witness")
    origin = qualified[0] if qualified else None
    witnesses = (
        [min((row for row in witnesses if row["epoch"] == origin), key=lambda row: row["rank"])]
        if origin is not None else []
    )
    require(manifest.get("functional_origin_epoch") == origin, "manifest origin mismatch")
    checkpoint = root / "origin_checkpoint.npz"
    require(checkpoint.exists() == (origin is not None), "checkpoint presence mismatch")
    if origin is not None:
        require("origin_checkpoint.npz" in manifest["artifacts"], "checkpoint not published")
        require(manifest.get("origin_checkpoint_sha256") == sha256(checkpoint), "checkpoint checksum mismatch")
        with np.load(checkpoint, allow_pickle=False) as saved:
            require(saved["local_epoch"].tolist() == saved["absolute_epoch"].tolist() == [origin], "checkpoint is not first origin")
            require(json.loads(str(saved["config_json"][0])) == manifest["config"], "checkpoint config mismatch")
            soup, pool = saved["soup"], saved["pool"]
            require(soup.dtype == np.uint8 and soup.shape == (POPULATION, 64), "checkpoint soup shape/type")
            require(pool.shape == (256,) and (pool >= 0).all(), "checkpoint pool")
            require(np.issubdtype(pool.dtype, np.integer), "checkpoint pool type")
            totals = saved["conserved_totals"]
            require(totals.shape == (256,) and np.issubdtype(totals.dtype, np.integer)
                    and (totals >= 0).all(), "checkpoint totals type/shape")
            require(np.array_equal(np.bincount(soup.ravel(), minlength=256) + pool, totals), "checkpoint conservation")
            origin_row = cast("pd.Series[Any]", indexed.loc[origin])
            require(saved["entropy_streak"].tolist() == [int(origin_row["functional_entropy_streak"])], "checkpoint streak")
            require(saved["changing_write_counter"].tolist() == [int(origin_row["cumulative_changing_write_attempts"])], "checkpoint changing counter")
            cumulative_keys = ["character_reads", "cumulative_execution_writes_success",
                               "cumulative_execution_scarcity_blocked", "cumulative_execution_friction_blocked",
                               "cumulative_mutation_writes_success", "cumulative_mutation_scarcity_blocked",
                               "cumulative_mutation_friction_blocked", "cumulative_cross_tape_copy_success",
                               "cumulative_cross_tape_copy_blocked"]
            require(saved["cumulative"].tolist() == [int(origin_row[k]) for k in cumulative_keys], "checkpoint cumulative counters")
            symbol_row = pd.read_csv(root / "symbols.csv").query("epoch == @origin")
            for saved_key, symbol_key in (("withdrawals", "withdrawals"), ("returns", "returns"),
                                         ("execution_blocked_by_symbol", "execution_blocked"),
                                         ("mutation_blocked_by_symbol", "mutation_blocked"),
                                         ("friction_blocked_by_symbol", "friction_blocked"),
                                         ("cross_a_to_b", "cross_a_to_b"), ("cross_b_to_a", "cross_b_to_a")):
                require(np.array_equal(saved[saved_key], symbol_row[symbol_key]), f"checkpoint ledger: {saved_key}")
            require(np.array_equal(pool, symbol_row["pool_count"]), "checkpoint pool ledger")
            values, counts = np.unique(soup, axis=0, return_counts=True)
            require(len(values) == origin_row["distinct_tapes"], "checkpoint distinct tapes mismatch")
            rank = np.argsort(-counts, kind="stable")[:1024]
            with np.load(root / "functional_assays" / f"epoch_{origin:06d}.npz", allow_pickle=False) as assay:
                require(np.array_equal(values[rank], assay["candidates"]) and np.array_equal(counts[rank], assay["abundances"]), "checkpoint candidate mismatch")
                witness = int(np.flatnonzero(assay["scores"] == 64)[0])
                require(saved["witness_rank"].tolist() == [witness] and saved["witness_score"].tolist() == [64]
                        and np.array_equal(saved["witness"], assay["candidates"][witness])
                        and saved["witness_abundance"].tolist() == [int(assay["abundances"][witness])]
                        and saved["evaluator_seed"].tolist() == [0], "checkpoint witness mismatch")
    return origin, witnesses


def summarize(
    root: Path, *, pool_multiplier: int = 16, allowed_seeds: Collection[int] = SEEDS
) -> tuple[dict[str, Any], pd.DataFrame, list[dict[str, Any]]]:
    result: dict[str, Any] = {"run_id": root.name, "seed": None,
                              "integrity": False, "origin": None, "error": ""}
    try:
        manifest = json.loads((root / "manifest.json").read_text())
        config = manifest["config"]
        result.update(seed=config.get("seed"))
        validate_config(config, pool_multiplier=pool_multiplier, allowed_seeds=allowed_seeds)
        require(manifest.get("status") == manifest.get("exit_status") == "success", "unsuccessful run")
        require(manifest.get("max_conservation_residual") == 0, "manifest conservation residual")
        verify_artifacts(root, manifest)
        require(json.loads((root / "config.json").read_text()) == config, "config file mismatch")
        writes = pd.read_csv(root / "writes.csv")
        aggregate = pd.read_csv(root / "aggregate.csv")
        functional = pd.read_csv(root / "functional_scores.csv", dtype={"witness_hex": str})
        callbacks = sorted(set(range(1, EPOCHS + 1, CALLBACK)) | {EPOCHS})
        require(writes["epoch"].tolist() == list(range(1, EPOCHS + 1)), "incomplete writes schedule")
        require(aggregate["epoch"].tolist() == callbacks, "incomplete callback schedule")
        require(aggregate["max_conservation_residual"].eq(0).all(), "aggregate conservation residual")
        count_columns = [c for c in writes if c not in ("blocked_fraction", "pool_entropy")]
        require(all(np.issubdtype(cast(np.dtype[Any], writes[c].dtype), np.integer) and writes[c].ge(0).all() for c in count_columns), "invalid write counts")
        for kind in ("execution", "mutation"):
            require(writes[f"{kind}_writes_blocked"].equals(writes[f"{kind}_scarcity_blocked"] + writes[f"{kind}_friction_blocked"]), "block category mismatch")
        blocks = writes[list(CATEGORIES)].sum(axis=1)
        require((blocks <= writes["changing_write_attempts"]).all(), "blocks exceed changing attempts")
        fractions = np.divide(blocks, writes["changing_write_attempts"],
                              out=np.zeros(len(writes)), where=writes["changing_write_attempts"].ne(0))
        require(np.allclose(fractions, writes["blocked_fraction"], rtol=1e-12, atol=1e-15), "blocked fraction mismatch")
        require(np.array_equal(writes["character_reads"].cumsum().iloc[np.array(callbacks) - 1],
                               aggregate["character_reads"]), "character read mismatch")
        for key in ["changing_write_attempts", "execution_writes_success", "execution_writes_blocked",
                    "mutation_writes_success", "mutation_writes_blocked", "cross_tape_copy_success",
                    "cross_tape_copy_blocked", *CATEGORIES]:
            require(np.array_equal(writes[key].cumsum().iloc[np.array(callbacks) - 1], aggregate[f"cumulative_{key}"]), f"cumulative mismatch: {key}")
        origin, witnesses = validate_function(root, aggregate, functional, manifest)
        # Reconstruct final tape composition from the deterministic initial soup and conserved pool.
        from experiments.paper_probe import initialize_soup
        # Numba's decorator stubs do not preserve this compiled callable's signature.
        initialize = cast(Callable[[int, int], NDArray[np.uint8]], initialize_soup)
        initial = np.bincount(initialize(POPULATION, int(config["seed"])).ravel(), minlength=256)
        symbols = pd.read_csv(root / "symbols.csv")
        require(all(np.issubdtype(cast(np.dtype[Any], symbols[c].dtype), np.integer) and symbols[c].ge(0).all()
                    for c in symbols), "invalid symbol counts")
        require(len(symbols) == len(callbacks) * 256 and
                np.array_equal(symbols["epoch"], np.repeat(callbacks, 256)) and
                np.array_equal(symbols["symbol"], np.tile(np.arange(256), len(callbacks))), "incomplete symbols schedule")
        initial_pool = symbols["initial_pool_count"].to_numpy().reshape(-1, 256)
        pools = symbols["pool_count"].to_numpy().reshape(-1, 256)
        require((initial_pool == initial_pool[0]).all() and (pools >= 0).all(), "invalid pool trajectories")
        expected_pool = initial * pool_multiplier
        require(np.array_equal(initial_pool[0], expected_pool), "unregistered initial pool")
        require(np.array_equal(pools.sum(axis=1), aggregate["pool_total"]) and int(pools[-1].sum()) == manifest["pool_total"], "pool total mismatch")
        require(np.array_equal(symbols["initial_pool_count"] + symbols["returns"] - symbols["withdrawals"], symbols["pool_count"]), "symbol ledger mismatch")
        compositions = initial + initial_pool - pools
        require((compositions >= 0).all() and (compositions.sum(axis=1) == POPULATION * 64).all(), "invalid conserved composition")
        if origin is not None:
            with np.load(root / "origin_checkpoint.npz", allow_pickle=False) as saved:
                require(np.array_equal(saved["conserved_totals"], initial + expected_pool),
                        "checkpoint totals differ from initialized reservoir")
                require(np.array_equal(np.bincount(saved["soup"].ravel(), minlength=256),
                                       compositions[callbacks.index(origin)]),
                        "checkpoint soup composition mismatch")
        require(writes["execution_friction_blocked"].eq(0).all()
                and writes["mutation_friction_blocked"].eq(0).all(), "unexpected friction blocks")
        for column, aggregate_keys in (
            ("execution_blocked", ["cumulative_execution_scarcity_blocked"]),
            ("mutation_blocked", ["cumulative_mutation_scarcity_blocked"]),
            ("friction_blocked", ["cumulative_execution_friction_blocked", "cumulative_mutation_friction_blocked"]),
        ):
            ledger = symbols[column].to_numpy().reshape(-1, 256)
            require((np.diff(ledger, axis=0) >= 0).all(), f"decreasing symbol ledger: {column}")
            require(np.array_equal(ledger.sum(axis=1), aggregate[aggregate_keys].sum(axis=1)),
                    f"symbol block total mismatch: {column}")
        for column in ("withdrawals", "returns", "cross_a_to_b", "cross_b_to_a"):
            require((np.diff(symbols[column].to_numpy().reshape(-1, 256), axis=0) >= 0).all(),
                    f"decreasing symbol ledger: {column}")
        require(math.isfinite(manifest["wall_time_s"]) and manifest["wall_time_s"] >= 0,
                "invalid runtime")
        first = writes.loc[blocks.gt(0), "epoch"]
        result.update(wall_time_s=manifest["wall_time_s"],
                      storage_bytes=sum(p.stat().st_size for p in root.rglob("*") if p.is_file()))
        result.update(integrity=True, origin=origin is not None, origin_epoch=origin,
                      total_blocks=int(blocks.sum()), first_block_epoch=int(first.iloc[0]) if len(first) else None,
                      changing_write_attempts=int(writes["changing_write_attempts"].sum()),
                      max_conservation_residual=0, max_functional_score=int(functional["max_score"].max()) if len(functional) else None,
                      eligible_callbacks=len(functional), max_entropy=float(aggregate["high_order_entropy"].max()),
                      final_entropy=float(aggregate["high_order_entropy"].iloc[-1]),
                      final_composition=json.dumps(compositions[-1].tolist(), separators=(",", ":")))
        result.update({key: int(writes[key].sum()) for key in CATEGORIES})
        trajectory = aggregate[["epoch", "high_order_entropy", "functional_entropy_streak", "functional_max_score",
                                "functional_candidate_count", "functional_score_64_count",
                                "elapsed_seconds", "cumulative_changing_write_attempts",
                                *[f"cumulative_{key}" for key in CATEGORIES]]].copy()
        trajectory.insert(0, "seed", result["seed"])
        for witness in witnesses:
            witness.update(seed=result["seed"])
        return result, trajectory, witnesses
    except (ValueError, KeyError, OSError, TypeError, IndexError, EOFError, BadZipFile) as error:
        result["error"] = f"{type(error).__name__}: {error}"
        return result, pd.DataFrame(), []


def evaluate(runs: pd.DataFrame) -> dict[str, Any]:
    """Apply the frozen ten-independent-seed, at-least-three-origin screen."""
    matrix = len(runs) == len(SEEDS) and set(runs["seed"]) == set(SEEDS)
    valid = runs[runs["integrity"].eq(True) & runs["origin"].isin([True, False])]
    # Duplicates are not independent replication, even in an invalid campaign.
    independent = valid[valid["seed"].isin(SEEDS) & ~runs.loc[valid.index, "seed"].duplicated(keep=False)]
    origins = int(independent["origin"].eq(True).sum())
    gates = {"integrity": bool(matrix and len(valid) == len(SEEDS)),
             "incidence_ge_3_of_10": origins >= 3}
    passed = all(gates.values())
    return {"gates": gates, "verified_runs": len(independent), "origins": origins,
            "expected_runs": 10, "minimum_origins": 3,
            "positive_control_viability": passed, "decision": "PASS" if passed else "FAIL",
            "next_step": (
                "Preregister a new held-out multiplier-16 versus multiplier-2 comparison; "
                "do not reuse AC-I001 outcomes as confirmation controls."
                if passed else
                "Stop the BFF origin campaign; do not tune the observer or extend successful-looking runs."
            )}


def analyze(runs_root: Path, output_dir: Path) -> dict[str, Any]:
    """Verify raw inputs and write deterministic, compact CSV and Markdown tables."""
    require(not output_dir.resolve().is_relative_to(runs_root.resolve())
            and not runs_root.resolve().is_relative_to(output_dir.resolve()),
            "output directory must be separate from raw runs")
    summaries, trajectories, witnesses = [], [], []
    for root in sorted(p for p in runs_root.iterdir() if p.is_dir()):
        summary, trajectory, tape_rows = summarize(root)
        summaries.append(summary)
        if not trajectory.empty:
            trajectories.append(trajectory)
        witnesses.extend(tape_rows)
    runs = pd.DataFrame(summaries, columns=None if summaries else
                        ["run_id", "seed", "integrity", "origin", "error"])
    decision = evaluate(runs)
    output_dir.mkdir(parents=True, exist_ok=True)
    tables = {
        "runs": runs,
        "incidence": pd.DataFrame([{key: decision[key] for key in
                                    ("verified_runs", "origins", "expected_runs", "minimum_origins")}]),
        "gates": pd.DataFrame([{"gate": key, "pass": value} for key, value in decision["gates"].items()]),
        "entropy": pd.concat(trajectories, ignore_index=True) if trajectories else
                   pd.DataFrame(columns=["seed", "epoch", "high_order_entropy", "functional_max_score"]),
        "score64_candidates": pd.DataFrame(witnesses, columns=[
            "seed", "epoch", "rank", "abundance", "tape_hex", "composition"]),
    }
    for name, table in tables.items():
        table.to_csv(output_dir / f"{name}.csv", index=False, float_format="%.17g", lineterminator="\n")
    lines = ["# AC-P001 high-resource functional-origin viability", "",
             f"**{decision['decision']}** — {decision['origins']}/10 verified origins; minimum 3/10.",
             f"Verified runs: {decision['verified_runs']}/10.", "",
             *[f"- {key}: {'PASS' if value else 'FAIL'}" for key, value in decision["gates"].items()], "",
             "| Seed | Integrity | Origin epoch | Max score | First block | Total blocks | Runtime (s) | Storage (bytes) |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in summaries:
        cells = [row.get(key) for key in ("seed", "integrity", "origin_epoch", "max_functional_score",
                                        "first_block_epoch", "total_blocks", "wall_time_s", "storage_bytes")]
        lines.append("| " + " | ".join("—" if value is None else
                     format(value, ".6g") if isinstance(value, float) else str(value)
                     for value in cells) + " |")
        if row["error"]:
            lines.append(f"\nIntegrity error ({row['run_id']}): {row['error']}\n")
    if not decision["gates"]["integrity"]:
        lines += ["", "Artifact integrity is incomplete: unknown outcomes cannot establish a biological negative."]
    elif not decision["positive_control_viability"]:
        lines += ["", "De novo functional-origin discovery is not viable at the tested 32,768-tape, "
                  "100,000-epoch scales under this preregistered screen."]
    lines += ["", decision["next_step"], "",
              "The 3/10 threshold is a minimum repeatability screen, not a significance test. "
              "Secondary outcomes cannot rescue a failed incidence gate.",
              "A pass supports only repeatable functional origin in a high-resource conserved artificial chemistry; "
              "it does not establish adaptation, organization, ecology, or organism identity.", "",
              "Missing functional scores mean unevaluated, not zero. Failed integrity leaves origins unknown. "
              "Persisted scores are checked for consistency without rerunning or changing the observer.",
              "Exact conservation is checked using recorded zero residuals, symbol ledgers, and deterministic "
              "initial totals; origin checkpoints also reconcile their full soup and pool. "
              "Non-origin soup states were not persisted for independent replay.",
              "CSV files contain callback entropy, functional scores and block totals, first score-64 checkpoint witnesses "
              "with abundance/composition, final reconstructed symbol composition, runtime, and storage.", ""]
    (output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return decision


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs_root", type=Path, nargs="?",
                        default=Path("sweeps/ac_p001_high_resource_origin_viability/runs"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(analyze(args.runs_root, args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
