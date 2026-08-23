"""Explicit Arrow schemas for raw simulator facts."""

from __future__ import annotations

import pyarrow as pa


def table_schemas() -> dict[str, pa.Schema]:
    """Return schemas whose shape is independent of a particular run."""

    # Variable-size nullable lists avoid a PyArrow 25 fixed-list/null decoding bug.
    # Spatial stages always write exactly [x, y]; Stage 0 writes null.
    cell = pa.list_(pa.int32())
    return {
        "ticks": pa.schema(
            [
                ("tick", pa.int64()),
                ("n_tapes", pa.int64()),
                ("n_free_cells", pa.int64()),
                ("pool_total", pa.int64()),
                ("pool_entropy", pa.float64()),
                ("pool_histogram", pa.list_(pa.int64(), 256)),
                ("energy_field_total", pa.float64()),
                ("energy_tape_total", pa.float64()),
                ("energy_dissipated_cum", pa.float64()),
                ("energy_influx_cum", pa.float64()),
                ("n_interactions", pa.int64()),
                ("n_writes_success", pa.int64()),
                ("n_writes_blocked", pa.int64()),
                ("n_dissolutions", pa.int64()),
                ("mean_tape_energy", pa.float64()),
                ("mean_tape_age", pa.float64()),
            ]
        ),
        "interactions": pa.schema(
            [
                ("tick", pa.int64()),
                ("round_index", pa.int64()),
                ("a_id", pa.int64()),
                ("b_id", pa.int64()),
                ("a_cell", cell),
                ("b_cell", cell),
                ("a_mutations", pa.int32()),
                ("b_mutations", pa.int32()),
                ("mutation_writes_success", pa.int32()),
                ("mutation_writes_blocked", pa.int32()),
                ("steps", pa.int64()),
                ("energy_spent", pa.float64()),
                ("writes_success", pa.int64()),
                ("writes_blocked", pa.int64()),
                ("halt_reason", pa.string()),
                ("a_bytes_changed", pa.int32()),
                ("b_bytes_changed", pa.int32()),
                ("a_hash_before", pa.string()),
                ("a_hash_after", pa.string()),
                ("b_hash_before", pa.string()),
                ("b_hash_after", pa.string()),
            ]
        ),
        "tapes": pa.schema(
            [
                ("tick", pa.int64()),
                ("tape_id", pa.int64()),
                ("cell_x", pa.int32()),
                ("cell_y", pa.int32()),
                ("age", pa.int64()),
                ("energy", pa.float64()),
                ("content_hash", pa.string()),
                ("length_nonzero", pa.int32()),
                ("byte_histogram", pa.list_(pa.int64(), 256)),
                ("full_bytes", pa.binary()),
            ]
        ),
        "lineage": pa.schema(
            [
                ("tape_id", pa.int64()),
                ("born_tick", pa.int64()),
                ("died_tick", pa.int64()),
                ("birth_cell", cell),
                ("death_cause", pa.string()),
                ("progenitor_ids", pa.list_(pa.int64())),
                ("content_hash_at_birth", pa.string()),
            ]
        ),
        "population": pa.schema(
            [
                ("epoch", pa.int64()),
                ("tick", pa.int64()),
                ("content_hash", pa.string()),
                ("count", pa.int64()),
                ("mean_age", pa.float64()),
                ("mean_energy", pa.float64()),
                ("first_seen_tick", pa.int64()),
            ]
        ),
        "events": pa.schema(
            [
                ("tick", pa.int64()),
                ("event_type", pa.string()),
                ("tape_id", pa.int64()),
                ("content_hash", pa.string()),
                ("details_json", pa.string()),
            ]
        ),
    }
