"""FR-I001 observational value-change provenance; no conserved-kernel semantics."""
from __future__ import annotations

from typing import Callable, cast

import numpy as np
from numpy.typing import NDArray

from experiments.paper_probe import execute_bff, functional_selfrep_score
from experiments.analyze_ac_p003_functional_origin_convergence import splitmix64

U8 = NDArray[np.uint8]
execute_reference = cast(Callable[[U8, int], int], execute_bff)
score_reference = cast(Callable[[U8, int], int], functional_selfrep_score)


def execute_provenance(joint: U8, labels: U8, max_steps: int) -> int:
    """Modify bytes and binary labels in place, returning character reads."""
    if any(a.dtype != np.uint8 or a.shape != (128,) for a in (joint, labels)):
        raise ValueError("expected uint8 joint tape and labels of length 128")
    if np.any(labels > 1) or np.shares_memory(joint, labels) or max_steps < 0:
        raise ValueError("invalid labels, aliasing, or budget")
    pc = h0 = h1 = steps = 0
    while steps < max_steps and 0 <= pc < 128:
        op = int(joint[pc])
        steps += 1
        next_pc = pc + 1
        if op == 60:
            h0 = (h0 - 1) & 127
        elif op == 62:
            h0 = (h0 + 1) & 127
        elif op == 123:
            h1 = (h1 - 1) & 127
        elif op == 125:
            h1 = (h1 + 1) & 127
        elif op == 43:
            joint[h0] = (int(joint[h0]) + 1) & 255
        elif op == 45:
            joint[h0] = (int(joint[h0]) - 1) & 255
        elif op in (46, 44):
            src, dst = (h0, h1) if op == 46 else (h1, h0)
            if joint[dst] != joint[src]:
                joint[dst] = joint[src]
                labels[dst] = labels[src]
        elif op == 91 and joint[h0] == 0:
            depth, candidate = 1, pc + 1
            while candidate < 128 and depth:
                if joint[candidate] == 91:
                    depth += 1
                elif joint[candidate] == 93:
                    depth -= 1
                candidate += 1
            if depth:
                break
            next_pc = candidate
        elif op == 93 and joint[h0] != 0:
            depth, candidate = 1, pc - 1
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
    return steps


def transfer(joint: U8, labels: U8, noise: U8) -> None:
    joint[:64] = joint[64:]
    labels[:64] = labels[64:]
    joint[64:] = noise
    labels[64:] = 0


def trial_noise(witness: int, trial: int) -> U8:
    if not 0 <= witness < 10 or not 0 <= trial < 13:
        raise ValueError("invalid witness or trial index")
    local = splitmix64(0xAC007000 + witness)
    return np.array([splitmix64(local ^ splitmix64((trial + 1) * 64 + b)) & 255
                     for b in range(64)], dtype=np.uint8)


def random_parent(witness: int) -> U8:
    if not 0 <= witness < 10:
        raise ValueError("invalid witness index")
    return np.array([splitmix64(0xAC007100 ^ splitmix64(witness * 64 + b)) & 255
                     for b in range(64)], dtype=np.uint8)


def propagate(parent: U8, noise: U8) -> tuple[U8, U8]:
    if any(a.dtype != np.uint8 or a.shape != (64,) for a in (parent, noise)):
        raise ValueError("expected uint8 parent and noise tapes of length 64")
    joint = np.concatenate((parent, noise))
    labels = np.concatenate((np.ones(64, dtype=np.uint8), np.zeros(64, dtype=np.uint8)))
    execute_provenance(joint, labels, 8192)
    for _ in range(4):
        transfer(joint, labels, noise)
        execute_provenance(joint, labels, 8192)
    return joint.reshape(2, 64), labels.reshape(2, 64)


def fixture_tape(code: bytes) -> U8:
    tape = np.zeros(128, dtype=np.uint8)
    tape[:len(code)] = np.frombuffer(code, dtype=np.uint8)
    return tape


def parity_gate() -> dict[str, int]:
    """Fail immediately on byte/step or independently specified label mismatch."""
    budgets = (1, 2, 16, 128, 1024, 8192)
    def compare(tape: U8, budget: int) -> None:
        expected, observed = tape.copy(), tape.copy()
        labels = np.arange(128, dtype=np.uint8) % 2
        a = execute_reference(expected, budget)
        b = execute_provenance(observed, labels, budget)
        if a != b or not np.array_equal(expected, observed):
            raise ValueError("FR-I001 byte/step parity defect")
    for case in range(1000):
        tape = np.array([splitmix64(0xAC007200 ^ splitmix64(case * 128 + b)) & 255
                         for b in range(128)], dtype=np.uint8)
        compare(tape, budgets[case % len(budgets)])
    codes = (b'}.', b'},', b'<+', b'<-', b'<>{}.', b'<[[]]', b'<[', b']',
             b'<+[[-]+]', b'+[.-]', b'}.,', b'><', b'<' * 128, b'{' * 128)
    for code in codes:
        for budget in budgets:
            tape = fixture_tape(code)
            if code == b'<+':
                tape[127] = 255
            compare(tape, budget)
    # Opposing labels in both directions, both changed and equal values.
    label_cases = 0
    for code, src, dst in ((b'}.', 0, 1), (b'},', 1, 0)):
        for equal in (False, True):
            for source_label in (0, 1):
                tape = fixture_tape(code)
                if equal:
                    # Heads point to data at the end, leaving instructions intact.
                    tape = fixture_tape(b'<' + b'{' * 2 + code[-1:])
                    src, dst = (127, 126) if code[-1:] == b'.' else (126, 127)
                    tape[src] = tape[dst] = 7
                else:
                    src, dst = (0, 1) if code[-1:] == b'.' else (1, 0)
                labels = np.zeros(128, dtype=np.uint8)
                labels[src], labels[dst] = source_label, 1 - source_label
                expected = labels.copy()
                expected[dst] = 1 - source_label if equal else source_label
                execute_provenance(tape, labels, 4 if equal else 2)
                if not np.array_equal(labels, expected):
                    raise ValueError("FR-I001 copy label defect")
                label_cases += 1
    for op, initial, final in ((b'+', 255, 0), (b'-', 0, 255)):
        for label in (0, 1):
            tape = fixture_tape(b'<' + op)
            tape[127] = initial
            labels = np.zeros(128, dtype=np.uint8)
            labels[127] = label
            expected = labels.copy()
            execute_provenance(tape, labels, 2)
            if tape[127] != final or not np.array_equal(labels, expected):
                raise ValueError("FR-I001 arithmetic label defect")
            label_cases += 1
    joint = np.arange(128, dtype=np.uint8)
    labels = joint % 2
    right, inherited = joint[64:].copy(), labels[64:].copy()
    noise = trial_noise(0, 0)
    transfer(joint, labels, noise)
    if not (np.array_equal(joint[:64], right) and np.array_equal(labels[:64], inherited)
            and np.array_equal(joint[64:], noise) and not labels[64:].any()):
        raise ValueError("FR-I001 serial transfer defect")
    return {"random_cases": 1000, "directed_cases": len(codes) * len(budgets),
            "label_cases": label_cases + 1}
