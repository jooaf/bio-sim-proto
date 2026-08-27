from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

from .native_report import print_native_report


def latest_recording(runs_root: Path) -> Path:
    candidates = [*runs_root.glob("*/run.sqlite"), *runs_root.glob("*/manifest.json")]
    if not candidates:
        raise SystemExit(f"no recorded runs found under {runs_root}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def latest_database(runs_root: Path) -> Path:
    """Backward-compatible SQLite-only lookup for callers using the old API."""

    candidates = list(runs_root.glob("*/run.sqlite"))
    if not candidates:
        raise SystemExit(f"no recorded SQLite runs found under {runs_root}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _resolve_recording(path: Path) -> Path:
    if not path.is_dir():
        if path.name == "manifest.json" and (path.parent / "run.sqlite").exists():
            return path.parent / "run.sqlite"
        return path
    manifest = path / "manifest.json"
    database = path / "run.sqlite"
    if database.exists():
        return database
    if manifest.exists():
        return manifest
    raise SystemExit(f"no supported recording found under {path}")


def _print_phase_learnings(database, summary, final) -> None:
    """Observables distilled from the bio-sim-proto phase 0/1 experiments.

    - Discontinuity: the first body-matter block is when the resource economy
      starts binding (phase-1 shadowing result), so report its tick.
    - Resource specificity: scarcity is structured, so name the limiting
      molecules instead of only aggregate block counts.
    - Saturation semantics: report late-window content turnover (births and
      deaths per 1,000 ticks per organism), not just population level.
    - Transience: distinguish a held late-window state from a decaying peak
      (phase-1 result: most emergent takeovers decay; persistence scales with
      population).
    """

    first_block = database.execute(
        "SELECT MIN(tick) FROM tick_metrics WHERE reproduction_body_matter_blocks > 0"
    ).fetchone()[0]
    print("\nphase-learnings:")
    print(
        f"  first_body_matter_block_tick={first_block if first_block is not None else 'none'}"
    )
    tables = {
        row[0]
        for row in database.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    if "matter_blocks" in tables:
        top = database.execute(
            """
            SELECT molecule_id, blocked_attempts
            FROM matter_blocks
            WHERE tick = (SELECT MAX(tick) FROM matter_blocks)
            ORDER BY blocked_attempts DESC, molecule_id
            LIMIT 5
            """
        ).fetchall()
        if top:
            described = ", ".join(
                f"molecule={row['molecule_id']}:{row['blocked_attempts']}" for row in top
            )
            print(f"  limiting_molecules={described}")
    rows = database.execute(
        "SELECT tick, population, births, deaths FROM tick_metrics ORDER BY tick"
    ).fetchall()
    if len(rows) >= 4:
        final_tick = final["tick"]
        window_start = rows[4 * len(rows) // 5]["tick"]
        window = [row for row in rows if row["tick"] > window_start]
        populations = [row["population"] for row in window]
        mean_population = sum(populations) / len(populations)
        span = max(1, window[-1]["tick"] - window[0]["tick"])
        births = window[-1]["births"] - window[0]["births"]
        deaths = window[-1]["deaths"] - window[0]["deaths"]
        birth_rate = births / span * 1000.0
        death_rate = deaths / span * 1000.0
        variance = sum((value - mean_population) ** 2 for value in populations) / len(populations)
        trend = (
            (populations[-1] - populations[0])
            / max(1.0, float(populations[0]))
            / span
            * 100_000.0
        )
        ratio = birth_rate / death_rate if death_rate > 0.0 else float("inf")
        transient = final["population"] < 0.5 * summary["peak_population"]
        print(
            f"  late_window=[{window[0]['tick']},{final_tick}] mean_population={mean_population:.1f} "
            f"cv={variance ** 0.5 / mean_population if mean_population else 0.0:.4f} "
            f"trend={trend:+.1f}%/1k_ticks"
        )
        print(
            f"  turnover: births={birth_rate:.1f}/1k_ticks deaths={death_rate:.1f}/1k_ticks "
            f"births_per_death={ratio:.3f} "
            f"per_organism={(birth_rate + death_rate) / 2.0 / max(mean_population, 1.0):.4f}"
        )
        print(f"  transient_peak={transient} (final {final['population']} vs peak {summary['peak_population']})")
    dominant = database.execute(
        """
        SELECT MAX(population) FROM species_states WHERE tick=?
        """,
        (final["tick"],),
    ).fetchone()[0]
    if dominant is not None and final["population"] > 0:
        print(f"  dominant_species_share={dominant / final['population']:.4f}")


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Summarize a recorded organism-simulation run")
    parser.add_argument(
        "recording",
        nargs="?",
        type=Path,
        help="run directory, manifest.json, or run.sqlite; defaults to the latest run",
    )
    args = parser.parse_args()
    configured_root = os.environ.get("ORGANISM_SIM_RUNS_DIR")
    runs_root = Path(configured_root) if configured_root else project_root / "runs"
    recording_path = _resolve_recording(args.recording or latest_recording(runs_root))
    if recording_path.name == "manifest.json":
        print_native_report(recording_path)
        return
    if recording_path.suffix != ".sqlite":
        raise SystemExit(f"unsupported recording: {recording_path}")
    database_path = recording_path
    with sqlite3.connect(database_path) as database:
        database.row_factory = sqlite3.Row
        tick_columns = {
            row["name"] for row in database.execute("PRAGMA table_info(tick_metrics)")
        }
        reproduction_fields = (
            (
                "MAX(reproduction_attempts)",
                "MAX(reproduction_resource_blocks)",
                "MAX(reproduction_probability_failures)",
                "MAX(reproduction_placement_failures)",
            )
            if "reproduction_attempts" in tick_columns
            else ("MAX(failed_reproductions + successful_reproductions)", "0", "0", "0")
        )
        resource_block_fields = (
            (
                "MAX(reproduction_mate_readiness_blocks)",
                "MAX(reproduction_energy_blocks)",
                "MAX(reproduction_body_matter_blocks)",
            )
            if "reproduction_energy_blocks" in tick_columns
            else ("0", "0", "0")
        )
        summary = database.execute(
            f"""
            SELECT
                MAX(tick) AS final_tick,
                MAX(population) AS peak_population,
                MAX(living_species) AS peak_species,
                MAX(births) AS births,
                MAX(deaths) AS deaths,
                {reproduction_fields[0]} AS reproduction_attempts,
                {reproduction_fields[1]} AS reproduction_resource_blocks,
                {resource_block_fields[0]} AS reproduction_mate_readiness_blocks,
                {resource_block_fields[1]} AS reproduction_energy_blocks,
                {resource_block_fields[2]} AS reproduction_body_matter_blocks,
                {reproduction_fields[2]} AS reproduction_probability_failures,
                {reproduction_fields[3]} AS reproduction_placement_failures,
                MAX(asexual_events) AS asexual_events,
                MAX(sexual_events) AS sexual_events,
                MAX(unique_sexual_parents) AS unique_sexual_parents,
                MAX(ABS(energy_error)) AS maximum_energy_error
            FROM tick_metrics
            """
        ).fetchone()
        final = database.execute("SELECT * FROM tick_metrics ORDER BY tick DESC LIMIT 1").fetchone()
        print(f"run: {database_path.parent.name}")
        print(f"database: {database_path}")
        print(
            f"ticks={summary['final_tick']} final_population={final['population']} "
            f"peak_population={summary['peak_population']} peak_species={summary['peak_species']}"
        )
        print(
            f"births={summary['births']} deaths={summary['deaths']} "
            f"asexual_events={summary['asexual_events']} sexual_events={summary['sexual_events']} "
            f"unique_sexual_parents={summary['unique_sexual_parents']}"
        )
        print(
            f"reproduction_attempts={summary['reproduction_attempts']} "
            f"resource_blocks={summary['reproduction_resource_blocks']} "
            f"mate_readiness_blocks={summary['reproduction_mate_readiness_blocks']} "
            f"energy_blocks={summary['reproduction_energy_blocks']} "
            f"body_matter_blocks={summary['reproduction_body_matter_blocks']} "
            f"probability_failures={summary['reproduction_probability_failures']} "
            f"placement_failures={summary['reproduction_placement_failures']}"
        )
        print(f"maximum_energy_error={summary['maximum_energy_error']:.3e}")
        _print_phase_learnings(database, summary, final)
        print("\nfinal species:")
        species_columns = {
            row["name"] for row in database.execute("PRAGMA table_info(species_states)")
        }
        origin_fields = (
            "origin, created_tick, parent_species_ids_json"
            if "origin" in species_columns
            else "'legacy' AS origin, 0 AS created_tick, '[]' AS parent_species_ids_json"
        )
        for row in database.execute(
            f"""
            SELECT species_id, population, births, deaths, representative_genome_id,
                   {origin_fields}
            FROM species_states
            WHERE tick=? AND population>0
            ORDER BY population DESC, species_id
            LIMIT 12
            """,
            (summary["final_tick"],),
        ):
            print(
                f"  species={row['species_id']} population={row['population']} "
                f"births={row['births']} deaths={row['deaths']} genome={row['representative_genome_id']} "
                f"origin={row['origin']} created={row['created_tick']} parents={row['parent_species_ids_json']}"
            )
        print("\nmost abundant final molecules:")
        for row in database.execute(
            """
            SELECT molecule_id, molecule_count, chemical_energy
            FROM molecule_states
            WHERE tick=?
            ORDER BY molecule_count DESC, molecule_id
            LIMIT 12
            """,
            (summary["final_tick"],),
        ):
            print(
                f"  molecule={row['molecule_id']} count={row['molecule_count']} "
                f"energy={row['chemical_energy']:.4g}"
            )


if __name__ == "__main__":
    main()
