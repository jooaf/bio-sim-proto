from __future__ import annotations

import json
import os
import sqlite3
import zlib
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self
from uuid import uuid4

import numpy as np

from .config import SimulationConfig
from .simulation import Simulation

SCHEMA_VERSION = 5


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


class RunRecorder:
    """Persistent analysis record for one GUI or headless launch.

    Tick tables retain analysis-friendly state every tick. Chunk heat grids and
    sparse environmental molecule fields (keyed by absolute world coordinates)
    are compressed into periodic world snapshots.
    Initial state plus tick tables and snapshots are sufficient for retrospective
    population, genome, chemistry, spatial, and conservation analyses.
    """

    def __init__(
        self,
        simulation: Simulation,
        *,
        source: str,
        runs_root: Path | None = None,
        previous_run_id: str | None = None,
    ) -> None:
        project_root = Path(__file__).resolve().parents[2]
        configured_root = os.environ.get("ORGANISM_SIM_RUNS_DIR")
        root = runs_root or (Path(configured_root) if configured_root else project_root / "runs")
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
        self.run_id = f"{timestamp}-seed{simulation.config.seed}-{uuid4().hex[:8]}"
        self.run_dir = root / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=False)
        self.database_path = self.run_dir / "run.sqlite"
        self.source = source
        self.previous_run_id = previous_run_id
        self.connection = sqlite3.connect(self.database_path)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=NORMAL")
        self.connection.execute("PRAGMA temp_store=MEMORY")
        self._create_schema()
        self._known_genomes: set[int] = set()
        self._known_sexual_parents: set[int] = set()
        self._organism_id_cursor = 1
        self._species_id_cursor = 1
        self._death_event_cursor = 0
        self._matter_block_cursor: dict[int, int] = {}
        self._alliance_event_cursor = 0
        self._colony_event_cursor = 0
        self._deaths_by_tick: dict[int, list[int]] = {}
        # This prototype transfers molecule batches without changing molecule
        # identity, so molecule and element counts are run invariants. Energy
        # remains dynamic and is aggregated from authoritative inventories.
        self._molecule_counts = [0] * len(simulation.catalog.molecules)
        for inventory in simulation.all_inventories():
            for molecule_id, batch in inventory.items():
                self._molecule_counts[molecule_id] += batch.count
        self._closed = False
        self._started_at = datetime.now(UTC).isoformat()
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "source": source,
            "previous_run_id": previous_run_id,
            "seed": simulation.config.seed,
            "started_utc": self._started_at,
            "database": self.database_path.name,
        }
        (self.run_dir / "manifest.json").write_text(_json(manifest) + "\n", encoding="utf-8")
        self._record_run_metadata(simulation)
        self.record_config(simulation.tick, simulation.config, reason="launch")
        self.record_tick(simulation, force_snapshot=True)
        self.connection.commit()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE run_metadata (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL
            );
            CREATE TABLE config_events (
                tick INTEGER NOT NULL,
                reason TEXT NOT NULL,
                config_json TEXT NOT NULL
            );
            CREATE TABLE elements (
                element_id INTEGER PRIMARY KEY,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE molecules (
                molecule_id INTEGER PRIMARY KEY,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE genomes (
                genome_id INTEGER PRIMARY KEY,
                first_tick INTEGER NOT NULL,
                parent_genome_ids_json TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE organisms (
                organism_id INTEGER PRIMARY KEY,
                first_tick INTEGER NOT NULL,
                birth_tick INTEGER NOT NULL,
                lineage_id INTEGER NOT NULL,
                species_id_at_birth INTEGER NOT NULL,
                parent_ids_json TEXT NOT NULL,
                generation INTEGER NOT NULL,
                genome_id INTEGER NOT NULL,
                phenotype_json TEXT NOT NULL
            );
            CREATE TABLE tick_metrics (
                tick INTEGER PRIMARY KEY,
                population INTEGER NOT NULL,
                living_species INTEGER NOT NULL,
                births INTEGER NOT NULL,
                deaths INTEGER NOT NULL,
                reproduction_attempts INTEGER NOT NULL,
                reproduction_resource_blocks INTEGER NOT NULL,
                reproduction_mate_readiness_blocks INTEGER NOT NULL,
                reproduction_energy_blocks INTEGER NOT NULL,
                reproduction_body_matter_blocks INTEGER NOT NULL,
                reproduction_probability_failures INTEGER NOT NULL,
                reproduction_placement_failures INTEGER NOT NULL,
                failed_reproductions INTEGER NOT NULL,
                successful_reproductions INTEGER NOT NULL,
                asexual_events INTEGER NOT NULL,
                sexual_events INTEGER NOT NULL,
                unique_sexual_parents INTEGER NOT NULL,
                living_sexual_parents INTEGER NOT NULL,
                attacks INTEGER NOT NULL,
                magic_casts INTEGER NOT NULL,
                alliances INTEGER NOT NULL,
                colonies INTEGER NOT NULL,
                chemical_energy REAL NOT NULL,
                mana_energy REAL NOT NULL,
                heat_energy REAL NOT NULL,
                effect_energy REAL NOT NULL,
                total_energy REAL NOT NULL,
                energy_error REAL NOT NULL
            );
            CREATE TABLE detail_ticks (
                tick INTEGER PRIMARY KEY
            );
            CREATE TABLE element_states (
                tick INTEGER NOT NULL,
                element_id INTEGER NOT NULL,
                element_count INTEGER NOT NULL,
                PRIMARY KEY (tick, element_id)
            );
            CREATE TABLE molecule_states (
                tick INTEGER NOT NULL,
                molecule_id INTEGER NOT NULL,
                molecule_count INTEGER NOT NULL,
                chemical_energy REAL NOT NULL,
                PRIMARY KEY (tick, molecule_id)
            );
            CREATE TABLE matter_blocks (
                tick INTEGER NOT NULL,
                molecule_id INTEGER NOT NULL,
                blocked_attempts INTEGER NOT NULL,
                PRIMARY KEY (tick, molecule_id)
            );
            CREATE TABLE organism_states (
                tick INTEGER NOT NULL,
                organism_id INTEGER NOT NULL,
                alive INTEGER NOT NULL,
                x INTEGER NOT NULL,
                y INTEGER NOT NULL,
                species_id INTEGER NOT NULL,
                colony_id INTEGER,
                area INTEGER NOT NULL,
                structural_mass INTEGER NOT NULL,
                chemical_energy REAL NOT NULL,
                energy_fraction REAL NOT NULL,
                mana REAL NOT NULL,
                integrity REAL NOT NULL,
                maintenance_debt REAL NOT NULL,
                toxin_load REAL NOT NULL,
                reproduction_cooldown INTEGER NOT NULL,
                offspring_count INTEGER NOT NULL,
                kills INTEGER NOT NULL,
                last_action TEXT NOT NULL,
                statuses_json TEXT NOT NULL,
                PRIMARY KEY (tick, organism_id)
            );
            CREATE TABLE organism_inventories (
                tick INTEGER NOT NULL,
                organism_id INTEGER NOT NULL,
                compartment TEXT NOT NULL,
                molecule_id INTEGER NOT NULL,
                molecule_count INTEGER NOT NULL,
                chemical_energy REAL NOT NULL,
                PRIMARY KEY (tick, organism_id, compartment, molecule_id)
            );
            CREATE TABLE species_states (
                tick INTEGER NOT NULL,
                species_id INTEGER NOT NULL,
                population INTEGER NOT NULL,
                births INTEGER NOT NULL,
                deaths INTEGER NOT NULL,
                representative_genome_id INTEGER NOT NULL,
                color_json TEXT NOT NULL,
                origin TEXT NOT NULL,
                created_tick INTEGER NOT NULL,
                parent_species_ids_json TEXT NOT NULL,
                founder_organism_id INTEGER,
                PRIMARY KEY (tick, species_id)
            );
            CREATE TABLE sexual_parents (
                organism_id INTEGER PRIMARY KEY,
                first_recorded_tick INTEGER NOT NULL
            );
            CREATE TABLE corpse_states (
                tick INTEGER NOT NULL,
                corpse_id INTEGER NOT NULL,
                source_id INTEGER NOT NULL,
                x INTEGER NOT NULL,
                y INTEGER NOT NULL,
                created_tick INTEGER NOT NULL,
                PRIMARY KEY (tick, corpse_id)
            );
            CREATE TABLE magic_effect_states (
                tick INTEGER NOT NULL,
                effect_id INTEGER NOT NULL,
                channel INTEGER NOT NULL,
                source_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                energy REAL NOT NULL,
                expires_tick INTEGER NOT NULL,
                PRIMARY KEY (tick, effect_id)
            );
            CREATE TABLE colony_states (
                tick INTEGER NOT NULL,
                colony_id INTEGER NOT NULL,
                members_json TEXT NOT NULL,
                bonus REAL NOT NULL,
                created_tick INTEGER NOT NULL,
                PRIMARY KEY (tick, colony_id)
            );
            CREATE TABLE alliances (
                left_organism_id INTEGER NOT NULL,
                right_organism_id INTEGER NOT NULL,
                created_tick INTEGER NOT NULL,
                PRIMARY KEY (left_organism_id, right_organism_id)
            );
            CREATE TABLE alliance_states (
                tick INTEGER NOT NULL,
                left_organism_id INTEGER NOT NULL,
                right_organism_id INTEGER NOT NULL,
                PRIMARY KEY (tick, left_organism_id, right_organism_id)
            );
            CREATE TABLE events (
                tick INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE world_snapshots (
                tick INTEGER PRIMARY KEY,
                chunk_size INTEGER NOT NULL,
                chunk_count INTEGER NOT NULL,
                heat_chunks_zlib BLOB NOT NULL,
                deposits_json_zlib BLOB NOT NULL
            );
            CREATE INDEX organism_states_species_idx ON organism_states (species_id, tick);
            CREATE INDEX organism_states_action_idx ON organism_states (last_action, tick);
            CREATE INDEX events_type_tick_idx ON events (event_type, tick);
            """
        )

    def _record_run_metadata(self, simulation: Simulation) -> None:
        metadata = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "source": self.source,
            "previous_run_id": self.previous_run_id,
            "started_utc": self._started_at,
            "seed": simulation.config.seed,
            "initial_elements": simulation.initial_elements,
            "initial_energy": simulation.initial_energy,
            "reference_energy": simulation.reference_energy,
            "reference_body_mass": simulation.reference_body_mass,
        }
        self.connection.executemany(
            "INSERT INTO run_metadata(key, value_json) VALUES (?, ?)",
            ((key, _json(value)) for key, value in metadata.items()),
        )
        self.connection.executemany(
            "INSERT INTO elements(element_id, payload_json) VALUES (?, ?)",
            ((element.element_id, _json(asdict(element))) for element in simulation.catalog.elements),
        )
        self.connection.executemany(
            "INSERT INTO molecules(molecule_id, payload_json) VALUES (?, ?)",
            ((molecule.molecule_id, _json(asdict(molecule))) for molecule in simulation.catalog.molecules),
        )

    def record_config(self, tick: int, config: SimulationConfig, *, reason: str) -> None:
        self.connection.execute(
            "INSERT INTO config_events(tick, reason, config_json) VALUES (?, ?, ?)",
            (tick, reason, _json(asdict(config))),
        )

    def record_tick(self, simulation: Simulation, *, force_snapshot: bool = False) -> None:
        if self._closed:
            raise RuntimeError("cannot record to a closed run")
        metrics_interval = max(1, simulation.config.recording_metrics_interval)
        if not force_snapshot and simulation.tick % metrics_interval != 0:
            return
        self._record_definitions_and_events(simulation)
        molecule_energies = [0.0] * len(simulation.catalog.molecules)
        for inventory in simulation.all_inventories():
            for molecule_id, batch in inventory.items():
                molecule_energies[molecule_id] += batch.energy
        chemical_energy = sum(molecule_energies)
        mana_energy = sum(
            simulation.organisms[organism_id].mana for organism_id in simulation.living_ids
        )
        heat_energy = simulation.world.total_heat()
        effect_energy = sum(effect.energy for effect in simulation.effects.values())
        total_energy = chemical_energy + mana_energy + heat_energy + effect_energy
        living_species = sum(species.population > 0 for species in simulation.species.values())
        stats = simulation.stats
        self.connection.execute(
            """
            INSERT INTO tick_metrics VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                simulation.tick,
                simulation.population,
                living_species,
                stats.births,
                stats.deaths,
                stats.reproduction_attempts,
                stats.reproduction_resource_blocks,
                stats.reproduction_mate_readiness_blocks,
                stats.reproduction_energy_blocks,
                stats.reproduction_body_matter_blocks,
                stats.reproduction_probability_failures,
                stats.reproduction_placement_failures,
                stats.failed_reproductions,
                stats.successful_reproductions,
                stats.asexual_reproduction_events,
                stats.sexual_reproduction_events,
                len(simulation.sexual_parent_ids),
                simulation.living_sexual_parent_count,
                stats.attacks,
                stats.magic_casts,
                len(simulation.alliances),
                len(simulation.colonies),
                chemical_energy,
                mana_energy,
                heat_energy,
                effect_energy,
                total_energy,
                total_energy - simulation.initial_energy - simulation.world.generated_energy,
            ),
        )
        self.connection.executemany(
            "INSERT INTO element_states VALUES (?, ?, ?)",
            (
                (simulation.tick, element_id, count)
                for element_id, count in enumerate(simulation.initial_elements)
            ),
        )
        self.connection.executemany(
            "INSERT INTO molecule_states VALUES (?, ?, ?, ?)",
            (
                (
                    simulation.tick,
                    molecule_id,
                    self._molecule_counts[molecule_id],
                    molecule_energies[molecule_id],
                )
                for molecule_id in range(len(self._molecule_counts))
            ),
        )
        matter_rows = []
        for molecule_id, blocked in simulation.stats.reproduction_matter_blocks_by_molecule.items():
            delta = blocked - self._matter_block_cursor.get(molecule_id, 0)
            if delta > 0:
                self._matter_block_cursor[molecule_id] = blocked
                matter_rows.append((simulation.tick, molecule_id, blocked))
        self.connection.executemany(
            "INSERT INTO matter_blocks VALUES (?, ?, ?)",
            matter_rows,
        )
        detail_interval = max(1, simulation.config.recording_detail_interval)
        if force_snapshot or simulation.tick % detail_interval == 0:
            self._record_detail_states(simulation)
        self._deaths_by_tick.pop(simulation.tick, None)
        interval = max(1, simulation.config.recording_snapshot_interval)
        if force_snapshot or simulation.tick % interval == 0:
            self._record_world_snapshot(simulation)
        commit_interval = max(1, simulation.config.recording_commit_interval)
        if force_snapshot or simulation.tick % commit_interval == 0:
            self.connection.commit()

    def _record_detail_states(self, simulation: Simulation) -> None:
        self.connection.execute("INSERT INTO detail_ticks VALUES (?)", (simulation.tick,))
        self._record_organism_states(simulation)
        self.connection.executemany(
            "INSERT INTO species_states VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                (
                    simulation.tick,
                    species.species_id,
                    species.population,
                    species.births,
                    species.deaths,
                    species.representative_genome.genome_id,
                    _json(species.color),
                    species.origin,
                    species.created_tick,
                    _json(species.parent_species_ids),
                    species.founder_organism_id,
                )
                for species in simulation.species.values()
            ),
        )
        self.connection.executemany(
            "INSERT INTO corpse_states VALUES (?, ?, ?, ?, ?, ?)",
            (
                (
                    simulation.tick,
                    corpse.corpse_id,
                    corpse.source_id,
                    corpse.position[0],
                    corpse.position[1],
                    corpse.created_tick,
                )
                for corpse in simulation.corpses.values()
            ),
        )
        self.connection.executemany(
            "INSERT INTO magic_effect_states VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                (
                    simulation.tick,
                    effect.effect_id,
                    effect.channel,
                    effect.source_id,
                    effect.target_id,
                    effect.energy,
                    effect.expires_tick,
                )
                for effect in simulation.effects.values()
            ),
        )
        self.connection.executemany(
            "INSERT INTO colony_states VALUES (?, ?, ?, ?, ?)",
            (
                (
                    simulation.tick,
                    colony.colony_id,
                    _json(sorted(colony.members)),
                    colony.bonus,
                    colony.created_tick,
                )
                for colony in simulation.colonies.values()
            ),
        )

    def _record_definitions_and_events(self, simulation: Simulation) -> None:
        next_organism_id = simulation._next_organism_id
        for organism_id in range(self._organism_id_cursor, next_organism_id):
            organism = simulation.organisms.get(organism_id)
            if organism is None:
                continue
            genome = organism.genome
            if genome.genome_id not in self._known_genomes:
                self.connection.execute(
                    "INSERT INTO genomes VALUES (?, ?, ?, ?)",
                    (
                        genome.genome_id,
                        organism.birth_tick,
                        _json(genome.parent_genome_ids),
                        _json(asdict(genome)),
                    ),
                )
                self._known_genomes.add(genome.genome_id)
            self.connection.execute(
                "INSERT INTO organisms VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    organism.organism_id,
                    organism.birth_tick,
                    organism.birth_tick,
                    organism.lineage_id,
                    organism.species_id,
                    _json(organism.parent_ids),
                    organism.generation,
                    genome.genome_id,
                    _json(asdict(organism.phenotype)),
                ),
            )
            event_type = "founder" if not organism.parent_ids else "birth"
            self._event(
                organism.birth_tick,
                event_type,
                str(organism.organism_id),
                {
                    "species_id": organism.species_id,
                    "genome_id": genome.genome_id,
                    "parent_ids": organism.parent_ids,
                },
            )
        self._organism_id_cursor = next_organism_id

        for death_tick, organism_id in simulation.death_events[self._death_event_cursor :]:
            organism = simulation.organisms[organism_id]
            self._event(
                death_tick,
                "death",
                str(organism_id),
                {"species_id": organism.species_id, "last_action": organism.last_action},
            )
            if death_tick == simulation.tick:
                self._deaths_by_tick.setdefault(death_tick, []).append(organism_id)
        self._death_event_cursor = len(simulation.death_events)

        for organism_id in simulation.sexual_parent_ids - self._known_sexual_parents:
            self.connection.execute(
                "INSERT INTO sexual_parents VALUES (?, ?)",
                (organism_id, simulation.tick),
            )
            self._event(simulation.tick, "sexual_parent", str(organism_id), {})
        self._known_sexual_parents.update(simulation.sexual_parent_ids)

        next_species_id = simulation._next_species_id
        for species_id in range(self._species_id_cursor, next_species_id):
            species = simulation.species[species_id]
            self._event(
                species.created_tick,
                "species_created",
                str(species.species_id),
                {
                    "representative_genome_id": species.representative_genome.genome_id,
                    "origin": species.origin,
                    "parent_species_ids": species.parent_species_ids,
                    "founder_organism_id": species.founder_organism_id,
                },
            )
        self._species_id_cursor = next_species_id

        for created_tick, left_id, right_id in simulation.alliance_events[self._alliance_event_cursor :]:
            self.connection.execute(
                "INSERT INTO alliances VALUES (?, ?, ?)",
                (left_id, right_id, created_tick),
            )
            ids = [left_id, right_id]
            self._event(created_tick, "alliance_created", f"{left_id}-{right_id}", {"members": ids})
        self._alliance_event_cursor = len(simulation.alliance_events)

        for created_tick, colony_id in simulation.colony_events[self._colony_event_cursor :]:
            colony = simulation.colonies.get(colony_id)
            if colony is not None:
                self._event(
                    created_tick,
                    "colony_created",
                    str(colony_id),
                    {"members": sorted(colony.members), "bonus": colony.bonus},
                )
        self._colony_event_cursor = len(simulation.colony_events)

    def _record_organism_states(self, simulation: Simulation) -> None:
        state_rows: list[tuple[Any, ...]] = []
        inventory_rows: list[tuple[Any, ...]] = []
        organism_ids = sorted(
            (*simulation.living_ids, *self._deaths_by_tick.get(simulation.tick, ()))
        )
        for organism_id in organism_ids:
            organism = simulation.organisms[organism_id]
            state_rows.append(
                (
                    simulation.tick,
                    organism.organism_id,
                    int(organism.alive),
                    organism.position[0],
                    organism.position[1],
                    organism.species_id,
                    organism.colony_id,
                    organism.area(simulation.catalog),
                    organism.structural_mass(simulation.catalog),
                    organism.chemical_energy(),
                    organism.energy_fraction(simulation.catalog),
                    organism.mana,
                    organism.integrity,
                    organism.maintenance_debt,
                    organism.toxin_load,
                    organism.reproduction_cooldown,
                    organism.offspring_count,
                    organism.kills,
                    organism.last_action,
                    _json(organism.statuses),
                )
            )
            for compartment, inventory in (
                ("body", organism.body),
                ("gut", organism.gut),
                ("waste", organism.waste),
            ):
                for molecule_id, batch in inventory.items():
                    inventory_rows.append(
                        (
                            simulation.tick,
                            organism.organism_id,
                            compartment,
                            molecule_id,
                            batch.count,
                            batch.energy,
                        )
                    )
        self.connection.executemany(
            "INSERT INTO organism_states VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            state_rows,
        )
        self.connection.executemany(
            "INSERT INTO organism_inventories VALUES (?, ?, ?, ?, ?, ?)",
            inventory_rows,
        )

    def _record_world_snapshot(self, simulation: Simulation) -> None:
        # Deposits are keyed by absolute [x, y] coordinates in the infinite
        # world; heat is stored as a sparse chunk table: an int64 header of
        # (chunk_x, chunk_y) pairs followed by each chunk's f64 heat grid.
        deposits = [
            [
                position[0],
                position[1],
                [
                    [molecule_id, batch.count, batch.energy]
                    for molecule_id, batch in sorted(inventory.items())
                ],
            ]
            for position, inventory in sorted(simulation.world.deposits.items())
            if inventory
        ]
        world = simulation.world
        hot = [
            (chunk.cx, chunk.cy, chunk.heat)
            for chunk in world.chunks.values()
            if chunk.has_heat
        ]
        header = (
            np.array([[cx, cy] for cx, cy, _ in hot], dtype="<i8")
            if hot
            else np.empty((0, 2), dtype="<i8")
        )
        heat_bytes = header.tobytes(order="C") + b"".join(
            heat.astype("<f8", copy=False).tobytes(order="C") for _, _, heat in hot
        )
        heat_blob = zlib.compress(heat_bytes, level=6)
        deposits_blob = zlib.compress(_json(deposits).encode("utf-8"), level=6)
        self.connection.execute(
            "INSERT INTO world_snapshots VALUES (?, ?, ?, ?, ?)",
            (
                simulation.tick,
                world.chunk_size,
                len(world.chunks),
                heat_blob,
                deposits_blob,
            ),
        )

    def _event(self, tick: int, event_type: str, entity_id: str, payload: Any) -> None:
        self.connection.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?)",
            (tick, event_type, entity_id, _json(payload)),
        )

    def close(self, simulation: Simulation | None = None) -> None:
        if self._closed:
            return
        if simulation is not None:
            if not self._tick_exists(simulation.tick):
                self.record_tick(simulation, force_snapshot=True)
            else:
                if not self._detail_exists(simulation.tick):
                    self._record_detail_states(simulation)
                if not self._snapshot_exists(simulation.tick):
                    self._record_world_snapshot(simulation)
        ended_at = datetime.now(UTC).isoformat()
        self.connection.execute(
            "INSERT OR REPLACE INTO run_metadata(key, value_json) VALUES (?, ?)",
            ("ended_utc", _json(ended_at)),
        )
        self.connection.commit()
        self.connection.close()
        manifest_path = self.run_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["ended_utc"] = ended_at
        if simulation is not None:
            manifest["final_tick"] = simulation.tick
            manifest["final_population"] = simulation.population
        manifest_path.write_text(_json(manifest) + "\n", encoding="utf-8")
        self._closed = True

    def _tick_exists(self, tick: int) -> bool:
        return self.connection.execute("SELECT 1 FROM tick_metrics WHERE tick=?", (tick,)).fetchone() is not None

    def _detail_exists(self, tick: int) -> bool:
        return self.connection.execute("SELECT 1 FROM detail_ticks WHERE tick=?", (tick,)).fetchone() is not None

    def _snapshot_exists(self, tick: int) -> bool:
        return self.connection.execute("SELECT 1 FROM world_snapshots WHERE tick=?", (tick,)).fetchone() is not None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
