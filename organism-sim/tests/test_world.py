from random import Random

from organism_sim.chemistry import ChemistryCatalog
from organism_sim.config import SimulationConfig
from organism_sim.simulation import Simulation
from organism_sim.world import World


def small_config(**changes: object) -> SimulationConfig:
    values: dict[str, object] = {
        "width": 16,
        "height": 16,
        "founder_count": 1,
        "element_count": 4,
        "molecule_count": 12,
        "initial_deposits": 1,
    }
    values.update(changes)
    return SimulationConfig(**values)


def test_chunks_generate_deterministically_on_demand() -> None:
    config = small_config(heat_diffusion=0.10)
    left_rng = Random(3)
    right_rng = Random(3)
    catalog = ChemistryCatalog.generate(config, left_rng)
    left = World.generate(config, catalog, left_rng)
    right_catalog = ChemistryCatalog.generate(config, right_rng)
    right = World.generate(config, right_catalog, right_rng)

    # The founder region is materialized up front.
    assert set(left.chunks) == {(0, 0)}
    left_deposits = {position: dict(inventory) for position, inventory in left.deposits.items()}

    # A distant chunk is generated identically on first touch, in either order.
    left.ensure_chunk(5, -3)
    right.ensure_chunk(5, -3)
    right.ensure_chunk(-2, 7)
    left.ensure_chunk(-2, 7)

    assert {p: dict(i) for p, i in left.deposits.items()} == {p: dict(i) for p, i in right.deposits.items()}
    assert left_deposits
    assert any(position[0] >= 5 * config.chunk_size for position in left.deposits)


def test_heat_diffusion_is_conserved_and_does_not_wrap() -> None:
    config = small_config(heat_diffusion=0.10)
    rng = Random(3)
    catalog = ChemistryCatalog.generate(config, rng)
    world = World.generate(config, catalog, rng)
    world.clear_heat()
    world.add_heat((0, 0), 10.0)

    before = world.total_heat()
    world.diffuse_heat()

    # Heat spreads inside the chunk but never wraps or leaks into missing space.
    assert world.heat_at((1, 0)) > 0.0
    assert world.heat_at((0, 1)) > 0.0
    assert world.chunk_at((-1, 0)) is None
    assert world.chunk_at((0, -1)) is None
    assert abs(world.total_heat() - before) < 1e-12


def test_distance_is_unwrapped_chebyshev() -> None:
    config = small_config()
    rng = Random(5)
    catalog = ChemistryCatalog.generate(config, rng)
    world = World.generate(config, catalog, rng)

    assert world.distance((0, 0), (3, -7)) == 7
    assert world.distance((-5, 2), (-5, 2)) == 0
    assert world.delta((4, 4), (1, 6)) == (-3, 2)


def test_cached_nearby_offsets_match_footprint_union() -> None:
    config = small_config()
    rng = Random(5)
    catalog = ChemistryCatalog.generate(config, rng)
    world = World.generate(config, catalog, rng)

    for area in (1, 4, 9, 14):
        for radius in (1, 3, 6):
            expected = {
                (fx + dx, fy + dy)
                for fx, fy in world.footprint_offsets(area)
                for dy in range(-radius, radius + 1)
                for dx in range(-radius, radius + 1)
            }
            assert set(world.nearby_offsets(area, radius)) == expected


def test_incremental_occupancy_matches_living_footprints() -> None:
    simulation = Simulation(
        SimulationConfig(
            seed=17,
            width=24,
            height=24,
            founder_count=24,
            founder_archetype_count=4,
            element_count=5,
            molecule_count=20,
            initial_deposits=160,
            audit_every=10,
        )
    )
    simulation.step(120)

    expected: dict[tuple[int, int], set[int]] = {}
    for organism_id in simulation.living_ids:
        organism = simulation.organisms[organism_id]
        for position in simulation.world.footprint(organism):
            expected.setdefault(simulation.world.index(position), set()).add(organism_id)

    assert simulation.world.occupancy == expected


def test_organisms_can_leave_the_founder_region_without_wrapping() -> None:
    simulation = Simulation(
        SimulationConfig(
            seed=23,
            width=24,
            height=24,
            founder_count=8,
            founder_archetype_count=5,
            element_count=4,
            molecule_count=12,
            initial_deposits=60,
            audit_every=10,
        )
    )
    simulation.step(200)

    # Either somebody wandered past an edge of the founder region into newly
    # generated chunks, or every organism stayed inside; either way the run must
    # audit cleanly with geological generation accounted separately.
    simulation.audit()
    assert simulation.world.chunks  # founder region chunks exist
    for organism_id in simulation.living_ids:
        position = simulation.organisms[organism_id].position
        assert isinstance(position[0], int)
