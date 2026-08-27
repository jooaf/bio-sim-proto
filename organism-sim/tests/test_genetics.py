from random import Random

from organism_sim.config import SimulationConfig
from organism_sim.genetics import GUILDS, Genome, Phenotype, TraitGene, species_color


def test_phenotypes_are_bounded_and_size_is_independent_of_metabolism() -> None:
    rng = Random(5)
    config = SimulationConfig(founder_count=1)
    samples: list[tuple[int, float]] = []
    asexual_rates: list[float] = []
    for genome_id in range(1, 80):
        genome = Genome.random(genome_id, rng)
        phenotype = Phenotype.sample(genome, rng, config)
        assert 1 <= phenotype.sight <= config.max_sight
        assert 1 <= phenotype.adult_area <= 14
        assert 0.0 <= phenotype.magic_resistance[0] <= 0.95
        assert 0.25 <= phenotype.asexual_rate <= 4.0
        samples.append((phenotype.adult_area, phenotype.basal))
        asexual_rates.append(phenotype.asexual_rate)

    # The generator does not derive metabolism from body area.
    areas_with_multiple_metabolisms = {
        area for area, _ in samples if len({round(basal, 3) for a, basal in samples if a == area}) > 1
    }
    assert areas_with_multiple_metabolisms
    assert max(asexual_rates) - min(asexual_rates) > 1.0


def test_logarithmic_recombination_cannot_overflow() -> None:
    rng = Random(71)
    low = TraitGene(500.0, 0.15, 500.0, 5000.0, logarithmic=True)
    high = TraitGene(5000.0, 0.15, 500.0, 5000.0, logarithmic=True)

    for _ in range(2000):
        child = TraitGene.blend((low, high), rng).mutated(rng, rate=1.0, magnitude=0.35)
        value = child.sample(rng)
        assert 500.0 <= value <= 5000.0


def test_guild_genomes_form_coherent_body_plans() -> None:
    rng = Random(19)
    hunters = [Genome.random(genome_id, rng, guild="hunter") for genome_id in range(1, 31)]
    grazers = [Genome.random(genome_id, rng, guild="grazer") for genome_id in range(31, 61)]

    # Guilds constrain their signature traits instead of sampling uniformly.
    assert min(g.traits["attack"].center for g in hunters) > max(g.traits["attack"].center for g in grazers)
    assert min(g.traits["speed"].center for g in hunters) > max(g.traits["speed"].center for g in grazers)
    hunter_area = sum(g.traits["adult_area"].center for g in hunters) / len(hunters)
    grazer_area = sum(g.traits["adult_area"].center for g in grazers) / len(grazers)
    assert grazer_area > hunter_area  # grazing body plans are larger on average

    # Magic affinity axes share a unit budget and trade off against resistance.
    for genome in hunters + grazers:
        affinity_total = sum(gene.center for gene in genome.magic_affinity)
        assert 0.2 <= affinity_total <= 1.8

    # Unknown guilds are rejected rather than silently ignored.
    try:
        Genome.random(1, rng, guild="unnamed")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown guild should raise ValueError")


def test_diet_anchoring_follows_catalog_chemistry() -> None:
    rng = Random(23)
    anchor = (0.7, 0.1, 0.1, 0.1)
    genome = Genome.random(1, rng, guild="grazer", diet_anchor=anchor)
    centers = tuple(gene.center for gene in genome.diet_signature)
    assert all(abs(center - value) < 0.1 for center, value in zip(centers, anchor))

    # Generalists keep a broad near-uniform diet signature.
    generalist = Genome.random(2, rng, guild="generalist")
    centers = tuple(gene.center for gene in generalist.diet_signature)
    assert max(centers) - min(centers) < 0.25


def test_guild_offspring_inherit_and_blend_guild_identity() -> None:
    rng = Random(41)
    parent = Genome.random(1, rng, guild="hunter")
    child = Genome.offspring(2, (parent,), rng, 1.0)
    assert child.guild == "hunter"

    other = Genome.random(3, rng, guild="grazer")
    hybrid = Genome.offspring(4, (parent, other), rng, 1.0)
    assert hybrid.guild == "generalist"


def test_species_colors_are_distinct_and_stable() -> None:
    rng = Random(7)
    genomes = [Genome.random(genome_id, rng, guild=guild) for genome_id, guild in enumerate(GUILDS, start=1)]
    colors = {species_color(species_id, genomes[species_id % len(genomes)]) for species_id in range(1, 25)}

    assert len(colors) >= 20  # golden-angle spacing keeps neighbours distinct
    assert all(species_color(1, genomes[0]) == species_color(1, genomes[0]) for _ in range(3))
