"""Offline categorical spatial structure and block-diversity analyses."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
from numpy.random import Generator
from numpy.typing import NDArray

from analysis.diversity import hill_number
from analysis.load import load_run
from soup.substrate.bff import INSTRUCTION_SET


@dataclass(frozen=True, slots=True)
class NeighborIdentityResult:
    observed: float
    null_mean: float
    null_std: float
    excess: float
    p_value: float
    edges: int
    permutations: int


@dataclass(frozen=True, slots=True)
class NeighborByteSimilarityResult:
    observed: float
    null_mean: float
    null_std: float
    excess: float
    p_value: float
    edges: int
    tape_length: int
    permutations: int


@dataclass(frozen=True, slots=True)
class PooledBetaResult:
    observed: float
    null_mean: float
    excess: float
    p_value: float
    snapshots: int
    permutations: int


def _validate_snapshot(snapshot: pd.DataFrame, width: int, height: int) -> pd.DataFrame:
    required = {"cell_x", "cell_y", "content_hash"}
    missing = required - set(snapshot.columns)
    if missing:
        raise ValueError(f"spatial snapshot is missing columns: {sorted(missing)}")
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    frame = snapshot.loc[:, ["cell_x", "cell_y", "content_hash"]].copy()
    if frame.empty:
        return frame
    if frame[["cell_x", "cell_y"]].duplicated().any():
        raise ValueError("a spatial snapshot contains duplicate occupied cells")
    if (
        (frame["cell_x"] < 0).any()
        or (frame["cell_x"] >= width).any()
        or (frame["cell_y"] < 0).any()
        or (frame["cell_y"] >= height).any()
    ):
        raise ValueError("spatial snapshot contains an out-of-bounds cell")
    return frame.reset_index(drop=True)


def _neighbor_edges(frame: pd.DataFrame, width: int, height: int, radius: int) -> NDArray[np.int64]:
    if radius <= 0:
        raise ValueError("radius must be positive")
    row_by_cell = {
        (int(cast(Any, row.cell_x)), int(cast(Any, row.cell_y))): row_index
        for row_index, row in enumerate(frame.itertuples(index=False))
    }
    edges: set[tuple[int, int]] = set()
    for (x, y), source in row_by_cell.items():
        neighboring_cells = {
            ((x + dx) % width, (y + dy) % height)
            for dy in range(-radius, radius + 1)
            for dx in range(-radius, radius + 1)
            if dx != 0 or dy != 0
        }
        neighboring_cells.discard((x, y))
        for cell in neighboring_cells:
            target = row_by_cell.get(cell)
            if target is not None and target != source:
                edges.add((min(source, target), max(source, target)))
    if not edges:
        return np.empty((0, 2), dtype=np.int64)
    return np.asarray(sorted(edges), dtype=np.int64)


def neighbor_identity_test(
    snapshot: pd.DataFrame,
    *,
    width: int,
    height: int,
    radius: int = 1,
    permutations: int = 999,
    rng: Generator | None = None,
) -> NeighborIdentityResult:
    """Compare equal-hash neighbor frequency with a fixed-occupancy label null."""

    if permutations <= 0:
        raise ValueError("permutations must be positive")
    frame = _validate_snapshot(snapshot, width, height)
    edges = _neighbor_edges(frame, width, height, radius)
    if len(edges) == 0:
        return NeighborIdentityResult(
            observed=float("nan"),
            null_mean=float("nan"),
            null_std=float("nan"),
            excess=float("nan"),
            p_value=float("nan"),
            edges=0,
            permutations=permutations,
        )
    labels = frame["content_hash"].astype(str).to_numpy()
    observed = float(np.mean(labels[edges[:, 0]] == labels[edges[:, 1]]))
    generator = np.random.default_rng(0) if rng is None else rng
    null = np.empty(permutations, dtype=np.float64)
    for index in range(permutations):
        shuffled = generator.permutation(labels)
        null[index] = float(np.mean(shuffled[edges[:, 0]] == shuffled[edges[:, 1]]))
    return NeighborIdentityResult(
        observed=observed,
        null_mean=float(np.mean(null)),
        null_std=float(np.std(null, ddof=1)) if permutations > 1 else 0.0,
        excess=observed - float(np.mean(null)),
        p_value=float((1 + np.count_nonzero(null >= observed - 1e-15)) / (permutations + 1)),
        edges=len(edges),
        permutations=permutations,
    )


def _full_byte_matrix(snapshot: pd.DataFrame) -> NDArray[np.uint8]:
    if "full_bytes" not in snapshot.columns:
        raise ValueError("spatial snapshot is missing full_bytes")
    values = snapshot["full_bytes"].tolist()
    if not values or any(value is None for value in values):
        raise ValueError("spatial byte similarity requires a complete full-byte snapshot")
    rows = [np.frombuffer(bytes(value), dtype=np.uint8) for value in values]
    lengths = {len(row) for row in rows}
    if len(lengths) != 1 or not lengths or next(iter(lengths)) == 0:
        raise ValueError("full-byte tapes must have one shared positive length")
    return np.stack(rows)


def neighbor_byte_similarity_test(
    snapshot: pd.DataFrame,
    *,
    width: int,
    height: int,
    radius: int = 1,
    permutations: int = 999,
    rng: Generator | None = None,
) -> NeighborByteSimilarityResult:
    """Compare positional byte identity of neighbors with a tape-permutation null."""

    if permutations <= 0:
        raise ValueError("permutations must be positive")
    frame = _validate_snapshot(snapshot, width, height)
    tapes = _full_byte_matrix(snapshot.reset_index(drop=True))
    edges = _neighbor_edges(frame, width, height, radius)
    if len(edges) == 0:
        return NeighborByteSimilarityResult(
            observed=float("nan"),
            null_mean=float("nan"),
            null_std=float("nan"),
            excess=float("nan"),
            p_value=float("nan"),
            edges=0,
            tape_length=tapes.shape[1],
            permutations=permutations,
        )
    observed = float(np.mean(tapes[edges[:, 0]] == tapes[edges[:, 1]]))
    generator = np.random.default_rng(0) if rng is None else rng
    null = np.empty(permutations, dtype=np.float64)
    for index in range(permutations):
        permutation = generator.permutation(len(tapes))
        null[index] = float(
            np.mean(tapes[permutation[edges[:, 0]]] == tapes[permutation[edges[:, 1]]])
        )
    null_mean = float(np.mean(null))
    return NeighborByteSimilarityResult(
        observed=observed,
        null_mean=null_mean,
        null_std=float(np.std(null, ddof=1)) if permutations > 1 else 0.0,
        excess=observed - null_mean,
        p_value=float((1 + np.count_nonzero(null >= observed - 1e-15)) / (permutations + 1)),
        edges=len(edges),
        tape_length=tapes.shape[1],
        permutations=permutations,
    )


def pooled_neighbor_byte_similarity_test(
    snapshots: list[pd.DataFrame],
    *,
    width: int,
    height: int,
    radius: int = 1,
    permutations: int = 999,
    rng: Generator | None = None,
) -> NeighborByteSimilarityResult:
    """Test the equal-weight mean byte similarity across multiple snapshots."""

    if not snapshots:
        raise ValueError("at least one spatial snapshot is required")
    if permutations <= 0:
        raise ValueError("permutations must be positive")
    prepared: list[tuple[NDArray[np.uint8], NDArray[np.int64]]] = []
    for snapshot in snapshots:
        frame = _validate_snapshot(snapshot, width, height)
        tapes = _full_byte_matrix(snapshot.reset_index(drop=True))
        edges = _neighbor_edges(frame, width, height, radius)
        if len(edges) == 0:
            raise ValueError("every pooled snapshot must contain occupied neighbor edges")
        prepared.append((tapes, edges))
    tape_lengths = {tapes.shape[1] for tapes, _ in prepared}
    if len(tape_lengths) != 1:
        raise ValueError("pooled snapshots must share one tape length")
    observed = float(
        np.mean(
            [np.mean(tapes[edges[:, 0]] == tapes[edges[:, 1]]) for tapes, edges in prepared]
        )
    )
    generator = np.random.default_rng(0) if rng is None else rng
    null = np.empty(permutations, dtype=np.float64)
    for permutation_index in range(permutations):
        values: list[float] = []
        for tapes, edges in prepared:
            permutation = generator.permutation(len(tapes))
            values.append(
                float(
                    np.mean(
                        tapes[permutation[edges[:, 0]]]
                        == tapes[permutation[edges[:, 1]]]
                    )
                )
            )
        null[permutation_index] = float(np.mean(values))
    null_mean = float(np.mean(null))
    return NeighborByteSimilarityResult(
        observed=observed,
        null_mean=null_mean,
        null_std=float(np.std(null, ddof=1)) if permutations > 1 else 0.0,
        excess=observed - null_mean,
        p_value=float((1 + np.count_nonzero(null >= observed - 1e-15)) / (permutations + 1)),
        edges=sum(len(edges) for _, edges in prepared),
        tape_length=next(iter(tape_lengths)),
        permutations=permutations,
    )


def bff_opcode_signature_snapshot(snapshot: pd.DataFrame) -> pd.DataFrame:
    """Replace exact hashes with ordered BFF-instruction signatures."""

    frame = snapshot.copy()
    tapes = _full_byte_matrix(frame)
    frame["content_hash"] = [
        bytes(int(value) for value in tape if int(value) in INSTRUCTION_SET).hex()
        for tape in tapes
    ]
    return frame


def pooled_categorical_beta_test(
    snapshots: list[pd.DataFrame],
    *,
    width: int,
    height: int,
    block_size: int,
    permutations: int = 999,
    rng: Generator | None = None,
) -> PooledBetaResult:
    """Test equal-weight mean q=1 beta for precomputed categorical labels."""

    if not snapshots:
        raise ValueError("at least one spatial snapshot is required")
    if permutations <= 0:
        raise ValueError("permutations must be positive")
    observed_values = [
        block_beta_diversity(
            snapshot,
            width=width,
            height=height,
            block_size=block_size,
            q_values=(1.0,),
        )[1.0]
        for snapshot in snapshots
    ]
    observed = float(np.mean(observed_values))
    generator = np.random.default_rng(0) if rng is None else rng
    null = np.empty(permutations, dtype=np.float64)
    for permutation_index in range(permutations):
        values: list[float] = []
        for snapshot in snapshots:
            shuffled = snapshot.copy()
            shuffled["content_hash"] = generator.permutation(
                snapshot["content_hash"].astype(str).to_numpy()
            )
            values.append(
                block_beta_diversity(
                    shuffled,
                    width=width,
                    height=height,
                    block_size=block_size,
                    q_values=(1.0,),
                )[1.0]
            )
        null[permutation_index] = float(np.mean(values))
    null_mean = float(np.mean(null))
    return PooledBetaResult(
        observed=observed,
        null_mean=null_mean,
        excess=observed - null_mean,
        p_value=float((1 + np.count_nonzero(null >= observed - 1e-15)) / (permutations + 1)),
        snapshots=len(snapshots),
        permutations=permutations,
    )


def pooled_bff_opcode_beta_test(
    snapshots: list[pd.DataFrame],
    *,
    width: int,
    height: int,
    block_size: int,
    permutations: int = 999,
    rng: Generator | None = None,
) -> PooledBetaResult:
    """Test mean q=1 opcode-signature beta across fixed snapshots."""

    prepared = [bff_opcode_signature_snapshot(snapshot) for snapshot in snapshots]
    return pooled_categorical_beta_test(
        prepared,
        width=width,
        height=height,
        block_size=block_size,
        permutations=permutations,
        rng=rng,
    )


def block_beta_diversity(
    snapshot: pd.DataFrame,
    *,
    width: int,
    height: int,
    block_size: int,
    q_values: tuple[float, ...] = (0.0, 1.0, 2.0),
) -> dict[float, float]:
    """Return multiplicative gamma/weighted-alpha diversity by lattice block."""

    if block_size <= 0:
        raise ValueError("block_size must be positive")
    frame = _validate_snapshot(snapshot, width, height)
    if frame.empty:
        return {q: float("nan") for q in q_values}
    frame["block_x"] = frame["cell_x"].astype(int) // block_size
    frame["block_y"] = frame["cell_y"].astype(int) // block_size
    total = len(frame)
    global_counts = frame["content_hash"].value_counts().to_numpy(dtype=np.int64)
    result: dict[float, float] = {}
    grouped = list(frame.groupby(["block_x", "block_y"], sort=True))
    for q in q_values:
        gamma = hill_number(global_counts, q)
        alpha = 0.0
        for _, block in grouped:
            block_counts = block["content_hash"].value_counts().to_numpy(dtype=np.int64)
            alpha += (len(block) / total) * hill_number(block_counts, q)
        result[q] = float(gamma / alpha) if alpha > 0.0 else float("nan")
    return result


def block_beta_permutation_test(
    snapshot: pd.DataFrame,
    *,
    width: int,
    height: int,
    block_size: int,
    permutations: int = 999,
    q_values: tuple[float, ...] = (0.0, 1.0, 2.0),
    rng: Generator | None = None,
) -> pd.DataFrame:
    """Compare observed block beta diversity with permuted content labels."""

    if permutations <= 0:
        raise ValueError("permutations must be positive")
    frame = _validate_snapshot(snapshot, width, height)
    if frame.empty:
        return pd.DataFrame(
            [
                {
                    "q": q,
                    "observed_beta": float("nan"),
                    "null_mean_beta": float("nan"),
                    "beta_excess": float("nan"),
                    "p_value": float("nan"),
                    "permutations": permutations,
                }
                for q in q_values
            ]
        )
    observed = block_beta_diversity(
        frame,
        width=width,
        height=height,
        block_size=block_size,
        q_values=q_values,
    )
    generator = np.random.default_rng(0) if rng is None else rng
    null: dict[float, NDArray[np.float64]] = {
        q: np.empty(permutations, dtype=np.float64) for q in q_values
    }
    labels = frame["content_hash"].astype(str).to_numpy()
    for permutation_index in range(permutations):
        shuffled = frame.copy()
        shuffled["content_hash"] = generator.permutation(labels)
        permuted_beta = block_beta_diversity(
            shuffled,
            width=width,
            height=height,
            block_size=block_size,
            q_values=q_values,
        )
        for q in q_values:
            null[q][permutation_index] = permuted_beta[q]
    rows: list[dict[str, float | int]] = []
    for q in q_values:
        null_values = null[q]
        observed_value = observed[q]
        rows.append(
            {
                "q": q,
                "observed_beta": observed_value,
                "null_mean_beta": float(np.mean(null_values)),
                "beta_excess": observed_value - float(np.mean(null_values)),
                "p_value": float(
                    (1 + np.count_nonzero(null_values >= observed_value - 1e-15))
                    / (permutations + 1)
                ),
                "permutations": permutations,
            }
        )
    return pd.DataFrame(rows)


def write_spatial_report(
    run_dir: str | Path,
    *,
    block_size: int = 8,
    permutations: int = 999,
    seed: int = 20260822,
    output: str | Path | None = None,
) -> Path:
    """Analyze every Stage 2 tape snapshot and write CSV plus Markdown results."""

    data = load_run(run_dir)
    if data.config.run.stage != 2:
        raise ValueError("spatial analysis requires a Stage 2 run")
    tapes = data.table("tapes")
    generator = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    for tick_value, snapshot in tapes.groupby("tick", sort=True):
        identity = neighbor_identity_test(
            snapshot,
            width=data.config.world.width,
            height=data.config.world.height,
            permutations=permutations,
            rng=generator,
        )
        beta = block_beta_permutation_test(
            snapshot,
            width=data.config.world.width,
            height=data.config.world.height,
            block_size=block_size,
            permutations=permutations,
            rng=generator,
        )
        beta_records = cast(list[dict[str, Any]], beta.to_dict(orient="records"))
        for beta_row in beta_records:
            rows.append(
                {
                    "tick": int(cast(Any, tick_value)),
                    "neighbor_identity": identity.observed,
                    "neighbor_null_mean": identity.null_mean,
                    "neighbor_excess": identity.excess,
                    "neighbor_p_value": identity.p_value,
                    **beta_row,
                }
            )
    results = pd.DataFrame(rows)
    result_path = data.run_dir / "analysis_spatial.csv"
    results.to_csv(result_path, index=False)
    target = Path(output) if output is not None else data.run_dir / "stage2_spatial_report.md"
    if results.empty:
        summary = "No spatial snapshots were available."
    else:
        final_tick = int(results["tick"].max())
        final = results[results["tick"] == final_tick]
        q1 = final[np.isclose(final["q"], 1.0)].iloc[0]
        summary = "\n".join(
            [
                f"- Final analyzed tick: {final_tick}",
                f"- Neighbor identity excess: {float(q1['neighbor_excess']):.6f}",
                f"- Neighbor permutation p-value: {float(q1['neighbor_p_value']):.4f}",
                f"- q=1 block beta: {float(q1['observed_beta']):.6f}",
                f"- q=1 beta-null mean: {float(q1['null_mean_beta']):.6f}",
                f"- q=1 beta permutation p-value: {float(q1['p_value']):.4f}",
            ]
        )
    target.write_text(
        "\n".join(
            [
                "# Stage 2 spatial analysis",
                "",
                f"- Run: `{data.run_dir}`",
                f"- Block size: {block_size}",
                f"- Permutations per snapshot/test: {permutations}",
                f"- Analysis seed: {seed}",
                summary,
                f"- Full results: `{result_path.name}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--block-size", type=int, default=8)
    parser.add_argument("--permutations", type=int, default=999)
    parser.add_argument("--seed", type=int, default=20260822)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(
        write_spatial_report(
            args.run_dir,
            block_size=args.block_size,
            permutations=args.permutations,
            seed=args.seed,
            output=args.output,
        )
    )


if __name__ == "__main__":
    main()
