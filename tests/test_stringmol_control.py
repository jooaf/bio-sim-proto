from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from experiments.stringmol.analyze_locality import (
    exact_sign_flip_greater,
    paired_bootstrap_interval,
)
from experiments.stringmol.ancestry import ancestry_trajectory, descendant_species
from experiments.stringmol.configure_control import (
    HOST,
    PARASITE_R,
    StringmolControlConfig,
    inoculum,
    render_config,
)
from experiments.stringmol.run_control import parse_population


def test_stringmol_source_and_patch_are_pinned() -> None:
    lock = json.loads(Path("experiments/stringmol/source.lock.json").read_text(encoding="utf-8"))
    patch = Path(
        "experiments/stringmol/patches/0001-fix-neighbor-selection-and-add-locality-controls.patch"
    ).read_text(encoding="utf-8")

    assert lock["commit"] == "15dad84da126a4f887ba945c23a13e89e827f067"
    assert lock["canonical_replicase"] == HOST
    assert "INTERACTION_RADIUS" in patch
    assert "PLACEMENT_RADIUS" in patch
    assert "count++" in patch
    assert "if(count==selected){" in patch


def test_stringmol_control_config_has_explicit_agents_and_matched_cells(tmp_path: Path) -> None:
    host_cells, parasite_cells = inoculum()
    config = StringmolControlConfig(
        condition="mixed",
        seed=202608310,
        interaction_radius=0,
        placement_radius=0,
    )

    text = render_config(config, tmp_path / "matrix.mtx")

    assert len(host_cells) == 140
    assert len(parasite_cells) == 10
    assert not set(host_cells) & set(parasite_cells)
    assert text.count(f"AGENT {HOST} 1 Q") == 140
    assert text.count(f"AGENT {PARASITE_R} 1 R") == 10
    assert text.count("GRIDPOS") == 150
    assert "NUMAGENTS 150" in text
    assert "INTERACTION_RADIUS 0" in text
    assert "PLACEMENT_RADIUS 0" in text


def test_stringmol_ancestry_closure_and_population_trajectory(tmp_path: Path) -> None:
    species = tmp_path / "splist100.dat"
    species.write_text(
        "1,-1,-1,1,HOST\n"
        "2,-1,-1,1,PARASITE\n"
        "3,1,2,4,10,3,CHILD\n"
        "4,3,1,2,20,2,GRANDCHILD\n"
        "5,1,1,5,30,1,HOSTCHILD\n",
        encoding="utf-8",
    )
    population = tmp_path / "popdy001.dat"
    population.write_text("0,1,9\n0,2,1\n100,1,4\n100,3,3\n100,4,2\n100,5,1\n", encoding="utf-8")

    assert descendant_species(species, 2) == {2, 3, 4}
    assert descendant_species(species, 2, "passive") == {2, 3}
    trajectory = ancestry_trajectory(population, species, 2)
    assert trajectory["ancestry_count"].tolist() == [1, 5]
    assert trajectory["ancestry_fraction"].tolist() == [0.1, 0.5]


def test_stringmol_paired_statistics_are_deterministic_and_directional() -> None:
    differences = np.asarray([0.2] * 10, dtype=np.float64)

    assert paired_bootstrap_interval(differences) == (0.2, 0.2)
    assert exact_sign_flip_greater(differences) == 1 / 1_024


def test_stringmol_population_parser_tracks_exact_seed_species(tmp_path: Path) -> None:
    population = tmp_path / "popdy001.dat"
    population.write_text(
        "0,1,140\n0,2,10\n100,1,130\n100,2,30\n100,3,2\n",
        encoding="utf-8",
    )

    summary = parse_population(population, parasite_species=2, host_species=1)

    assert summary["initial_total"] == 150
    assert summary["final_total"] == 162
    assert summary["final_host_count"] == 130
    assert summary["initial_parasite_count"] == 10
    assert summary["maximum_parasite_count"] == 30
    assert summary["final_parasite_count"] == 30
