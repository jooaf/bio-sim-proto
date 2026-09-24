"""Separate FR-I002 conserved provenance kernels.

Mechanics copied from phase1_probe blob 3805a0d4987f2c24ba70fe25e9b688a9f40cb137.
Only successful value changes assign labels. Arrays are updated in place, just
like the production API; returned tuples contain the identical mechanics metrics.
Callers supply separate uint8 binary label arrays matching the byte array shape.
No production entry point imports this module.
"""
from __future__ import annotations

from typing import Any
import numba as nb
import numpy as np
from numpy.typing import NDArray
from experiments.paper_probe import JOINT_LENGTH, TAPE_LENGTH, derived_seed, splitmix64

@nb.njit(inline="always")
def provenance_write(
    joint: NDArray[np.uint8],
    labels: NDArray[np.uint8],
    new_label: int,
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
    labels[index] = new_label
    return 1


@nb.njit(inline="always")
def provenance_write_with_friction(
    joint: NDArray[np.uint8],
    labels: NDArray[np.uint8],
    new_label: int,
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
    return provenance_write(
        joint, labels, new_label, index, value, pool, withdrawals, returns, blocked_by_symbol
    )


@nb.njit
def execute_bff_provenance(
    joint: NDArray[np.uint8],
    labels: NDArray[np.uint8],
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
            outcome = provenance_write_with_friction(
                joint,
                labels,
                int(labels[source]) if op == 46 or op == 44 else int(labels[destination]),
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
def mutate_and_execute_provenance_epoch(
    soup: NDArray[np.uint8],
    labels: NDArray[np.uint8],
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
        joint_labels = np.empty(JOINT_LENGTH, dtype=np.uint8)
        joint_labels[:TAPE_LENGTH] = labels[first]
        joint_labels[TAPE_LENGTH:] = labels[second]
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
                outcome = provenance_write_with_friction(
                    joint,
                    joint_labels,
                    0,
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
        result: Any = execute_bff_provenance(  # type: ignore[call-arg]
            joint,
            joint_labels,
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
        labels[first] = joint_labels[:TAPE_LENGTH]
        labels[second] = joint_labels[TAPE_LENGTH:]
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

