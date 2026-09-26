"""Fail-closed individual DAG and artifact analysis for frozen SM-L001."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
from typing import Any

EVENT_COLUMNS = "event,timestep,population,child_id,active_id,passive_id,child_species,active_species,passive_species,child_label,active_label,passive_label,x,y,child_sequence_hex,active_sequence_hex,passive_sequence_hex".split(",")
SNAPSHOT_COLUMNS = "tick,id,species,label,x,y,sequence_hex".split(",")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def integer(value: str, low: int = 0, high: int = 2**31 - 1) -> int:
    require(re.fullmatch(r"0|-?[1-9][0-9]*", value) is not None, "noncanonical integer")
    number = int(value)
    require(low <= number <= high, "integer out of bounds")
    return number


def sequence(value: str, empty: bool = False) -> bytes:
    require(re.fullmatch(r"(?:[0-9A-F]{2})*", value) is not None, "noncanonical hex")
    raw = bytes.fromhex(value)
    require((bool(raw) or empty) and b"\0" not in raw, "invalid C string bytes")
    return raw


def rows(path: Path, columns: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="ascii") as f:
        reader = csv.reader(f, strict=True)
        require(next(reader, None) == columns, "wrong CSV header")
        result = []
        for row in reader:
            require(len(row) == len(columns), "wrong CSV width")
            result.append(dict(zip(columns, row, strict=True)))
        return result


def agent(row: dict[str, str], prefix: str = "") -> dict[str, Any]:
    return {
        "id": integer(row[prefix + "id"]),
        "species": integer(row[prefix + "species"], 1),
        "label": integer(row[prefix + "label"], 0, 255),
        "x": integer(row["x"], 0, 39),
        "y": integer(row["y"], 0, 39),
        "sequence_hex": sequence(row[prefix + "sequence_hex"]).hex().upper(),
    }


def analyze_run(directory: Path, expected: list[dict[str, Any]], *, nsteps: int = 5000, exit_status: int = 0) -> dict[str, Any]:
    from experiments.stringmol.lineage_workflow import loader_ok
    require(exit_status == 0, "unsuccessful simulator exit")
    require(loader_ok(directory), "loader fallback warning")
    require((directory / "stdout.txt").read_bytes().count(b"FINISHED smspatial\n") == 1, "missing normal simulator exit")
    events = rows(directory / "lineage_events001.csv", EVENT_COLUMNS)
    snapshots = rows(directory / "lineage_snapshots001.csv", SNAPSHOT_COLUMNS)
    require(bool(events) and events[-1]["event"] == "END", "END must be last")
    require(sum(r["event"] == "END" for r in events) == 1, "exactly one END required")
    end = events[-1]
    end_tick = integer(end["timestep"], 1, nsteps)
    end_population = integer(end["population"], 0, 1600)
    require(end_tick == nsteps or end_population == 0, "early nonextinct exit")
    for key in EVENT_COLUMNS[3:14]:
        require(end[key] == "-1", "END identity sentinel")
    for key in EVENT_COLUMNS[14:]:
        require(end[key] == "", "END sequence sentinel")

    initial: dict[int, dict[str, Any]] = {}
    labels: dict[int, int] = {}
    born: dict[int, int] = {}
    depth: dict[int, int] = {}
    passive_depth: dict[int, int] = {}
    active_ids: set[int] = set()
    passive_ids: set[int] = set()
    matches = 0
    comparisons = []
    last_tick = 0
    last_child = -1
    saw_birth = False
    for row in events[:-1]:
        event = row["event"]
        require(event in {"INIT", "BIRTH"}, "unknown event")
        tick = integer(row["timestep"], 0, end_tick - 1)
        require(tick >= last_tick, "event time reversal")
        last_tick = tick
        require(row["population"] == "-1", "event population sentinel")
        child = agent(row, "child_")
        idx = child["id"]
        require(idx not in depth, "individual ID reuse")
        if event == "INIT":
            require(not saw_birth and tick == 0, "late INIT")
            for prefix in ("active_", "passive_"):
                for key in ("id", "species", "label"):
                    require(row[prefix + key] == "-1", "INIT parent sentinel")
                require(row[prefix + "sequence_hex"] == "", "INIT parent sequence")
            initial[idx] = child
            depth[idx] = passive_depth[idx] = 0
            last_child = max(last_child, idx)
        else:
            saw_birth = True
            require(idx > last_child, "individual allocation ordering wrap")
            last_child = idx
            active = integer(row["active_id"])
            passive = integer(row["passive_id"])
            require(active in depth and passive in depth, "parent not previously introduced")
            require(active != passive and idx > active and idx > passive, "invalid causal DAG edges")
            for prefix, parent in (("active_", active), ("passive_", passive)):
                integer(row[prefix + "species"], 1)
                require(integer(row[prefix + "label"], 0, 255) == labels[parent], "event parent label differs from introduction")
                sequence(row[prefix + "sequence_hex"])
            require(row["child_label"] == row["passive_label"], "passive label inheritance mismatch")
            depth[idx] = 1 + max(depth[active], depth[passive])
            passive_depth[idx] = 1 + passive_depth[passive]
            born[idx] = tick
            active_ids.add(active)
            passive_ids.add(passive)
            match = row["child_sequence_hex"] == row["passive_sequence_hex"]
            matches += match
            comparisons.append({"child_id": idx, "passive_id": passive, "match": match, **{prefix + "sha256": hashlib.sha256(sequence(row[prefix + "sequence_hex"])).hexdigest() for prefix in ("child_", "active_", "passive_")}})
        labels[idx] = child["label"]
    require(len(expected) == 140 and len({r["id"] for r in expected}) == 140, "expected inoculum invalid")
    require(initial == {r["id"]: r for r in expected}, "INIT inoculum mismatch")
    require(end_population <= len(labels), "END population exceeds total introduced identities")

    by_tick: dict[int, list[dict[str, Any]]] = defaultdict(list)
    last_pair = (-1, -1)
    for row in snapshots:
        tick = integer(row["tick"], 0, end_tick - 1)
        item = agent(row)
        idx = item["id"]
        require((tick, idx) > last_pair, "snapshot order or duplicate ID")
        last_pair = (tick, idx)
        require(idx in depth, "snapshot contains unknown identity")
        require(item["label"] == labels[idx], "snapshot label differs from introduction")
        require(idx in initial or born[idx] < tick, "snapshot predates birth")
        by_tick[tick].append(item)
    expected_ticks = set(range(0, end_tick if end_population == 0 else nsteps, 100))
    require(set(by_tick) == expected_ticks, "incomplete snapshot checkpoint set")
    require({r["id"]: r for r in by_tick[0]} == initial, "tick zero mismatch")
    counts: dict[int, Counter[int]] = {}
    for tick, items in by_tick.items():
        require(len({(r["x"], r["y"]) for r in items}) == len(items), "duplicate occupied cell")
        counts[tick] = Counter(r["species"] for r in items)

    population: dict[int, Counter[int]] = defaultdict(Counter)
    with (directory / "popdy001.dat").open(newline="", encoding="ascii") as f:
        for row_values in csv.reader(f):
            require(len(row_values) == 3, "invalid population row")
            tick, species, count = [integer(v.strip()) for v in row_values]
            require(species > 0 and count > 0 and species not in population[tick], "invalid population species count")
            population[tick][species] = count
    require(dict(population) == counts, "snapshot/population total or species mismatch")
    last_snapshot_tick = max(by_tick)
    # Snapshots precede tick execution, so births on that tick are also later.
    end_population_bound = len(by_tick[last_snapshot_tick]) + sum(tick >= last_snapshot_tick for tick in born.values())
    require(end_population <= end_population_bound, "END population exceeds last snapshot plus subsequent births")
    # An observed final checkpoint wins even if END proves later extinction.
    endpoint = nsteps - 100
    if endpoint in by_tick:
        final = by_tick[endpoint]
        final_population = len(final)
        descendants = sum(r["id"] not in initial for r in final)
    else:
        require(end_population == 0 and end_tick <= endpoint, "missing endpoint without verified early extinction")
        final_population = descendants = 0
    births = len(born)
    return {"successful_births": births, "unique_active_parents": len(active_ids), "unique_passive_parents": len(passive_ids), "passive_sequence_matches": matches, "passive_sequence_mismatches": births - matches, "passive_sequence_match_fraction": matches / births if births else None, "max_two_parent_depth": max(depth.values()), "max_passive_depth": max(passive_depth.values()), "final_population": final_population, "final_noninitial_descendants": descendants, "final_descendant_fraction": descendants / final_population if final_population else 0.0, "end_timestep": end_tick, "end_population": end_population, "sequence_comparisons": comparisons}


def analyze_campaign(manifest: Path) -> dict[str, Any]:
    from experiments.stringmol.lineage_workflow import inventory, read, record, verify_preparation
    results = []
    failures = []
    try:
        data = verify_preparation(manifest)
        require(read(manifest.parent / "campaign.json") == {"input_manifest": record(manifest), "workers": 6}, "campaign input mismatch")
        receipts = read(manifest.parent / "campaign-results.json")
        require(len(receipts) == 20, "incomplete campaign")
    except (ValueError, OSError, KeyError, TypeError, csv.Error) as exc:
        return {"decision": "unevaluable", "denominator": 20, "failures": [str(exc)]}
    for index, r in enumerate(data["runs"]):
        try:
            directory = Path(r["directory"])
            receipt = read(directory.with_suffix(".inventory.json"))
            require(receipt == receipts[index], "campaign receipt mismatch")
            require(receipt["input_manifest"] == record(manifest), "input manifest hash mismatch")
            require(receipt["condition"] == r["condition"] and receipt["seed"] == r["seed"], "run identity mismatch")
            require(receipt["files"] == inventory(directory), "post-run inventory mismatch")
            summary = analyze_run(directory, r["expected_initial"], exit_status=receipt["exit_status"])
            results.append({"condition": r["condition"], "seed": r["seed"], **summary})
        except (ValueError, OSError, KeyError, TypeError, csv.Error) as exc:
            failures.append({"condition": r["condition"], "seed": r["seed"], "error": str(exc)})
    hosts = [r for r in results if r["condition"] == "host"]
    inert = [r for r in results if r["condition"] == "inert"]
    joint = [r["seed"] for r in hosts if r["successful_births"] >= 100 and r["max_two_parent_depth"] >= 2 and r["final_noninitial_descendants"] >= 100 and r["final_descendant_fraction"] >= 0.5]
    passed = len(joint) >= 8 and len(inert) == 10 and all(r["successful_births"] == 0 and r["max_two_parent_depth"] < 2 for r in inert)
    return {"decision": "unevaluable" if failures else ("pass" if passed else "fail"), "denominator": 20, "joint_host_seeds": joint, "runs": results, "failures": failures}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze_campaign(args.manifest.resolve()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
