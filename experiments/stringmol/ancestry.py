"""Parse Stringmol species parentage into a neutral parasite-ancestry family."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Literal, cast

import pandas as pd


def species_parentage(path: Path) -> dict[int, set[int]]:
    """Return every observed child species' nonnegative parent species IDs."""

    parents: dict[int, set[int]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.reader(handle):
            if len(row) < 4:
                continue
            child = int(row[0])
            active_parent = int(row[1])
            passive_parent = int(row[2])
            parents.setdefault(child, set())
            if active_parent >= 0:
                parents[child].add(active_parent)
            if passive_parent >= 0:
                parents[child].add(passive_parent)
    return parents


def descendant_species(
    path: Path,
    founder_species: int,
    parent_role: Literal["either", "passive"] = "either",
) -> set[int]:
    """Compute descendants through either parent or the inherited passive label."""

    if parent_role == "either":
        parents = species_parentage(path)
    else:
        parents = {}
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.reader(handle):
                if len(row) < 4:
                    continue
                child = int(row[0])
                passive_parent = int(row[2])
                parents.setdefault(child, set())
                if passive_parent >= 0:
                    parents[child].add(passive_parent)
    family = {founder_species}
    changed = True
    while changed:
        changed = False
        for child, child_parents in parents.items():
            if child not in family and child_parents & family:
                family.add(child)
                changed = True
    return family


def ancestry_trajectory(
    population_path: Path,
    species_path: Path,
    founder_species: int,
    parent_role: Literal["either", "passive"] = "either",
) -> pd.DataFrame:
    """Sum exact species counts over a frozen transitive ancestry family."""

    family = descendant_species(species_path, founder_species, parent_role)
    with population_path.open(newline="", encoding="utf-8") as handle:
        raw = list(csv.reader(handle))
    rows = [
        {"tick": int(row[0]), "species": int(row[1]), "count": int(row[2])}
        for row in raw
        if len(row) == 3
    ]
    if not rows:
        raise ValueError(f"no population rows in {population_path}")
    frame = pd.DataFrame(rows)
    output: list[dict[str, Any]] = []
    for tick, snapshot in frame.groupby("tick", sort=True):
        total = int(snapshot["count"].sum())
        family_count = int(snapshot.loc[snapshot["species"].isin(family), "count"].sum())
        output.append(
            {
                "tick": int(cast(Any, tick)),
                "total_count": total,
                "ancestry_count": family_count,
                "ancestry_fraction": family_count / total,
                "family_species_count": len(family),
            }
        )
    return pd.DataFrame(output)
