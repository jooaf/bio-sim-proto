"""Token-audited Phase 1 BFF probe for explicit pool-mediated matter paths.

Byte values remain the physical state. Token IDs are deterministic bookkeeping
labels for otherwise indistinguishable copies of the same byte value. A LIFO
pool convention reconstructs one valid token history without changing byte-level
execution or availability.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numba as nb
import numpy as np
from numpy.typing import NDArray

from experiments.paper_probe import (
    JOINT_LENGTH,
    TAPE_LENGTH,
    complexity_row,
    derived_seed,
    initialize_soup,
    shuffle_indices,
    splitmix64,
)
from experiments.phase1_probe import jensen_shannon_divergence, pool_entropy


@nb.njit
def record_blocked(
    symbol: int,
    local_counts: NDArray[np.int64],
    touched: NDArray[np.int16],
    n_touched: int,
) -> int:
    if local_counts[symbol] == 0:
        touched[n_touched] = symbol
        n_touched += 1
    local_counts[symbol] += 1
    return n_touched


@nb.njit
def token_write(
    joint: NDArray[np.uint8],
    joint_tokens: NDArray[np.int64],
    destination: int,
    destination_tape: int,
    new_value: int,
    opcode: int,
    source_tape: int,
    interaction_sequence: int,
    epoch: int,
    pair_index: int,
    pool_counts: NDArray[np.int64],
    pool_heads: NDArray[np.int64],
    next_token: NDArray[np.int64],
    token_symbol: NDArray[np.uint8],
    last_return_tape: NDArray[np.int32],
    last_return_sequence: NDArray[np.int64],
    token_returns: NDArray[np.int64],
    token_reacquisitions: NDArray[np.int64],
    flow: NDArray[np.int64],
    event_count: NDArray[np.int64],
    event_sequence: NDArray[np.int64],
    event_epoch: NDArray[np.int64],
    event_pair: NDArray[np.int32],
    event_token: NDArray[np.int64],
    event_symbol: NDArray[np.uint8],
    event_donor: NDArray[np.int32],
    event_receiver: NDArray[np.int32],
    event_residence: NDArray[np.int64],
    event_opcode: NDArray[np.int16],
    event_source: NDArray[np.int32],
    event_overflow: NDArray[np.int64],
    sample_denominator: int,
) -> int:
    """Exchange one labeled token: 0=no-op, 1=changed, 2=blocked."""

    value = new_value & 0xFF
    old_value = int(joint[destination])
    if old_value == value:
        return 0
    new_token = int(pool_heads[value])
    if new_token < 0:
        return 2

    pool_heads[value] = next_token[new_token]
    pool_counts[value] -= 1
    old_token = int(joint_tokens[destination])
    pool_counts[old_value] += 1
    next_token[old_token] = pool_heads[old_value]
    pool_heads[old_value] = old_token

    donor = int(last_return_tape[new_token])
    if donor >= 0:
        flow[donor, destination_tape] += 1
        token_reacquisitions[new_token] += 1
        sampled = int(splitmix64(np.uint64(new_token)) % np.uint64(sample_denominator)) == 0
        if sampled:
            position = int(event_count[0])
            if position < len(event_token):
                event_sequence[position] = interaction_sequence
                event_epoch[position] = epoch
                event_pair[position] = pair_index
                event_token[position] = new_token
                event_symbol[position] = token_symbol[new_token]
                event_donor[position] = donor
                event_receiver[position] = destination_tape
                event_residence[position] = interaction_sequence - last_return_sequence[new_token]
                event_opcode[position] = opcode
                event_source[position] = source_tape
                event_count[0] += 1
            else:
                event_overflow[0] += 1

    last_return_tape[old_token] = destination_tape
    last_return_sequence[old_token] = interaction_sequence
    token_returns[old_token] += 1
    last_return_tape[new_token] = -1
    joint[destination] = value
    joint_tokens[destination] = new_token
    return 1


@nb.njit
def execute_bff_tokenized(
    joint: NDArray[np.uint8],
    joint_tokens: NDArray[np.int64],
    first_tape: int,
    second_tape: int,
    interaction_sequence: int,
    epoch: int,
    pair_index: int,
    max_steps: int,
    pool_counts: NDArray[np.int64],
    pool_heads: NDArray[np.int64],
    next_token: NDArray[np.int64],
    token_symbol: NDArray[np.uint8],
    last_return_tape: NDArray[np.int32],
    last_return_sequence: NDArray[np.int64],
    token_returns: NDArray[np.int64],
    token_reacquisitions: NDArray[np.int64],
    flow: NDArray[np.int64],
    blocked_by_symbol: NDArray[np.int64],
    local_counts: NDArray[np.int64],
    touched: NDArray[np.int16],
    n_touched: int,
    event_count: NDArray[np.int64],
    event_sequence: NDArray[np.int64],
    event_epoch: NDArray[np.int64],
    event_pair: NDArray[np.int32],
    event_token: NDArray[np.int64],
    event_symbol: NDArray[np.uint8],
    event_donor: NDArray[np.int32],
    event_receiver: NDArray[np.int32],
    event_residence: NDArray[np.int64],
    event_opcode: NDArray[np.int16],
    event_source: NDArray[np.int32],
    event_overflow: NDArray[np.int64],
    sample_denominator: int,
) -> tuple[int, int, int, int]:
    pc = 0
    head0 = 0
    head1 = 0
    steps = 0
    successful = 0
    blocked = 0
    while steps < max_steps and 0 <= pc < JOINT_LENGTH:
        op = int(joint[pc])
        steps += 1
        next_pc = pc + 1
        if op == 60:
            head0 = (head0 - 1) & (JOINT_LENGTH - 1)
        elif op == 62:
            head0 = (head0 + 1) & (JOINT_LENGTH - 1)
        elif op == 123:
            head1 = (head1 - 1) & (JOINT_LENGTH - 1)
        elif op == 125:
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
            source_tape = first_tape if source < TAPE_LENGTH else second_tape
            destination_tape = first_tape if destination < TAPE_LENGTH else second_tape
            outcome = token_write(
                joint,
                joint_tokens,
                destination,
                destination_tape,
                new_value,
                op,
                source_tape,
                interaction_sequence,
                epoch,
                pair_index,
                pool_counts,
                pool_heads,
                next_token,
                token_symbol,
                last_return_tape,
                last_return_sequence,
                token_returns,
                token_reacquisitions,
                flow,
                event_count,
                event_sequence,
                event_epoch,
                event_pair,
                event_token,
                event_symbol,
                event_donor,
                event_receiver,
                event_residence,
                event_opcode,
                event_source,
                event_overflow,
                sample_denominator,
            )
            if outcome == 2:
                blocked += 1
                blocked_by_symbol[new_value] += 1
                n_touched = record_blocked(new_value, local_counts, touched, n_touched)
            else:
                successful += 1
        elif op == 91 and joint[head0] == 0:
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
        elif op == 93 and joint[head0] != 0:
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
    return steps, successful, blocked, n_touched


@nb.njit
def run_tokenized_epoch(
    soup: NDArray[np.uint8],
    tape_tokens: NDArray[np.int64],
    order: NDArray[np.uint32],
    seed: int,
    epoch: int,
    mutation_threshold: int,
    max_steps: int,
    pool_counts: NDArray[np.int64],
    pool_heads: NDArray[np.int64],
    next_token: NDArray[np.int64],
    token_symbol: NDArray[np.uint8],
    last_return_tape: NDArray[np.int32],
    last_return_sequence: NDArray[np.int64],
    token_returns: NDArray[np.int64],
    token_reacquisitions: NDArray[np.int64],
    flow: NDArray[np.int64],
    execution_blocked_by_symbol: NDArray[np.int64],
    mutation_blocked_by_symbol: NDArray[np.int64],
    event_count: NDArray[np.int64],
    event_sequence: NDArray[np.int64],
    event_epoch: NDArray[np.int64],
    event_pair: NDArray[np.int32],
    event_token: NDArray[np.int64],
    event_symbol: NDArray[np.uint8],
    event_donor: NDArray[np.int32],
    event_receiver: NDArray[np.int32],
    event_residence: NDArray[np.int64],
    event_opcode: NDArray[np.int16],
    event_source: NDArray[np.int32],
    event_overflow: NDArray[np.int64],
    sample_denominator: int,
) -> tuple[int, int, int, int, int, int, int, int, int, int]:
    population_size = len(soup)
    total_steps = 0
    execution_success = 0
    execution_blocked = 0
    mutation_success = 0
    mutation_blocked = 0
    blocked_interactions = 0
    max_interaction_blocked = 0
    max_interaction_top_symbol = -1
    max_interaction_top_count = 0
    max_interaction_steps = 0
    epoch_seed = derived_seed(np.uint64(seed), np.uint64(epoch))
    local_counts = np.zeros(256, dtype=np.int64)
    touched = np.empty(256, dtype=np.int16)

    for pair_index in range(population_size // 2):
        first = int(order[2 * pair_index])
        second = int(order[2 * pair_index + 1])
        sequence = epoch * (population_size // 2) + pair_index
        joint = np.empty(JOINT_LENGTH, dtype=np.uint8)
        joint_tokens = np.empty(JOINT_LENGTH, dtype=np.int64)
        joint[:TAPE_LENGTH] = soup[first]
        joint[TAPE_LENGTH:] = soup[second]
        joint_tokens[:TAPE_LENGTH] = tape_tokens[first]
        joint_tokens[TAPE_LENGTH:] = tape_tokens[second]
        n_touched = 0

        for byte_index in range(JOINT_LENGTH):
            random_value = splitmix64(
                (np.uint64(population_size) * epoch_seed + np.uint64(pair_index))
                * np.uint64(JOINT_LENGTH)
                + np.uint64(byte_index)
            )
            probability_draw = (random_value >> np.uint64(8)) & np.uint64((1 << 30) - 1)
            if probability_draw < np.uint64(mutation_threshold):
                destination_tape = first if byte_index < TAPE_LENGTH else second
                new_value = int(random_value & np.uint64(0xFF))
                outcome = token_write(
                    joint,
                    joint_tokens,
                    byte_index,
                    destination_tape,
                    new_value,
                    -1,
                    -1,
                    sequence,
                    epoch,
                    pair_index,
                    pool_counts,
                    pool_heads,
                    next_token,
                    token_symbol,
                    last_return_tape,
                    last_return_sequence,
                    token_returns,
                    token_reacquisitions,
                    flow,
                    event_count,
                    event_sequence,
                    event_epoch,
                    event_pair,
                    event_token,
                    event_symbol,
                    event_donor,
                    event_receiver,
                    event_residence,
                    event_opcode,
                    event_source,
                    event_overflow,
                    sample_denominator,
                )
                if outcome == 2:
                    mutation_blocked += 1
                    mutation_blocked_by_symbol[new_value] += 1
                    n_touched = record_blocked(new_value, local_counts, touched, n_touched)
                else:
                    mutation_success += 1

        result = execute_bff_tokenized(
            joint,
            joint_tokens,
            first,
            second,
            sequence,
            epoch,
            pair_index,
            max_steps,
            pool_counts,
            pool_heads,
            next_token,
            token_symbol,
            last_return_tape,
            last_return_sequence,
            token_returns,
            token_reacquisitions,
            flow,
            execution_blocked_by_symbol,
            local_counts,
            touched,
            n_touched,
            event_count,
            event_sequence,
            event_epoch,
            event_pair,
            event_token,
            event_symbol,
            event_donor,
            event_receiver,
            event_residence,
            event_opcode,
            event_source,
            event_overflow,
            sample_denominator,
        )
        steps, successful, blocked, n_touched = result
        total_steps += steps
        execution_success += successful
        execution_blocked += blocked
        interaction_blocked = 0
        top_symbol = -1
        top_count = 0
        for touched_index in range(n_touched):
            symbol = int(touched[touched_index])
            count = int(local_counts[symbol])
            interaction_blocked += count
            if count > top_count:
                top_count = count
                top_symbol = symbol
            local_counts[symbol] = 0
        if interaction_blocked > 0:
            blocked_interactions += 1
        if interaction_blocked > max_interaction_blocked:
            max_interaction_blocked = interaction_blocked
            max_interaction_top_symbol = top_symbol
            max_interaction_top_count = top_count
            max_interaction_steps = steps
        soup[first] = joint[:TAPE_LENGTH]
        soup[second] = joint[TAPE_LENGTH:]
        tape_tokens[first] = joint_tokens[:TAPE_LENGTH]
        tape_tokens[second] = joint_tokens[TAPE_LENGTH:]

    return (
        total_steps,
        execution_success,
        execution_blocked,
        mutation_success,
        mutation_blocked,
        blocked_interactions,
        max_interaction_blocked,
        max_interaction_top_symbol,
        max_interaction_top_count,
        max_interaction_steps,
    )


def initialize_tokens(
    soup: NDArray[np.uint8], pool_counts: NDArray[np.int64]
) -> tuple[NDArray[np.int64], NDArray[np.uint8], NDArray[np.int64], NDArray[np.int64]]:
    tape_token_count = soup.size
    total_tokens = tape_token_count + int(pool_counts.sum())
    tape_tokens = np.arange(tape_token_count, dtype=np.int64).reshape(soup.shape)
    token_symbol = np.empty(total_tokens, dtype=np.uint8)
    token_symbol[:tape_token_count] = soup.ravel()
    pool_heads = np.full(256, -1, dtype=np.int64)
    next_token = np.full(total_tokens, -1, dtype=np.int64)
    cursor = tape_token_count
    for symbol in range(256):
        for _ in range(int(pool_counts[symbol])):
            token_symbol[cursor] = symbol
            next_token[cursor] = pool_heads[symbol]
            pool_heads[symbol] = cursor
            cursor += 1
    return tape_tokens, token_symbol, pool_heads, next_token


def validate_token_state(
    soup: NDArray[np.uint8],
    tape_tokens: NDArray[np.int64],
    pool_counts: NDArray[np.int64],
    pool_heads: NDArray[np.int64],
    next_token: NDArray[np.int64],
    token_symbol: NDArray[np.uint8],
    conserved_totals: NDArray[np.int64],
) -> None:
    if not np.array_equal(token_symbol[tape_tokens.ravel()], soup.ravel()):
        raise RuntimeError("tape token symbols do not match tape bytes")
    seen = np.zeros(len(token_symbol), dtype=np.uint8)
    seen[tape_tokens.ravel()] += 1
    stack_counts = np.zeros(256, dtype=np.int64)
    for symbol in range(256):
        token = int(pool_heads[symbol])
        while token >= 0:
            if int(token_symbol[token]) != symbol:
                raise RuntimeError("pool token is on the wrong symbol stack")
            seen[token] += 1
            stack_counts[symbol] += 1
            token = int(next_token[token])
    if not np.array_equal(stack_counts, pool_counts):
        raise RuntimeError("pool token stacks disagree with pool counts")
    if not bool(np.all(seen == 1)):
        raise RuntimeError("a token is missing or appears more than once")
    tape_counts = np.bincount(soup.ravel(), minlength=256).astype(np.int64)
    if not np.array_equal(tape_counts + pool_counts, conserved_totals):
        raise RuntimeError("per-symbol conservation failed")


def git_commit() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], check=False, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def write_manifest(path: Path, values: dict[str, Any]) -> None:
    path.write_text(json.dumps(values, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_trace(
    *,
    population_size: int,
    epochs: int,
    seed: int,
    mutation_rate: float,
    pool_multiplier: float,
    callback_interval: int,
    output_dir: Path,
    sample_denominator: int = 64,
    max_events: int = 250_000,
    max_steps: int = 8192,
    flow_window: int = 2000,
) -> Path:
    if population_size <= 0 or population_size % 2:
        raise ValueError("population_size must be a positive even number")
    if epochs <= 0 or callback_interval <= 0 or max_steps <= 0:
        raise ValueError("epochs, callback_interval, and max_steps must be positive")
    if not 0.0 <= mutation_rate <= 1.0:
        raise ValueError("mutation_rate must be in 0..1")
    if pool_multiplier <= 0.0 or not math.isfinite(pool_multiplier):
        raise ValueError("pool_multiplier must be finite and positive")
    if sample_denominator <= 0 or max_events <= 0:
        raise ValueError("sample_denominator and max_events must be positive")
    if flow_window <= 0:
        raise ValueError("flow_window must be positive")

    multiplier_slug = format(pool_multiplier, ".8g").replace(".", "p")
    run_dir = output_dir / f"trace_m{multiplier_slug}_n{population_size}_s{seed}"
    run_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "phase": 1,
        "probe": "token_metabolic_trace",
        "population_size": population_size,
        "epochs": epochs,
        "seed": seed,
        "mutation_rate": mutation_rate,
        "pool_multiplier": pool_multiplier,
        "callback_interval": callback_interval,
        "sample_denominator": sample_denominator,
        "max_events": max_events,
        "max_steps": max_steps,
        "token_pool_order": "symbol_local_lifo",
        "flow_window": flow_window,
    }
    manifest_path = run_dir / "manifest.json"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("exit_status") == "success" and existing.get("config") == config:
            return run_dir
    manifest: dict[str, Any] = {
        "run_id": run_dir.name,
        "status": "running",
        "exit_status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "config": config,
    }
    write_manifest(manifest_path, manifest)
    (run_dir / "config.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    started = time.perf_counter()
    try:
        soup = initialize_soup(population_size, seed)
        initial_tape_counts = np.bincount(soup.ravel(), minlength=256).astype(np.int64)
        initial_pool = np.rint(initial_tape_counts.astype(np.float64) * pool_multiplier).astype(np.int64)
        pool_counts = initial_pool.copy()
        conserved_totals = initial_tape_counts + initial_pool
        tape_tokens, token_symbol, pool_heads, next_token = initialize_tokens(soup, pool_counts)
        token_returns = np.zeros(len(token_symbol), dtype=np.int64)
        token_reacquisitions = np.zeros(len(token_symbol), dtype=np.int64)
        last_return_tape = np.full(len(token_symbol), -1, dtype=np.int32)
        last_return_sequence = np.full(len(token_symbol), -1, dtype=np.int64)
        flow = np.zeros((population_size, population_size), dtype=np.int64)
        previous_flow = np.zeros((population_size, population_size), dtype=np.int64)
        execution_blocked_by_symbol = np.zeros(256, dtype=np.int64)
        mutation_blocked_by_symbol = np.zeros(256, dtype=np.int64)
        order = np.arange(population_size, dtype=np.uint32)
        mutation_threshold = round(mutation_rate * (1 << 30))

        event_count = np.zeros(1, dtype=np.int64)
        event_overflow = np.zeros(1, dtype=np.int64)
        event_sequence = np.empty(max_events, dtype=np.int64)
        event_epoch = np.empty(max_events, dtype=np.int64)
        event_pair = np.empty(max_events, dtype=np.int32)
        event_token = np.empty(max_events, dtype=np.int64)
        event_symbol = np.empty(max_events, dtype=np.uint8)
        event_donor = np.empty(max_events, dtype=np.int32)
        event_receiver = np.empty(max_events, dtype=np.int32)
        event_residence = np.empty(max_events, dtype=np.int64)
        event_opcode = np.empty(max_events, dtype=np.int16)
        event_source = np.empty(max_events, dtype=np.int32)

        epoch_fields = [
            "epoch", "character_reads", "execution_writes_success", "execution_writes_blocked",
            "mutation_writes_success", "mutation_writes_blocked", "blocked_interactions",
            "epoch_blocked_total", "max_interaction_blocked", "max_interaction_fraction_of_epoch_blocking",
            "max_interaction_top_symbol", "max_interaction_top_symbol_share", "max_interaction_steps",
            "pool_entropy", "zero_pool_symbols", "cumulative_reacquisitions", "cumulative_cross_tape_reacquisitions",
        ]
        aggregate_fields = [
            "epoch", "elapsed_seconds", "character_reads", "byte_entropy", "brotli_size", "compressed_bpb",
            "high_order_entropy", "pool_total", "pool_entropy", "pool_jsd_from_initial", "zero_pool_symbols",
            "max_conservation_residual", "token_validation_passed", "cumulative_returns",
            "cumulative_reacquisitions", "cumulative_cross_tape_reacquisitions", "flow_edges",
        ]
        cumulative_steps = 0
        epochs_path = run_dir / "epochs.csv"
        aggregate_path = run_dir / "aggregate.csv"
        flow_windows_path = run_dir / "flow_edges_windows.csv"
        with (
            epochs_path.open("w", newline="", encoding="utf-8") as epochs_handle,
            aggregate_path.open("w", newline="", encoding="utf-8") as aggregate_handle,
            flow_windows_path.open("w", newline="", encoding="utf-8") as flow_windows_handle,
        ):
            epoch_writer = csv.DictWriter(epochs_handle, fieldnames=epoch_fields)
            aggregate_writer = csv.DictWriter(aggregate_handle, fieldnames=aggregate_fields)
            flow_window_writer = csv.DictWriter(
                flow_windows_handle,
                fieldnames=["window", "start_epoch", "end_epoch", "donor_tape", "receiver_tape", "token_transfers"],
            )
            epoch_writer.writeheader()
            aggregate_writer.writeheader()
            flow_window_writer.writeheader()
            for epoch in range(epochs):
                shuffle_indices(order, seed, epoch)
                result = run_tokenized_epoch(
                    soup,
                    tape_tokens,
                    order,
                    seed,
                    epoch,
                    mutation_threshold,
                    max_steps,
                    pool_counts,
                    pool_heads,
                    next_token,
                    token_symbol,
                    last_return_tape,
                    last_return_sequence,
                    token_returns,
                    token_reacquisitions,
                    flow,
                    execution_blocked_by_symbol,
                    mutation_blocked_by_symbol,
                    event_count,
                    event_sequence,
                    event_epoch,
                    event_pair,
                    event_token,
                    event_symbol,
                    event_donor,
                    event_receiver,
                    event_residence,
                    event_opcode,
                    event_source,
                    event_overflow,
                    sample_denominator,
                )
                cumulative_steps += result[0]
                epoch_blocked = result[2] + result[4]
                if (epoch + 1) % flow_window == 0 or epoch + 1 == epochs:
                    window_flow = flow - previous_flow
                    donors, receivers = np.nonzero(window_flow)
                    for donor, receiver in zip(donors, receivers, strict=True):
                        flow_window_writer.writerow(
                            {
                                "window": epoch // flow_window,
                                "start_epoch": epoch - (epoch % flow_window) + 1,
                                "end_epoch": epoch + 1,
                                "donor_tape": int(donor),
                                "receiver_tape": int(receiver),
                                "token_transfers": int(window_flow[donor, receiver]),
                            }
                        )
                    flow_windows_handle.flush()
                    previous_flow = flow.copy()
                cross_reacquisitions = int(flow.sum() - np.trace(flow))
                epoch_writer.writerow(
                    {
                        "epoch": epoch + 1,
                        "character_reads": result[0],
                        "execution_writes_success": result[1],
                        "execution_writes_blocked": result[2],
                        "mutation_writes_success": result[3],
                        "mutation_writes_blocked": result[4],
                        "blocked_interactions": result[5],
                        "epoch_blocked_total": epoch_blocked,
                        "max_interaction_blocked": result[6],
                        "max_interaction_fraction_of_epoch_blocking": 0.0 if epoch_blocked == 0 else result[6] / epoch_blocked,
                        "max_interaction_top_symbol": result[7],
                        "max_interaction_top_symbol_share": 0.0 if result[6] == 0 else result[8] / result[6],
                        "max_interaction_steps": result[9],
                        "pool_entropy": pool_entropy(pool_counts),
                        "zero_pool_symbols": int(np.count_nonzero(pool_counts == 0)),
                        "cumulative_reacquisitions": int(token_reacquisitions.sum()),
                        "cumulative_cross_tape_reacquisitions": cross_reacquisitions,
                    }
                )
                if epoch % callback_interval != 0 and epoch + 1 != epochs:
                    continue
                validate_token_state(
                    soup,
                    tape_tokens,
                    pool_counts,
                    pool_heads,
                    next_token,
                    token_symbol,
                    conserved_totals,
                )
                tape_counts = np.bincount(soup.ravel(), minlength=256).astype(np.int64)
                residual = int(np.max(np.abs(tape_counts + pool_counts - conserved_totals)))
                complexity = complexity_row(soup, epoch + 1, time.perf_counter() - started, cumulative_steps)
                aggregate_writer.writerow(
                    {
                        **complexity,
                        "pool_total": int(pool_counts.sum()),
                        "pool_entropy": pool_entropy(pool_counts),
                        "pool_jsd_from_initial": jensen_shannon_divergence(initial_pool, pool_counts),
                        "zero_pool_symbols": int(np.count_nonzero(pool_counts == 0)),
                        "max_conservation_residual": residual,
                        "token_validation_passed": True,
                        "cumulative_returns": int(token_returns.sum()),
                        "cumulative_reacquisitions": int(token_reacquisitions.sum()),
                        "cumulative_cross_tape_reacquisitions": cross_reacquisitions,
                        "flow_edges": int(np.count_nonzero(flow)),
                    }
                )
                epochs_handle.flush()
                aggregate_handle.flush()

        flow_path = run_dir / "flow_edges.csv"
        with flow_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["donor_tape", "receiver_tape", "token_transfers"])
            writer.writeheader()
            donors, receivers = np.nonzero(flow)
            for donor, receiver in zip(donors, receivers, strict=True):
                writer.writerow(
                    {
                        "donor_tape": int(donor),
                        "receiver_tape": int(receiver),
                        "token_transfers": int(flow[donor, receiver]),
                    }
                )

        token_path = run_dir / "token_summary.csv"
        with token_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["token_id", "symbol", "returns", "reacquisitions"])
            writer.writeheader()
            active = np.flatnonzero((token_returns > 0) | (token_reacquisitions > 0))
            for token in active:
                writer.writerow(
                    {
                        "token_id": int(token),
                        "symbol": int(token_symbol[token]),
                        "returns": int(token_returns[token]),
                        "reacquisitions": int(token_reacquisitions[token]),
                    }
                )

        events_path = run_dir / "sampled_token_events.csv"
        with events_path.open("w", newline="", encoding="utf-8") as handle:
            fields = [
                "interaction_sequence", "epoch", "pair_index", "token_id", "symbol", "donor_tape",
                "receiver_tape", "pool_residence_interactions", "opcode", "template_source_tape",
            ]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for index in range(int(event_count[0])):
                writer.writerow(
                    {
                        "interaction_sequence": int(event_sequence[index]),
                        "epoch": int(event_epoch[index]) + 1,
                        "pair_index": int(event_pair[index]),
                        "token_id": int(event_token[index]),
                        "symbol": int(event_symbol[index]),
                        "donor_tape": int(event_donor[index]),
                        "receiver_tape": int(event_receiver[index]),
                        "pool_residence_interactions": int(event_residence[index]),
                        "opcode": int(event_opcode[index]),
                        "template_source_tape": int(event_source[index]),
                    }
                )

        blocked_path = run_dir / "blocked_symbols.csv"
        with blocked_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["symbol", "execution_blocked", "mutation_blocked"])
            writer.writeheader()
            for symbol in range(256):
                writer.writerow(
                    {
                        "symbol": symbol,
                        "execution_blocked": int(execution_blocked_by_symbol[symbol]),
                        "mutation_blocked": int(mutation_blocked_by_symbol[symbol]),
                    }
                )

        validate_token_state(
            soup,
            tape_tokens,
            pool_counts,
            pool_heads,
            next_token,
            token_symbol,
            conserved_totals,
        )
        manifest.update(
            {
                "status": "success",
                "exit_status": "success",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "wall_time_s": time.perf_counter() - started,
                "max_conservation_residual": 0,
                "token_validation_passed": True,
                "sampled_events": int(event_count[0]),
                "event_overflow": int(event_overflow[0]),
                "total_returns": int(token_returns.sum()),
                "total_reacquisitions": int(token_reacquisitions.sum()),
                "cross_tape_reacquisitions": int(flow.sum() - np.trace(flow)),
                "flow_edges": int(np.count_nonzero(flow)),
                "artifacts": [
                    epochs_path.name,
                    aggregate_path.name,
                    flow_path.name,
                    flow_windows_path.name,
                    token_path.name,
                    events_path.name,
                    blocked_path.name,
                ],
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
    parser.add_argument("--sample-denominator", type=int, default=64)
    parser.add_argument("--max-events", type=int, default=250_000)
    parser.add_argument("--max-steps", type=int, default=8192)
    parser.add_argument("--flow-window", type=int, default=2000)
    parser.add_argument("--output-dir", type=Path, default=Path("experiments/phase1_runs/metabolic_trace"))
    args = parser.parse_args()
    print(
        run_trace(
            population_size=args.population_size,
            epochs=args.epochs,
            seed=args.seed,
            mutation_rate=args.mutation_rate,
            pool_multiplier=args.pool_multiplier,
            callback_interval=args.callback_interval,
            output_dir=args.output_dir,
            sample_denominator=args.sample_denominator,
            max_events=args.max_events,
            max_steps=args.max_steps,
            flow_window=args.flow_window,
        )
    )


if __name__ == "__main__":
    main()
