"""Exact-conservation, bounded-log Phase 1 BFF experiment probe.

The global symbol pool makes interaction order observable, so this kernel is
intentionally serial. It uses the paper probe's deterministic SplitMix64
initialization, mutation stream, shuffled disjoint pairing, and BFF semantics,
while routing every changing write through one exact per-symbol ledger.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import time
import zlib
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numba as nb
import numpy as np
from numpy.typing import NDArray

from analysis.complexity import byte_entropy
from experiments.paper_probe import (
    JOINT_LENGTH,
    TAPE_LENGTH,
    complexity_row,
    derived_seed,
    initialize_soup,
    score_selfrep_candidates,
    shuffle_indices,
    splitmix64,
)

INSTRUCTIONS = np.asarray([60, 62, 123, 125, 45, 43, 46, 44, 91, 93], dtype=np.uint8)
FUNCTIONAL_ENTROPY_THRESHOLD = 1.0
FUNCTIONAL_ENTROPY_STREAK = 10
FUNCTIONAL_CANDIDATE_LIMIT = 1024
FUNCTIONAL_EVALUATOR_SEED = 0
FUNCTIONAL_OBSERVATION_VERSION = "paper-selfrep-v1-top1024-abundance-lex-ties"


def ranked_functional_candidates(
    values: NDArray[np.uint8], counts: NDArray[np.int64], limit: int = FUNCTIONAL_CANDIDATE_LIMIT
) -> tuple[NDArray[np.uint8], NDArray[np.int64]]:
    """Return abundance-ranked exact tapes with lexicographic stable ties."""

    rank = np.argsort(-counts, kind="stable")[:limit]
    return np.ascontiguousarray(values[rank]), np.ascontiguousarray(counts[rank])


def functional_scores(
    values: NDArray[np.uint8], counts: NDArray[np.int64]
) -> tuple[NDArray[np.uint8], NDArray[np.int64], NDArray[np.int64]]:
    """Apply the frozen paper evaluator to the frozen candidate ordering."""

    candidates, abundances = ranked_functional_candidates(values, counts)
    scores = score_selfrep_candidates(candidates, FUNCTIONAL_EVALUATOR_SEED)
    return candidates, abundances, scores


def next_entropy_streak(current: int, entropy: float) -> int:
    """Advance the contemporaneous functional-origin entropy gate."""

    if not math.isfinite(entropy):
        raise ValueError("functional observation requires finite high-order entropy")
    return current + 1 if entropy >= FUNCTIONAL_ENTROPY_THRESHOLD else 0


@nb.njit(inline="always")
def conserved_write(
    joint: NDArray[np.uint8],
    index: int,
    new_value: int,
    pool: NDArray[np.int64],
    withdrawals: NDArray[np.int64],
    returns: NDArray[np.int64],
    blocked_by_symbol: NDArray[np.int64],
) -> int:
    """Apply one atomic exchange: 0=no-op, 1=changed, 2=blocked."""

    value = new_value & 0xFF
    old_value = int(joint[index])
    if old_value == value:
        return 0
    if pool[value] <= 0:
        blocked_by_symbol[value] += 1
        return 2
    pool[value] -= 1
    pool[old_value] += 1
    withdrawals[value] += 1
    returns[old_value] += 1
    joint[index] = value
    return 1


@nb.njit(inline="always")
def conserved_write_with_friction(
    joint: NDArray[np.uint8],
    index: int,
    new_value: int,
    pool: NDArray[np.int64],
    withdrawals: NDArray[np.int64],
    returns: NDArray[np.int64],
    blocked_by_symbol: NDArray[np.int64],
    friction_blocked_by_symbol: NDArray[np.int64],
    friction_threshold: int,
    friction_seed: int,
    changing_write_counter: NDArray[np.int64],
) -> int:
    """Apply symbol-independent rejection before an ordinary conserved write.

    Outcomes are 0=no-op, 1=changed, 2=scarcity blocked, 3=friction blocked.
    """

    value = new_value & 0xFF
    if int(joint[index]) == value:
        return 0
    counter = int(changing_write_counter[0])
    changing_write_counter[0] += 1
    if friction_threshold > 0:
        key = np.uint64(friction_seed) ^ np.uint64(0xAC1001)
        draw = (splitmix64(key + np.uint64(counter)) >> np.uint64(8)) & np.uint64((1 << 30) - 1)
        if draw < np.uint64(friction_threshold):
            friction_blocked_by_symbol[value] += 1
            return 3
    return conserved_write(
        joint, index, value, pool, withdrawals, returns, blocked_by_symbol
    )


@nb.njit
def execute_bff_conserved(
    joint: NDArray[np.uint8],
    pool: NDArray[np.int64],
    withdrawals: NDArray[np.int64],
    returns: NDArray[np.int64],
    blocked_by_symbol: NDArray[np.int64],
    cross_a_to_b: NDArray[np.int64],
    cross_b_to_a: NDArray[np.int64],
    max_steps: int,
    friction_blocked_by_symbol: NDArray[np.int64],
    friction_threshold: int,
    friction_seed: int,
    changing_write_counter: NDArray[np.int64],
) -> tuple[int, int, int, int, int, int]:
    """Execute one joint tape with exact pool-mediated writes."""

    pc = 0
    head0 = 0
    head1 = 0
    steps = 0
    successful = 0
    scarcity_blocked = 0
    friction_blocked = 0
    cross_success = 0
    cross_blocked = 0
    while steps < max_steps and 0 <= pc < JOINT_LENGTH:
        op = int(joint[pc])
        steps += 1
        next_pc = pc + 1
        if op == 60:  # <
            head0 = (head0 - 1) & (JOINT_LENGTH - 1)
        elif op == 62:  # >
            head0 = (head0 + 1) & (JOINT_LENGTH - 1)
        elif op == 123:  # {
            head1 = (head1 - 1) & (JOINT_LENGTH - 1)
        elif op == 125:  # }
            head1 = (head1 + 1) & (JOINT_LENGTH - 1)
        elif op == 43 or op == 45 or op == 46 or op == 44:
            source = head0
            destination = head0
            if op == 43:
                new_value = (int(joint[head0]) + 1) & 0xFF
            elif op == 45:
                new_value = (int(joint[head0]) - 1) & 0xFF
            elif op == 46:
                source = head0
                destination = head1
                new_value = int(joint[source])
            else:
                source = head1
                destination = head0
                new_value = int(joint[source])
            is_cross_copy = (op == 46 or op == 44) and (source // TAPE_LENGTH != destination // TAPE_LENGTH)
            outcome = conserved_write_with_friction(
                joint,
                destination,
                new_value,
                pool,
                withdrawals,
                returns,
                blocked_by_symbol,
                friction_blocked_by_symbol,
                friction_threshold,
                friction_seed,
                changing_write_counter,
            )
            if outcome == 2:
                scarcity_blocked += 1
                if is_cross_copy:
                    cross_blocked += 1
            elif outcome == 3:
                friction_blocked += 1
                if is_cross_copy:
                    cross_blocked += 1
            else:
                successful += 1
                if is_cross_copy and outcome == 1:
                    cross_success += 1
                    if source < TAPE_LENGTH:
                        cross_a_to_b[new_value] += 1
                    else:
                        cross_b_to_a[new_value] += 1
        elif op == 91 and joint[head0] == 0:  # [
            depth = 1
            candidate = pc + 1
            while candidate < JOINT_LENGTH and depth:
                if joint[candidate] == 91:
                    depth += 1
                elif joint[candidate] == 93:
                    depth -= 1
                candidate += 1
            if depth:
                break
            next_pc = candidate
        elif op == 93 and joint[head0] != 0:  # ]
            depth = 1
            candidate = pc - 1
            while candidate >= 0 and depth:
                if joint[candidate] == 93:
                    depth += 1
                elif joint[candidate] == 91:
                    depth -= 1
                candidate -= 1
            if depth:
                break
            next_pc = candidate + 2
        pc = next_pc
    return steps, successful, scarcity_blocked, friction_blocked, cross_success, cross_blocked


@nb.njit
def mutate_and_execute_conserved_epoch(
    soup: NDArray[np.uint8],
    order: NDArray[np.uint32],
    pool: NDArray[np.int64],
    seed: int,
    epoch: int,
    mutation_threshold: int,
    max_steps: int,
    withdrawals: NDArray[np.int64],
    returns: NDArray[np.int64],
    execution_blocked_by_symbol: NDArray[np.int64],
    mutation_blocked_by_symbol: NDArray[np.int64],
    friction_blocked_by_symbol: NDArray[np.int64],
    cross_a_to_b: NDArray[np.int64],
    cross_b_to_a: NDArray[np.int64],
    friction_threshold: int,
    friction_seed: int,
    changing_write_counter: NDArray[np.int64],
) -> tuple[int, int, int, int, int, int, int, int, int]:
    """Mutate and execute an ordered Phase 1 epoch serially."""

    total_steps = 0
    execution_success = 0
    execution_scarcity_blocked = 0
    execution_friction_blocked = 0
    mutation_success = 0
    mutation_scarcity_blocked = 0
    mutation_friction_blocked = 0
    cross_success = 0
    cross_blocked = 0
    population_size = len(soup)
    epoch_seed = derived_seed(np.uint64(seed), np.uint64(epoch))
    for pair_index in range(population_size // 2):
        first = int(order[2 * pair_index])
        second = int(order[2 * pair_index + 1])
        joint = np.empty(JOINT_LENGTH, dtype=np.uint8)
        joint[:TAPE_LENGTH] = soup[first]
        joint[TAPE_LENGTH:] = soup[second]
        for byte_index in range(JOINT_LENGTH):
            random_value = splitmix64(
                (np.uint64(population_size) * epoch_seed + np.uint64(pair_index))
                * np.uint64(JOINT_LENGTH)
                + np.uint64(byte_index)
            )
            probability_draw = (random_value >> np.uint64(8)) & np.uint64((1 << 30) - 1)
            if probability_draw < np.uint64(mutation_threshold):
                outcome = conserved_write_with_friction(
                    joint,
                    byte_index,
                    int(random_value & np.uint64(0xFF)),
                    pool,
                    withdrawals,
                    returns,
                    mutation_blocked_by_symbol,
                    friction_blocked_by_symbol,
                    friction_threshold,
                    friction_seed,
                    changing_write_counter,
                )
                if outcome == 2:
                    mutation_scarcity_blocked += 1
                elif outcome == 3:
                    mutation_friction_blocked += 1
                else:
                    mutation_success += 1
        result: Any = execute_bff_conserved(  # type: ignore[call-arg]
            joint,
            pool,
            withdrawals,
            returns,
            execution_blocked_by_symbol,
            cross_a_to_b,
            cross_b_to_a,
            max_steps,
            friction_blocked_by_symbol,
            friction_threshold,
            friction_seed,
            changing_write_counter,
        )
        total_steps += result[0]
        execution_success += result[1]
        execution_scarcity_blocked += result[2]
        execution_friction_blocked += result[3]
        cross_success += result[4]
        cross_blocked += result[5]
        soup[first] = joint[:TAPE_LENGTH]
        soup[second] = joint[TAPE_LENGTH:]
    return (
        total_steps,
        execution_success,
        execution_scarcity_blocked,
        execution_friction_blocked,
        mutation_success,
        mutation_scarcity_blocked,
        mutation_friction_blocked,
        cross_success,
        cross_blocked,
    )


def pool_entropy(pool: NDArray[np.int64]) -> float:
    total = int(pool.sum())
    if total == 0:
        return 0.0
    probabilities = pool[pool > 0].astype(np.float64) / total
    return float(-np.sum(probabilities * np.log2(probabilities)))


def jensen_shannon_divergence(first: NDArray[np.int64], second: NDArray[np.int64]) -> float:
    """Return base-2 Jensen-Shannon divergence between count vectors."""

    p = first.astype(np.float64) / float(first.sum())
    q = second.astype(np.float64) / float(second.sum())
    midpoint = 0.5 * (p + q)
    p_mask = p > 0
    q_mask = q > 0
    return float(
        0.5 * np.sum(p[p_mask] * np.log2(p[p_mask] / midpoint[p_mask]))
        + 0.5 * np.sum(q[q_mask] * np.log2(q[q_mask] / midpoint[q_mask]))
    )


def git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def write_manifest(path: Path, values: dict[str, Any]) -> None:
    path.write_text(json.dumps(values, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def save_origin_checkpoint(path: Path, **arrays: Any) -> None:
    """Atomically save an exact first-qualified conserved state bundle."""

    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    temporary.replace(path)


def run_probe(
    *,
    population_size: int,
    epochs: int,
    seed: int,
    mutation_rate: float,
    pool_multiplier: float,
    callback_interval: int,
    output_dir: Path,
    max_steps: int = 8192,
    pool_mode: str = "histogram_matched",
    pool_exclude_top: int = 0,
    pool_exclude_symbols: tuple[int, ...] = (),
    initial_soup: Path | None = None,
    epoch_offset: int = 0,
    final_soup: Path | None = None,
    friction_rejection_rate: float = 0.0,
    functional_observation: bool = False,
) -> Path:
    """Run one deterministic Phase 1 condition and return its directory."""

    if population_size <= 0 or population_size % 2:
        raise ValueError("population_size must be a positive even number")
    if epochs <= 0 or callback_interval <= 0:
        raise ValueError("epochs and callback_interval must be positive")
    if not 0.0 <= mutation_rate <= 1.0:
        raise ValueError("mutation_rate must be in 0..1")
    if not 0.0 <= friction_rejection_rate <= 1.0:
        raise ValueError("friction_rejection_rate must be in 0..1")
    if pool_multiplier < 0.0 or not math.isfinite(pool_multiplier):
        raise ValueError("pool_multiplier must be finite and nonnegative")
    if max_steps <= 0:
        raise ValueError("max_steps must be positive")
    if pool_mode not in {"histogram_matched", "uniform", "excluded_top", "excluded_list"}:
        raise ValueError(
            "pool_mode must be 'histogram_matched', 'uniform', 'excluded_top', or 'excluded_list'"
        )
    if pool_mode == "excluded_top" and not 1 <= pool_exclude_top < 256:
        raise ValueError("pool_exclude_top must be in 1..255 for excluded_top mode")
    if pool_mode == "excluded_list":
        if not pool_exclude_symbols:
            raise ValueError("excluded_list mode requires pool_exclude_symbols")
        if len(set(pool_exclude_symbols)) != len(pool_exclude_symbols):
            raise ValueError("pool_exclude_symbols must be distinct")
        if not all(0 <= symbol < 256 for symbol in pool_exclude_symbols):
            raise ValueError("pool_exclude_symbols must be byte values in 0..255")
        if len(pool_exclude_symbols) >= 256:
            raise ValueError("pool_exclude_symbols must leave at least one symbol")
    if pool_mode not in {"excluded_top", "excluded_list"}:
        if pool_exclude_top or pool_exclude_symbols:
            raise ValueError("pool exclusion parameters require an exclusion pool_mode")
    if epoch_offset < 0:
        raise ValueError("epoch_offset must be nonnegative")

    multiplier_slug = format(pool_multiplier, ".8g").replace(".", "p")
    if pool_mode == "histogram_matched":
        mode_suffix = ""
    elif pool_mode == "uniform":
        mode_suffix = "_uniform"
    elif pool_mode == "excluded_top":
        mode_suffix = f"_excl{pool_exclude_top}"
    else:
        digest = zlib.crc32(bytes(sorted(pool_exclude_symbols))) & 0xFFFFFFFF
        mode_suffix = f"_exlist{len(pool_exclude_symbols)}_{digest:08x}"
    friction_suffix = (
        "" if friction_rejection_rate == 0.0
        else f"_fric{format(friction_rejection_rate, '.8g').replace('.', 'p')}"
    )
    cont_suffix = "" if initial_soup is None else "_cont"
    run_dir = output_dir / f"p1_m{multiplier_slug}_n{population_size}_s{seed}{mode_suffix}{friction_suffix}{cont_suffix}"
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / "manifest.json"
    config = {
        "phase": 1,
        "population_size": population_size,
        "tape_length": TAPE_LENGTH,
        "epochs": epochs,
        "seed": seed,
        "mutation_rate": mutation_rate,
        "pool_multiplier": pool_multiplier,
        "callback_interval": callback_interval,
        "max_steps": max_steps,
        "pairing_mode": "paper_splitmix64_shuffled_disjoint",
        "execution_mode": "serial_exact_global_pool",
        "friction_rejection_rate": friction_rejection_rate,
        "friction_hash_domain": "splitmix64(seed_xor_0xAC1001_plus_changing_write_counter)",
        "functional_observation": functional_observation,
    }
    if functional_observation:
        config["functional_observation_spec"] = {
            "version": FUNCTIONAL_OBSERVATION_VERSION,
            "entropy_threshold": FUNCTIONAL_ENTROPY_THRESHOLD,
            "consecutive_callbacks": FUNCTIONAL_ENTROPY_STREAK,
            "candidate_limit": FUNCTIONAL_CANDIDATE_LIMIT,
            "candidate_order": "descending abundance; lexicographic stable ties",
            "evaluator_seed": FUNCTIONAL_EVALUATOR_SEED,
            "qualification_score": TAPE_LENGTH,
            "checkpoint_policy": "first contemporaneous qualifying callback",
        }
    if epoch_offset:
        config["epoch_offset"] = epoch_offset
    if initial_soup is not None:
        config["initial_soup"] = str(initial_soup)
    if pool_mode != "histogram_matched":
        config["pool_mode"] = pool_mode
    if pool_exclude_top:
        config["pool_exclude_top"] = pool_exclude_top
    if pool_exclude_symbols:
        config["pool_exclude_symbols"] = list(pool_exclude_symbols)
    if final_soup is not None:
        config["final_soup"] = str(final_soup)
    existing: dict[str, Any] = {}
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
    if existing.get("exit_status") == "success" and existing.get("config") == config:
        return run_dir

    started_at = datetime.now(timezone.utc)
    manifest: dict[str, Any] = {
        "run_id": run_dir.name,
        "status": "running",
        "exit_status": "running",
        "started_at": started_at.isoformat(),
        "git_commit": git_commit(),
        "config": config,
    }
    write_manifest(manifest_path, manifest)
    (run_dir / "config.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    aggregate_path = run_dir / "aggregate.csv"
    writes_path = run_dir / "writes.csv"
    symbols_path = run_dir / "symbols.csv"
    functional_path = run_dir / "functional_scores.csv"
    functional_assay_dir = run_dir / "functional_assays"
    origin_checkpoint_path = run_dir / "origin_checkpoint.npz"
    try:
        if initial_soup is None:
            soup: NDArray[np.uint8] = initialize_soup(population_size, seed)  # type: ignore[assignment, call-arg, type-var]
        else:
            loaded = np.load(initial_soup)
            if loaded.shape != (population_size, TAPE_LENGTH) or loaded.dtype != np.uint8:
                raise ValueError(
                    f"initial soup {initial_soup} must be uint8 of shape "
                    f"({population_size}, {TAPE_LENGTH}); got {loaded.dtype} {loaded.shape}"
                )
            soup = loaded.copy()
        tape_counts_initial = np.bincount(soup.ravel(), minlength=256).astype(np.int64)
        matched_pool = np.rint(tape_counts_initial.astype(np.float64) * pool_multiplier).astype(np.int64)
        if pool_mode == "histogram_matched":
            initial_pool = matched_pool
        elif pool_mode == "uniform":
            initial_pool = np.full(256, int(matched_pool.sum()) // 256, dtype=np.int64)
            initial_pool[: int(matched_pool.sum()) % 256] += 1
        else:
            # Exclusion pools: zero stock of the excluded symbols, mass
            # redistributed proportionally over the rest (largest-remainder
            # apportionment keeps the total exact).
            total = int(matched_pool.sum())
            if pool_mode == "excluded_top":
                rank = np.argsort(-tape_counts_initial, kind="stable")
                excluded = np.zeros(256, dtype=bool)
                excluded[rank[:pool_exclude_top]] = True
            else:
                excluded = np.zeros(256, dtype=bool)
                excluded[list(pool_exclude_symbols)] = True
            weights = np.where(excluded, 0, matched_pool).astype(np.int64)
            weight_sum = int(weights.sum())
            if weight_sum <= 0:
                raise ValueError("no non-excluded symbols carry pool mass")
            shares = weights.astype(np.float64) * total / weight_sum
            initial_pool = np.floor(shares).astype(np.int64)
            remainder = total - int(initial_pool.sum())
            fractional = shares - initial_pool
            for index in np.argsort(-fractional, kind="stable")[:remainder]:
                initial_pool[index] += 1
        pool = initial_pool.copy()
        conserved_totals = tape_counts_initial + pool
        order = np.arange(population_size, dtype=np.uint32)
        mutation_threshold = round(mutation_rate * (1 << 30))
        withdrawals = np.zeros(256, dtype=np.int64)
        returns = np.zeros(256, dtype=np.int64)
        execution_blocked_by_symbol = np.zeros(256, dtype=np.int64)
        mutation_blocked_by_symbol = np.zeros(256, dtype=np.int64)
        friction_blocked_by_symbol = np.zeros(256, dtype=np.int64)
        cross_a_to_b = np.zeros(256, dtype=np.int64)
        cross_b_to_a = np.zeros(256, dtype=np.int64)
        changing_write_counter = np.zeros(1, dtype=np.int64)
        friction_threshold = round(friction_rejection_rate * (1 << 30))

        aggregate_fields = [
            "epoch", "elapsed_seconds", "character_reads", "byte_entropy", "brotli_size",
            "compressed_bpb", "high_order_entropy", "pool_total", "pool_entropy",
            "pool_jsd_from_initial", "soup_jsd_from_pool", "soup_jsd_from_uniform",
            "zero_pool_symbols", "dominant_tape_count",
            "dominant_tape_fraction", "distinct_tapes", "active_instruction_fraction",
            "cumulative_changing_write_attempts",
            "cumulative_execution_writes_success", "cumulative_execution_writes_blocked",
            "cumulative_execution_scarcity_blocked", "cumulative_execution_friction_blocked",
            "cumulative_mutation_writes_success", "cumulative_mutation_writes_blocked",
            "cumulative_mutation_scarcity_blocked", "cumulative_mutation_friction_blocked",
            "cumulative_cross_tape_copy_success", "cumulative_cross_tape_copy_blocked",
            "recycled_withdrawal_lower_bound", "max_conservation_residual",
        ]
        if functional_observation:
            aggregate_fields += [
                "functional_entropy_streak", "functional_scoring_performed",
                "functional_candidate_count", "functional_max_score",
                "functional_score_64_count", "functional_origin_qualified",
            ]
        functional_fields = [
            "epoch", "absolute_epoch", "entropy_streak", "candidate_count",
            "max_score", "score_64_count", "origin_qualified",
            "witness_rank", "witness_abundance", "witness_hex",
        ]
        write_fields = [
            "epoch", "character_reads", "changing_write_attempts",
            "execution_writes_success", "execution_writes_blocked",
            "execution_scarcity_blocked", "execution_friction_blocked",
            "mutation_writes_success", "mutation_writes_blocked",
            "mutation_scarcity_blocked", "mutation_friction_blocked",
            "cross_tape_copy_success", "cross_tape_copy_blocked", "blocked_fraction",
            "pool_entropy", "zero_pool_symbols",
        ]
        symbol_fields = [
            "epoch", "symbol", "pool_count", "initial_pool_count", "withdrawals", "returns",
            "execution_blocked", "mutation_blocked", "friction_blocked",
            "cross_a_to_b", "cross_b_to_a",
        ]
        started = time.perf_counter()
        cumulative = np.zeros(9, dtype=np.int64)
        entropy_streak = 0
        origin_epoch: int | None = None
        with (
            aggregate_path.open("w", newline="", encoding="utf-8") as aggregate_handle,
            writes_path.open("w", newline="", encoding="utf-8") as writes_handle,
            symbols_path.open("w", newline="", encoding="utf-8") as symbols_handle,
            (
                functional_path.open("w", newline="", encoding="utf-8")
                if functional_observation else nullcontext(None)
            ) as functional_handle,
        ):
            aggregate_writer = csv.DictWriter(aggregate_handle, fieldnames=aggregate_fields)
            writes_writer = csv.DictWriter(writes_handle, fieldnames=write_fields)
            symbols_writer = csv.DictWriter(symbols_handle, fieldnames=symbol_fields)
            functional_writer = (
                csv.DictWriter(functional_handle, fieldnames=functional_fields)
                if functional_handle is not None else None
            )
            aggregate_writer.writeheader()
            writes_writer.writeheader()
            symbols_writer.writeheader()
            if functional_writer is not None:
                functional_writer.writeheader()

            for epoch_index in range(epochs):
                shuffle_indices(order, seed, epoch_index + epoch_offset)  # type: ignore[call-arg, type-var]
                changing_before = int(changing_write_counter[0])
                interval: Any = mutate_and_execute_conserved_epoch(  # type: ignore[call-arg]
                    soup,
                    order,
                    pool,
                    seed,
                    epoch_index + epoch_offset,
                    mutation_threshold,
                    max_steps,
                    withdrawals,
                    returns,
                    execution_blocked_by_symbol,
                    mutation_blocked_by_symbol,
                    friction_blocked_by_symbol,
                    cross_a_to_b,
                    cross_b_to_a,
                    friction_threshold,
                    seed,
                    changing_write_counter,
                )
                cumulative += np.asarray(interval, dtype=np.int64)
                changing_attempts = int(changing_write_counter[0]) - changing_before
                execution_blocked = interval[2] + interval[3]
                mutation_blocked = interval[5] + interval[6]
                blocked = execution_blocked + mutation_blocked
                writes_writer.writerow(
                    {
                        "epoch": epoch_index + 1,
                        "character_reads": interval[0],
                        "changing_write_attempts": changing_attempts,
                        "execution_writes_success": interval[1],
                        "execution_writes_blocked": execution_blocked,
                        "execution_scarcity_blocked": interval[2],
                        "execution_friction_blocked": interval[3],
                        "mutation_writes_success": interval[4],
                        "mutation_writes_blocked": mutation_blocked,
                        "mutation_scarcity_blocked": interval[5],
                        "mutation_friction_blocked": interval[6],
                        "cross_tape_copy_success": interval[7],
                        "cross_tape_copy_blocked": interval[8],
                        "blocked_fraction": 0.0 if changing_attempts == 0 else blocked / changing_attempts,
                        "pool_entropy": pool_entropy(pool),
                        "zero_pool_symbols": int(np.count_nonzero(pool == 0)),
                    }
                )
                if epoch_index % callback_interval != 0 and epoch_index + 1 != epochs:
                    continue

                tape_counts = np.bincount(soup.ravel(), minlength=256).astype(np.int64)
                residual = int(np.max(np.abs(tape_counts + pool - conserved_totals)))
                if residual != 0:
                    raise RuntimeError(f"symbol conservation residual {residual} at epoch {epoch_index + 1}")
                values, counts = np.unique(soup, axis=0, return_counts=True)
                complexity = complexity_row(
                    soup,
                    epoch_index + 1,
                    time.perf_counter() - started,
                    int(cumulative[0]),
                )
                functional_metrics: dict[str, Any] = {}
                if functional_observation:
                    entropy_streak = next_entropy_streak(
                        entropy_streak, float(complexity["high_order_entropy"])
                    )
                    functional_metrics = {
                        "functional_entropy_streak": entropy_streak,
                        "functional_scoring_performed": False,
                        "functional_candidate_count": "",
                        "functional_max_score": "",
                        "functional_score_64_count": "",
                        "functional_origin_qualified": False,
                    }
                    if entropy_streak >= FUNCTIONAL_ENTROPY_STREAK:
                        candidates, abundances, scores = functional_scores(values, counts)
                        functional_assay_dir.mkdir(exist_ok=True)
                        save_origin_checkpoint(
                            functional_assay_dir / f"epoch_{epoch_index + 1:06d}.npz",
                            candidates=candidates,
                            abundances=abundances,
                            scores=scores,
                            evaluator_seed=np.asarray([FUNCTIONAL_EVALUATOR_SEED], dtype=np.int64),
                        )
                        max_score = int(scores.max()) if len(scores) else 0
                        qualified_indices = np.flatnonzero(scores == TAPE_LENGTH)
                        qualified = len(qualified_indices) > 0
                        witness_index = int(qualified_indices[0]) if qualified else -1
                        assert functional_writer is not None
                        functional_writer.writerow(
                            {
                                "epoch": epoch_index + 1,
                                "absolute_epoch": epoch_offset + epoch_index + 1,
                                "entropy_streak": entropy_streak,
                                "candidate_count": len(candidates),
                                "max_score": max_score,
                                "score_64_count": len(qualified_indices),
                                "origin_qualified": qualified,
                                "witness_rank": witness_index if qualified else "",
                                "witness_abundance": int(abundances[witness_index]) if qualified else "",
                                "witness_hex": candidates[witness_index].tobytes().hex() if qualified else "",
                            }
                        )
                        functional_metrics = {
                            "functional_entropy_streak": entropy_streak,
                            "functional_scoring_performed": True,
                            "functional_candidate_count": len(candidates),
                            "functional_max_score": max_score,
                            "functional_score_64_count": len(qualified_indices),
                            "functional_origin_qualified": qualified,
                        }
                        if qualified and origin_epoch is None:
                            origin_epoch = epoch_index + 1
                            save_origin_checkpoint(
                                origin_checkpoint_path,
                                soup=soup,
                                pool=pool,
                                conserved_totals=conserved_totals,
                                cumulative=cumulative,
                                withdrawals=withdrawals,
                                returns=returns,
                                execution_blocked_by_symbol=execution_blocked_by_symbol,
                                mutation_blocked_by_symbol=mutation_blocked_by_symbol,
                                friction_blocked_by_symbol=friction_blocked_by_symbol,
                                cross_a_to_b=cross_a_to_b,
                                cross_b_to_a=cross_b_to_a,
                                changing_write_counter=changing_write_counter,
                                local_epoch=np.asarray([origin_epoch], dtype=np.int64),
                                absolute_epoch=np.asarray([epoch_offset + origin_epoch], dtype=np.int64),
                                entropy_streak=np.asarray([entropy_streak], dtype=np.int64),
                                witness=candidates[witness_index],
                                witness_rank=np.asarray([witness_index], dtype=np.int64),
                                witness_abundance=np.asarray([abundances[witness_index]], dtype=np.int64),
                                witness_score=np.asarray([scores[witness_index]], dtype=np.int64),
                                evaluator_seed=np.asarray([FUNCTIONAL_EVALUATOR_SEED], dtype=np.int64),
                                config_json=np.asarray([json.dumps(config, sort_keys=True)]),
                            )
                withdrawal_total = int(withdrawals.sum())
                recycled = int(np.maximum(withdrawals - initial_pool, 0).sum())
                aggregate_writer.writerow(
                    {
                        **complexity,
                        "pool_total": int(pool.sum()),
                        "pool_entropy": pool_entropy(pool),
                        "pool_jsd_from_initial": jensen_shannon_divergence(initial_pool, pool),
                        "soup_jsd_from_pool": jensen_shannon_divergence(tape_counts, pool),
                        "soup_jsd_from_uniform": jensen_shannon_divergence(
                            tape_counts, np.ones(256, dtype=np.int64)
                        ),
                        "zero_pool_symbols": int(np.count_nonzero(pool == 0)),
                        "dominant_tape_count": int(counts.max()),
                        "dominant_tape_fraction": float(counts.max() / population_size),
                        "distinct_tapes": int(len(counts)),
                        "active_instruction_fraction": float(np.isin(soup, INSTRUCTIONS).mean()),
                        "cumulative_changing_write_attempts": int(changing_write_counter[0]),
                        "cumulative_execution_writes_success": int(cumulative[1]),
                        "cumulative_execution_writes_blocked": int(cumulative[2] + cumulative[3]),
                        "cumulative_execution_scarcity_blocked": int(cumulative[2]),
                        "cumulative_execution_friction_blocked": int(cumulative[3]),
                        "cumulative_mutation_writes_success": int(cumulative[4]),
                        "cumulative_mutation_writes_blocked": int(cumulative[5] + cumulative[6]),
                        "cumulative_mutation_scarcity_blocked": int(cumulative[5]),
                        "cumulative_mutation_friction_blocked": int(cumulative[6]),
                        "cumulative_cross_tape_copy_success": int(cumulative[7]),
                        "cumulative_cross_tape_copy_blocked": int(cumulative[8]),
                        "recycled_withdrawal_lower_bound": 0.0 if withdrawal_total == 0 else recycled / withdrawal_total,
                        "max_conservation_residual": residual,
                        **functional_metrics,
                    }
                )
                for symbol in range(256):
                    symbols_writer.writerow(
                        {
                            "epoch": epoch_index + 1,
                            "symbol": symbol,
                            "pool_count": int(pool[symbol]),
                            "initial_pool_count": int(initial_pool[symbol]),
                            "withdrawals": int(withdrawals[symbol]),
                            "returns": int(returns[symbol]),
                            "execution_blocked": int(execution_blocked_by_symbol[symbol]),
                            "mutation_blocked": int(mutation_blocked_by_symbol[symbol]),
                            "friction_blocked": int(friction_blocked_by_symbol[symbol]),
                            "cross_a_to_b": int(cross_a_to_b[symbol]),
                            "cross_b_to_a": int(cross_b_to_a[symbol]),
                        }
                    )
                aggregate_handle.flush()
                writes_handle.flush()
                symbols_handle.flush()
                if functional_handle is not None:
                    functional_handle.flush()

        wall_time = time.perf_counter() - started
        if final_soup is not None:
            final_soup.parent.mkdir(parents=True, exist_ok=True)
            np.save(final_soup, soup)
        manifest.update(
            {
                "status": "success",
                "exit_status": "success",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "wall_time_s": wall_time,
                "pool_total": int(pool.sum()),
                "max_conservation_residual": 0,
                "functional_origin_epoch": origin_epoch,
                "artifacts": [aggregate_path.name, writes_path.name, symbols_path.name]
                + ([functional_path.name, functional_assay_dir.name] if functional_observation else [])
                + ([origin_checkpoint_path.name] if origin_epoch is not None else [])
                + ([final_soup.name] if final_soup is not None else []),
            }
        )
        write_manifest(manifest_path, manifest)
        return run_dir
    except BaseException as error:
        manifest.update(
            {
                "status": "failed",
                "exit_status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "error_type": type(error).__name__,
                "error": str(error),
            }
        )
        write_manifest(manifest_path, manifest)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--population-size", type=int, default=256)
    parser.add_argument("--epochs", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--mutation-rate", type=float, default=1.0 / 4096.0)
    parser.add_argument("--pool-multiplier", type=float, required=True)
    parser.add_argument("--callback-interval", type=int, default=100)
    parser.add_argument("--max-steps", type=int, default=8192)
    parser.add_argument("--pool-mode", choices=("histogram_matched", "uniform", "excluded_top", "excluded_list"), default="histogram_matched")
    parser.add_argument("--pool-exclude-top", type=int, default=0)
    parser.add_argument("--pool-exclude-symbols", type=str, default="", help="comma-separated byte values for excluded_list mode")
    parser.add_argument("--friction-rejection-rate", type=float, default=0.0)
    parser.add_argument("--functional-observation", action="store_true")
    parser.add_argument("--save-final-soup", type=Path)
    parser.add_argument("--initial-soup", type=Path)
    parser.add_argument("--epoch-offset", type=int, default=0)
    parser.add_argument("--output-dir", type=Path, default=Path("experiments/phase1_runs"))
    args = parser.parse_args()
    print(
        run_probe(
            population_size=args.population_size,
            epochs=args.epochs,
            seed=args.seed,
            mutation_rate=args.mutation_rate,
            pool_multiplier=args.pool_multiplier,
            callback_interval=args.callback_interval,
            max_steps=args.max_steps,
            pool_mode=args.pool_mode,
            pool_exclude_top=args.pool_exclude_top,
            pool_exclude_symbols=tuple(
                int(value) for value in args.pool_exclude_symbols.split(",") if value.strip()
            ),
            initial_soup=args.initial_soup,
            epoch_offset=args.epoch_offset,
            final_soup=args.save_final_soup,
            friction_rejection_rate=args.friction_rejection_rate,
            functional_observation=args.functional_observation,
            output_dir=args.output_dir,
        )
    )


if __name__ == "__main__":
    main()
