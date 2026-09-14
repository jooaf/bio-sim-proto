"""Deterministic analysis of the frozen AC-I001 confirmation (no assay retuning).

Run with RUNS_ROOT --output-dir OUTPUT. Outputs never default to reports/.
Integrity errors invalidate support; unreadable outcomes remain unknown, not zero.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable, cast
from zipfile import BadZipFile

import numpy as np
import pandas as pd
from numpy.typing import NDArray

SEEDS = tuple(range(202611000, 202611020))
ARMS = ("control", "natural_six", "friction")
EPOCHS, POPULATION, CALLBACK = 100_000, 32_768, 100
RATE = 0.27555027572734614
SIX = [0, 44, 60, 91, 93, 125]
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


def exact_discordance(favored_only: int, natural_only: int) -> float:
    """P[Binomial(b+c, 1/2) >= b]; no discordance gives p=1."""
    if favored_only < 0 or natural_only < 0:
        raise ValueError("discordance counts must be nonnegative")
    n = favored_only + natural_only
    return cast(float, sum(math.comb(n, k) for k in range(favored_only, n + 1)) / 2**n)


def arm_for(config: dict[str, Any]) -> str:
    mode = config.get("pool_mode", "histogram_matched")
    rate = config.get("friction_rejection_rate", 0)
    if mode == "excluded_list" and config.get("pool_exclude_symbols") == SIX and rate == 0:
        return "natural_six"
    if mode == "histogram_matched" and not config.get("pool_exclude_symbols") and not config.get("pool_exclude_top"):
        if rate == 0:
            return "control"
        if rate == RATE:
            return "friction"
    raise ValueError("unregistered treatment")


def validate_config(config: dict[str, Any]) -> None:
    expected = {
        "phase": 1, "population_size": POPULATION, "tape_length": 64,
        "epochs": EPOCHS, "mutation_rate": 1 / 4096, "pool_multiplier": 2,
        "callback_interval": CALLBACK, "max_steps": 8192,
        "pairing_mode": "paper_splitmix64_shuffled_disjoint",
        "execution_mode": "serial_exact_global_pool",
        "functional_observation": True, "functional_observation_spec": SPEC,
        "friction_hash_domain": "splitmix64(seed_xor_0xAC1001_plus_changing_write_counter)",
    }
    for key, value in expected.items():
        require(config.get(key) == value, f"unregistered config: {key}")
    require(config.get("seed") in SEEDS, "unregistered seed")
    require(not config.get("initial_soup") and config.get("epoch_offset", 0) == 0,
            "confirmation must be independently initialized")
    require(not config.get("pool_exclude_top"), "unexpected exclusion parameter")


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
            require(np.array_equal(np.bincount(soup.ravel(), minlength=256) + pool, saved["conserved_totals"]), "checkpoint conservation")
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
            rank = np.argsort(-counts, kind="stable")[:1024]
            with np.load(root / "functional_assays" / f"epoch_{origin:06d}.npz", allow_pickle=False) as assay:
                require(np.array_equal(values[rank], assay["candidates"]) and np.array_equal(counts[rank], assay["abundances"]), "checkpoint candidate mismatch")
                witness = int(np.flatnonzero(assay["scores"] == 64)[0])
                require(saved["witness_rank"].tolist() == [witness] and saved["witness_score"].tolist() == [64]
                        and np.array_equal(saved["witness"], assay["candidates"][witness])
                        and saved["witness_abundance"].tolist() == [int(assay["abundances"][witness])]
                        and saved["evaluator_seed"].tolist() == [0], "checkpoint witness mismatch")
    return origin, witnesses


def summarize(root: Path) -> tuple[dict[str, Any], pd.DataFrame, list[dict[str, Any]]]:
    result: dict[str, Any] = {"run_id": root.name, "seed": None, "arm": None,
                              "integrity": False, "origin": None, "error": ""}
    try:
        manifest = json.loads((root / "manifest.json").read_text())
        config = manifest["config"]
        result.update(seed=config.get("seed"), arm=arm_for(config))
        validate_config(config)
        require(manifest.get("status") == manifest.get("exit_status") == "success", "unsuccessful run")
        require(manifest.get("max_conservation_residual") == 0, "manifest conservation residual")
        verify_artifacts(root, manifest)
        require(json.loads((root / "config.json").read_text()) == config, "config file mismatch")
        writes = pd.read_csv(root / "writes.csv")
        aggregate = pd.read_csv(root / "aggregate.csv")
        functional = pd.read_csv(root / "functional_scores.csv")
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
        expected_pool = initial * 2
        if result["arm"] == "natural_six":
            total = int(expected_pool.sum())
            expected_pool[SIX] = 0
            shares = expected_pool.astype(float) * total / int(expected_pool.sum())
            expected_pool = np.floor(shares).astype(np.int64)
            remainder = total - int(expected_pool.sum())
            expected_pool[np.argsort(-(shares - expected_pool), kind="stable")[:remainder]] += 1
        require(np.array_equal(initial_pool[0], expected_pool), "unregistered initial pool")
        require(np.array_equal(pools.sum(axis=1), aggregate["pool_total"]) and int(pools[-1].sum()) == manifest["pool_total"], "pool total mismatch")
        require(np.array_equal(symbols["initial_pool_count"] + symbols["returns"] - symbols["withdrawals"], symbols["pool_count"]), "symbol ledger mismatch")
        compositions = initial + initial_pool - pools
        require((compositions >= 0).all() and (compositions.sum(axis=1) == POPULATION * 64).all(), "invalid conserved composition")
        first = writes.loc[blocks.gt(0), "epoch"]
        result.update(integrity=True, origin=origin is not None, origin_epoch=origin,
                      total_blocks=int(blocks.sum()), first_block_epoch=int(first.iloc[0]) if len(first) else None,
                      changing_write_attempts=int(writes["changing_write_attempts"].sum()),
                      max_conservation_residual=0, max_functional_score=int(functional["max_score"].max()) if len(functional) else None,
                      eligible_callbacks=len(functional), max_entropy=float(aggregate["high_order_entropy"].max()),
                      final_entropy=float(aggregate["high_order_entropy"].iloc[-1]),
                      final_composition=json.dumps(compositions[-1].tolist(), separators=(",", ":")))
        result.update({key: int(writes[key].sum()) for key in CATEGORIES})
        trajectory = aggregate[["epoch", "high_order_entropy", "functional_entropy_streak", "functional_max_score"]].copy()
        trajectory.insert(0, "arm", result["arm"])
        trajectory.insert(0, "seed", result["seed"])
        for witness in witnesses:
            witness.update(seed=result["seed"], arm=result["arm"])
        return result, trajectory, witnesses
    except (ValueError, KeyError, OSError, TypeError, IndexError, EOFError, BadZipFile) as error:
        result["error"] = f"{type(error).__name__}: {error}"
        return result, pd.DataFrame(), []


def evaluate(runs: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    expected = {(seed, arm) for seed in SEEDS for arm in ARMS}
    matrix = len(runs) == 60 and set(zip(runs["seed"], runs["arm"])) == expected
    integrity = bool(matrix and runs["integrity"].eq(True).all() and runs["origin"].isin([True, False]).all())
    valid = runs[runs["integrity"].eq(True)].copy()
    incidence = pd.DataFrame([{"arm": arm, "verified_runs": int((valid["arm"] == arm).sum()),
                               "origins": int(valid.loc[valid["arm"] == arm, "origin"].eq(True).sum()),
                               "expected_runs": 20} for arm in ARMS])
    paired: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    gates = {"integrity": integrity, "positive_controls": False, "mechanical_match": False,
             "selective_incidence_contrast": False, "nonspecific_control_viability": False}
    details: dict[str, Any] = {"median_block_ratio": None, "matched_pairs": None}
    if integrity:
        pivot = valid.pivot(index="seed", columns="arm", values="origin").astype(bool)
        blocks = valid.pivot(index="seed", columns="arm", values="total_blocks")
        for seed in SEEDS:
            denominator = int(cast(int, blocks.loc[seed, "natural_six"]))
            ratio = float(cast(int, blocks.loc[seed, "friction"]) / denominator) if denominator > 0 else None
            paired.append({"seed": seed, **{arm: bool(pivot.loc[seed, arm]) for arm in ARMS},
                           **{f"{arm}_blocks": int(cast(int, blocks.loc[seed, arm])) for arm in ARMS},
                           "friction_natural_ratio": ratio,
                           "block_match": ratio is not None and 0.67 <= ratio <= 1.5})
        for arm in ("friction", "control"):
            favored, natural = pivot[arm], pivot["natural_six"]
            b, c = int((favored & ~natural).sum()), int((~favored & natural).sum())
            comparisons.append({"comparison": f"{arm}_vs_natural_six", "both": int((favored & natural).sum()),
                                "neither": int((~favored & ~natural).sum()), "favored_only": b, "natural_only": c,
                                "incidence_difference": (b - c) / 20, "p_one_sided": exact_discordance(b, c),
                                "pass": b - c >= 4 and exact_discordance(b, c) <= 0.05})
        totals = pivot.sum()
        median_natural = float(blocks["natural_six"].median())
        ratio = float(blocks["friction"].median()) / median_natural if median_natural > 0 else None
        matched = sum(row["block_match"] for row in paired)
        details.update(median_block_ratio=ratio, matched_pairs=matched)
        gates.update(positive_controls=bool(totals["control"] >= 5 and totals["friction"] >= 5),
                     mechanical_match=bool(ratio is not None and 0.8 <= ratio <= 1.25 and matched >= 16),
                     selective_incidence_contrast=all(row["pass"] for row in comparisons),
                     nonspecific_control_viability=bool(totals["friction"] >= totals["control"] - 2))
    support = all(gates.values())
    decision = {"gates": gates, **details, "class_specific_support": support,
                "decision": "PASS" if support else "FAIL — stop AC-I002–AC-I004",
                "comparisons": comparisons, "incidence": incidence.to_dict("records")}
    return decision, pd.DataFrame(paired), incidence


def analyze(runs_root: Path, output_dir: Path) -> dict[str, Any]:
    summaries, trajectories, witnesses = [], [], []
    for root in sorted(p for p in runs_root.iterdir() if p.is_dir()):
        summary, trajectory, tape_rows = summarize(root)
        summaries.append(summary)
        if not trajectory.empty:
            trajectories.append(trajectory)
        witnesses.extend(tape_rows)
    runs = pd.DataFrame(summaries, columns=None if summaries else ["run_id", "seed", "arm", "integrity", "origin", "error"])
    decision, pairs, incidence = evaluate(runs)
    output_dir.mkdir(parents=True, exist_ok=True)
    tables = {"runs": runs, "pairs": pairs, "incidence": incidence,
              "contrasts": pd.DataFrame(decision["comparisons"]),
              "entropy": pd.concat(trajectories, ignore_index=True) if trajectories else pd.DataFrame(),
              "score64_candidates": pd.DataFrame(witnesses, columns=["seed", "arm", "epoch", "rank", "abundance", "tape_hex", "composition"]),
              "gates": pd.DataFrame([{"gate": k, "pass": v} for k, v in decision["gates"].items()])}
    for name, table in tables.items():
        table.to_csv(output_dir / f"{name}.csv", index=False, float_format="%.17g", lineterminator="\n")
    lines = ["# AC-I001 frozen confirmation analysis", "", f"**{decision['decision']}**", "",
             "| Arm | Verified runs | Origins | Expected |", "|---|---:|---:|---:|"]
    for row in decision["incidence"]:
        lines.append(f"| {row['arm']} | {row['verified_runs']} | {row['origins']} | 20 |")
    lines += ["", *[f"- {key}: {'PASS' if value else 'FAIL'}" for key, value in decision["gates"].items()], "",
              f"Median friction/natural-six total-block ratio: {decision['median_block_ratio']}; matched pairs: {decision['matched_pairs']}.", ""]
    for row in decision["comparisons"]:
        lines.append(f"- {row['comparison']}: discordants {row['favored_only']}/{row['natural_only']}; difference {row['incidence_difference']:.2f}; exact one-sided p={row['p_one_sided']:.8g}.")
    if not decision["gates"]["positive_controls"]:
        lines += ["", "Positive-control gate failed or could not be verified. No class-specific support is permitted."]
    lines += ["", "Missing functional scores mean unevaluated, not score zero. Failed integrity leaves outcomes unknown.",
              "Nonsignificance is not equivalence. The viability bound is descriptive. No adaptation, organization, communication, self-maintenance, or organism claim follows.",
              "Integrity requires complete checksum verification and cross-checking persisted assay scores; scores are not re-evaluated with new seeds.",
              "Final symbol composition is reconstructed from deterministic initial tape counts and conserved pool ledgers.", ""]
    (output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return decision


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs_root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    decision = analyze(args.runs_root, args.output_dir)
    print(json.dumps(decision, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
