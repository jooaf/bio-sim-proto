# Prototype Implementation Plan

This plan intentionally prioritizes a visible, playable prototype over the full engineered architecture in `SPEC.md`. The specification remains the source of truth for a future production rewrite.

## Architecture

- `config.py`: adjustable generation and live simulation parameters
- `chemistry.py`: elements, molecule types/batches, generated catalog, energy capacity
- `genetics.py`: genome distributions, phenotype sampling, recombination, mutation, distance
- `entities.py`: organism, species, magical effect, alliance, and corpse state
- `world.py`: toroidal cells, molecule deposits, heat field, spatial occupancy
- `simulation.py`: deterministic tick loop, actions, metabolism, reactions, reproduction, death, audits
- `app.py`: pygame rendering, controls, sliders, overlays, and selected-organism inspector

## Prototype stages

1. Scaffold an independent Python/pygame-ce package.
2. Generate a bounded toroidal chemical world with exact discrete matter and continuous energy totals.
3. Spawn organisms with sampled genomes, variable footprints, metabolism independent of size, and utility-driven actions.
4. Add movement, feeding, digestion, heat, mana, toxins, detoxification, attacks, magic, reproduction, species, alliances, and colonies in compact forms.
5. Add a pygame interface with adjustable defaults and live controls.
6. Validate deterministic stepping and conservation invariants with tests.

## Simplifications

- Molecule reactions use balanced decomposition into monatomic products rather than a large reaction graph.
- Species use online centroid assignment rather than periodic clustering.
- Sexual reproduction initially supports contacting groups but normally forms pairs.
- Alliances and colonies use lightweight compatibility rules and maintenance bonuses.
- Saves, charts, and Rust FFI are deferred until the prototype demonstrates that the simulation is interesting.

## Acceptance criteria

- `uv run organism-sim` opens an interactive pygame window.
- A seeded world starts with hundreds of organisms and procedural chemistry.
- Organisms move, eat, metabolize, absorb heat, use magic, reproduce, and die.
- Matter is conserved exactly by element.
- Energy is conserved within floating-point tolerance.
- Sliders can alter simulation speed and important live coefficients; generation controls are adjustable before reset.
- Headless tests exercise conservation, toroidal wrapping, deterministic stepping, and failed reproductive energy cost.
