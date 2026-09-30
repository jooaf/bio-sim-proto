"""Independent SM-C001 full-buffer reconstruction and fixed-denominator outcomes.

Wire format: ASCII, LF (including final LF), no quoting, canonical decimal,
ALXII order, uppercase fixed-width buffer hex. Artifacts use SHA-256 of raw bytes.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
from math import comb
from pathlib import Path
import re
from typing import Any

from experiments.stringmol.analyze_lineage import (
    EVENT_COLUMNS, SNAPSHOT_COLUMNS, analyze_run as lineage_run, integer, require, rows,
)

ALPHABET = "ABC$DEF%GH^IJK?LMN}OPQ>RST=UVWXYZ"
MAXL0 = 2001
LIMIT = 2**63 - 1
PARTITION = ["boundary_error", "read_null", "deletion_no_write", "final_byte_noop", "accepted_changed", "scarcity_blocked"]
COUNTERS = ["attempts", *PARTITION, "accepted_positive_growth"]
LEDGERS = ["copy_withdrawals", "copy_returns", "decay_returns", "failed_placement_returns", "cleavage_discard_returns", "missing_blocked_units"]
ARRAYS = ["molecular", "pool", "initial", *LEDGERS, "pool_minimum"]


def fields(prefix: str) -> list[str]:
    return [f"{prefix}_{ord(s):02X}" for s in ALPHABET]


COLUMNS = ["tick", "event", *fields("molecular"), *fields("pool"), *fields("initial"), "max_residual", *COUNTERS,
           *(f for p in LEDGERS for f in fields(p)), "molecular_bytes", "free_bytes", *fields("pool_minimum")]
BUFFER_COLUMNS = ["tick", "event", "id", "full_buffer_hex"]


def canonical_rows(path: Path, columns: list[str]) -> list[dict[str, str]]:
    data = rows(path, columns)
    canonical = ",".join(columns) + "\n" + "".join(",".join(r[c] for c in columns) + "\n" for r in data)
    require(path.read_bytes() == canonical.encode("ascii"), "noncanonical CSV bytes")
    return data


def full_buffer(value: str, maxl0: int) -> bytes:
    require(len(value) == 2 * maxl0 and re.fullmatch(r"[0-9A-F]+", value) is not None, "invalid full-buffer hex")
    raw = bytes.fromhex(value)
    require(raw[-1] == 0, "reserved terminator is not NUL")
    require(set(raw) <= set(ALPHABET.encode()) | {0}, "non-ALXII buffer byte")
    return raw


def initial_material(expected: list[dict[str, Any]], mode: str, amount: int, maxl0: int = MAXL0) -> dict[str, Any]:
    require(mode in {"histogram", "uniform"} and 0 <= amount <= LIMIT, "invalid pool parameters")
    buffers = {str(a["id"]): (bytes.fromhex(a["sequence_hex"]) + bytes(maxl0 - len(bytes.fromhex(a["sequence_hex"])))).hex().upper() for a in expected}
    count: Counter[int] = Counter()
    for value in buffers.values():
        count.update(full_buffer(value, maxl0))
    molecular = [count[ord(s)] for s in ALPHABET]
    pool = [n * amount if mode == "histogram" else amount for n in molecular]
    total = [a + b for a, b in zip(molecular, pool, strict=True)]
    require(all(n <= LIMIT for n in [*pool, *total]), "initial inventory overflow")
    return {"maxl0": maxl0, "alphabet": ALPHABET, "buffers": buffers, "molecular": molecular, "pool": pool, "total": total, "mode": mode, "amount": amount}


def analyze_run(directory: Path, expected: list[dict[str, Any]], mode: str, amount: int, *,
                nsteps: int = 5000, exit_status: int = 0, maxl0: int = MAXL0) -> dict[str, Any]:
    lineage = lineage_run(directory, expected, nsteps=nsteps, exit_status=exit_status)
    initial = initial_material(expected, mode, amount, maxl0)
    aggregates = canonical_rows(directory / "conservation001.csv", COLUMNS)
    raw_rows = canonical_rows(directory / "conservation_buffers001.csv", BUFFER_COLUMNS)
    end = lineage["end_timestep"]
    checkpoints = [(t, "CHECKPOINT") for t in range(0, end, 100)] + [(end, "END")]
    require([(integer(r["tick"]), r["event"]) for r in aggregates] == checkpoints, "conservation checkpoint/END set")
    buffers: dict[tuple[int, str], dict[int, bytes]] = defaultdict(dict)
    last_order = (-1, -1)
    order = {k: i for i, k in enumerate(checkpoints)}
    for row in raw_rows:
        key = (integer(row["tick"]), row["event"])
        require(key in order, "unknown buffer checkpoint")
        idx = integer(row["id"])
        pair = (order[key], idx)
        require(pair > last_order, "buffer ID ordering/duplicate")
        last_order = pair
        buffers[key][idx] = full_buffer(row["full_buffer_hex"], maxl0)
    snapshots: dict[int, dict[int, bytes]] = defaultdict(dict)
    for r in rows(directory / "lineage_snapshots001.csv", SNAPSHOT_COLUMNS):
        snapshots[integer(r["tick"])][integer(r["id"])] = bytes.fromhex(r["sequence_hex"])
    events = rows(directory / "lineage_events001.csv", EVENT_COLUMNS)
    introduced = {integer(r["child_id"]): integer(r["timestep"]) for r in events[:-1]}
    previous: dict[str, Any] | None = None
    summaries = []
    dead: set[int] = set()
    previous_ids: set[int] = set()
    for row, key in zip(aggregates, checkpoints, strict=True):
        nums = {k: integer(v, 0, LIMIT) for k, v in row.items() if k not in {"tick", "event"}}
        arrays = {p: [nums[f] for f in fields(p)] for p in ARRAYS}
        actual = buffers[key]
        ids = set(actual)
        require(not ids & dead, "resurrected buffer identity")
        dead.update(previous_ids - ids)
        previous_ids = ids
        require(all(i in introduced and (introduced[i] < key[0] or key[0] == 0) for i in ids), "buffer identity predates introduction")
        visible = {i: b.split(b"\0", 1)[0] for i, b in actual.items()}
        require(all(visible.values()), "extant zero-length molecule")
        if key[1] == "CHECKPOINT":
            require(visible == snapshots[key[0]], "buffer/snapshot IDs or visible prefixes differ")
        else:
            require(len(actual) == lineage["end_population"], "END buffer population mismatch")
            # Patch 0002 exposes END population, not END sequences/IDs. Identity
            # membership and no resurrection are independently checked above.
        count: Counter[int] = Counter()
        for raw in actual.values():
            count.update(raw)
        molecular = [count[ord(s)] for s in ALPHABET]
        require(molecular == arrays["molecular"], "independent molecular reconstruction mismatch")
        require(arrays["initial"] == initial["total"], "initial total mismatch")
        require(all(m + p == t for m, p, t in zip(molecular, arrays["pool"], initial["total"], strict=True)), "nonzero conservation residual")
        require(nums["max_residual"] == 0 and nums["boundary_error"] == 0, "scientific boundary/residual error")
        require(nums["attempts"] == sum(nums[p] for p in PARTITION), "copy partition mismatch")
        require(nums["accepted_positive_growth"] <= nums["accepted_changed"], "growth subset mismatch")
        require(nums["molecular_bytes"] == sum(molecular) and nums["free_bytes"] == sum(arrays["pool"]), "byte totals mismatch")
        for s in range(33):
            reconciled = initial["pool"][s] - arrays["copy_withdrawals"][s] + sum(arrays[p][s] for p in LEDGERS[1:5])
            require(reconciled == arrays["pool"][s], "gross pool reconciliation mismatch")
            minimum = arrays["pool_minimum"][s]
            require(max(0, initial["pool"][s] - arrays["copy_withdrawals"][s]) <= minimum <= min(initial["pool"][s], arrays["pool"][s]), "invalid all-time pool minimum")
        require(nums["scarcity_blocked"] <= sum(arrays["missing_blocked_units"]) <= 2 * nums["scarcity_blocked"], "missing blocked units")
        # Native insertion can round its float draw to 1 and select key[N],
        # the NUL byte. A changing copy can therefore have only returns, and
        # cumulative net copy growth can be zero or negative even after growth.
        # The frozen checks are partition, growth subset, and symbol-wise gross
        # reconciliation above; no withdrawal-per-change/net-growth assumption.
        if previous is None:
            require({str(i): b.hex().upper() for i, b in actual.items()} == initial["buffers"], "initial buffer mismatch")
            require(arrays["pool"] == arrays["pool_minimum"] == initial["pool"], "initial pool/minimum mismatch")
            require(all(nums[k] == 0 for k in COUNTERS) and all(not any(arrays[p]) for p in LEDGERS), "nonzero initial counters")
        else:
            require(all(nums[k] >= previous["nums"][k] for k in COUNTERS), "counter reversal")
            for p in LEDGERS:
                require(all(a >= b for a, b in zip(arrays[p], previous["arrays"][p], strict=True)), "ledger reversal")
            require(all(a <= b for a, b in zip(arrays["pool_minimum"], previous["arrays"]["pool_minimum"], strict=True)), "minimum increased")
            for s in range(33):
                prior = previous["arrays"]
                withdrawals_delta = arrays["copy_withdrawals"][s] - prior["copy_withdrawals"][s]
                lower = min(prior["pool_minimum"][s], max(0, prior["pool"][s] - withdrawals_delta))
                require(arrays["pool_minimum"][s] >= lower, "minimum dropped beyond interval withdrawals")
        previous = {"nums": nums, "arrays": arrays}
        summaries.append({"tick": key[0], "event": key[1], "population": len(actual), **{k: nums[k] for k in COUNTERS},
                          "molecular_bytes": nums["molecular_bytes"], "free_bytes": nums["free_bytes"], **arrays})
    return {**lineage, "zero_residual": True, "conservation": summaries, "end_conservation": summaries[-1]}


def outcomes(results: list[dict[str, Any]], failures: list[dict[str, Any]]) -> dict[str, Any]:
    by_pair = {(r["condition"], r["seed"]): r for r in results}
    joint = [r["seed"] for r in results if r["condition"] == "m16" and r["successful_births"] >= 100 and r["max_two_parent_depth"] >= 2 and r["final_noninitial_descendants"] >= 100 and r["final_descendant_fraction"] >= .5]
    pairs = []
    for seed in range(202621000, 202621010):
        if ("m16", seed) not in by_pair or ("m0", seed) not in by_pair:
            continue
        high, low = by_pair["m16", seed], by_pair["m0", seed]
        pairs.append({"seed": seed, "birth_difference": high["successful_births"] - low["successful_births"],
                      "descendant_difference": high["final_noninitial_descendants"] - low["final_noninitial_descendants"],
                      "scarcity_win": low["end_conservation"]["scarcity_blocked"] > high["end_conservation"]["scarcity_blocked"]})
    birth_wins = sum(p["birth_difference"] > 0 for p in pairs)
    scarcity_wins = sum(p["scarcity_win"] for p in pairs)
    scarcity_all = len(by_pair) == 20 and all(by_pair["m0", s]["end_conservation"]["scarcity_blocked"] > 0 for s in range(202621000, 202621010))
    passed = len(joint) >= 8 and scarcity_all and birth_wins >= 8 and scarcity_wins >= 8
    return {"decision": "unevaluable" if failures or len(by_pair) != 20 else "pass" if passed else "fail", "denominator": 20,
            "joint_m16_seeds": joint, "pairs": pairs, "birth_wins": birth_wins, "scarcity_wins": scarcity_wins,
            "birth_coin_tail": sum(comb(10, k) for k in range(birth_wins, 11)) / 1024,
            "scarcity_coin_tail": sum(comb(10, k) for k in range(scarcity_wins, 11)) / 1024,
            "runs": results, "failures": failures}


def analyze_campaign(manifest: Path) -> dict[str, Any]:
    from experiments.stringmol.conservation_workflow import verify_preparation
    from experiments.stringmol.lineage_workflow import inventory, read, record
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    try:
        data = verify_preparation(manifest)
        require(read(manifest.parent / "campaign.json") == {"input_manifest": record(manifest), "workers": 6}, "campaign input mismatch")
        receipts = read(manifest.parent / "campaign-results.json")
        require(len(receipts) == 20, "incomplete campaign")
    except (ValueError, OSError, KeyError, TypeError, csv.Error) as exc:
        return outcomes([], [{"error": str(exc)}])
    for i, r in enumerate(data["runs"]):
        try:
            directory = Path(r["directory"])
            receipt = read(directory.with_suffix(".inventory.json"))
            require(receipt == receipts[i] and receipt["input_manifest"] == record(manifest), "receipt input mismatch")
            require(receipt["condition"] == r["condition"] and receipt["seed"] == r["seed"], "receipt identity mismatch")
            require(receipt["files"] == inventory(directory), "output inventory mismatch")
            summary = analyze_run(directory, r["expected_initial"], "histogram", r["amount"], exit_status=receipt["exit_status"])
            results.append({"condition": r["condition"], "seed": r["seed"], **summary})
        except (ValueError, OSError, KeyError, TypeError, csv.Error) as exc:
            failures.append({"condition": r["condition"], "seed": r["seed"], "error": str(exc)})
    return outcomes(results, failures)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze_campaign(args.manifest.resolve()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
