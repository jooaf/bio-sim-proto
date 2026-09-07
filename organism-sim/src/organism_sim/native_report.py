from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from statistics import median
from typing import Any

MetricRow = dict[str, Any]


def _read_jsonl(path: Path) -> list[MetricRow]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as lines:
        return [json.loads(line) for line in lines if line.strip()]


def _counter(row: MetricRow, name: str) -> int:
    return int(row.get(name, 0))


def _peak_counter(rows: list[MetricRow], name: str) -> tuple[int, int]:
    peak = max(rows, key=lambda row: _counter(row, name))
    return _counter(peak, name), int(peak["tick"])


def _window(rows: list[MetricRow], start_fraction: float, end_fraction: float) -> list[MetricRow]:
    first_tick = int(rows[0]["tick"])
    final_tick = int(rows[-1]["tick"])
    span = max(1, final_tick - first_tick)
    start = first_tick + span * start_fraction
    end = first_tick + span * end_fraction
    return [row for row in rows if start <= int(row["tick"]) <= end]


def _positive_tps(rows: Iterable[MetricRow]) -> list[float]:
    return [
        float(row["actual_ticks_per_second"])
        for row in rows
        if float(row.get("actual_ticks_per_second", 0.0)) > 0.0
    ]


def _percent(part: float, whole: float) -> float:
    return 100.0 * part / whole if whole else 0.0


def print_native_report(manifest_path: Path) -> None:
    """Summarize compact Rust headless or GUI JSONL without loading NPZ state."""

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_dir = manifest_path.parent
    metrics_path = run_dir / manifest.get("metrics", "metrics.jsonl")
    rows = _read_jsonl(metrics_path)

    print(f"run: {manifest.get('run_id', run_dir.name)}")
    print(f"manifest: {manifest_path}")
    print(f"recording_format={manifest.get('recording_format', 'unknown')}")
    build = manifest.get("build")
    if build:
        print(
            f"kernel_build={build.get('kernel_version', 'unknown')} "
            f"binary_sha256={build.get('kernel_binary_sha256', 'unknown')}"
        )
        print(f"config_sha256={manifest.get('config_sha256', 'unknown')}")
    elif manifest.get("kernel") == "rust":
        print("kernel_build=unavailable (legacy manifest)")
    if not rows:
        print("no metric rows were recorded")
        return

    first = rows[0]
    final = rows[-1]
    peak_population = max(int(row.get("population", 0)) for row in rows)
    peak_species = max(int(row.get("living_species", 0)) for row in rows)
    peak_tick = next(
        int(row["tick"])
        for row in rows
        if int(row.get("population", 0)) == peak_population
    )
    extinct_rows = [row for row in rows if int(row.get("population", 0)) == 0]
    print(
        f"ticks={int(final['tick'])} final_population={int(final['population'])} "
        f"peak_population={peak_population} peak_tick={peak_tick} "
        f"peak_species={peak_species}"
    )
    trajectory_rows = rows
    if int(final["population"]) == 0 and extinct_rows:
        extinction_tick = int(extinct_rows[0]["tick"])
        print(f"extinction_tick={extinction_tick}")
        trajectory_rows = [row for row in rows if int(row["tick"]) <= extinction_tick]
    trajectory_final = trajectory_rows[-1]
    print(
        f"births={_counter(final, 'births')} deaths={_counter(final, 'deaths')} "
        f"asexual_events={_counter(final, 'asexual_reproduction_events')} "
        f"sexual_events={_counter(final, 'sexual_reproduction_events')}"
    )

    attempts = _counter(final, "reproduction_attempts")
    successes = _counter(final, "successful_reproductions")
    failure_fields = (
        ("resource", "reproduction_resource_blocks"),
        ("probability", "reproduction_probability_failures"),
        ("placement", "reproduction_placement_failures"),
    )
    failure_text = " ".join(
        f"{label}={_counter(final, field)} ({_percent(_counter(final, field), attempts):.1f}%)"
        for label, field in failure_fields
    )
    print(
        f"reproduction_attempts={attempts} successes={successes} "
        f"({_percent(successes, attempts):.1f}%) {failure_text}"
    )
    print(
        "resource_blocks: "
        f"mate={_counter(final, 'reproduction_mate_readiness_blocks')} "
        f"energy={_counter(final, 'reproduction_energy_blocks')} "
        f"body_matter={_counter(final, 'reproduction_body_matter_blocks')}"
    )

    late = _window(trajectory_rows, 0.8, 1.0)
    late_frontier_density_change: float | None = None
    if len(late) >= 2:
        late_first = late[0]
        tick_span = max(
            1, int(trajectory_final["tick"]) - int(late_first["tick"])
        )
        populations = [int(row["population"]) for row in late]
        mean_population = sum(populations) / len(populations)
        births = _counter(trajectory_final, "births") - _counter(late_first, "births")
        deaths = _counter(trajectory_final, "deaths") - _counter(late_first, "deaths")
        birth_rate = births / tick_span * 1000.0
        death_rate = deaths / tick_span * 1000.0
        trend = (
            (populations[-1] - populations[0])
            / max(1.0, float(populations[0]))
            / tick_span
            * 100_000.0
        )
        print("\nlate-window dynamics:")
        print(
            f"  ticks=[{int(late_first['tick'])},{int(trajectory_final['tick'])}] "
            f"mean_population={mean_population:.1f} trend={trend:+.1f}%/1k_ticks"
        )
        print(
            f"  births={birth_rate:.1f}/1k_ticks deaths={death_rate:.1f}/1k_ticks "
            f"births_per_death={birth_rate / death_rate if death_rate else float('inf'):.3f}"
        )

    if bool(final.get("biodeposits_enabled", False)):
        print("\nphysical biodeposits:")
        print(
            f"  positions={_counter(final, 'biodeposit_positions')} "
            f"total_density={float(final.get('biodeposit_total_density', 0.0)):.3g} "
            f"max_density={float(final.get('biodeposit_max_density', 0.0)):.3g}"
        )

    configured_cellular = bool(
        manifest.get("config", {}).get("cellular_emergence_enabled", False)
    )
    cellular_enabled = bool(
        final.get("cellular_affordances_enabled", configured_cellular)
    )
    print("\ncellular emergence:")
    if not cellular_enabled:
        print("  status=DISABLED (no modules, bonds, joined groups, or guests can form)")
    else:
        peak_bonds, peak_bond_tick = _peak_counter(rows, "physical_bonds")
        peak_groups, peak_group_tick = _peak_counter(rows, "bond_components")
        peak_size, peak_size_tick = _peak_counter(rows, "largest_bond_component")
        peak_bonded_cells, peak_bonded_tick = _peak_counter(rows, "bonded_cells")
        print(
            f"  status=ENABLED final_groups={_counter(final, 'bond_components')} "
            f"final_largest_group={_counter(final, 'largest_bond_component')}"
        )
        print(
            f"  peak_largest_group={peak_size} at_tick={peak_size_tick} "
            f"peak_groups={peak_groups} at_tick={peak_group_tick}"
        )
        print(
            f"  final_bonds={_counter(final, 'physical_bonds')} "
            f"peak_bonds={peak_bonds} at_tick={peak_bond_tick} "
            f"peak_bonded_cells={peak_bonded_cells} at_tick={peak_bonded_tick}"
        )
        print(
            f"  modules={_counter(final, 'module_instances')} "
            f"expressed={_counter(final, 'expressed_module_instances')} "
            f"guests={_counter(final, 'internal_guests')} "
            f"internalizations={_counter(final, 'internalizations')}"
        )
        print(
            f"  bond_formations={_counter(final, 'bond_formations')} "
            f"bond_breaks={_counter(final, 'bond_breaks')}"
        )
        if bool(final.get("coordinated_components_enabled", False)):
            print(
                f"  component_actions={_counter(final, 'component_actions')} "
                f"component_moves={_counter(final, 'component_moves')} "
                f"propagules={_counter(final, 'component_propagules')} "
                f"propagated_cells={_counter(final, 'propagated_cells')}"
            )

    print("\necology and scale:")
    initial_species = int(first.get("living_species", 0))
    final_species = int(final.get("living_species", 0))
    print(f"  living_species={initial_species}->{final_species}")
    if "dominant_species_share" in final:
        print(
            f"  dominant_species_share={float(final['dominant_species_share']):.4f} "
            f"population={int(final.get('dominant_species_population', 0))}"
        )
    initial_chunks = _counter(first, "generated_chunks")
    final_chunks = _counter(final, "generated_chunks")
    initial_deposits = _counter(first, "deposit_positions")
    final_deposits = _counter(final, "deposit_positions")
    print(
        f"  generated_chunks={initial_chunks}->{final_chunks} "
        f"deposit_positions={initial_deposits}->{final_deposits}"
    )
    if final_chunks > initial_chunks:
        print(
            f"  expansion={1000.0 * (final_chunks - initial_chunks) / max(1, int(final['tick']) - int(first['tick'])):.2f} "
            "chunks/1k_ticks"
        )
    if final_chunks > 0:
        final_frontier_density = int(final["population"]) / final_chunks
        density_text = f"  population_per_generated_chunk={final_frontier_density:.2f}"
        if len(late) >= 2:
            late_first_chunks = _counter(late[0], "generated_chunks")
            if late_first_chunks > 0:
                late_first_density = int(late[0]["population"]) / late_first_chunks
                if late_first_density > 0.0:
                    late_frontier_density_change = (
                        final_frontier_density / late_first_density - 1.0
                    )
                    density_text += (
                        f" late_change={late_frontier_density_change:+.1%}"
                    )
        print(density_text)

    early_tps = _positive_tps(_window(trajectory_rows, 0.1, 0.3))
    late_tps = _positive_tps(late)
    if early_tps and late_tps:
        early_median = median(early_tps)
        late_median = median(late_tps)
        print("\nperformance:")
        print(
            f"  median_ticks_per_second early={early_median:.2f} late={late_median:.2f} "
            f"retained={_percent(late_median, early_median):.1f}%"
        )

    audit_path = run_dir / manifest.get("audit", "audit.json")
    if audit_path.exists():
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        energy_error = float(audit.get("energy_error", 0.0))
        accounting_scale = float(
            audit.get(
                "energy_accounting_scale",
                abs(float(audit.get("initial_energy", 0.0)))
                + abs(float(audit.get("generated_energy", 0.0))),
            )
        )
        print("\nconservation:")
        print(
            f"  elements_ok={audit.get('elements_ok')} energy_ok={audit.get('energy_ok')} "
            f"energy_error={energy_error:.3e} "
            f"relative_error={abs(energy_error) / max(accounting_scale, 1e-300):.3e}"
        )
        if "energy_tolerance" in audit:
            print(f"  energy_tolerance={float(audit['energy_tolerance']):.3e}")

    season_events_path = run_dir / manifest.get(
        "season_events", "season_events.jsonl"
    )
    season_events = _read_jsonl(season_events_path)
    if season_events and bool(season_events[0].get("enabled", False)):
        charge = [
            float(event["target"]["resource_charge_multiplier"])
            for event in season_events
        ]
        decomposition = [
            float(event["target"]["decomposition_multiplier"])
            for event in season_events
        ]
        print("\nrandom environment seasons:")
        print(
            f"  transitions={max(0, len(season_events) - 1)} "
            f"resource_multiplier=[{min(charge):.3f},{max(charge):.3f}] "
            f"decomposition_multiplier=[{min(decomposition):.3f},{max(decomposition):.3f}]"
        )

    events_path = run_dir / manifest.get("config_events", "config_events.jsonl")
    events = _read_jsonl(events_path)
    print("\nconfiguration provenance:")
    if not events:
        if manifest.get("source") == "gui" and manifest.get("schema_version", 1) < 2:
            print("  unavailable: this GUI schema recorded startup config only")
        else:
            print("  no live kernel updates")
    else:
        for event in events:
            changes = ", ".join(
                f"{name}={value}" for name, value in sorted(event["changes"].items())
            )
            print(f"  tick={int(event['tick'])} revision={int(event['revision'])} {changes}")

    observations: list[str] = []
    if final_species <= 1 < initial_species:
        observations.append("founder diversity collapsed to one or zero living species")
    if len(late) >= 2 and int(final["population"]) > int(late[0]["population"]) * 1.25:
        if (
            late_frontier_density_change is not None
            and abs(late_frontier_density_change) <= 0.2
        ):
            observations.append(
                "global growth tracked frontier expansion while population per generated chunk stayed stable"
            )
        else:
            observations.append(
                "population was still expanding rapidly in the final 20% of ticks"
            )
    if attempts and _counter(final, "reproduction_probability_failures") > attempts * 0.5:
        observations.append("probability rejection, not energy, dominated reproduction failures")
    if early_tps and late_tps and median(late_tps) < median(early_tps) * 0.5:
        observations.append("simulation throughput fell by more than half as the ecology grew")
    if observations:
        print("\nnotable observations:")
        for observation in observations:
            print(f"  - {observation}")


__all__ = ["print_native_report"]
