//! Rust tick kernel for the emergent organism simulation.
//!
//! Self-contained port of the Python `Simulation` engine behind a coarse PyO3
//! boundary. The kernel is SELF-DETERMINISTIC (own xoshiro256++ RNG); it does
//! not reproduce Python's Mersenne Twister streams. Validation is via
//! matter/energy conservation and same-seed determinism.

mod behavior;
mod chemistry;
mod config;
mod emergence;
mod entities;
mod genetics;
mod rng;
mod scheduler;
mod seasons;
mod world;

use behavior::intent::{
    ActionIntent, IntentCandidate, IntentKind, IntentTarget, CANDIDATE_FEATURE_COUNT,
    MAX_INTENT_CANDIDATES,
};
use behavior::neural::NeuralState;
use behavior::BehaviorModel;
use chemistry::{
    add_batch, inventory_count, inventory_energy, Batch, Catalog, Inventory, ReactionRule,
};
use config::SimConfig;
use emergence::{Bond, InternalGuest, ModulePrimitive};
use entities::{last_action, Colony, Corpse, MagicEffect, Organism, Species, Stats};
use genetics::{
    Genome, Phenotype, ACTION_COUNT, ACTION_NAMES, A_ALLY, A_ATTACK, A_DETOX, A_EAT, A_FLEE,
    A_FORAGE, A_HEAT, A_HUNT, A_MAGIC, A_REPRODUCE, A_REST, A_SEEK_MATE, A_WANDER, F_HUNGER,
    F_MATE,
};
use rng::{median, py_round, Fnv, Rng};
use rustc_hash::{FxHashMap, FxHashSet};
use scheduler::Scheduler;
use seasons::{SeasonEvent, SeasonProfile, SeasonState};
use world::{GenMolecule, Position, World, WorldGenParams};

use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use rayon::prelude::*;
use std::collections::{BTreeMap, BTreeSet};
use std::sync::Arc;

const CORPSE_TTL: u32 = 200;
const MAX_GENOME_DISTANCE_CACHE: usize = 2_000_000;
const ENERGY_ABSOLUTE_TOLERANCE: f64 = 1e-7;
const ENERGY_INITIAL_RELATIVE_TOLERANCE: f64 = 1e-10;
const ENERGY_ACCOUNTING_RELATIVE_TOLERANCE: f64 = 5e-12;
const DIRECTIONS_CLOCKWISE: [(i32, i32); 8] = [
    (0, -1),
    (1, -1),
    (1, 0),
    (1, 1),
    (0, 1),
    (-1, 1),
    (-1, 0),
    (-1, -1),
];
const EGOCENTRIC_FORWARD: [f32; 8] = [1.0, 0.707, 0.0, -0.707, -1.0, -0.707, 0.0, 0.707];
const EGOCENTRIC_RIGHT: [f32; 8] = [0.0, 0.707, 1.0, 0.707, 0.0, -0.707, -1.0, -0.707];
const NO_ORGANISM_INDEX: usize = usize::MAX;
const NO_BATCH_INDEX: usize = usize::MAX;
type SharedOffsets = Arc<[(i32, i32)]>;
type NearbyOffsetCache = FxHashMap<(usize, usize), SharedOffsets>;
type FoodCandidate = (Position, u16, f64);

struct CellObservations {
    food: Option<FoodCandidate>,
    heat_position: Position,
    local_heat: f64,
}

#[derive(Clone, Debug)]
struct RankedIntentCandidate {
    salience: f32,
    tie_key: u64,
    candidate: IntentCandidate,
}

#[derive(Default)]
struct MemoryProbeDelta {
    state_l1: f64,
    decision: bool,
    argmax_changed: bool,
    ambiguous_food: bool,
    ambiguous_argmax_changed: bool,
    stateful_return: bool,
    zero_state_return: bool,
}

struct ParallelProposal {
    actor_id: u32,
    intent: ActionIntent,
    sight_cost: f64,
    next_neural_state: NeuralState,
    current_food_slot: u8,
    current_food_signal: f32,
    neural_failure: bool,
    memory_probe: MemoryProbeDelta,
}

struct ParallelMaintenanceDelta {
    organism_id: u32,
    position: Position,
    heat: f64,
    brain_paid: f64,
    hidden_brain_paid: f64,
    recurrent_brain_paid: f64,
    dirty_old_area: Option<usize>,
    expelled: Option<Batch>,
    byproduct: Option<(f64, f64)>,
    attrition_kill: bool,
}

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
enum ConflictKey {
    Organism(u32),
    Occupancy(Position),
    Deposit(Position, u16),
    Heat(Position),
    Alliance(u32, u32),
    Lifecycle,
    Effects,
    Reproduction,
}

struct ParallelSelfResolutionDelta {
    organism_id: u32,
    position: Position,
    heat: f64,
    selected_kind: IntentKind,
    final_kind: IntentKind,
    neural_failure: bool,
    memory_probe: MemoryProbeDelta,
}

fn unit_f32(value: f64) -> f32 {
    value.clamp(0.0, 1.0) as f32
}

fn diet_reactivity_mean(phenotype: &Phenotype, catalog: &Catalog) -> f64 {
    let mut weighted_reactivity = 0.0;
    let mut total_match = 0.0;
    for molecule in &catalog.molecules {
        let dietary_match = genetics::similarity(&molecule.signature, &phenotype.diet_signature);
        total_match += dietary_match;
        weighted_reactivity += dietary_match * molecule.reactivity;
    }
    if total_match > 0.0 {
        weighted_reactivity / total_match
    } else {
        0.0
    }
}

fn chemistry_signals_for(organism: &Organism, world: &World, config: &SimConfig) -> (f64, f64) {
    if !config.dynamic_chemistry_enabled {
        return (0.0, 0.0);
    }
    let (catalyst, toxin) = world.byproduct_at(organism.position);
    let diet_reactivity = organism.diet_reactivity_mean;
    let sensitivity = organism.phenotype.toxin_sensitivity.iter().sum::<f64>() / 4.0;
    let fit = config.chemistry_coupling
        * (catalyst * diet_reactivity - toxin * sensitivity).clamp(-1.0, 1.0);
    (fit, toxin)
}

fn guest_reactivity_for(organism: &Organism, catalog: &Catalog) -> f64 {
    let Some(cellular) = &organism.cellular else {
        return 0.0;
    };
    let mut total_units = 0.0;
    let mut weighted_reactivity = 0.0;
    for guest in &cellular.guests {
        for batch in &guest.inventory {
            if batch.count <= 0 {
                continue;
            }
            let units = batch.count as f64;
            total_units += units;
            weighted_reactivity += units * catalog.molecules[batch.molecule_id as usize].reactivity;
        }
    }
    if total_units > 0.0 {
        (weighted_reactivity / total_units).clamp(0.0, 1.0)
    } else {
        0.0
    }
}

fn calculate_byproduct_emission(
    batch: &Batch,
    reactivity: f64,
    permeability: f64,
    strength: f64,
) -> (f64, f64) {
    let energy = batch.energy.max(0.0);
    (
        energy * strength * (0.25 + reactivity),
        energy * strength * reactivity * permeability,
    )
}

fn energy_tolerance(initial_energy: f64, generated_energy: f64) -> f64 {
    let initial_scale = initial_energy.abs();
    let accounting_scale = initial_scale + generated_energy.abs();
    ENERGY_ABSOLUTE_TOLERANCE
        .max(initial_scale * ENERGY_INITIAL_RELATIVE_TOLERANCE)
        .max(accounting_scale * ENERGY_ACCOUNTING_RELATIVE_TOLERANCE)
}

fn direction_index(direction: (i32, i32)) -> usize {
    DIRECTIONS_CLOCKWISE
        .iter()
        .position(|&candidate| candidate == direction)
        .unwrap_or(2)
}

fn egocentric_direction(facing: (i32, i32), slot: usize) -> (i32, i32) {
    DIRECTIONS_CLOCKWISE[(direction_index(facing) + slot) % DIRECTIONS_CLOCKWISE.len()]
}

fn egocentric_slot(facing: (i32, i32), delta: (i64, i64)) -> usize {
    let signed = (delta.0.signum() as i32, delta.1.signum() as i32);
    (direction_index(signed) + DIRECTIONS_CLOCKWISE.len() - direction_index(facing))
        % DIRECTIONS_CLOCKWISE.len()
}

fn position_tie_key(position: Position) -> u64 {
    (position.0 as u64).rotate_left(32) ^ position.1 as u64
}

fn make_intent_candidate(
    last_intent_kind: u8,
    kind: IntentKind,
    target: IntentTarget,
    duration: u32,
    chemical_cost: f64,
    mana_cost: f64,
    reference_energy: f64,
) -> IntentCandidate {
    let mut features = [0.0; CANDIDATE_FEATURE_COUNT];
    features[behavior::intent::C_CHEMICAL_COST] =
        unit_f32(chemical_cost / reference_energy.max(1e-9));
    features[behavior::intent::C_MANA_COST] = unit_f32(mana_cost / reference_energy.max(1e-9));
    features[behavior::intent::C_DURATION] = unit_f32(duration as f64 / 8.0);
    features[behavior::intent::C_TARGET_KNOWN] = if target == IntentTarget::None {
        0.0
    } else {
        1.0
    };
    features[behavior::intent::C_PERSISTENCE] = if last_intent_kind == kind as u8 {
        1.0
    } else {
        0.0
    };
    IntentCandidate {
        kind,
        target,
        features,
        predicted_duration_ticks: duration,
        predicted_chemical_cost: chemical_cost,
        predicted_mana_cost: mana_cost,
    }
}

fn append_ranked_candidates(
    candidates: &mut Vec<IntentCandidate>,
    pool: &mut Vec<RankedIntentCandidate>,
    limit: usize,
) {
    pool.sort_by(|left, right| {
        right
            .salience
            .total_cmp(&left.salience)
            .then_with(|| left.tie_key.cmp(&right.tie_key))
    });
    candidates.extend(
        pool.iter()
            .take(limit)
            .map(|ranked| ranked.candidate.clone()),
    );
    pool.clear();
}

fn v2_last_action_code(kind: IntentKind) -> u8 {
    match kind {
        IntentKind::Wait => last_action::V2_WAIT,
        IntentKind::Move => last_action::V2_MOVE,
        IntentKind::Ingest => last_action::V2_INGEST,
        IntentKind::Repair => last_action::V2_REPAIR,
        IntentKind::AbsorbHeat => last_action::V2_ABSORB_HEAT,
        IntentKind::Detox => last_action::V2_DETOX,
        IntentKind::Attack => last_action::V2_ATTACK,
        IntentKind::CastMagic => last_action::V2_CAST_MAGIC,
        IntentKind::Reproduce => last_action::V2_REPRODUCE,
        IntentKind::ProposeAlliance => last_action::V2_PROPOSE_ALLIANCE,
    }
}

/// Alphabetical action order (Python `sorted(eligible)` iteration order).
const ACTION_ORDER_ALPHA: [usize; ACTION_COUNT] = [
    A_ALLY,
    A_ATTACK,
    A_DETOX,
    A_EAT,
    A_FLEE,
    A_FORAGE,
    A_HEAT,
    A_HUNT,
    A_MAGIC,
    A_REPRODUCE,
    A_REST,
    A_SEEK_MATE,
    A_WANDER,
];

/// Streams: chemistry / world / founders / dynamics, derived from the seed.
struct Streams {
    chemistry: Rng,
    world: Rng,
    founders: Rng,
    dynamics: Rng,
    seasons: Rng,
}

struct DeadRecord {
    organism_id: u32,
    genome_id: u32,
    lineage_id: u32,
    species_id: u32,
    parent_ids: [u32; 2],
    parent_count: u8,
    generation: u32,
    birth_tick: u32,
    death_tick: u32,
    position: Position,
    cause: u8,
    offspring_count: u32,
    kills: u32,
}

impl Streams {
    fn from_seed(seed: i64) -> Streams {
        let s = seed as u64;
        Streams {
            chemistry: Rng::new(rng::mix64(s ^ 0xA5A5_0000_0000_0001)),
            world: Rng::new(rng::mix64(s ^ 0xA5A5_0000_0000_0002)),
            founders: Rng::new(rng::mix64(s ^ 0xA5A5_0000_0000_0003)),
            dynamics: Rng::new(rng::mix64(s ^ 0xA5A5_0000_0000_0004)),
            seasons: Rng::new(rng::mix64(s ^ 0xA5A5_0000_0000_0005)),
        }
    }
}

#[derive(Clone, Copy)]
enum TaxonKey {
    Lineage,
    Species,
    TraitsOnly,
}

#[derive(Clone, Copy)]
struct CohortPreset {
    tile_size: i64,
    bins: i64,
    representatives: usize,
    taxon: TaxonKey,
    include_dynamic_state: bool,
}

#[derive(Debug)]
struct CohortCompression {
    protected: usize,
    classes: usize,
    representatives: usize,
    represented_work: usize,
}

#[derive(Default, Debug)]
struct EmergenceMetrics {
    module_instances: usize,
    expressed_module_instances: usize,
    module_primitive_counts: [usize; ModulePrimitive::COUNT],
    compartment_tags_used: usize,
    compartment_tag_counts: [usize; emergence::COMPARTMENT_TAGS as usize],
    physical_bonds: usize,
    bonded_cells: usize,
    bond_components: usize,
    largest_bond_component: usize,
    internal_guests: usize,
    expression_variance: f64,
}

#[derive(Default, Debug)]
struct EmergenceStats {
    bond_formations: u64,
    bond_breaks: u64,
    energy_exchanges: u64,
    internalizations: u64,
    guest_replications: u64,
    guest_losses: u64,
    guest_energy_demand: f64,
    guest_energy_exchange: f64,
    component_actions: u64,
    component_moves: u64,
    propagules: u64,
    propagated_cells: u64,
}

#[derive(Default, Debug)]
struct ChemistryMetrics {
    regime_mean: f64,
    regime_variance: f64,
    species_association: f64,
    guest_regime_delta: f64,
    guest_hosts: usize,
}

struct ComponentMovePlan {
    member_id: u32,
    origin: Position,
    destination: Position,
    cost: f64,
    old_cells: Vec<Position>,
    new_cells: Vec<Position>,
}

#[derive(Default, Debug)]
struct PhaseProfile {
    heat_diffusion_ns: u128,
    deposit_production_ns: u128,
    effects_ns: u128,
    decomposition_ns: u128,
    organism_loop_ns: u128,
    organism_ordering_ns: u128,
    upkeep_ns: u128,
    digestion_ns: u128,
    decision_ns: u128,
    parallel_maintenance_ns: u128,
    parallel_prepare_ns: u128,
    parallel_intent_ns: u128,
    parallel_grouping_ns: u128,
    parallel_resolution_ns: u128,
    corpse_expiry_ns: u128,
    occupancy_refresh_ns: u128,
    audit_ns: u128,
    total_ns: u128,
}

#[derive(Debug)]
struct CompressibilityMetrics {
    population: usize,
    exact_policy_keys: usize,
    lineage_count: usize,
    species_count: usize,
    rare_lineage_organisms: usize,
    rare_species_organisms: usize,
    novel_organisms: usize,
    physiology_critical: usize,
    low_reserve: usize,
    critical_reserve: usize,
    near_integrity_death: usize,
    near_debt_death: usize,
    near_toxin_threshold: usize,
    post_lifespan: usize,
    active_status: usize,
    action_due_now: usize,
    action_due_within_8: usize,
    nonempty_gut: usize,
    colony_members: usize,
    organism_tiles_8: usize,
    organism_tiles_16: usize,
    organism_tiles_32: usize,
    generated_chunks: usize,
    active_heat_chunks: usize,
    active_heat_cells: usize,
    active_deposit_positions: usize,
    active_deposit_batches: usize,
    occupied_cells: usize,
    lineage_safe: CohortCompression,
    species_safe: CohortCompression,
    trait_only: CohortCompression,
}

pub struct KernelState {
    config: SimConfig,
    catalog: Catalog,
    reaction_rules: Vec<ReactionRule>,
    reaction_reactant_flags: Vec<bool>,
    world: World,
    /// Dense living working set; permanent IDs map through organism_indices.
    organisms: Vec<Organism>,
    organism_indices: Vec<usize>,
    dead_positions: Vec<Position>,
    living: FxHashSet<u32>,
    /// Same IDs as `living`, maintained in canonical pre-shuffle order.
    living_ordered: BTreeSet<u32>,
    /// genome_owners[genome_id - 1] -> organism_id, or zero before placement.
    genome_owners: Vec<u32>,
    dead_records: Vec<DeadRecord>,
    /// species[id - 1].
    species: Vec<Species>,
    corpses: FxHashMap<u32, Corpse>,
    effects: FxHashMap<u32, MagicEffect>,
    colonies: FxHashMap<u32, Colony>,
    alliances: FxHashSet<(u32, u32)>,
    bonds: FxHashMap<(u32, u32), Bond>,
    emergence_stats: EmergenceStats,
    stats: Stats,
    tick: u32,
    next_organism_id: u32,
    next_genome_id: u32,
    next_species_id: u32,
    next_effect_id: u32,
    next_corpse_id: u32,
    next_colony_id: u32,
    occupancy_dirty: FxHashMap<u32, Vec<Position>>,
    genome_distances: FxHashMap<(u32, u32), f64>,
    reference_energy: f64,
    reference_body_mass: f64,
    initial_elements: Vec<i64>,
    initial_energy: f64,
    rng: Rng,
    seasons: SeasonState,

    // ---- reusable buffers (no per-tick allocation) ----
    order: Vec<u32>,
    diffuse_sources: Vec<((i64, i64), Vec<f64>)>,
    diffuse_source_index: FxHashMap<(i64, i64), usize>,
    diffuse_scratch: Vec<f64>,
    deposit_positions: Vec<Position>,
    reaction_positions: Vec<Position>,
    reaction_batch_indices: Vec<usize>,
    reaction_products: Vec<Batch>,
    heat_adds: Vec<(Position, f64)>,
    footprint_buf: Vec<Position>,
    action_cells_r1: Vec<Position>,
    action_cells_sight: Vec<Position>,
    action_nearby: Vec<u32>,
    action_contact: Vec<u32>,
    action_visible_mate_draws: Vec<(u32, f64)>,
    action_contact_mate_draws: Vec<(u32, f64)>,
    action_scores: Vec<(usize, f64)>,
    action_weights: Vec<f64>,
    v2_candidates: Vec<IntentCandidate>,
    v2_candidate_pool: Vec<RankedIntentCandidate>,
    v2_scores: Vec<f64>,
    v2_footprint: Vec<Position>,
    child_candidates: Vec<Position>,
    fp_offsets: FxHashMap<usize, SharedOffsets>,
    nearby_offsets: NearbyOffsetCache,
    bond_candidates: FxHashSet<(u32, u32)>,
    bond_candidate_scratch: Vec<(u32, u32)>,
    bond_edge_scratch: Vec<((u32, u32), Bond)>,
    bond_scratch: Vec<Bond>,
    signal_update_scratch: Vec<(u32, f32)>,
    emergence_id_scratch: Vec<u32>,
    component_roots: Vec<u32>,
    component_members: FxHashMap<u32, Vec<u32>>,
    component_acted: FxHashSet<u32>,
    parallel_pool: Option<rayon::ThreadPool>,
    parallel_due: Vec<u32>,
}

fn normalized_bin(value: f64, minimum: f64, maximum: f64, bins: i64) -> i64 {
    if !value.is_finite() || maximum <= minimum {
        return 0;
    }
    let scaled = ((value - minimum) / (maximum - minimum)).clamp(0.0, 1.0);
    (scaled * bins as f64).floor().min((bins - 1) as f64) as i64
}

fn exact_policy_key(organism: &Organism) -> u64 {
    let mut hash = Fnv::new();
    hash.i64(organism.position.0);
    hash.i64(organism.position.1);
    hash.u64(organism.species_id as u64);
    hash.u64(organism.lineage_id as u64);
    organism.phenotype.hash_into(&mut hash);
    for batch in &organism.body {
        hash.u64(batch.molecule_id as u64);
        hash.i64(batch.count);
        hash.f64(batch.energy);
    }
    hash.f64(organism.mana);
    hash.f64(organism.integrity);
    hash.f64(organism.maintenance_debt);
    hash.f64(organism.toxin_load);
    hash.u64(organism.birth_tick as u64);
    hash.u64(organism.next_action_tick as u64);
    hash.u64(organism.colony_id.unwrap_or(0) as u64);
    hash.u64(organism.water_status.is_some() as u64);
    hash.u64(organism.earth_status.is_some() as u64);
    hash.finish()
}

fn cohort_key(
    organism: &Organism,
    catalog: &Catalog,
    tick: u32,
    reference_energy: f64,
    colony_bonus: f64,
    preset: CohortPreset,
) -> u64 {
    let phenotype = &organism.phenotype;
    let mut hash = Fnv::new();
    hash.i64(organism.position.0.div_euclid(preset.tile_size));
    hash.i64(organism.position.1.div_euclid(preset.tile_size));
    match preset.taxon {
        TaxonKey::Lineage => hash.u64(organism.lineage_id as u64),
        TaxonKey::Species => hash.u64(organism.species_id as u64),
        TaxonKey::TraitsOnly => hash.u64(organism.genome.guild as u64),
    }
    hash.i64(normalized_bin(colony_bonus, 0.0, 1.0, preset.bins));

    // Distributional cohorts retain phenotype, reserve, age, toxin, inventory,
    // and action-phase variation inside representative particles. State-bucket
    // experiments can opt into making the dynamic dimensions class keys.
    if preset.include_dynamic_state {
        let body_energy = organism.chemical_energy();
        let body_capacity: f64 = organism
            .body
            .iter()
            .map(|batch| {
                catalog.molecules[batch.molecule_id as usize].energy_capacity * batch.count as f64
            })
            .sum();
        let age = tick.saturating_sub(organism.birth_tick) as f64;
        let action_wait = organism.next_action_tick.saturating_sub(tick).min(64) as f64;
        let first_energy_molecule = organism
            .body
            .iter()
            .find(|batch| batch.energy > 1e-12)
            .map(|batch| batch.molecule_id as u64)
            .unwrap_or(u16::MAX as u64);
        hash.i64(normalized_bin(
            organism.mana / phenotype.mana_capacity.max(1e-12),
            0.0,
            1.0,
            preset.bins,
        ));
        hash.i64(normalized_bin(
            body_energy / body_capacity.max(1e-12),
            0.0,
            1.0,
            preset.bins,
        ));
        hash.i64(normalized_bin(
            organism.integrity / organism.max_integrity.max(1e-12),
            0.0,
            1.0,
            preset.bins,
        ));
        hash.i64(normalized_bin(
            organism.maintenance_debt / (4.0 * reference_energy).max(1e-12),
            0.0,
            1.0,
            preset.bins,
        ));
        hash.i64(normalized_bin(
            organism.toxin_load / phenotype.toxin_tolerance.max(1e-12),
            0.0,
            2.0,
            preset.bins,
        ));
        hash.i64(normalized_bin(
            age / (phenotype.lifespan as f64).max(1.0),
            0.0,
            1.0,
            preset.bins,
        ));
        hash.i64(normalized_bin(action_wait, 0.0, 64.0, preset.bins));
        hash.u64(first_energy_molecule);
        hash.u64(organism.body.len().min(64) as u64);
    }
    hash.finish()
}

fn compression_summary(
    class_counts: &FxHashMap<u64, usize>,
    protected: usize,
    representatives: usize,
) -> CohortCompression {
    let representative_count: usize = class_counts
        .values()
        .map(|&count| count.min(representatives))
        .sum();
    CohortCompression {
        protected,
        classes: class_counts.len(),
        representatives: representative_count,
        represented_work: protected + representative_count,
    }
}

fn v3_area(organism: &Organism, catalog: &Catalog) -> usize {
    let mass = organism.peek_structural_mass(catalog) as f64;
    let ratio = (mass / organism.target_mass.max(1.0)).min(1.0);
    py_round(organism.phenotype.adult_area as f64 * ratio)
        .max(1)
        .min(organism.phenotype.adult_area) as usize
}

fn v3_local_maintenance(
    organism: &mut Organism,
    config: &SimConfig,
    catalog: &Catalog,
    world: &World,
    reference_energy: f64,
    tick: u32,
    colony_bonus: f64,
) -> ParallelMaintenanceDelta {
    let mut rng = scheduler::phase_rng(
        config.seed,
        tick,
        organism.organism_id,
        0,
        scheduler::MAINTENANCE_SUBSYSTEM,
    );
    let position = organism.position;
    let mut heat = 0.0;
    let (local_fit, local_toxin) = chemistry_signals_for(organism, world, config);

    let decay = organism.mana * config.mana_decay;
    organism.mana -= decay;
    heat += decay;

    let (brain_base_demand, brain_hidden_demand, brain_recurrent_demand) =
        match config.behavior_model {
            BehaviorModel::LegacyLinearMacroV1 => (0.0, 0.0, 0.0),
            BehaviorModel::LinearIntentV2 => (
                reference_energy * config.brain_cost_multiplier * config.brain_base_cost,
                0.0,
                0.0,
            ),
            BehaviorModel::RecurrentIntentV2 => {
                let policy = organism
                    .phenotype
                    .recurrent_policy
                    .as_ref()
                    .expect("recurrent organisms must have a recurrent phenotype");
                (
                    reference_energy * config.brain_cost_multiplier * config.brain_base_cost,
                    reference_energy
                        * config.brain_cost_multiplier
                        * config.brain_hidden_cost
                        * policy.hidden_expression_mean(),
                    reference_energy
                        * config.brain_cost_multiplier
                        * config.brain_recurrent_cost
                        * policy.recurrent_expression_mean(),
                )
            }
        };
    let brain_demand = brain_base_demand + brain_hidden_demand + brain_recurrent_demand;
    let physiological_demand = organism.phenotype.basal
        * reference_energy
        * config.maintenance_cost_multiplier
        * (1.0 - colony_bonus);
    let mana_target = physiological_demand * organism.phenotype.mana_preference;
    let mana_paid = organism.mana.min(mana_target);
    organism.mana -= mana_paid;
    let physiological_chemical_demand = physiological_demand - mana_paid;
    let chemical_paid = organism.consume_body_energy(physiological_chemical_demand + brain_demand);
    let brain_paid = (chemical_paid - physiological_chemical_demand).clamp(0.0, brain_demand);
    let paid = mana_paid + chemical_paid;
    let demand = physiological_demand + brain_demand;
    heat += paid;
    let hidden_brain_paid = if brain_demand > 0.0 {
        brain_paid * brain_hidden_demand / brain_demand
    } else {
        0.0
    };
    let recurrent_brain_paid = if brain_demand > 0.0 {
        brain_paid * brain_recurrent_demand / brain_demand
    } else {
        0.0
    };
    organism.brain_energy_spent += brain_paid;
    organism.hidden_brain_energy_spent += hidden_brain_paid;
    organism.recurrent_brain_energy_spent += recurrent_brain_paid;

    let deficit = demand - paid;
    if deficit > 1e-12 {
        organism.maintenance_debt += deficit;
        organism.integrity -= deficit / reference_energy.max(1e-9) * 0.25;
    } else {
        organism.maintenance_debt = (organism.maintenance_debt - demand * 0.2).max(0.0);
    }
    if organism.toxin_load > organism.phenotype.toxin_tolerance {
        let excess = organism.toxin_load - organism.phenotype.toxin_tolerance;
        organism.integrity -= excess * 0.0015;
    }
    organism.toxin_load *= 0.999;

    let age = tick as i64 - organism.birth_tick as i64;
    if age > organism.phenotype.lifespan {
        let ratio = age as f64 / organism.phenotype.lifespan as f64;
        let mut base_hazard = (0.0005 * ratio * ratio).min(0.08);
        let support_budget = (organism.chemical_energy() * 0.002)
            .min(organism.mana * 0.002)
            .min(base_hazard * reference_energy);
        if support_budget > 0.0 {
            let mana_support = organism.mana.min(support_budget * 0.5);
            organism.mana -= mana_support;
            let chemical_support = organism.consume_body_energy(support_budget - mana_support);
            let spent = mana_support + chemical_support;
            heat += spent;
            let denominator = (base_hazard * reference_energy).max(1e-9);
            base_hazard *= (1.0 - spent / denominator).max(0.05);
        }
        if rng.chance(base_hazard) {
            organism.integrity = 0.0;
        }
    }
    let attrition_kill =
        organism.integrity <= 0.0 || organism.maintenance_debt > reference_energy * 4.0;
    let mut dirty_old_area = None;
    let mut expelled = None;
    let mut byproduct = None;

    if !attrition_kill
        && !organism.gut.is_empty()
        && rng.f64() <= (config.reaction_rate * 0.35).min(1.0)
    {
        let old_area = v3_area(organism, catalog);
        let molecule_id = organism.gut[0].molecule_id;
        let mut product = {
            let source = &mut organism.gut[0];
            let taken = source.take(1);
            if source.count == 0 {
                organism.gut.remove(0);
            }
            taken
        };
        let molecule = &catalog.molecules[molecule_id as usize];
        let dietary_match =
            genetics::similarity(&molecule.signature, &organism.phenotype.diet_signature);
        let activation = organism.consume_body_energy(reference_energy * 0.0005);
        heat += activation;
        let catalysis =
            organism.substrate_module_expression(ModulePrimitive::Catalysis, molecule_id);
        let guest_boost = if config.dynamic_chemistry_enabled {
            1.0 + config.guest_niche_coupling * guest_reactivity_for(organism, catalog)
        } else {
            1.0
        };
        let capture_target = (product.energy
            * organism.phenotype.digestion
            * dietary_match
            * (1.0 + config.emergence_module_effect * catalysis)
            * (1.0 + local_fit)
            * guest_boost)
            .clamp(0.0, product.energy);
        let captured = organism.add_body_energy(capture_target, catalog);
        let remaining = product.energy - captured;
        let process_heat = remaining * 0.15;
        heat += process_heat;
        product.energy = (remaining - process_heat).max(0.0);
        if config.dynamic_chemistry_enabled {
            byproduct = Some(calculate_byproduct_emission(
                &product,
                molecule.reactivity,
                molecule.permeability,
                config.byproduct_strength,
            ));
        }
        let sensitivity: f64 = (0..4)
            .map(|index| molecule.signature[index] * organism.phenotype.toxin_sensitivity[index])
            .sum();
        let environmental_toxin_scale = if config.dynamic_chemistry_enabled {
            1.0 + (local_toxin * config.chemistry_coupling).clamp(0.0, 2.0)
        } else {
            1.0
        };
        organism.toxin_load +=
            molecule.reactivity * molecule.permeability * sensitivity * environmental_toxin_scale;
        let can_grow = (organism.peek_structural_mass(catalog) as f64) < organism.target_mass * 1.3;
        if rng.chance(organism.phenotype.assimilation * dietary_match) && can_grow {
            dirty_old_area = Some(old_area);
            add_batch(&mut organism.body, product);
            organism.invalidate_body_cache();
        } else {
            add_batch(&mut organism.waste, product);
        }
        if organism.toxin_load > organism.phenotype.toxin_tolerance {
            let detox_cost = organism.chemical_energy().min(reference_energy * 0.002);
            let spent = organism.consume_body_energy(detox_cost);
            heat += spent;
            organism.toxin_load =
                (organism.toxin_load - spent / reference_energy.max(1e-9) * 2.0).max(0.0);
        }
        if inventory_count(&organism.waste) > 12 {
            let source = &mut organism.waste[0];
            let count = (source.count / 2).max(1);
            let taken = source.take(count);
            if source.count == 0 {
                organism.waste.remove(0);
            }
            expelled = Some(taken);
        }
    }

    ParallelMaintenanceDelta {
        organism_id: organism.organism_id,
        position,
        heat,
        brain_paid,
        hidden_brain_paid,
        recurrent_brain_paid,
        dirty_old_area,
        expelled,
        byproduct,
        attrition_kill,
    }
}

fn v3_commit_self_proposal(
    organism: &mut Organism,
    proposal: ParallelProposal,
    reference_energy: f64,
    tick: u32,
    update_memory_trace: bool,
) -> ParallelSelfResolutionDelta {
    let position = organism.position;
    let mut heat = 0.0;
    if proposal.sight_cost > 0.0 {
        let spent = organism.consume_body_energy(proposal.sight_cost);
        heat += spent;
    }
    let final_kind = match proposal.intent.kind {
        IntentKind::Wait => IntentKind::Wait,
        IntentKind::Repair if organism.integrity < organism.max_integrity => {
            let cost = organism.chemical_energy().min(reference_energy * 0.005);
            let spent = organism.consume_body_energy(cost);
            heat += spent;
            organism.integrity =
                (organism.integrity + spent / reference_energy).min(organism.max_integrity);
            IntentKind::Repair
        }
        IntentKind::Detox if organism.toxin_load > 0.0 => {
            let cost = organism.chemical_energy().min(reference_energy * 0.01);
            let spent = organism.consume_body_energy(cost);
            heat += spent;
            organism.toxin_load =
                (organism.toxin_load - 3.0 * spent / reference_energy.max(1e-9)).max(0.0);
            IntentKind::Detox
        }
        _ => IntentKind::Wait,
    };
    organism.last_intent_kind = final_kind as u8;
    organism.last_action = v2_last_action_code(final_kind);
    organism.next_action_tick = tick + proposal.intent.predicted_duration_ticks.max(1);
    organism.decision_count += 1;
    organism.neural_state = proposal.next_neural_state;
    if update_memory_trace {
        organism.previous_food_slot = proposal.current_food_slot;
        organism.previous_food_signal = proposal.current_food_signal;
    }
    if proposal.neural_failure {
        organism.neural_numerical_errors += 1;
    }
    ParallelSelfResolutionDelta {
        organism_id: organism.organism_id,
        position,
        heat,
        selected_kind: proposal.intent.kind,
        final_kind,
        neural_failure: proposal.neural_failure,
        memory_probe: proposal.memory_probe,
    }
}

impl KernelState {
    pub fn new(config: SimConfig) -> Result<KernelState, String> {
        config.validate()?;
        if !config.behavior_model.is_implemented() {
            return Err(format!(
                "behavior_model {:?} is schema-only in the Stage 1 scaffold",
                config.behavior_model.as_str()
            ));
        }
        let mut streams = Streams::from_seed(config.seed);
        let catalog = Catalog::generate(&config, &mut streams.chemistry);
        let reaction_rules = if config.dynamic_chemistry_enabled {
            catalog.reaction_rules(config.reaction_rule_count)
        } else {
            Vec::new()
        };
        let mut reaction_reactant_flags = vec![false; catalog.molecules.len()];
        for rule in &reaction_rules {
            reaction_reactant_flags[rule.a as usize] = true;
            reaction_reactant_flags[rule.b as usize] = true;
        }
        let gen_molecules: Vec<GenMolecule> = catalog
            .molecules
            .iter()
            .map(|m| GenMolecule {
                molecule_id: m.molecule_id,
                energy_capacity: m.energy_capacity,
                composition: m.composition.clone(),
            })
            .collect();
        let params = WorldGenParams {
            region_width: config.width,
            region_height: config.height,
            chunk_size: config.chunk_size,
            initial_deposits: config.initial_deposits,
            batch_min: config.initial_batch_min,
            batch_max: config.initial_batch_max,
            element_count: config.element_count,
            molecule_weights: None,
        };
        let terrain_seed = streams.world.next_u64();
        let world = World::generate(params, gen_molecules, terrain_seed);
        let seasons = SeasonState::new(&config, streams.seasons);
        let parallel_pool = if config.scheduler == Scheduler::ParallelV3 {
            let mut builder = rayon::ThreadPoolBuilder::new()
                .thread_name(|index| format!("organism-sim-v3-{index}"));
            if config.parallel_workers > 0 {
                builder = builder.num_threads(config.parallel_workers);
            }
            Some(
                builder
                    .build()
                    .map_err(|error| format!("parallel scheduler init failed: {error}"))?,
            )
        } else {
            None
        };

        let mut state = KernelState {
            reference_energy: catalog.reference_energy,
            config,
            catalog,
            reaction_rules,
            reaction_reactant_flags,
            world,
            organisms: Vec::new(),
            organism_indices: Vec::new(),
            dead_positions: Vec::new(),
            living: FxHashSet::default(),
            living_ordered: BTreeSet::new(),
            genome_owners: Vec::new(),
            dead_records: Vec::new(),
            species: Vec::new(),
            corpses: FxHashMap::default(),
            effects: FxHashMap::default(),
            colonies: FxHashMap::default(),
            alliances: FxHashSet::default(),
            bonds: FxHashMap::default(),
            emergence_stats: EmergenceStats::default(),
            stats: Stats::default(),
            tick: 0,
            next_organism_id: 1,
            next_genome_id: 1,
            next_species_id: 1,
            next_effect_id: 1,
            next_corpse_id: 1,
            next_colony_id: 1,
            occupancy_dirty: FxHashMap::default(),
            genome_distances: FxHashMap::default(),
            reference_body_mass: 1.0,
            initial_elements: Vec::new(),
            initial_energy: 0.0,
            rng: streams.dynamics,
            seasons,
            order: Vec::new(),
            diffuse_sources: Vec::new(),
            diffuse_source_index: FxHashMap::default(),
            diffuse_scratch: Vec::new(),
            deposit_positions: Vec::new(),
            reaction_positions: Vec::new(),
            reaction_batch_indices: Vec::new(),
            reaction_products: Vec::new(),
            heat_adds: Vec::new(),
            footprint_buf: Vec::new(),
            action_cells_r1: Vec::new(),
            action_cells_sight: Vec::new(),
            action_nearby: Vec::new(),
            action_contact: Vec::new(),
            action_visible_mate_draws: Vec::new(),
            action_contact_mate_draws: Vec::new(),
            action_scores: Vec::new(),
            action_weights: Vec::new(),
            v2_candidates: Vec::with_capacity(MAX_INTENT_CANDIDATES),
            v2_candidate_pool: Vec::new(),
            v2_scores: Vec::with_capacity(MAX_INTENT_CANDIDATES),
            v2_footprint: Vec::new(),
            child_candidates: Vec::new(),
            fp_offsets: FxHashMap::default(),
            nearby_offsets: FxHashMap::default(),
            bond_candidates: FxHashSet::default(),
            bond_candidate_scratch: Vec::new(),
            bond_edge_scratch: Vec::new(),
            bond_scratch: Vec::new(),
            signal_update_scratch: Vec::new(),
            emergence_id_scratch: Vec::new(),
            component_roots: Vec::new(),
            component_members: FxHashMap::default(),
            component_acted: FxHashSet::default(),
            parallel_pool,
            parallel_due: Vec::new(),
        };
        let founders_rng = streams.founders;
        state.spawn_founders(founders_rng);
        if state.config.deposit_match_ecology {
            let weights = state.founder_body_weights();
            state.world.set_molecule_weights(weights);
        }
        let mut masses: Vec<f64> = state
            .living
            .iter()
            .map(|&id| state.organism(id).peek_structural_mass(&state.catalog) as f64)
            .collect();
        if !masses.is_empty() {
            state.reference_body_mass = median(&mut masses);
        }
        state.initial_elements = state.dynamic_element_totals();
        state.initial_energy = state.total_energy() - state.world.generated_energy;
        Ok(state)
    }

    // ------------------------------------------------------------- accessors

    #[inline]
    fn organism_index(&self, id: u32) -> usize {
        let index = self.organism_indices[id as usize - 1];
        assert_ne!(index, NO_ORGANISM_INDEX, "organism {id} is not living");
        index
    }

    #[inline]
    fn has_organism(&self, id: u32) -> bool {
        id > 0
            && self
                .organism_indices
                .get(id as usize - 1)
                .is_some_and(|&index| index != NO_ORGANISM_INDEX)
    }

    #[inline]
    fn organism_mut(&mut self, id: u32) -> &mut Organism {
        let index = self.organism_index(id);
        &mut self.organisms[index]
    }

    #[inline]
    fn organism(&self, id: u32) -> &Organism {
        &self.organisms[self.organism_index(id)]
    }

    fn insert_organism(&mut self, organism: Organism) {
        let id = organism.organism_id;
        let index = self.organisms.len();
        self.organism_indices[id as usize - 1] = index;
        self.dead_positions[id as usize - 1] = organism.position;
        self.organisms.push(organism);
    }

    fn remove_organism(&mut self, id: u32) -> Organism {
        let index = self.organism_index(id);
        self.organism_indices[id as usize - 1] = NO_ORGANISM_INDEX;
        let removed = self.organisms.swap_remove(index);
        self.dead_positions[id as usize - 1] = removed.position;
        if index < self.organisms.len() {
            let moved_id = self.organisms[index].organism_id;
            self.organism_indices[moved_id as usize - 1] = index;
        }
        removed
    }

    fn position_for_id(&self, id: u32) -> Position {
        if self.has_organism(id) {
            self.organism(id).position
        } else {
            self.dead_positions
                .get(id as usize - 1)
                .copied()
                .unwrap_or((0, 0))
        }
    }

    pub fn population(&self) -> usize {
        self.living.len()
    }

    pub fn tick(&self) -> u32 {
        self.tick
    }

    fn effective_worker_count(&self) -> usize {
        self.parallel_pool
            .as_ref()
            .map_or(1, rayon::ThreadPool::current_num_threads)
    }

    fn emergence_metrics(&self) -> EmergenceMetrics {
        if !self.config.cellular_emergence_enabled {
            return EmergenceMetrics::default();
        }
        let mut metrics = EmergenceMetrics {
            physical_bonds: self.bonds.len(),
            ..EmergenceMetrics::default()
        };
        let mut expression_sum = 0.0;
        let mut expression_squared_sum = 0.0;
        let mut expression_count = 0usize;
        for &organism_id in &self.living {
            let organism = self.organism(organism_id);
            if let (Some(genome), Some(cellular)) = (&organism.genome.emergence, &organism.cellular)
            {
                metrics.module_instances += genome.modules.len();
                for module in &genome.modules {
                    metrics.module_primitive_counts[module.primitive as usize] += 1;
                    metrics.compartment_tag_counts[module.compartment_tag as usize] += 1;
                }
                metrics.expressed_module_instances += cellular
                    .expression
                    .iter()
                    .filter(|&&value| value >= 0.5)
                    .count();
                let tags: FxHashSet<u8> = genome
                    .modules
                    .iter()
                    .map(|module| module.compartment_tag)
                    .collect();
                metrics.compartment_tags_used += tags.len();
                metrics.internal_guests += cellular.guests.len();
                for &expression in &cellular.expression {
                    let value = expression as f64;
                    expression_sum += value;
                    expression_squared_sum += value * value;
                    expression_count += 1;
                }
            }
        }
        if expression_count > 0 {
            let mean = expression_sum / expression_count as f64;
            metrics.expression_variance =
                (expression_squared_sum / expression_count as f64 - mean * mean).max(0.0);
        }

        let mut adjacency: FxHashMap<u32, Vec<u32>> = FxHashMap::default();
        for bond in self.bonds.values() {
            if self.living.contains(&bond.left) && self.living.contains(&bond.right) {
                adjacency.entry(bond.left).or_default().push(bond.right);
                adjacency.entry(bond.right).or_default().push(bond.left);
            }
        }
        metrics.bonded_cells = adjacency.len();
        let mut visited: FxHashSet<u32> = FxHashSet::default();
        let mut stack = Vec::new();
        for &start in adjacency.keys() {
            if !visited.insert(start) {
                continue;
            }
            metrics.bond_components += 1;
            stack.clear();
            stack.push(start);
            let mut size = 0;
            while let Some(current) = stack.pop() {
                size += 1;
                if let Some(neighbors) = adjacency.get(&current) {
                    for &neighbor in neighbors {
                        if visited.insert(neighbor) {
                            stack.push(neighbor);
                        }
                    }
                }
            }
            metrics.largest_bond_component = metrics.largest_bond_component.max(size);
        }
        metrics
    }

    /// Summarize spatial association between living populations and the local
    /// chemical regime. The regime is a bounded catalyst-minus-toxin score;
    /// this deliberately measures an environmental fact rather than assigning
    /// an ecological role to an organism.
    fn chemistry_metrics(&self) -> ChemistryMetrics {
        if !self.config.dynamic_chemistry_enabled || self.living_ordered.is_empty() {
            return ChemistryMetrics::default();
        }

        let population = self.living_ordered.len() as f64;
        let mut sum = 0.0;
        let mut sum_squared = 0.0;
        let mut species_groups: BTreeMap<u32, (usize, f64)> = BTreeMap::new();
        let mut guest_sum = 0.0;
        let mut guest_count = 0usize;
        let mut no_guest_sum = 0.0;
        let mut no_guest_count = 0usize;
        for &organism_id in &self.living_ordered {
            let organism = self.organism(organism_id);
            let (catalyst, toxin) = self.world.byproduct_at(organism.position);
            let total = catalyst + toxin;
            let regime = if total > 0.0 {
                (catalyst - toxin) / (1.0 + total)
            } else {
                0.0
            };
            sum += regime;
            sum_squared += regime * regime;
            let group = species_groups
                .entry(organism.species_id)
                .or_insert((0, 0.0));
            group.0 += 1;
            group.1 += regime;
            let has_guest = organism
                .cellular
                .as_ref()
                .is_some_and(|cellular| !cellular.guests.is_empty());
            if has_guest {
                guest_sum += regime;
                guest_count += 1;
            } else {
                no_guest_sum += regime;
                no_guest_count += 1;
            }
        }

        let mean = sum / population;
        let total_sum_squares = (sum_squared - sum * sum / population).max(0.0);
        let between_sum_squares = species_groups
            .values()
            .map(|&(count, group_sum)| {
                let count = count as f64;
                count * (group_sum / count - mean).powi(2)
            })
            .sum::<f64>();
        let species_association = if total_sum_squares > 1.0e-12 {
            (between_sum_squares / total_sum_squares).clamp(0.0, 1.0)
        } else {
            0.0
        };
        let guest_mean = if guest_count > 0 {
            guest_sum / guest_count as f64
        } else {
            0.0
        };
        let no_guest_mean = if no_guest_count > 0 {
            no_guest_sum / no_guest_count as f64
        } else {
            0.0
        };
        ChemistryMetrics {
            regime_mean: mean,
            regime_variance: total_sum_squares / population,
            species_association,
            guest_regime_delta: if guest_count > 0 && no_guest_count > 0 {
                guest_mean - no_guest_mean
            } else {
                0.0
            },
            guest_hosts: guest_count,
        }
    }

    fn compressibility_metrics(&self) -> CompressibilityMetrics {
        const RARE_LIMIT: usize = 32;
        const NOVEL_TICKS: u32 = 64;

        let lineage_safe_preset = CohortPreset {
            tile_size: 8,
            bins: 32,
            representatives: 8,
            taxon: TaxonKey::Lineage,
            include_dynamic_state: false,
        };
        let species_safe_preset = CohortPreset {
            tile_size: 16,
            bins: 16,
            representatives: 8,
            taxon: TaxonKey::Species,
            include_dynamic_state: false,
        };
        let trait_only_preset = CohortPreset {
            tile_size: 32,
            bins: 8,
            representatives: 4,
            taxon: TaxonKey::TraitsOnly,
            include_dynamic_state: false,
        };

        let mut lineage_populations: FxHashMap<u32, usize> = FxHashMap::default();
        let mut species_populations: FxHashMap<u32, usize> = FxHashMap::default();
        for &organism_id in &self.living {
            let organism = self.organism(organism_id);
            *lineage_populations.entry(organism.lineage_id).or_default() += 1;
            *species_populations.entry(organism.species_id).or_default() += 1;
        }

        let mut exact_keys: FxHashSet<u64> = FxHashSet::default();
        let mut tiles_8: FxHashSet<Position> = FxHashSet::default();
        let mut tiles_16: FxHashSet<Position> = FxHashSet::default();
        let mut tiles_32: FxHashSet<Position> = FxHashSet::default();
        let mut lineage_classes: FxHashMap<u64, usize> = FxHashMap::default();
        let mut species_classes: FxHashMap<u64, usize> = FxHashMap::default();
        let mut trait_classes: FxHashMap<u64, usize> = FxHashMap::default();

        let mut rare_lineage_organisms = 0;
        let mut rare_species_organisms = 0;
        let mut novel_organisms = 0;
        let mut physiology_critical = 0;
        let mut low_reserve = 0;
        let mut critical_reserve = 0;
        let mut near_integrity_death = 0;
        let mut near_debt_death = 0;
        let mut near_toxin_threshold = 0;
        let mut post_lifespan = 0;
        let mut active_status = 0;
        let mut action_due_now = 0;
        let mut action_due_within_8 = 0;
        let mut nonempty_gut = 0;
        let mut colony_members = 0;
        let mut lineage_protected = 0;
        let mut species_protected = 0;
        let mut trait_protected = 0;

        for &organism_id in &self.living {
            let organism = self.organism(organism_id);
            let phenotype = &organism.phenotype;
            let age_ticks = self.tick.saturating_sub(organism.birth_tick);
            let age = age_ticks as i64;
            let colony_bonus = if self.config.replaces_abstract_colonies() {
                0.0
            } else {
                organism
                    .colony_id
                    .and_then(|colony_id| self.colonies.get(&colony_id))
                    .map(|colony| colony.bonus)
                    .unwrap_or(0.0)
            };
            let demand = phenotype.basal
                * self.reference_energy
                * self.config.maintenance_cost_multiplier
                * (1.0 - colony_bonus);
            let reserve_ticks = (organism.mana + organism.chemical_energy()) / demand.max(1e-12);
            let is_low_reserve = reserve_ticks <= 8.0;
            let is_critical_reserve = reserve_ticks <= 2.0;
            let is_near_integrity = organism.integrity <= organism.max_integrity * 0.10;
            let is_near_debt = organism.maintenance_debt >= self.reference_energy * 3.5;
            let is_near_toxin = organism.toxin_load >= phenotype.toxin_tolerance.max(1e-12) * 0.90;
            let is_post_lifespan = age > phenotype.lifespan;
            let has_status = organism.water_status.is_some() || organism.earth_status.is_some();
            // Toxin-threshold and old-age channels remain cohort-eligible via
            // representative distributions and bounded event counts. Only
            // imminent solvency/death states and active statuses force an
            // individual fallback here.
            let is_physiology_critical =
                is_critical_reserve || is_near_integrity || is_near_debt || has_status;
            let is_novel = age_ticks <= NOVEL_TICKS;
            let is_rare_lineage = lineage_populations[&organism.lineage_id] <= RARE_LIMIT;
            let is_rare_species = species_populations[&organism.species_id] <= RARE_LIMIT;
            let protect_lineage = is_physiology_critical || is_novel || is_rare_lineage;
            let protect_species = is_physiology_critical || is_novel || is_rare_species;
            let protect_trait = is_physiology_critical || is_novel;

            exact_keys.insert(exact_policy_key(organism));
            tiles_8.insert((
                organism.position.0.div_euclid(8),
                organism.position.1.div_euclid(8),
            ));
            tiles_16.insert((
                organism.position.0.div_euclid(16),
                organism.position.1.div_euclid(16),
            ));
            tiles_32.insert((
                organism.position.0.div_euclid(32),
                organism.position.1.div_euclid(32),
            ));

            if protect_lineage {
                lineage_protected += 1;
            } else {
                *lineage_classes
                    .entry(cohort_key(
                        organism,
                        &self.catalog,
                        self.tick,
                        self.reference_energy,
                        colony_bonus,
                        lineage_safe_preset,
                    ))
                    .or_default() += 1;
            }
            if protect_species {
                species_protected += 1;
            } else {
                *species_classes
                    .entry(cohort_key(
                        organism,
                        &self.catalog,
                        self.tick,
                        self.reference_energy,
                        colony_bonus,
                        species_safe_preset,
                    ))
                    .or_default() += 1;
            }
            if protect_trait {
                trait_protected += 1;
            } else {
                *trait_classes
                    .entry(cohort_key(
                        organism,
                        &self.catalog,
                        self.tick,
                        self.reference_energy,
                        colony_bonus,
                        trait_only_preset,
                    ))
                    .or_default() += 1;
            }

            rare_lineage_organisms += is_rare_lineage as usize;
            rare_species_organisms += is_rare_species as usize;
            novel_organisms += is_novel as usize;
            physiology_critical += is_physiology_critical as usize;
            low_reserve += is_low_reserve as usize;
            critical_reserve += is_critical_reserve as usize;
            near_integrity_death += is_near_integrity as usize;
            near_debt_death += is_near_debt as usize;
            near_toxin_threshold += is_near_toxin as usize;
            post_lifespan += is_post_lifespan as usize;
            active_status += has_status as usize;
            action_due_now += (organism.next_action_tick <= self.tick) as usize;
            action_due_within_8 +=
                (organism.next_action_tick <= self.tick.saturating_add(8)) as usize;
            nonempty_gut += (!organism.gut.is_empty()) as usize;
            colony_members += organism.colony_id.is_some() as usize;
        }

        let active_heat_chunks = self
            .world
            .chunks
            .values()
            .filter(|chunk| chunk.heat.iter().any(|&heat| heat > 1e-12))
            .count();
        let active_heat_cells = self
            .world
            .chunks
            .values()
            .map(|chunk| chunk.heat.iter().filter(|&&heat| heat > 1e-12).count())
            .sum();
        let active_deposit_positions = self
            .world
            .deposits
            .values()
            .filter(|inventory| inventory.iter().any(|batch| batch.count > 0))
            .count();
        let active_deposit_batches = self
            .world
            .deposits
            .values()
            .map(|inventory| inventory.iter().filter(|batch| batch.count > 0).count())
            .sum();

        CompressibilityMetrics {
            population: self.living.len(),
            exact_policy_keys: exact_keys.len(),
            lineage_count: lineage_populations.len(),
            species_count: species_populations.len(),
            rare_lineage_organisms,
            rare_species_organisms,
            novel_organisms,
            physiology_critical,
            low_reserve,
            critical_reserve,
            near_integrity_death,
            near_debt_death,
            near_toxin_threshold,
            post_lifespan,
            active_status,
            action_due_now,
            action_due_within_8,
            nonempty_gut,
            colony_members,
            organism_tiles_8: tiles_8.len(),
            organism_tiles_16: tiles_16.len(),
            organism_tiles_32: tiles_32.len(),
            generated_chunks: self.world.chunks.len(),
            active_heat_chunks,
            active_heat_cells,
            active_deposit_positions,
            active_deposit_batches,
            occupied_cells: self.world.occupied_cells,
            lineage_safe: compression_summary(
                &lineage_classes,
                lineage_protected,
                lineage_safe_preset.representatives,
            ),
            species_safe: compression_summary(
                &species_classes,
                species_protected,
                species_safe_preset.representatives,
            ),
            trait_only: compression_summary(
                &trait_classes,
                trait_protected,
                trait_only_preset.representatives,
            ),
        }
    }

    // ---------------------------------------------------------------- setup

    fn sample_diet_anchor(&mut self, guild: usize, rng: &mut Rng) -> Option<[f64; 4]> {
        if guild == 0 {
            return None;
        }
        let mut ordered: Vec<usize> = (0..self.catalog.molecules.len()).collect();
        if guild == 1 {
            ordered.sort_by(|&a, &b| {
                let ma = &self.catalog.molecules[a];
                let mb = &self.catalog.molecules[b];
                ma.complexity
                    .partial_cmp(&mb.complexity)
                    .unwrap()
                    .then(mb.stability.partial_cmp(&ma.stability).unwrap())
            });
        } else if guild == 2 {
            ordered.sort_by(|&a, &b| {
                self.catalog.molecules[b]
                    .energy_capacity
                    .partial_cmp(&self.catalog.molecules[a].energy_capacity)
                    .unwrap()
            });
        }
        let pool_len = ordered.len().max(2) / 2;
        let pool: Vec<usize> = ordered.into_iter().take(pool_len.max(2)).collect();
        let k = 2.min(pool.len());
        let picks = rng.sample_indices(pool.len(), k);
        let mut anchor = [0.0f64; 4];
        for &p in &picks {
            let signature = self.catalog.molecules[pool[p]].signature;
            for (value, component) in anchor.iter_mut().zip(signature) {
                *value += component;
            }
        }
        for value in &mut anchor {
            *value /= picks.len() as f64;
        }
        let total: f64 = anchor.iter().sum();
        for value in &mut anchor {
            *value /= total;
        }
        Some(anchor)
    }

    fn claim_genome_id(&mut self) -> u32 {
        let id = self.next_genome_id;
        self.next_genome_id += 1;
        self.genome_owners.push(0);
        id
    }
    fn claim_organism_id(&mut self) -> u32 {
        let id = self.next_organism_id;
        self.next_organism_id += 1;
        self.organism_indices.push(NO_ORGANISM_INDEX);
        self.dead_positions.push((0, 0));
        id
    }

    fn spawn_founders(&mut self, mut rng: Rng) {
        let archetype_count = self
            .config
            .founder_archetype_count
            .min(self.config.founder_count);
        let mut archetypes: Vec<Genome> = Vec::with_capacity(archetype_count);
        for index in 0..archetype_count {
            let guild = index % genetics::GUILD_COUNT;
            let anchor = self.sample_diet_anchor(guild, &mut rng);
            let genome = Genome::random(
                self.claim_genome_id(),
                &mut rng,
                guild,
                anchor,
                &self.config,
            );
            archetypes.push(genome);
        }
        let mut archetype_species: FxHashMap<usize, u32> = FxHashMap::default();
        for founder_index in 0..self.config.founder_count {
            let archetype_index = if founder_index < archetype_count {
                founder_index
            } else {
                rng.below(archetype_count as u64) as usize
            };
            let parent_genome = &archetypes[archetype_index];
            let mut genome = Genome::offspring(
                self.claim_genome_id(),
                &[parent_genome],
                &mut rng,
                0.20,
                &self.config,
            );
            if let Some(recurrent) = &mut genome.recurrent_policy {
                recurrent.silence_memory();
            }
            let phenotype = Phenotype::sample(&genome, &mut rng, &self.config);
            // Body built from digestible molecules so morphology follows diet.
            let diet = phenotype.diet_signature;
            let mut digestible: Vec<usize> = (0..self.catalog.molecules.len()).collect();
            digestible.sort_by(|&a, &b| {
                let sim_a = genetics::similarity(&self.catalog.molecules[a].signature, &diet);
                let sim_b = genetics::similarity(&self.catalog.molecules[b].signature, &diet);
                sim_b.partial_cmp(&sim_a).unwrap()
            });
            let pool_len = (digestible.len() / 3).max(3);
            let pool: Vec<usize> = digestible.into_iter().take(pool_len).collect();
            let k_choice = rng.randint(2, 4).min(pool.len() as i64) as usize;
            let choices = rng.sample_indices(pool.len(), k_choice);
            let total_units = (phenotype.adult_area * rng.randint(2, 4)).max(4);
            let mut body: Inventory = Vec::new();
            for (index, &pool_idx) in choices.iter().enumerate() {
                let molecule = &self.catalog.molecules[pool[pool_idx]];
                let count = (total_units / choices.len() as i64
                    + if (index as i64) < total_units % choices.len() as i64 {
                        1
                    } else {
                        0
                    })
                .max(1);
                add_batch(
                    &mut body,
                    Batch {
                        molecule_id: molecule.molecule_id,
                        count,
                        energy: molecule.energy_capacity * count as f64 * rng.uniform(0.45, 0.95),
                    },
                );
            }
            let target_mass = self.catalog.inventory_mass(&body) as f64;
            let organism_id = self.claim_organism_id();
            let mut organism = Organism::new(
                organism_id,
                organism_id,
                genome.clone(),
                phenotype,
                body,
                target_mass,
            );
            organism.diet_reactivity_mean =
                diet_reactivity_mean(&organism.phenotype, &self.catalog);
            organism.mana = rng.uniform(0.0, organism.phenotype.mana_capacity * 0.2);
            organism.max_integrity = (4.0
                + organism.phenotype.adult_area as f64 * organism.phenotype.density * 2.0)
                .max(2.0);
            organism.integrity = organism.max_integrity;
            if !self.place_founder(&mut organism, &mut rng) {
                continue;
            }
            let species_id = match archetype_species.get(&archetype_index) {
                Some(&sid) => {
                    self.species[sid as usize - 1].population += 1;
                    sid
                }
                None => {
                    let sid = self.create_species(&genome, 0, Vec::new(), None);
                    archetype_species.insert(archetype_index, sid);
                    sid
                }
            };
            organism.species_id = species_id;
            let organism_id = organism.organism_id;
            self.genome_owners[organism.genome.genome_id as usize - 1] = organism_id;
            self.living.insert(organism_id);
            self.living_ordered.insert(organism_id);
            let footprint = self.footprint_of(&mut organism);
            self.world.add_to_occupancy(organism_id, &footprint);
            self.insert_organism(organism);
        }
    }

    fn place_founder(&mut self, organism: &mut Organism, rng: &mut Rng) -> bool {
        for _ in 0..300 {
            let x = rng.below(self.config.width as u64) as i64;
            let y = rng.below(self.config.height as u64) as i64;
            if self.can_place(organism, (x, y), organism.organism_id) {
                organism.position = (x, y);
                return true;
            }
        }
        false
    }

    fn founder_body_weights(&self) -> Vec<f64> {
        let mut totals = vec![0.0f64; self.catalog.molecules.len()];
        for &id in &self.living {
            for batch in &self.organisms[self.organism_indices[id as usize - 1]].body {
                totals[batch.molecule_id as usize] += batch.count as f64;
            }
        }
        let total: f64 = totals.iter().sum();
        if total <= 0.0 {
            return vec![1.0; totals.len()];
        }
        totals.iter().map(|v| v / total).collect()
    }

    // --------------------------------------------------------- footprints

    fn footprint_offsets(&mut self, area: usize) -> SharedOffsets {
        if let Some(offsets) = self.fp_offsets.get(&area) {
            return Arc::clone(offsets);
        }
        let mut candidates: Vec<(i32, i32)> = Vec::new();
        let mut radius = 0i32;
        while candidates.len() < area {
            candidates.clear();
            for dy in -radius..=radius {
                for dx in -radius..=radius {
                    candidates.push((dx, dy));
                }
            }
            candidates.sort_by(|a, b| {
                let da = (a.0 * a.0 + a.1 * a.1) as f64;
                let db = (b.0 * b.0 + b.1 * b.1) as f64;
                da.partial_cmp(&db)
                    .unwrap()
                    .then(a.1.abs().cmp(&b.1.abs()))
                    .then(a.0.abs().cmp(&b.0.abs()))
                    .then(a.cmp(b))
            });
            radius += 1;
        }
        candidates.truncate(area);
        let offsets: SharedOffsets = candidates.into();
        self.fp_offsets.insert(area, Arc::clone(&offsets));
        offsets
    }

    fn nearby_offsets(&mut self, area: usize, radius: usize) -> SharedOffsets {
        let key = (area, radius);
        if let Some(offsets) = self.nearby_offsets.get(&key) {
            return Arc::clone(offsets);
        }
        let fp = self.footprint_offsets(area);
        let mut set: FxHashSet<(i32, i32)> = FxHashSet::default();
        let r = radius as i32;
        for &(fx, fy) in fp.iter() {
            for dy in -r..=r {
                for dx in -r..=r {
                    set.insert((fx + dx, fy + dy));
                }
            }
        }
        let mut offsets: Vec<(i32, i32)> = set.into_iter().collect();
        offsets.sort();
        let offsets: SharedOffsets = offsets.into();
        self.nearby_offsets.insert(key, Arc::clone(&offsets));
        offsets
    }

    fn footprint_area(&mut self, organism_id: u32) -> usize {
        let catalog = &self.catalog;
        self.organisms[self.organism_indices[organism_id as usize - 1]].area(catalog)
    }

    /// Compute the organism's footprint (at its current position) into buf.
    /// Returns the area used.
    fn footprint_into(&mut self, organism_id: u32, buf: &mut Vec<Position>) -> usize {
        let area = self.footprint_area(organism_id);
        let (ox, oy) = self.organisms[self.organism_indices[organism_id as usize - 1]].position;
        let offsets = self.footprint_offsets(area);
        buf.clear();
        buf.extend(
            offsets
                .iter()
                .map(|&(dx, dy)| (ox + dx as i64, oy + dy as i64)),
        );
        self.world.ensure_positions(buf);
        area
    }

    fn footprint_cells(&mut self, organism_id: u32) -> Vec<Position> {
        let mut cells = Vec::new();
        self.footprint_into(organism_id, &mut cells);
        cells
    }

    fn footprint_of(&mut self, organism: &mut Organism) -> Vec<Position> {
        let area = organism.area(&self.catalog);
        let (ox, oy) = organism.position;
        let offsets = self.footprint_offsets(area);
        let cells: Vec<Position> = offsets
            .iter()
            .map(|&(dx, dy)| (ox + dx as i64, oy + dy as i64))
            .collect();
        self.world.ensure_positions(&cells);
        cells
    }

    fn can_place_area(&mut self, area: usize, position: Position, ignore_id: u32) -> bool {
        let offsets = self.footprint_offsets(area);
        self.footprint_buf.clear();
        self.footprint_buf.extend(
            offsets
                .iter()
                .map(|&(dx, dy)| (position.0 + dx as i64, position.1 + dy as i64)),
        );
        self.world.area_free(&self.footprint_buf, ignore_id)
    }

    /// can_place: would the organism's footprint at `position` be free of
    /// other organisms (ignoring `ignore_id`)?
    fn can_place(&mut self, organism: &mut Organism, position: Position, ignore_id: u32) -> bool {
        let area = organism.area(&self.catalog);
        self.can_place_area(area, position, ignore_id)
    }

    // ------------------------------------------------------------ main tick

    pub fn step(&mut self, count: u32) {
        for _ in 0..count {
            self.tick += 1;
            self.seasons.advance(self.tick, &self.config);
            self.world.diffuse_heat(
                self.config.heat_diffusion,
                &mut self.diffuse_sources,
                &mut self.diffuse_source_index,
                &mut self.diffuse_scratch,
            );
            self.prepare_deposit_positions();
            self.produce_deposits();
            self.resolve_effects();
            self.decompose_environment();
            self.run_environmental_reactions();
            if self.config.biodeposits_enabled {
                self.world
                    .decay_biodeposits(self.config.biodeposit_decay_rate);
            }
            if self.config.dynamic_chemistry_enabled {
                self.world
                    .decay_byproducts(self.config.byproduct_decay_rate);
            }
            self.run_organism_loop();
            self.update_cellular_network();
            self.expire_corpses();
            self.refresh_dirty_occupancy();
            if self.config.audit_every > 0 && self.tick.is_multiple_of(self.config.audit_every) {
                let _ = self.audit(false);
            }
        }
    }

    fn profile_step(&mut self, count: u32) -> PhaseProfile {
        use std::time::Instant;

        let mut profile = PhaseProfile::default();
        let total_started = Instant::now();
        for _ in 0..count {
            self.tick += 1;
            self.seasons.advance(self.tick, &self.config);

            let started = Instant::now();
            self.world.diffuse_heat(
                self.config.heat_diffusion,
                &mut self.diffuse_sources,
                &mut self.diffuse_source_index,
                &mut self.diffuse_scratch,
            );
            profile.heat_diffusion_ns += started.elapsed().as_nanos();

            let started = Instant::now();
            self.prepare_deposit_positions();
            self.produce_deposits();
            profile.deposit_production_ns += started.elapsed().as_nanos();

            let started = Instant::now();
            self.resolve_effects();
            profile.effects_ns += started.elapsed().as_nanos();

            let started = Instant::now();
            self.decompose_environment();
            self.run_environmental_reactions();
            if self.config.biodeposits_enabled {
                self.world
                    .decay_biodeposits(self.config.biodeposit_decay_rate);
            }
            if self.config.dynamic_chemistry_enabled {
                self.world
                    .decay_byproducts(self.config.byproduct_decay_rate);
            }
            profile.decomposition_ns += started.elapsed().as_nanos();

            let started = Instant::now();
            self.run_organism_loop_profiled(&mut profile);
            self.update_cellular_network();
            profile.organism_loop_ns += started.elapsed().as_nanos();

            let started = Instant::now();
            self.expire_corpses();
            profile.corpse_expiry_ns += started.elapsed().as_nanos();

            let started = Instant::now();
            self.refresh_dirty_occupancy();
            profile.occupancy_refresh_ns += started.elapsed().as_nanos();

            if self.config.audit_every > 0 && self.tick.is_multiple_of(self.config.audit_every) {
                let started = Instant::now();
                let _ = self.audit(false);
                profile.audit_ns += started.elapsed().as_nanos();
            }
        }
        profile.total_ns = total_started.elapsed().as_nanos();
        profile
    }

    fn rebuild_bond_components(&mut self) {
        let required = self.next_organism_id as usize;
        self.component_roots.resize(required, 0);
        self.component_roots.fill(0);
        for &organism_id in &self.living_ordered {
            self.component_roots[organism_id as usize] = organism_id;
        }

        fn root(roots: &mut [u32], organism_id: u32) -> u32 {
            let mut current = organism_id;
            while roots[current as usize] != current {
                current = roots[current as usize];
            }
            let result = current;
            let mut current = organism_id;
            while roots[current as usize] != current {
                let parent = roots[current as usize];
                roots[current as usize] = result;
                current = parent;
            }
            result
        }

        for bond in self.bonds.values() {
            if !self.living.contains(&bond.left) || !self.living.contains(&bond.right) {
                continue;
            }
            let left_root = root(&mut self.component_roots, bond.left);
            let right_root = root(&mut self.component_roots, bond.right);
            if left_root != right_root {
                let (minimum, maximum) = if left_root < right_root {
                    (left_root, right_root)
                } else {
                    (right_root, left_root)
                };
                self.component_roots[maximum as usize] = minimum;
            }
        }

        self.component_members.clear();
        for &organism_id in &self.living_ordered {
            let component_root = root(&mut self.component_roots, organism_id);
            self.component_roots[organism_id as usize] = component_root;
            self.component_members
                .entry(component_root)
                .or_default()
                .push(organism_id);
        }
    }

    fn bond_component_facts(&self) -> (Vec<u32>, FxHashMap<u32, u32>) {
        let mut roots = vec![0; self.next_organism_id as usize];
        for &organism_id in &self.living_ordered {
            roots[organism_id as usize] = organism_id;
        }
        fn root(roots: &mut [u32], organism_id: u32) -> u32 {
            let mut current = organism_id;
            while roots[current as usize] != current {
                current = roots[current as usize];
            }
            current
        }
        for bond in self.bonds.values() {
            if !self.living.contains(&bond.left) || !self.living.contains(&bond.right) {
                continue;
            }
            let left = root(&mut roots, bond.left);
            let right = root(&mut roots, bond.right);
            if left != right {
                let (minimum, maximum) = if left < right {
                    (left, right)
                } else {
                    (right, left)
                };
                roots[maximum as usize] = minimum;
            }
        }
        let mut sizes = FxHashMap::default();
        for &organism_id in &self.living_ordered {
            let component_root = root(&mut roots, organism_id);
            roots[organism_id as usize] = component_root;
            *sizes.entry(component_root).or_default() += 1;
        }
        (roots, sizes)
    }

    fn coordinated_components_enabled(&self) -> bool {
        self.config.cellular_emergence_enabled && self.config.emergence_coordinated_components
    }

    fn component_root_for(&self, organism_id: u32) -> u32 {
        self.component_roots
            .get(organism_id as usize)
            .copied()
            .filter(|&root| root != 0)
            .unwrap_or(organism_id)
    }

    fn same_bond_component(&self, left: u32, right: u32) -> bool {
        left != right && self.component_root_for(left) == self.component_root_for(right)
    }

    fn run_coordinated_organism_loop(&mut self) {
        self.order.clear();
        self.order.extend(self.living_ordered.iter().copied());
        self.rng.shuffle(&mut self.order);
        let count = self.order.len();
        for index in 0..count {
            let organism_id = self.order[index];
            if !self.living.contains(&organism_id) {
                continue;
            }
            self.upkeep(organism_id);
            if self.living.contains(&organism_id) {
                self.digest_gut(organism_id);
            }
        }

        self.rebuild_bond_components();
        self.component_acted.clear();
        for index in 0..count {
            let organism_id = self.order[index];
            if !self.living.contains(&organism_id)
                || self.tick < self.organism(organism_id).next_action_tick
            {
                continue;
            }
            let component_root = self.component_root_for(organism_id);
            if !self.component_acted.insert(component_root) {
                continue;
            }
            let members = self
                .component_members
                .get(&component_root)
                .cloned()
                .unwrap_or_else(|| vec![organism_id]);
            self.decide_and_act(organism_id);
            if members.len() <= 1 {
                continue;
            }
            self.emergence_stats.component_actions += 1;
            let Some(authority) = members
                .iter()
                .copied()
                .find(|&member| member == organism_id && self.has_organism(member))
            else {
                continue;
            };
            let (next_action_tick, last_action, last_intent_kind) = {
                let organism = self.organism(authority);
                (
                    organism.next_action_tick,
                    organism.last_action,
                    organism.last_intent_kind,
                )
            };
            let synchronized_tick = members
                .iter()
                .copied()
                .filter(|&member| self.has_organism(member))
                .map(|member| {
                    self.organism(member)
                        .next_action_tick
                        .max(self.tick + self.v2_action_delay(member))
                })
                .fold(next_action_tick, u32::max);
            for member in members {
                if self.has_organism(member) {
                    let organism = self.organism_mut(member);
                    organism.next_action_tick = synchronized_tick;
                    organism.last_action = last_action;
                    organism.last_intent_kind = last_intent_kind;
                }
            }
        }
    }

    fn parallel_cells(&self, oid: u32, radius: usize) -> Vec<Position> {
        let organism = self.organism(oid);
        let area = self.parallel_area(organism);
        let offsets = self
            .nearby_offsets
            .get(&(area, radius))
            .expect("parallel-v3 nearby offsets must be prepared");
        offsets
            .iter()
            .map(|&(dx, dy)| {
                (
                    organism.position.0 + dx as i64,
                    organism.position.1 + dy as i64,
                )
            })
            .collect()
    }

    fn parallel_area(&self, organism: &Organism) -> usize {
        let mass = organism.peek_structural_mass(&self.catalog) as f64;
        let ratio = (mass / organism.target_mass.max(1.0)).min(1.0);
        py_round(organism.phenotype.adult_area as f64 * ratio)
            .max(1)
            .min(organism.phenotype.adult_area) as usize
    }

    fn parallel_footprint(&self, oid: u32) -> Vec<Position> {
        let organism = self.organism(oid);
        self.fp_offsets[&self.parallel_area(organism)]
            .iter()
            .map(|&(dx, dy)| {
                (
                    organism.position.0 + dx as i64,
                    organism.position.1 + dy as i64,
                )
            })
            .collect()
    }

    fn parallel_area_free(&self, area: usize, position: Position, ignore_id: u32) -> bool {
        self.fp_offsets[&area].iter().all(|&(dx, dy)| {
            let cell = (position.0 + dx as i64, position.1 + dy as i64);
            !self
                .world
                .occupants_at(cell)
                .is_some_and(|occupants| occupants.iter().any(|&id| id != ignore_id))
        })
    }

    fn propose_parallel_v3(&self, oid: u32) -> ParallelProposal {
        use behavior::intent::*;
        use behavior::observation::*;

        let organism = self.organism(oid);
        let mut proposal_rng =
            scheduler::decision_rng(self.config.seed, self.tick, oid, organism.decision_count);
        let cells_r1 = self.parallel_cells(oid, 1);
        let realized_sight = organism.phenotype.sight;
        let cells_sight = if realized_sight > 1 {
            self.parallel_cells(oid, realized_sight)
        } else {
            Vec::new()
        };
        let proposed_sight_cost = self.config.sight_cost_per_cell
            * self.reference_energy
            * ((cells_sight.len() as i64 - cells_r1.len() as i64).max(0)) as f64;
        let (effective_sight, sight_cost, cells) =
            if realized_sight > 1 && organism.chemical_energy() >= proposed_sight_cost {
                (realized_sight, proposed_sight_cost, cells_sight.as_slice())
            } else {
                (1, 0.0, cells_r1.as_slice())
            };
        let footprint = self.parallel_footprint(oid);
        let origin = organism.position;
        let facing = organism.facing;

        let mut nearby = Vec::new();
        for &cell in cells {
            if let Some(occupants) = self.world.occupants_at(cell) {
                nearby.extend(occupants.iter().copied());
            }
        }
        nearby.sort_unstable();
        nearby.dedup();
        nearby.retain(|id| {
            *id != oid && self.living.contains(id) && !self.same_bond_component(oid, *id)
        });
        let mut contact = Vec::new();
        for &cell in &cells_r1 {
            if let Some(occupants) = self.world.occupants_at(cell) {
                contact.extend(occupants.iter().copied());
            }
        }
        contact.sort_unstable();
        contact.dedup();
        contact.retain(|id| {
            *id != oid && self.living.contains(id) && !self.same_bond_component(oid, *id)
        });

        let mut directional_food = [0.0f32; 8];
        let mut directional_toxin = [0.0f32; 8];
        let mut directional_heat = [0.0f32; 8];
        let mut directional_prey = [0.0f32; 8];
        let mut directional_threat = [0.0f32; 8];
        let mut directional_mate = [0.0f32; 8];
        let mut local_food = 0.0f32;
        let mut local_heat = 0.0f32;
        let mut visible_food = false;
        let mut visible_heat = false;
        let reference_energy = self.reference_energy.max(1e-9);

        for &position in cells {
            let slot = egocentric_slot(facing, (position.0 - origin.0, position.1 - origin.1));
            let distance_discount = 1.0 / (1.0 + World::distance(origin, position) as f64);
            if let Some(inventory) = self.world.deposits.get(&position) {
                for batch in inventory {
                    if batch.count <= 0 {
                        continue;
                    }
                    let (dietary_match, hazard) =
                        organism.food_chemistry_at(batch.molecule_id as usize);
                    let density = batch.energy / batch.count as f64 / reference_energy;
                    directional_food[slot] = directional_food[slot].max(unit_f32(
                        (dietary_match * density - hazard).max(0.0) * distance_discount,
                    ));
                    directional_toxin[slot] =
                        directional_toxin[slot].max(unit_f32(hazard.max(0.0) * distance_discount));
                    if footprint.contains(&position) {
                        local_food = local_food.max(directional_food[slot]);
                    }
                    visible_food = true;
                }
            }
            let heat =
                unit_f32(self.world.heat_at_peek(position) / reference_energy * distance_discount);
            directional_heat[slot] = directional_heat[slot].max(heat);
            if footprint.contains(&position) {
                local_heat = local_heat.max(heat);
            }
            visible_heat |= heat > 0.0;
        }

        let mut maximum_threat = 0.0f32;
        let mut maximum_prey = 0.0f32;
        let mut best_mate = 0.0f32;
        for &target_id in &nearby {
            let (prey, threat, mate, _, _) = self.v2_target_metrics(oid, target_id);
            let target_position = self.organism(target_id).position;
            let slot = egocentric_slot(
                facing,
                (target_position.0 - origin.0, target_position.1 - origin.1),
            );
            directional_prey[slot] = directional_prey[slot].max(prey);
            directional_threat[slot] = directional_threat[slot].max(threat);
            directional_mate[slot] = directional_mate[slot].max(mate);
            maximum_prey = maximum_prey.max(prey);
            maximum_threat = maximum_threat.max(threat);
            best_mate = best_mate.max(mate);
        }

        let capacity: f64 = organism
            .body
            .iter()
            .map(|batch| {
                self.catalog.molecules[batch.molecule_id as usize].energy_capacity
                    * batch.count as f64
            })
            .sum();
        let energy_fraction = if capacity > 0.0 {
            organism.chemical_energy() / capacity
        } else {
            0.0
        };
        let phenotype = &organism.phenotype;
        let mass = organism.peek_structural_mass(&self.catalog) as f64;
        let chemical_energy = organism.chemical_energy() - sight_cost;
        let age = self.tick.saturating_sub(organism.birth_tick) as f64;
        let age_ratio = age / phenotype.lifespan.max(1) as f64;
        let cooldown_remaining = organism.reproduction_cooldown.saturating_sub(self.tick) as f64;
        let mut observation = ObservationV2::default();
        observation.values[O_RESERVE] = unit_f32(energy_fraction);
        observation.values[O_HUNGER] = unit_f32(1.0 - energy_fraction);
        observation.values[O_MANA] = unit_f32(organism.mana / phenotype.mana_capacity.max(1e-9));
        observation.values[O_MAINTENANCE_DEBT] =
            unit_f32(organism.maintenance_debt / (4.0 * reference_energy));
        observation.values[O_INTEGRITY] =
            unit_f32(organism.integrity / organism.max_integrity.max(1e-9));
        observation.values[O_TOXIN] =
            unit_f32(organism.toxin_load / phenotype.toxin_tolerance.max(1e-9));
        observation.values[O_AGE] = unit_f32(age_ratio);
        observation.values[O_SENESCENCE] = unit_f32((age_ratio - 1.0).max(0.0));
        observation.values[O_GROWTH_DEFICIT] = unit_f32(1.0 - mass / organism.target_mass.max(1.0));
        observation.values[O_REPRODUCTIVE_RESERVE] = unit_f32(energy_fraction);
        observation.values[O_REPRODUCTIVE_COOLDOWN] =
            unit_f32(cooldown_remaining / phenotype.maturity_age.max(1) as f64);
        observation.values[O_REPRODUCTIVE_READY] = if self.is_reproductively_ready(oid) {
            1.0
        } else {
            0.0
        };
        observation.values[O_BODY_MASS] = unit_f32(mass / self.reference_body_mass.max(1.0));
        observation.values[O_SPEED] = unit_f32((phenotype.speed - 0.5) / 3.5);
        observation.values[O_SIGHT] =
            unit_f32(effective_sight as f64 / self.config.max_sight.max(1) as f64);
        observation.values[O_COLONY] = if organism.colony_id.is_some() {
            1.0
        } else {
            0.0
        };
        if self.config.dynamic_chemistry_enabled {
            let (local_fit, environmental_toxin) = self.local_chemistry_signals(organism);
            observation.values[O_LOCAL_FOOD] = unit_f32(local_food as f64 + 0.5 * local_fit);
            observation.values[O_TOXIN] = unit_f32(
                organism.toxin_load / organism.phenotype.toxin_tolerance.max(1.0e-9)
                    + environmental_toxin * self.config.chemistry_coupling,
            );
        } else {
            observation.values[O_LOCAL_FOOD] = local_food;
        }
        observation.values[O_VISIBLE_FOOD] = directional_food.iter().copied().fold(0.0, f32::max);
        observation.values[O_LOCAL_HEAT] = local_heat;
        observation.values[O_VISIBLE_HEAT] = directional_heat.iter().copied().fold(0.0, f32::max);
        observation.values[O_THREAT] = maximum_threat;
        observation.values[O_PREY] = maximum_prey;
        observation.values[O_MATE] = best_mate;
        observation.values[O_CONTACT_CROWDING] = unit_f32(contact.len() as f64 / 8.0);
        observation.values[O_VISIBLE_CROWDING] =
            unit_f32(nearby.len() as f64 / (8 * effective_sight.max(1)) as f64);
        observation.values[O_FOOD_KNOWN] = if visible_food { 1.0 } else { 0.0 };
        observation.values[O_ORGANISM_KNOWN] = if nearby.is_empty() { 0.0 } else { 1.0 };
        observation.values[O_HEAT_KNOWN] = if visible_heat { 1.0 } else { 0.0 };

        let duration = self.v2_action_delay(oid);
        let last_kind = organism.last_intent_kind;
        let mut candidates = Vec::with_capacity(MAX_INTENT_CANDIDATES);
        let mut pool = Vec::new();
        candidates.push(make_intent_candidate(
            last_kind,
            IntentKind::Wait,
            IntentTarget::None,
            duration,
            0.0,
            0.0,
            reference_energy,
        ));
        if organism.integrity < organism.max_integrity && chemical_energy > 0.0 {
            candidates.push(make_intent_candidate(
                last_kind,
                IntentKind::Repair,
                IntentTarget::None,
                duration,
                chemical_energy.min(reference_energy * 0.005),
                0.0,
                reference_energy,
            ));
        }

        let move_cost = self.v2_move_cost(oid);
        if chemical_energy >= move_cost {
            let area = self.parallel_area(organism);
            for slot in 0..8 {
                let direction = egocentric_direction(facing, slot);
                let destination = (origin.0 + direction.0 as i64, origin.1 + direction.1 as i64);
                if !self.parallel_area_free(area, destination, oid) {
                    continue;
                }
                let mut candidate = make_intent_candidate(
                    last_kind,
                    IntentKind::Move,
                    IntentTarget::Position(destination),
                    duration,
                    move_cost,
                    0.0,
                    reference_energy,
                );
                candidate.features[C_FOOD] = directional_food[slot];
                candidate.features[C_TOXIN] = directional_toxin[slot];
                candidate.features[C_HEAT] = directional_heat[slot];
                candidate.features[C_PREY] = directional_prey[slot];
                candidate.features[C_THREAT] = directional_threat[slot];
                candidate.features[C_MATE] = directional_mate[slot];
                candidate.features[C_CROWDING] = unit_f32(
                    self.world
                        .occupants_at(destination)
                        .map_or(0, |ids| ids.len()) as f64
                        / 8.0,
                );
                candidate.features[C_FORWARD] = EGOCENTRIC_FORWARD[slot];
                candidate.features[C_RIGHT] = EGOCENTRIC_RIGHT[slot];
                candidate.features[C_DISTANCE] = unit_f32(1.0 / effective_sight.max(1) as f64);
                candidates.push(candidate);
            }
        }

        for &position in &footprint {
            if let Some(inventory) = self.world.deposits.get(&position) {
                for batch in inventory {
                    if batch.count <= 0 {
                        continue;
                    }
                    let (dietary_match, hazard) =
                        organism.food_chemistry_at(batch.molecule_id as usize);
                    let density = batch.energy / batch.count as f64 / reference_energy;
                    let food_value = unit_f32((dietary_match * density - hazard).max(0.0));
                    let count = 2.min(batch.count);
                    let cost = self.config.reference_ingest_cost * reference_energy * count as f64;
                    if chemical_energy < cost {
                        continue;
                    }
                    let mut candidate = make_intent_candidate(
                        last_kind,
                        IntentKind::Ingest,
                        IntentTarget::Food {
                            position,
                            molecule_id: batch.molecule_id,
                        },
                        duration,
                        cost,
                        0.0,
                        reference_energy,
                    );
                    candidate.features[C_FOOD] = food_value;
                    candidate.features[C_TOXIN] = unit_f32(hazard.max(0.0));
                    pool.push(RankedIntentCandidate {
                        salience: food_value - candidate.features[C_TOXIN],
                        tie_key: position_tie_key(position) ^ batch.molecule_id as u64,
                        candidate,
                    });
                }
            }
        }
        append_ranked_candidates(&mut candidates, &mut pool, 4);

        if organism.mana < phenotype.mana_capacity {
            if let Some((&position, heat)) = footprint
                .iter()
                .map(|position| (position, self.world.heat_at_peek(*position)))
                .max_by(|left, right| left.1.total_cmp(&right.1))
            {
                if heat > 1e-9 {
                    let mut candidate = make_intent_candidate(
                        last_kind,
                        IntentKind::AbsorbHeat,
                        IntentTarget::Position(position),
                        duration,
                        0.0,
                        0.0,
                        reference_energy,
                    );
                    candidate.features[C_HEAT] = unit_f32(heat / reference_energy);
                    candidates.push(candidate);
                }
            }
        }
        if organism.toxin_load > phenotype.toxin_tolerance * 0.5 && chemical_energy > 0.0 {
            candidates.push(make_intent_candidate(
                last_kind,
                IntentKind::Detox,
                IntentTarget::None,
                duration,
                chemical_energy.min(reference_energy * 0.01),
                0.0,
                reference_energy,
            ));
        }

        let attack_cost = self.config.reference_attack_cost
            * reference_energy
            * (mass / self.reference_body_mass.max(1.0))
            * phenotype.attack
            * phenotype.attack
            / phenotype.attack_efficiency;
        if chemical_energy >= attack_cost {
            for &target_id in &contact {
                let (prey, threat, mate, social, distance) = self.v2_target_metrics(oid, target_id);
                let mut candidate = make_intent_candidate(
                    last_kind,
                    IntentKind::Attack,
                    IntentTarget::Organism(target_id),
                    duration,
                    attack_cost,
                    0.0,
                    reference_energy,
                );
                candidate.features[C_PREY] = prey;
                candidate.features[C_THREAT] = threat;
                candidate.features[C_MATE] = mate;
                candidate.features[C_SOCIAL] = social;
                candidate.features[C_DISTANCE] = distance;
                pool.push(RankedIntentCandidate {
                    salience: prey,
                    tie_key: target_id as u64,
                    candidate,
                });
            }
        }
        append_ranked_candidates(&mut candidates, &mut pool, 4);

        if organism.mana > 1e-9 {
            let mana_cost = (organism.mana * 0.30).min(reference_energy * 0.5);
            for &target_id in &nearby {
                let (prey, threat, mate, social, distance) = self.v2_target_metrics(oid, target_id);
                let mut candidate = make_intent_candidate(
                    last_kind,
                    IntentKind::CastMagic,
                    IntentTarget::Organism(target_id),
                    duration,
                    0.0,
                    mana_cost,
                    reference_energy,
                );
                candidate.features[C_PREY] = prey;
                candidate.features[C_THREAT] = threat;
                candidate.features[C_MATE] = mate;
                candidate.features[C_SOCIAL] = social;
                candidate.features[C_DISTANCE] = distance;
                pool.push(RankedIntentCandidate {
                    salience: prey.max(threat),
                    tie_key: target_id as u64,
                    candidate,
                });
            }
        }
        append_ranked_candidates(&mut candidates, &mut pool, 4);

        if self.is_reproductively_ready(oid) {
            let single_cost = self.config.reference_reproduction_cost
                * self.config.reproduction_cost_multiplier
                * reference_energy
                * mass
                * phenotype.reproduction_fraction
                / self.reference_body_mass.max(1.0);
            if chemical_energy >= single_cost {
                let mut candidate = make_intent_candidate(
                    last_kind,
                    IntentKind::Reproduce,
                    IntentTarget::SelfReproduction,
                    duration,
                    single_cost,
                    0.0,
                    reference_energy,
                );
                candidate.features[C_MATE] =
                    unit_f32(phenotype.asexual.max(self.config.asexual_probability_floor));
                candidates.push(candidate);
            }
            for &target_id in &contact {
                let target = self.organism(target_id);
                if !self.is_reproductively_ready(target_id) || target.phenotype.sexual <= 0.05 {
                    continue;
                }
                let (prey, threat, mate, social, distance) = self.v2_target_metrics(oid, target_id);
                let target_mass = target.peek_structural_mass(&self.catalog) as f64;
                let share = self.config.reference_reproduction_cost
                    * self.config.reproduction_cost_multiplier
                    * reference_energy
                    * (mass * phenotype.reproduction_fraction
                        + target_mass * target.phenotype.reproduction_fraction)
                    / self.reference_body_mass.max(1.0)
                    * 0.5;
                if chemical_energy < share || target.chemical_energy() < share {
                    continue;
                }
                let mut candidate = make_intent_candidate(
                    last_kind,
                    IntentKind::Reproduce,
                    IntentTarget::Organism(target_id),
                    duration,
                    share,
                    0.0,
                    reference_energy,
                );
                candidate.features[C_PREY] = prey;
                candidate.features[C_THREAT] = threat;
                candidate.features[C_MATE] = mate;
                candidate.features[C_SOCIAL] = social;
                candidate.features[C_DISTANCE] = distance;
                pool.push(RankedIntentCandidate {
                    salience: mate,
                    tie_key: target_id as u64,
                    candidate,
                });
            }
            append_ranked_candidates(&mut candidates, &mut pool, 4);
        }

        for &target_id in &contact {
            let edge = if oid < target_id {
                (oid, target_id)
            } else {
                (target_id, oid)
            };
            if self.alliances.contains(&edge) {
                continue;
            }
            let (prey, threat, mate, social, distance) = self.v2_target_metrics(oid, target_id);
            let mut candidate = make_intent_candidate(
                last_kind,
                IntentKind::ProposeAlliance,
                IntentTarget::Organism(target_id),
                duration,
                0.0,
                0.0,
                reference_energy,
            );
            candidate.features[C_PREY] = prey;
            candidate.features[C_THREAT] = threat;
            candidate.features[C_MATE] = mate;
            candidate.features[C_SOCIAL] = social;
            candidate.features[C_DISTANCE] = distance;
            pool.push(RankedIntentCandidate {
                salience: social,
                tie_key: target_id as u64,
                candidate,
            });
        }
        append_ranked_candidates(&mut candidates, &mut pool, 4);
        debug_assert!(candidates.len() <= MAX_INTENT_CANDIDATES);

        let mut current_food_slot = 0u8;
        let mut current_food_signal = directional_food[0];
        for (slot, &signal) in directional_food.iter().enumerate().skip(1) {
            if signal > current_food_signal {
                current_food_slot = slot as u8;
                current_food_signal = signal;
            }
        }
        let policy = phenotype
            .intent_policy
            .as_ref()
            .expect("parallel-v3 requires a V2 intent policy");
        let global_scores = policy.global_scores(&observation);
        let (recurrent_output, next_neural_state, neural_failure) =
            if self.config.behavior_model == BehaviorModel::RecurrentIntentV2 {
                let recurrent = phenotype
                    .recurrent_policy
                    .as_ref()
                    .expect("recurrent organisms must have a recurrent phenotype");
                match recurrent.infer(
                    &observation,
                    organism.neural_state,
                    self.config.recurrent_state_lesion,
                ) {
                    Some(output) => (Some(output), output.next_state, false),
                    None => (None, NeuralState::default(), true),
                }
            } else {
                (None, organism.neural_state, false)
            };
        let scores: Vec<f64> = candidates
            .iter()
            .map(|candidate| {
                let score = match recurrent_output {
                    Some(output) => {
                        policy.score_with_globals(&global_scores, candidate)
                            + output.score(candidate)
                    }
                    None => policy.score_with_globals(&global_scores, candidate),
                };
                if score.is_finite() {
                    score
                } else {
                    f64::NEG_INFINITY
                }
            })
            .collect();

        let mut memory_probe = MemoryProbeDelta::default();
        if self.config.memory_probe_enabled
            && self.config.behavior_model == BehaviorModel::RecurrentIntentV2
        {
            let recurrent = phenotype.recurrent_policy.as_ref().unwrap();
            if let Some(zero_state_output) =
                recurrent.infer(&observation, NeuralState::default(), false)
            {
                let stateful_index = scores
                    .iter()
                    .enumerate()
                    .max_by(|left, right| left.1.total_cmp(right.1).then(right.0.cmp(&left.0)))
                    .map_or(0, |(index, _)| index);
                let zero_state_index = candidates
                    .iter()
                    .enumerate()
                    .map(|(index, candidate)| {
                        (
                            index,
                            policy.score_with_globals(&global_scores, candidate)
                                + zero_state_output.score(candidate),
                        )
                    })
                    .max_by(|left, right| left.1.total_cmp(&right.1).then(right.0.cmp(&left.0)))
                    .map_or(0, |(index, _)| index);
                let ambiguous = current_food_signal <= 1.0e-6
                    && organism.previous_food_signal >= 0.05
                    && organism.previous_food_slot < 8;
                let returns_to_previous_food = |candidate: &IntentCandidate| {
                    candidate.kind == IntentKind::Move
                        && matches!(candidate.target, IntentTarget::Position(destination)
                            if egocentric_slot(facing, (destination.0 - origin.0, destination.1 - origin.1))
                                == organism.previous_food_slot as usize)
                };
                memory_probe = MemoryProbeDelta {
                    state_l1: organism
                        .neural_state
                        .values
                        .iter()
                        .map(|value| value.abs() as f64)
                        .sum(),
                    decision: true,
                    argmax_changed: stateful_index != zero_state_index,
                    ambiguous_food: ambiguous,
                    ambiguous_argmax_changed: ambiguous && stateful_index != zero_state_index,
                    stateful_return: ambiguous
                        && returns_to_previous_food(&candidates[stateful_index]),
                    zero_state_return: ambiguous
                        && returns_to_previous_food(&candidates[zero_state_index]),
                };
            }
        }

        let temperature = policy.decision_temperature.max(0.05) as f64;
        let maximum = scores.iter().copied().fold(f64::NEG_INFINITY, f64::max);
        let weights: Vec<f64> = scores
            .iter()
            .map(|score| (((score - maximum) / temperature).clamp(-30.0, 30.0)).exp())
            .collect();
        let total: f64 = weights.iter().sum();
        let selected_index = if neural_failure {
            0
        } else if total.is_finite() && total > 0.0 {
            let mut draw = proposal_rng.f64() * total;
            let mut selected = candidates.len() - 1;
            for (index, weight) in weights.iter().enumerate() {
                draw -= *weight;
                if draw <= 0.0 {
                    selected = index;
                    break;
                }
            }
            selected
        } else {
            0
        };

        ParallelProposal {
            actor_id: oid,
            intent: candidates[selected_index].to_intent(oid),
            sight_cost,
            next_neural_state,
            current_food_slot,
            current_food_signal,
            neural_failure,
            memory_probe,
        }
    }

    fn parallel_target_within(&self, actor_id: u32, target_id: u32, radius: usize) -> bool {
        self.parallel_cells(actor_id, radius).iter().any(|&cell| {
            self.world
                .occupants_at(cell)
                .is_some_and(|occupants| occupants.contains(&target_id))
        })
    }

    fn validate_parallel_v3_intent(&self, intent: ActionIntent) -> ActionIntent {
        let valid = match intent.target {
            IntentTarget::Organism(target_id) if !self.has_organism(target_id) => false,
            IntentTarget::Organism(target_id) => match intent.kind {
                IntentKind::Attack | IntentKind::Reproduce | IntentKind::ProposeAlliance => {
                    self.parallel_target_within(intent.actor_id, target_id, 1)
                }
                IntentKind::CastMagic => self.parallel_target_within(
                    intent.actor_id,
                    target_id,
                    self.organism(intent.actor_id).phenotype.sight,
                ),
                _ => true,
            },
            IntentTarget::Food {
                position,
                molecule_id,
            } => self.world.deposits.get(&position).is_some_and(|inventory| {
                inventory
                    .iter()
                    .any(|batch| batch.molecule_id == molecule_id && batch.count > 0)
            }),
            IntentTarget::Position(position) if intent.kind == IntentKind::AbsorbHeat => {
                self.world.heat_at_peek(position) > 1e-9
            }
            _ => true,
        };
        if valid {
            intent
        } else {
            ActionIntent {
                kind: IntentKind::Wait,
                target: IntentTarget::None,
                ..intent
            }
        }
    }

    fn parallel_v3_conflict_keys(&self, proposal: &ParallelProposal) -> Vec<ConflictKey> {
        let actor_id = proposal.actor_id;
        let actor_position = self.organism(actor_id).position;
        let mut keys = vec![
            ConflictKey::Organism(actor_id),
            ConflictKey::Heat(actor_position),
        ];
        match proposal.intent.target {
            IntentTarget::Organism(target_id) => {
                keys.push(ConflictKey::Organism(target_id));
                match proposal.intent.kind {
                    IntentKind::Attack => keys.push(ConflictKey::Lifecycle),
                    IntentKind::CastMagic => {
                        keys.push(ConflictKey::Effects);
                        if self.has_organism(target_id) {
                            keys.push(ConflictKey::Heat(self.organism(target_id).position));
                        }
                    }
                    IntentKind::Reproduce => keys.push(ConflictKey::Reproduction),
                    IntentKind::ProposeAlliance => {
                        let edge = if actor_id < target_id {
                            (actor_id, target_id)
                        } else {
                            (target_id, actor_id)
                        };
                        keys.push(ConflictKey::Alliance(edge.0, edge.1));
                    }
                    _ => {}
                }
            }
            IntentTarget::Position(position) => match proposal.intent.kind {
                IntentKind::Move => {
                    let area = self.parallel_area(self.organism(actor_id));
                    for &(offset_x, offset_y) in self.fp_offsets[&area].iter() {
                        keys.push(ConflictKey::Occupancy((
                            actor_position.0 + offset_x as i64,
                            actor_position.1 + offset_y as i64,
                        )));
                        keys.push(ConflictKey::Occupancy((
                            position.0 + offset_x as i64,
                            position.1 + offset_y as i64,
                        )));
                    }
                }
                IntentKind::AbsorbHeat => keys.push(ConflictKey::Heat(position)),
                _ => {}
            },
            IntentTarget::Food {
                position,
                molecule_id,
            } => keys.push(ConflictKey::Deposit(position, molecule_id)),
            IntentTarget::SelfReproduction => keys.push(ConflictKey::Reproduction),
            IntentTarget::None => {}
        }
        keys
    }

    fn parallel_v3_isolated_components(&self, proposals: &[ParallelProposal]) -> Vec<bool> {
        fn root(parents: &mut [usize], index: usize) -> usize {
            let mut current = index;
            while parents[current] != current {
                current = parents[current];
            }
            let result = current;
            let mut current = index;
            while parents[current] != current {
                let parent = parents[current];
                parents[current] = result;
                current = parent;
            }
            result
        }

        let mut parents: Vec<usize> = (0..proposals.len()).collect();
        let mut owners: FxHashMap<ConflictKey, usize> = FxHashMap::default();
        for (index, proposal) in proposals.iter().enumerate() {
            for key in self.parallel_v3_conflict_keys(proposal) {
                if let Some(&other) = owners.get(&key) {
                    let left = root(&mut parents, index);
                    let right = root(&mut parents, other);
                    if left != right {
                        let (minimum, maximum) = if left < right {
                            (left, right)
                        } else {
                            (right, left)
                        };
                        parents[maximum] = minimum;
                    }
                } else {
                    owners.insert(key, index);
                }
            }
        }
        let roots: Vec<usize> = (0..proposals.len())
            .map(|index| root(&mut parents, index))
            .collect();
        let mut sizes: FxHashMap<usize, usize> = FxHashMap::default();
        for &component_root in &roots {
            *sizes.entry(component_root).or_default() += 1;
        }
        proposals
            .iter()
            .enumerate()
            .map(|(index, proposal)| {
                sizes[&roots[index]] == 1
                    && matches!(
                        proposal.intent.kind,
                        IntentKind::Wait | IntentKind::Repair | IntentKind::Detox
                    )
            })
            .collect()
    }

    fn apply_parallel_v3_resolution_stats(
        &mut self,
        selected_kind: IntentKind,
        final_kind: IntentKind,
        neural_failure: bool,
        probe: MemoryProbeDelta,
    ) {
        if neural_failure {
            self.stats.neural_numerical_errors += 1;
            self.stats.v2_intent_failures += 1;
        }
        self.stats.memory_probe_decisions += probe.decision as u64;
        self.stats.memory_probe_state_l1_sum += probe.state_l1;
        self.stats.memory_probe_argmax_changes += probe.argmax_changed as u64;
        self.stats.memory_probe_ambiguous_food_events += probe.ambiguous_food as u64;
        self.stats.memory_probe_ambiguous_argmax_changes += probe.ambiguous_argmax_changed as u64;
        self.stats.memory_probe_stateful_return_choices += probe.stateful_return as u64;
        self.stats.memory_probe_zero_state_return_choices += probe.zero_state_return as u64;
        self.stats.v2_intent_counts[final_kind.as_index()] += 1;
        if final_kind != selected_kind {
            self.stats.v2_intent_failures += 1;
        }
    }

    fn resolve_parallel_v3(&mut self, proposals: Vec<ParallelProposal>) -> (u128, u128) {
        use std::time::Instant;

        let grouping_started = Instant::now();
        let isolated = self.parallel_v3_isolated_components(&proposals);
        let grouping_ns = grouping_started.elapsed().as_nanos();
        let resolution_started = Instant::now();
        let mut slots: Vec<Option<ParallelProposal>> =
            (0..self.organisms.len()).map(|_| None).collect();
        let mut serial = Vec::new();
        for (proposal, parallel) in proposals.into_iter().zip(isolated) {
            if parallel {
                let index = self.organism_indices[proposal.actor_id as usize - 1];
                slots[index] = Some(proposal);
            } else {
                serial.push(proposal);
            }
        }
        let reference_energy = self.reference_energy;
        let tick = self.tick;
        let update_memory_trace = self.config.memory_probe_enabled;
        let pool = self
            .parallel_pool
            .as_ref()
            .expect("parallel-v3 thread pool must exist");
        let mut local_deltas = pool.install(|| {
            self.organisms
                .par_iter_mut()
                .zip(slots.into_par_iter())
                .filter_map(|(organism, proposal)| {
                    proposal.map(|proposal| {
                        v3_commit_self_proposal(
                            organism,
                            proposal,
                            reference_energy,
                            tick,
                            update_memory_trace,
                        )
                    })
                })
                .collect::<Vec<_>>()
        });
        local_deltas.sort_unstable_by_key(|delta| delta.organism_id);
        for delta in local_deltas {
            if delta.heat > 0.0 {
                self.world.add_heat(delta.position, delta.heat);
            }
            self.apply_parallel_v3_resolution_stats(
                delta.selected_kind,
                delta.final_kind,
                delta.neural_failure,
                delta.memory_probe,
            );
        }
        for proposal in serial {
            self.commit_parallel_v3(proposal);
        }
        (grouping_ns, resolution_started.elapsed().as_nanos())
    }

    fn commit_parallel_v3(&mut self, proposal: ParallelProposal) {
        let oid = proposal.actor_id;
        if !self.has_organism(oid) || !self.organism(oid).alive {
            return;
        }
        if proposal.sight_cost > 0.0 {
            if self.organism(oid).chemical_energy() + 1e-12 < proposal.sight_cost {
                return;
            }
            let spent = self
                .organism_mut(oid)
                .consume_body_energy(proposal.sight_cost);
            let position = self.organism(oid).position;
            self.world.add_heat(position, spent);
        }
        let validated_intent = self.validate_parallel_v3_intent(proposal.intent);
        let final_kind = self.commit_v2_intent(&validated_intent);
        let update_memory_trace = self.config.memory_probe_enabled;
        let next_action_tick = self.tick + proposal.intent.predicted_duration_ticks.max(1);
        {
            let organism = self.organism_mut(oid);
            organism.last_intent_kind = final_kind as u8;
            organism.last_action = v2_last_action_code(final_kind);
            organism.next_action_tick = next_action_tick;
            organism.decision_count += 1;
            organism.neural_state = proposal.next_neural_state;
            if update_memory_trace {
                organism.previous_food_slot = proposal.current_food_slot;
                organism.previous_food_signal = proposal.current_food_signal;
            }
            if proposal.neural_failure {
                organism.neural_numerical_errors += 1;
            }
        }
        self.apply_parallel_v3_resolution_stats(
            proposal.intent.kind,
            final_kind,
            proposal.neural_failure,
            proposal.memory_probe,
        );
    }

    fn parallel_v3_upkeep_prefix(&mut self, oid: u32) {
        let reference_energy = self.reference_energy;
        if self.config.cellular_emergence_enabled {
            let position = self.organism(oid).position;
            let heat_signal =
                (self.world.heat_at_peek(position) / reference_energy.max(1.0)).clamp(0.0, 1.0);
            let season_signal =
                ((self.seasons.current.resource_charge_multiplier - 0.4) / 1.2).clamp(0.0, 1.0);
            let (energy_signal, debt_signal, toxin_signal, local_signal) = {
                let catalog = &self.catalog;
                let organism = &mut self.organisms[self.organism_indices[oid as usize - 1]];
                (
                    organism.energy_fraction(catalog).clamp(0.0, 1.0),
                    (organism.maintenance_debt / (4.0 * reference_energy).max(1.0)).clamp(0.0, 1.0),
                    (organism.toxin_load / organism.phenotype.toxin_tolerance.max(0.1))
                        .clamp(0.0, 1.0),
                    organism
                        .cellular
                        .as_ref()
                        .map_or(0.0, |state| state.local_signal as f64),
                )
            };
            self.organism_mut(oid).regulate_cellular([
                energy_signal as f32,
                debt_signal as f32,
                toxin_signal as f32,
                heat_signal as f32,
                season_signal as f32,
                local_signal as f32,
            ]);
            let module_demand = reference_energy
                * self.config.emergence_module_cost
                * self.organism(oid).module_upkeep();
            let paid = self.organism_mut(oid).consume_body_energy(module_demand);
            self.world.add_heat(position, paid);
            if paid < module_demand {
                self.organism_mut(oid).maintenance_debt += module_demand - paid;
            }
        }

        let production_target = reference_energy * self.config.primary_production_rate;
        if production_target > 0.0 {
            let footprint = self.footprint_cells(oid);
            let harvested = self.world.remove_heat(&footprint, production_target);
            let position = self.organism(oid).position;
            let produced = {
                let catalog = &self.catalog;
                self.organisms[self.organism_indices[oid as usize - 1]]
                    .add_body_energy(harvested, catalog)
            };
            self.world.add_heat(position, harvested - produced);
        }
    }

    fn run_parallel_v3_maintenance(&mut self) -> u128 {
        use std::time::Instant;

        let started = Instant::now();
        self.order.clear();
        self.order.extend(self.living_ordered.iter().copied());
        for index in 0..self.order.len() {
            self.parallel_v3_upkeep_prefix(self.order[index]);
        }

        let colony_bonuses: Vec<f64> = self
            .organisms
            .iter()
            .map(|organism| {
                if self.config.replaces_abstract_colonies() {
                    0.0
                } else {
                    organism
                        .colony_id
                        .and_then(|colony_id| self.colonies.get(&colony_id))
                        .map_or(0.0, |colony| colony.bonus)
                }
            })
            .collect();
        let config = &self.config;
        let catalog = &self.catalog;
        let reference_energy = self.reference_energy;
        let tick = self.tick;
        let pool = self
            .parallel_pool
            .as_ref()
            .expect("parallel-v3 thread pool must exist");
        let mut deltas = pool.install(|| {
            self.organisms
                .par_iter_mut()
                .zip(colony_bonuses.par_iter().copied())
                .map(|(organism, colony_bonus)| {
                    v3_local_maintenance(
                        organism,
                        config,
                        catalog,
                        &self.world,
                        reference_energy,
                        tick,
                        colony_bonus,
                    )
                })
                .collect::<Vec<_>>()
        });
        deltas.sort_unstable_by_key(|delta| delta.organism_id);

        let mut kills = Vec::new();
        for delta in deltas {
            if delta.heat > 0.0 {
                self.world.add_heat(delta.position, delta.heat);
            }
            self.stats.brain_energy_spent += delta.brain_paid;
            self.stats.hidden_brain_energy_spent += delta.hidden_brain_paid;
            self.stats.recurrent_brain_energy_spent += delta.recurrent_brain_paid;
            if let Some(old_area) = delta.dirty_old_area {
                if !self.occupancy_dirty.contains_key(&delta.organism_id) {
                    let offsets = self.footprint_offsets(old_area);
                    let old_positions = offsets
                        .iter()
                        .map(|&(offset_x, offset_y)| {
                            (
                                delta.position.0 + offset_x as i64,
                                delta.position.1 + offset_y as i64,
                            )
                        })
                        .collect();
                    self.occupancy_dirty
                        .insert(delta.organism_id, old_positions);
                }
            }
            if let Some(expelled) = delta.expelled {
                self.world.deposit_batch_raw(delta.position, expelled);
            }
            if let Some((catalyst, toxin)) = delta.byproduct {
                self.world.add_byproduct(delta.position, catalyst, toxin);
                if catalyst > 0.0 || toxin > 0.0 {
                    self.stats.byproduct_emissions += 1;
                }
            }
            if delta.attrition_kill {
                kills.push(delta.organism_id);
            }
        }
        for organism_id in kills {
            self.kill(organism_id, last_action::DEAD_ATTRITION);
        }
        started.elapsed().as_nanos()
    }

    fn run_parallel_v3_organism_loop(&mut self, profile: Option<&mut PhaseProfile>) {
        use std::time::Instant;

        let maintenance_ns = self.run_parallel_v3_maintenance();

        let prepare_started = Instant::now();
        let mut due = std::mem::take(&mut self.parallel_due);
        due.clear();
        due.extend(
            self.living_ordered
                .iter()
                .copied()
                .filter(|&oid| self.tick >= self.organism(oid).next_action_tick),
        );
        let mut prepared = Vec::new();
        for &oid in &due {
            let area = self.parallel_area(self.organism(oid));
            let sight = self.organism(oid).phenotype.sight;
            let _ = self.footprint_offsets(area);
            let _ = self.nearby_offsets(area, 1);
            let _ = self.nearby_offsets(area, sight);
            self.nearby_cells_into(oid, sight, &mut prepared);
            let catalog = &self.catalog;
            self.organisms[self.organism_indices[oid as usize - 1]].ensure_food_chemistry(catalog);
        }
        let prepare_ns = prepare_started.elapsed().as_nanos();
        let intent_started = Instant::now();
        let proposals = self
            .parallel_pool
            .as_ref()
            .expect("parallel-v3 thread pool must exist")
            .install(|| {
                due.par_iter()
                    .map(|&oid| self.propose_parallel_v3(oid))
                    .collect::<Vec<_>>()
            });
        let intent_ns = intent_started.elapsed().as_nanos();
        let (grouping_ns, resolution_ns) = self.resolve_parallel_v3(proposals);
        self.parallel_due = due;
        if let Some(profile) = profile {
            profile.parallel_maintenance_ns += maintenance_ns;
            profile.parallel_prepare_ns += prepare_ns;
            profile.parallel_intent_ns += intent_ns;
            profile.parallel_grouping_ns += grouping_ns;
            profile.parallel_resolution_ns += resolution_ns;
            profile.decision_ns += intent_ns;
        }
    }

    fn run_organism_loop_profiled(&mut self, profile: &mut PhaseProfile) {
        use std::time::Instant;

        if self.config.scheduler == Scheduler::ParallelV3 {
            self.run_parallel_v3_organism_loop(Some(profile));
            return;
        }
        if self.coordinated_components_enabled() && !self.bonds.is_empty() {
            let started = Instant::now();
            self.run_coordinated_organism_loop();
            profile.organism_ordering_ns += started.elapsed().as_nanos();
            return;
        }

        let started = Instant::now();
        self.order.clear();
        self.order.extend(self.living_ordered.iter().copied());
        self.rng.shuffle(&mut self.order);
        profile.organism_ordering_ns += started.elapsed().as_nanos();
        let n = self.order.len();
        for i in 0..n {
            let oid = self.order[i];
            if !self.living.contains(&oid) {
                continue;
            }
            let started = Instant::now();
            self.upkeep(oid);
            profile.upkeep_ns += started.elapsed().as_nanos();
            if !self.living.contains(&oid) {
                continue;
            }
            let started = Instant::now();
            self.digest_gut(oid);
            profile.digestion_ns += started.elapsed().as_nanos();
            let (next_action_tick, tick) = {
                let organism = self.organism(oid);
                (organism.next_action_tick, self.tick)
            };
            if tick >= next_action_tick {
                let started = Instant::now();
                self.decide_and_act(oid);
                profile.decision_ns += started.elapsed().as_nanos();
            }
        }
    }

    fn run_organism_loop(&mut self) {
        if self.config.scheduler == Scheduler::ParallelV3 {
            self.run_parallel_v3_organism_loop(None);
            return;
        }
        if self.coordinated_components_enabled() && !self.bonds.is_empty() {
            self.run_coordinated_organism_loop();
            return;
        }
        self.order.clear();
        self.order.extend(self.living_ordered.iter().copied());
        self.rng.shuffle(&mut self.order);
        let n = self.order.len();
        for i in 0..n {
            let oid = self.order[i];
            if !self.living.contains(&oid) {
                continue;
            }
            self.upkeep(oid);
            if !self.living.contains(&oid) {
                continue;
            }
            self.digest_gut(oid);
            let (next_action_tick, tick) = {
                let o = self.organism(oid);
                (o.next_action_tick, self.tick)
            };
            if tick >= next_action_tick {
                self.decide_and_act(oid);
            }
        }
    }

    // -------------------------------------------------------------- upkeep

    fn upkeep(&mut self, oid: u32) {
        let reference_energy = self.reference_energy;
        let mana_decay = self.config.mana_decay;
        let maintenance_cost_multiplier = self.config.maintenance_cost_multiplier;
        let tick = self.tick;

        if self.config.cellular_emergence_enabled {
            let position = self.organism(oid).position;
            let heat_signal =
                (self.world.heat_at_peek(position) / reference_energy.max(1.0)).clamp(0.0, 1.0);
            let season_signal =
                ((self.seasons.current.resource_charge_multiplier - 0.4) / 1.2).clamp(0.0, 1.0);
            let (energy_signal, debt_signal, toxin_signal, local_signal) = {
                let catalog = &self.catalog;
                let organism = &mut self.organisms[self.organism_indices[oid as usize - 1]];
                let energy_signal = organism.energy_fraction(catalog).clamp(0.0, 1.0);
                let debt_signal =
                    (organism.maintenance_debt / (4.0 * reference_energy).max(1.0)).clamp(0.0, 1.0);
                let toxin_signal = (organism.toxin_load
                    / organism.phenotype.toxin_tolerance.max(0.1))
                .clamp(0.0, 1.0);
                let local_signal = organism
                    .cellular
                    .as_ref()
                    .map_or(0.0, |state| state.local_signal as f64);
                (energy_signal, debt_signal, toxin_signal, local_signal)
            };
            self.organism_mut(oid).regulate_cellular([
                energy_signal as f32,
                debt_signal as f32,
                toxin_signal as f32,
                heat_signal as f32,
                season_signal as f32,
                local_signal as f32,
            ]);
            let module_demand = reference_energy
                * self.config.emergence_module_cost
                * self.organism(oid).module_upkeep();
            let paid = self.organism_mut(oid).consume_body_energy(module_demand);
            self.world.add_heat(position, paid);
            if paid < module_demand {
                self.organism_mut(oid).maintenance_debt += module_demand - paid;
            }
        }

        // primary production: harvest heat over footprint into body energy.
        // At exactly zero the old path only generated already-occupied chunks
        // and performed a zero transfer, so it is safe to skip completely.
        let production_target = reference_energy * self.config.primary_production_rate;
        if production_target > 0.0 {
            let footprint = self.footprint_cells(oid);
            let harvested = self.world.remove_heat(&footprint, production_target);
            let position = self.organism(oid).position;
            let produced = {
                let catalog = &self.catalog;
                self.organisms[self.organism_indices[oid as usize - 1]]
                    .add_body_energy(harvested, catalog)
            };
            self.world.add_heat(position, harvested - produced);
        }

        let (decay, position) = {
            let organism = &mut self.organisms[self.organism_indices[oid as usize - 1]];
            let decay = organism.mana * mana_decay;
            organism.mana -= decay;
            (decay, organism.position)
        };
        self.world.add_heat(position, decay);

        let colony_bonus = if self.config.replaces_abstract_colonies() {
            0.0
        } else {
            self.organism(oid)
                .colony_id
                .and_then(|cid| self.colonies.get(&cid))
                .map(|c| c.bonus)
                .unwrap_or(0.0)
        };
        let (brain_base_demand, brain_hidden_demand, brain_recurrent_demand) = match self
            .config
            .behavior_model
        {
            BehaviorModel::LegacyLinearMacroV1 => (0.0, 0.0, 0.0),
            BehaviorModel::LinearIntentV2 => (
                reference_energy * self.config.brain_cost_multiplier * self.config.brain_base_cost,
                0.0,
                0.0,
            ),
            BehaviorModel::RecurrentIntentV2 => {
                let policy = self
                    .organism(oid)
                    .phenotype
                    .recurrent_policy
                    .as_ref()
                    .expect("recurrent organisms must have a recurrent phenotype");
                (
                    reference_energy
                        * self.config.brain_cost_multiplier
                        * self.config.brain_base_cost,
                    reference_energy
                        * self.config.brain_cost_multiplier
                        * self.config.brain_hidden_cost
                        * policy.hidden_expression_mean(),
                    reference_energy
                        * self.config.brain_cost_multiplier
                        * self.config.brain_recurrent_cost
                        * policy.recurrent_expression_mean(),
                )
            }
        };
        let brain_demand = brain_base_demand + brain_hidden_demand + brain_recurrent_demand;
        let (paid, demand, brain_paid, position) = {
            let organism = &mut self.organisms[self.organism_indices[oid as usize - 1]];
            let physiological_demand = organism.phenotype.basal
                * reference_energy
                * maintenance_cost_multiplier
                * (1.0 - colony_bonus);
            let mana_target = physiological_demand * organism.phenotype.mana_preference;
            let mana_paid = organism.mana.min(mana_target);
            organism.mana -= mana_paid;
            let physiological_chemical_demand = physiological_demand - mana_paid;
            let chemical_paid =
                organism.consume_body_energy(physiological_chemical_demand + brain_demand);
            let brain_paid =
                (chemical_paid - physiological_chemical_demand).clamp(0.0, brain_demand);
            (
                mana_paid + chemical_paid,
                physiological_demand + brain_demand,
                brain_paid,
                organism.position,
            )
        };
        self.world.add_heat(position, paid);
        if brain_paid > 0.0 {
            let hidden_paid = if brain_demand > 0.0 {
                brain_paid * brain_hidden_demand / brain_demand
            } else {
                0.0
            };
            let recurrent_paid = if brain_demand > 0.0 {
                brain_paid * brain_recurrent_demand / brain_demand
            } else {
                0.0
            };
            self.stats.brain_energy_spent += brain_paid;
            self.stats.hidden_brain_energy_spent += hidden_paid;
            self.stats.recurrent_brain_energy_spent += recurrent_paid;
            let organism = self.organism_mut(oid);
            organism.brain_energy_spent += brain_paid;
            organism.hidden_brain_energy_spent += hidden_paid;
            organism.recurrent_brain_energy_spent += recurrent_paid;
        }
        let deficit = demand - paid;
        {
            let organism = &mut self.organisms[self.organism_indices[oid as usize - 1]];
            if deficit > 1e-12 {
                organism.maintenance_debt += deficit;
                organism.integrity -= deficit / reference_energy.max(1e-9) * 0.25;
            } else {
                organism.maintenance_debt = (organism.maintenance_debt - demand * 0.2).max(0.0);
            }

            if organism.toxin_load > organism.phenotype.toxin_tolerance {
                let excess = organism.toxin_load - organism.phenotype.toxin_tolerance;
                organism.integrity -= excess * 0.0015;
            }
            organism.toxin_load *= 0.999;
        }

        let mut attrition_kill = false;
        {
            let organism = &mut self.organisms[self.organism_indices[oid as usize - 1]];
            let age = tick as i64 - organism.birth_tick as i64;
            if age > organism.phenotype.lifespan {
                let ratio = age as f64 / organism.phenotype.lifespan as f64;
                let mut base_hazard = (0.0005 * ratio * ratio).min(0.08);
                let chemical_energy = organism.chemical_energy();
                let support_budget = (chemical_energy * 0.002)
                    .min(organism.mana * 0.002)
                    .min(base_hazard * reference_energy);
                if support_budget > 0.0 {
                    let mana_support = organism.mana.min(support_budget * 0.5);
                    organism.mana -= mana_support;
                    let chemical_support =
                        organism.consume_body_energy(support_budget - mana_support);
                    let spent = mana_support + chemical_support;
                    let position = organism.position;
                    self.world.add_heat(position, spent);
                    let denom = (base_hazard * reference_energy).max(1e-9);
                    base_hazard *= (1.0 - spent / denom).max(0.05);
                }
                attrition_kill = self.rng.chance(base_hazard);
            }
        }
        if attrition_kill {
            self.organism_mut(oid).integrity = 0.0;
        }

        let (integrity, debt) = {
            let o = self.organism(oid);
            (o.integrity, o.maintenance_debt)
        };
        if integrity <= 0.0 || debt > reference_energy * 4.0 {
            self.kill(oid, last_action::DEAD_ATTRITION);
        }
    }

    // ------------------------------------------------------------- digest

    fn digest_gut(&mut self, oid: u32) {
        let has_gut = !self.organism(oid).gut.is_empty();
        if !has_gut || self.rng.f64() > (self.config.reaction_rate * 0.35).min(1.0) {
            return;
        }
        let molecule_id = self.organism(oid).gut[0].molecule_id;
        let product = {
            let organism = self.organism_mut(oid);
            let source = &mut organism.gut[0];
            let taken = source.take(1);
            if source.count == 0 {
                organism.gut.remove(0);
            }
            taken
        };
        let def_signature = self.catalog.molecules[molecule_id as usize].signature;
        let def_reactivity = self.catalog.molecules[molecule_id as usize].reactivity;
        let def_permeability = self.catalog.molecules[molecule_id as usize].permeability;
        let (diet_signature, toxin_sensitivity, digestion, assimilation) = {
            let p = &self.organism(oid).phenotype;
            (
                p.diet_signature,
                p.toxin_sensitivity,
                p.digestion,
                p.assimilation,
            )
        };
        let match_ = genetics::similarity(&def_signature, &diet_signature);

        let activation_target = self.reference_energy * 0.0005;
        let activation = self
            .organism_mut(oid)
            .consume_body_energy(activation_target);
        let position = self.organism(oid).position;
        self.world.add_heat(position, activation);

        let catalysis = self
            .organism(oid)
            .substrate_module_expression(ModulePrimitive::Catalysis, molecule_id);
        let (local_fit, local_toxin) = self.local_chemistry_signals(self.organism(oid));
        let guest_boost = if self.config.dynamic_chemistry_enabled {
            1.0 + self.config.guest_niche_coupling * self.guest_reactivity(oid)
        } else {
            1.0
        };
        let capture_target = (product.energy
            * digestion
            * match_
            * (1.0 + self.config.emergence_module_effect * catalysis)
            * (1.0 + local_fit)
            * guest_boost)
            .clamp(0.0, product.energy);
        let captured = {
            let catalog = &self.catalog;
            self.organisms[self.organism_indices[oid as usize - 1]]
                .add_body_energy(capture_target, catalog)
        };
        let remaining = product.energy - captured;
        let process_heat = remaining * 0.15;
        let mut product = product;
        product.energy = (remaining - process_heat).max(0.0);
        let position = self.organism(oid).position;
        self.world.add_heat(position, process_heat);
        if self.config.dynamic_chemistry_enabled {
            let (catalyst_emission, toxin_emission) = Self::byproduct_emission(
                &product,
                def_reactivity,
                def_permeability,
                self.config.byproduct_strength,
            );
            self.world
                .add_byproduct(position, catalyst_emission, toxin_emission);
            if catalyst_emission > 0.0 || toxin_emission > 0.0 {
                self.stats.byproduct_emissions += 1;
            }
        }

        let sensitivity: f64 = (0..4)
            .map(|i| def_signature[i] * toxin_sensitivity[i])
            .sum();
        {
            let environmental_toxin_scale = if self.config.dynamic_chemistry_enabled {
                1.0 + (local_toxin * self.config.chemistry_coupling).clamp(0.0, 2.0)
            } else {
                1.0
            };
            let organism = self.organism_mut(oid);
            organism.toxin_load +=
                def_reactivity * def_permeability * sensitivity * environmental_toxin_scale;
        }

        let target_mass = {
            let organism = self.organism(oid);
            let mass = organism.peek_structural_mass(&self.catalog) as f64;
            mass < organism.target_mass * 1.3
        };
        let grow = self.rng.chance(assimilation * match_);
        if grow && target_mass {
            self.mark_occupancy_dirty(oid);
            let organism = self.organism_mut(oid);
            add_batch(&mut organism.body, product);
            organism.invalidate_body_cache();
        } else {
            let organism = self.organism_mut(oid);
            add_batch(&mut organism.waste, product);
        }

        let over_tolerance = {
            let organism = self.organism(oid);
            organism.toxin_load > organism.phenotype.toxin_tolerance
        };
        if over_tolerance {
            let detox_cost = self
                .organism(oid)
                .chemical_energy()
                .min(self.reference_energy * 0.002);
            let spent = self.organism_mut(oid).consume_body_energy(detox_cost);
            let position = self.organism(oid).position;
            self.world.add_heat(position, spent);
            let reference_energy = self.reference_energy;
            let organism = self.organism_mut(oid);
            organism.toxin_load =
                (organism.toxin_load - spent / reference_energy.max(1e-9) * 2.0).max(0.0);
        }

        let expel = inventory_count(&self.organism(oid).waste) > 12;
        if expel {
            let expelled = {
                let organism = self.organism_mut(oid);
                let source = &mut organism.waste[0];
                let count = (source.count / 2).max(1);
                let taken = source.take(count);
                if source.count == 0 {
                    organism.waste.remove(0);
                }
                taken
            };
            let position = self.organism(oid).position;
            self.world.deposit_batch_raw(position, expelled);
        }
    }

    // ------------------------------------------------ dynamic chemistry

    /// Byproduct emissions from a digested batch. These are scalar local
    /// conditions, not ledgered matter or energy.
    fn byproduct_emission(
        batch: &Batch,
        reactivity: f64,
        permeability: f64,
        strength: f64,
    ) -> (f64, f64) {
        calculate_byproduct_emission(batch, reactivity, permeability, strength)
    }

    fn local_chemistry_signals(&self, organism: &Organism) -> (f64, f64) {
        chemistry_signals_for(organism, &self.world, &self.config)
    }

    /// Local byproduct fit in [-1, 1]: catalysts help a reactive diet while
    /// environmental toxin penalizes sensitive metabolisms.
    fn local_chemistry_fit(&self, organism: &Organism) -> f64 {
        self.local_chemistry_signals(organism).0
    }

    /// Mean reactivity of material held by a host's internal guests.
    fn guest_reactivity(&self, organism_id: u32) -> f64 {
        if !self.has_organism(organism_id) {
            return 0.0;
        }
        guest_reactivity_for(self.organism(organism_id), &self.catalog)
    }

    // --------------------------------------------------- environment phases

    fn prepare_deposit_positions(&mut self) {
        self.deposit_positions.clear();
        if self.config.deposit_production_rate > 0.0
            || self.config.decomposition_rate > 0.0
            || self.config.dynamic_chemistry_enabled
        {
            self.deposit_positions
                .extend(self.world.deposits.keys().copied());
            if self.config.dynamic_chemistry_enabled {
                self.deposit_positions.sort_unstable();
                self.reaction_positions.clear();
                if !self.reaction_rules.is_empty() {
                    self.reaction_positions
                        .extend(self.deposit_positions.iter().copied().filter(|position| {
                            self.world.deposits.get(position).is_some_and(|inventory| {
                                inventory.iter().any(|batch| {
                                    self.reaction_reactant_flags
                                        .get(batch.molecule_id as usize)
                                        .copied()
                                        .unwrap_or(false)
                                        && batch.count > 0
                                })
                            })
                        }));
                }
            }
        }
    }

    fn produce_deposits(&mut self) {
        let rate =
            self.config.deposit_production_rate * self.seasons.current.resource_charge_multiplier;
        if rate <= 0.0 {
            return;
        }
        let capacities: Vec<f64> = self
            .catalog
            .molecules
            .iter()
            .map(|m| m.energy_capacity)
            .collect();
        let affinities = &self.seasons.current.molecule_charge_affinities;
        for &position in self.deposit_positions.iter() {
            let heat = self.world.heat_at_peek(position);
            if heat <= 1e-12 {
                continue;
            }
            let mut capacity = 0.0f64;
            let mut seasonal_capacity = 0.0f64;
            if let Some(inventory) = self.world.deposits.get(&position) {
                for batch in inventory {
                    let molecule_id = batch.molecule_id as usize;
                    let headroom = capacities[molecule_id] * batch.count as f64 - batch.energy;
                    capacity += headroom;
                    seasonal_capacity += headroom * affinities[molecule_id];
                }
            }
            if capacity <= 1e-12 {
                continue;
            }
            let local_affinity = seasonal_capacity / capacity;
            let wanted = (heat * rate * local_affinity).min(capacity);
            let removed = self.world.remove_heat_at(position, wanted);
            if removed <= 0.0 {
                continue;
            }
            if let Some(inventory) = self.world.deposits.get_mut(&position) {
                for batch in inventory.iter_mut() {
                    let molecule_id = batch.molecule_id as usize;
                    let headroom = capacities[molecule_id] * batch.count as f64 - batch.energy;
                    if headroom > 0.0 {
                        batch.energy += removed * (headroom / capacity);
                    }
                }
            }
        }
    }

    fn decompose_environment(&mut self) {
        let rate = self.config.decomposition_rate * self.seasons.current.decomposition_multiplier;
        if rate <= 0.0 {
            return;
        }
        let instability = self.catalog.instability.clone();
        self.heat_adds.clear();
        for &position in self.deposit_positions.iter() {
            let mut released = 0.0;
            if let Some(inventory) = self.world.deposits.get_mut(&position) {
                for batch in inventory.iter_mut() {
                    let amount = batch.energy * rate * instability[batch.molecule_id as usize];
                    batch.energy -= amount;
                    released += amount;
                }
            }
            if released > 0.0 {
                self.heat_adds.push((position, released));
            }
        }
        for &(position, amount) in self.heat_adds.iter() {
            self.world.add_heat(position, amount);
        }
    }

    fn run_environmental_reactions(&mut self) {
        const MAX_REACTIONS_PER_CELL: usize = 2;
        if !self.config.dynamic_chemistry_enabled
            || self.reaction_rules.is_empty()
            || self.config.environmental_reaction_rate <= 0.0
        {
            return;
        }

        let base_rate = self.config.environmental_reaction_rate;
        let thermodynamics = self.config.reaction_thermodynamics;
        let reference_energy = self.reference_energy.max(1.0e-9);
        let mut batch_indices = std::mem::take(&mut self.reaction_batch_indices);
        batch_indices.resize(self.catalog.molecules.len(), NO_BATCH_INDEX);
        let mut products = std::mem::take(&mut self.reaction_products);

        for position_index in 0..self.reaction_positions.len() {
            let position = self.reaction_positions[position_index];
            batch_indices.fill(NO_BATCH_INDEX);
            {
                let Some(inventory) = self.world.deposits.get(&position) else {
                    continue;
                };
                for (index, batch) in inventory.iter().enumerate() {
                    if batch.count > 0 {
                        batch_indices[batch.molecule_id as usize] = index;
                    }
                }
            }
            let heat = self.world.heat_at_peek(position);
            let (catalyst, _) = self.world.byproduct_at(position);
            let temperature_factor =
                (1.0 + (heat / (2.0 * reference_energy)).min(1.0)).clamp(1.0, 2.0);
            let catalyst_factor = 1.0 + 2.0 * catalyst.clamp(0.0, 1.0);
            let mut reactions = 0usize;
            let mut reaction_heat = 0.0;
            products.clear();

            for rule in self.reaction_rules.iter().copied() {
                if reactions >= MAX_REACTIONS_PER_CELL {
                    break;
                }
                let a_index = batch_indices[rule.a as usize];
                let b_index = batch_indices[rule.b as usize];
                let available = a_index != NO_BATCH_INDEX
                    && b_index != NO_BATCH_INDEX
                    && self.world.deposits.get(&position).is_some_and(|inventory| {
                        if a_index == b_index {
                            inventory[a_index].count >= 2
                        } else {
                            inventory[a_index].count > 0 && inventory[b_index].count > 0
                        }
                    });
                if !available {
                    continue;
                }
                let product_id = rule.c as usize;
                let season_factor = self
                    .seasons
                    .current
                    .molecule_charge_affinities
                    .get(product_id)
                    .copied()
                    .unwrap_or(1.0)
                    .clamp(0.25, 2.0);
                let probability =
                    (base_rate * temperature_factor * season_factor * catalyst_factor)
                        .clamp(0.0, 1.0);
                if !self.rng.chance(probability) {
                    continue;
                }

                let Some((released, product)) =
                    self.world
                        .deposits
                        .get_mut(&position)
                        .and_then(|inventory| {
                            if inventory[a_index].count <= 0
                                || inventory[b_index].count <= 0
                                || (a_index == b_index && inventory[a_index].count < 2)
                            {
                                return None;
                            }
                            let first = inventory[a_index].take(1);
                            let second = if a_index == b_index {
                                inventory[a_index].take(1)
                            } else {
                                inventory[b_index].take(1)
                            };
                            let input_energy = first.energy + second.energy;
                            let released = input_energy * thermodynamics;
                            Some((
                                released,
                                Batch {
                                    molecule_id: rule.c,
                                    count: 1,
                                    energy: input_energy - released,
                                },
                            ))
                        })
                else {
                    continue;
                };
                reaction_heat += released;
                products.push(product);
                reactions += 1;
                self.stats.environmental_reactions += 1;
            }

            if let Some(inventory) = self.world.deposits.get_mut(&position) {
                inventory.retain(|batch| batch.count > 0);
                for product in products.drain(..) {
                    add_batch(inventory, product);
                }
            }
            if reaction_heat > 0.0 {
                self.world.add_heat(position, reaction_heat);
            }
        }

        self.reaction_batch_indices = batch_indices;
        self.reaction_products = products;
    }

    fn update_cellular_network(&mut self) {
        if !self.config.cellular_emergence_enabled {
            return;
        }

        self.bond_candidates.clear();
        for &organism_id in &self.living_ordered {
            let position = self.organism(organism_id).position;
            for dy in -1..=1 {
                for dx in -1..=1 {
                    if dx == 0 && dy == 0 {
                        continue;
                    }
                    if let Some(occupants) =
                        self.world.occupants_at((position.0 + dx, position.1 + dy))
                    {
                        for &other_id in occupants {
                            if other_id == organism_id || !self.living.contains(&other_id) {
                                continue;
                            }
                            let edge = if organism_id < other_id {
                                (organism_id, other_id)
                            } else {
                                (other_id, organism_id)
                            };
                            self.bond_candidates.insert(edge);
                        }
                    }
                }
            }
        }

        let mut candidate_edges = std::mem::take(&mut self.bond_candidate_scratch);
        candidate_edges.clear();
        candidate_edges.extend(self.bond_candidates.iter().copied());
        for &edge @ (left_id, right_id) in &candidate_edges {
            if self.bonds.contains_key(&edge) {
                continue;
            }
            let (compatibility, structure, retention, related) = {
                let left = self.organism(left_id);
                let right = self.organism(right_id);
                let left_genome = left.genome.emergence.as_ref().unwrap();
                let right_genome = right.genome.emergence.as_ref().unwrap();
                let compatibility = left_genome.receptor_similarity(right_genome);
                let structure = left.module_expression(ModulePrimitive::Structure)
                    * right.module_expression(ModulePrimitive::Structure);
                let retention =
                    (left_genome.bond_retention + right_genome.bond_retention) as f64 * 0.5;
                let related =
                    left.parent_ids.contains(&right_id) || right.parent_ids.contains(&left_id);
                (compatibility, structure, retention, related)
            };
            let inheritance_factor = if related { 1.0 + retention } else { 1.0 };
            let probability = (self.config.emergence_bond_rate
                * compatibility
                * structure.tanh()
                * inheritance_factor)
                .clamp(0.0, 1.0);
            if probability > 0.0 && self.rng.chance(probability) {
                self.bonds.insert(
                    edge,
                    Bond {
                        left: left_id,
                        right: right_id,
                        formed_tick: self.tick,
                        strength: (compatibility * structure.tanh()).clamp(0.01, 1.0) as f32,
                    },
                );
                self.emergence_stats.bond_formations += 1;
            }
        }

        let mut bond_edges = std::mem::take(&mut self.bond_edge_scratch);
        bond_edges.clear();
        bond_edges.extend(self.bonds.iter().map(|(&edge, &bond)| (edge, bond)));
        candidate_edges.clear();
        for (edge, bond) in &bond_edges {
            let break_probability = (self.config.emergence_bond_break_rate
                / (0.1 + bond.strength as f64))
                .clamp(0.0, 1.0);
            let random_break = break_probability > 0.0 && self.rng.chance(break_probability);
            if !self.living.contains(&bond.left)
                || !self.living.contains(&bond.right)
                || World::distance(
                    self.position_for_id(bond.left),
                    self.position_for_id(bond.right),
                ) > 1
                || random_break
            {
                candidate_edges.push(*edge);
            }
        }
        for &edge in &candidate_edges {
            self.bonds.remove(&edge);
            self.emergence_stats.bond_breaks += 1;
        }

        for organism in &mut self.organisms {
            if let Some(cellular) = &mut organism.cellular {
                cellular.local_signal = 0.0;
            }
        }
        let mut bonds = std::mem::take(&mut self.bond_scratch);
        bonds.clear();
        bonds.extend(self.bonds.values().copied());
        let mut signal_updates = std::mem::take(&mut self.signal_update_scratch);
        signal_updates.clear();
        signal_updates.reserve(bonds.len() * 2);
        for bond in &bonds {
            let left_signal = self
                .organism(bond.left)
                .cellular
                .as_ref()
                .map_or(0.0, |state| state.emitted_signal);
            let right_signal = self
                .organism(bond.right)
                .cellular
                .as_ref()
                .map_or(0.0, |state| state.emitted_signal);
            signal_updates.push((bond.left, right_signal * bond.strength));
            signal_updates.push((bond.right, left_signal * bond.strength));
        }
        for &(organism_id, signal) in &signal_updates {
            if self.has_organism(organism_id) {
                if let Some(cellular) = &mut self.organism_mut(organism_id).cellular {
                    cellular.local_signal = (cellular.local_signal + signal).clamp(0.0, 1.0);
                }
            }
        }

        for &bond in &bonds {
            if !self.has_organism(bond.left) || !self.has_organism(bond.right) {
                continue;
            }
            let (left_energy, right_energy, exchange) = {
                let left = self.organism(bond.left);
                let right = self.organism(bond.right);
                let left_genome = left.genome.emergence.as_ref().unwrap();
                let right_genome = right.genome.emergence.as_ref().unwrap();
                (
                    left.chemical_energy(),
                    right.chemical_energy(),
                    left_genome.exchange.min(right_genome.exchange) as f64,
                )
            };
            let difference = left_energy - right_energy;
            if difference.abs() <= self.reference_energy * 1.0e-6 {
                continue;
            }
            let (source_id, target_id) = if difference > 0.0 {
                (bond.left, bond.right)
            } else {
                (bond.right, bond.left)
            };
            let requested = difference.abs()
                * self.config.emergence_exchange_rate
                * exchange
                * bond.strength as f64;
            let transferred = self.organism_mut(source_id).consume_body_energy(requested);
            let accepted = {
                let catalog = &self.catalog;
                self.organisms[self.organism_indices[target_id as usize - 1]]
                    .add_body_energy(transferred, catalog)
            };
            self.world
                .add_heat(self.organism(target_id).position, transferred - accepted);
            if transferred > 0.0 {
                self.emergence_stats.energy_exchanges += 1;
            }
        }

        let mut living_ids = std::mem::take(&mut self.emergence_id_scratch);
        living_ids.clear();
        living_ids.extend(self.living_ordered.iter().copied());
        for &organism_id in &living_ids {
            self.update_internal_guests(organism_id);
        }
        self.bond_candidate_scratch = candidate_edges;
        self.bond_edge_scratch = bond_edges;
        self.bond_scratch = bonds;
        self.signal_update_scratch = signal_updates;
        self.emergence_id_scratch = living_ids;
    }

    fn debit_guest_energy(guest: &mut InternalGuest, amount: f64) -> f64 {
        let mut remaining = amount.max(0.0);
        let free = guest.free_energy.min(remaining);
        guest.free_energy -= free;
        remaining -= free;
        let mut paid = free;
        for batch in &mut guest.inventory {
            let debit = batch.energy.min(remaining);
            batch.energy -= debit;
            remaining -= debit;
            paid += debit;
            if remaining <= 1.0e-15 {
                break;
            }
        }
        paid
    }

    fn update_internal_guests(&mut self, organism_id: u32) {
        if !self.has_organism(organism_id) {
            return;
        }
        let position = self.organism(organism_id).position;
        let tolerance = self
            .organism(organism_id)
            .genome
            .emergence
            .as_ref()
            .map_or(0.0, |genome| genome.guest_tolerance as f64);
        let mut guests = self
            .organism_mut(organism_id)
            .cellular
            .as_mut()
            .map(|state| std::mem::take(&mut state.guests))
            .unwrap_or_default();
        let mut retained = Vec::with_capacity(guests.len());
        let mut offspring = Vec::new();
        let niche_fit = if self.config.dynamic_chemistry_enabled {
            self.local_chemistry_fit(self.organism(organism_id))
        } else {
            0.0
        };
        for mut guest in guests.drain(..) {
            guest.age = guest.age.saturating_add(1);
            let demand = self.reference_energy
                * self.config.emergence_module_cost
                * (0.05 + 0.15 * (1.0 - tolerance))
                * (1.0 - self.config.guest_niche_coupling * niche_fit.max(0.0)).max(0.0);
            let paid = Self::debit_guest_energy(&mut guest, demand);
            self.world.add_heat(position, paid);
            self.emergence_stats.guest_energy_demand += paid;
            let guest_energy = inventory_energy(&guest.inventory) + guest.free_energy;
            if guest_energy <= self.reference_energy * 1.0e-8 {
                for batch in guest.inventory.drain(..) {
                    add_batch(&mut self.organism_mut(organism_id).body, batch);
                }
                self.organism_mut(organism_id).invalidate_body_cache();
                self.emergence_stats.guest_losses += 1;
                continue;
            }

            let exchange = self.config.emergence_exchange_rate
                * guest.exchange as f64
                * tolerance
                * (1.0 + self.config.guest_niche_coupling * niche_fit.max(0.0));
            let offered = guest_energy * exchange;
            let transferred = Self::debit_guest_energy(&mut guest, offered);
            let accepted = {
                let catalog = &self.catalog;
                self.organisms[self.organism_indices[organism_id as usize - 1]]
                    .add_body_energy(transferred, catalog)
            };
            self.world.add_heat(position, transferred - accepted);
            self.emergence_stats.guest_energy_exchange += accepted;

            if retained.len() + offspring.len() + 1 < self.config.emergence_max_internal_guests
                && guest_energy > self.reference_energy * 0.5
                && guest.inventory.iter().any(|batch| batch.count >= 4)
                && self.rng.chance(0.0005 * tolerance)
            {
                let mut child_inventory = Vec::new();
                for batch in &mut guest.inventory {
                    let count = batch.count / 2;
                    if count > 0 {
                        add_batch(&mut child_inventory, batch.take(count));
                    }
                }
                let child_free_energy = guest.free_energy * 0.5;
                guest.free_energy -= child_free_energy;
                offspring.push(InternalGuest {
                    source_organism_id: guest.source_organism_id,
                    genome_id: guest.genome_id,
                    species_id: guest.species_id,
                    inventory: child_inventory,
                    free_energy: child_free_energy,
                    exchange: guest.exchange,
                    age: 0,
                });
                self.emergence_stats.guest_replications += 1;
            }
            retained.push(guest);
        }
        retained.extend(offspring);
        if let Some(cellular) = &mut self.organism_mut(organism_id).cellular {
            cellular.guests = retained;
        }
    }

    fn resolve_effects(&mut self) {
        let expired: Vec<u32> = self
            .effects
            .iter()
            .filter(|(_, e)| self.tick >= e.expires_tick)
            .map(|(id, _)| *id)
            .collect();
        for effect_id in expired {
            let effect = self.effects.remove(&effect_id).unwrap();
            let position = if effect.target_id != 0 {
                self.position_for_id(effect.target_id)
            } else if effect.source_id != 0 {
                self.position_for_id(effect.source_id)
            } else {
                (0, 0)
            };
            self.world.add_heat(position, effect.energy);
            if self.has_organism(effect.target_id) {
                let organism = self.organism_mut(effect.target_id);
                if effect.channel == 1 {
                    organism.water_status = None;
                } else if effect.channel == 2 {
                    organism.earth_status = None;
                }
            }
        }
    }

    fn expire_corpses(&mut self) {
        let dead: Vec<u32> = self
            .corpses
            .iter()
            .filter(|(_, c)| self.tick.saturating_sub(c.created_tick) > CORPSE_TTL)
            .map(|(id, _)| *id)
            .collect();
        for corpse_id in dead {
            self.corpses.remove(&corpse_id);
        }
    }

    // ------------------------------------------------------------ decisions

    fn nearby_cells_into(&mut self, oid: u32, radius: usize, buf: &mut Vec<Position>) {
        let (organism_area, position) = {
            let organism = &mut self.organisms[self.organism_indices[oid as usize - 1]];
            let area = organism.area(&self.catalog);
            (area, organism.position)
        };
        let offsets = self.nearby_offsets(organism_area, radius);
        buf.clear();
        buf.extend(
            offsets
                .iter()
                .map(|&(dx, dy)| (position.0 + dx as i64, position.1 + dy as i64)),
        );
        self.world.ensure_positions(buf);
    }

    #[cfg(test)]
    fn hottest_cell(&self, cells: &[Position]) -> (Position, f64) {
        let mut cells = cells.iter().copied();
        let first = cells.next().expect("nearby cells must not be empty");
        let mut hottest_position = first;
        let mut hottest_value = self.world.heat_at_peek(first);
        for position in cells {
            let heat = self.world.heat_at_peek(position);
            // Python's manual scan keeps the first position on equal heat.
            if heat > hottest_value {
                hottest_position = position;
                hottest_value = heat;
            }
        }
        (hottest_position, hottest_value)
    }

    /// Observe food, heat, and occupants in one ordered cell traversal.
    fn observe_cells(&mut self, oid: u32, cells: &[Position]) -> CellObservations {
        let noise_scale;
        {
            let organism = &mut self.organisms[self.organism_indices[oid as usize - 1]];
            noise_scale = 0.25 + organism.phenotype.risk;
            organism.ensure_food_chemistry(&self.catalog);
        }
        let origin = self.organism(oid).position;
        let reference_energy = self.reference_energy.max(1e-9);
        let mut best: Option<(Position, u16, f64)> = None;
        let mut hottest_position = cells[0];
        let mut hottest_value = self.world.heat_at_peek(cells[0]);
        for &position in cells {
            if let Some(inventory) = self.world.deposits.get(&position) {
                if !inventory.is_empty() {
                    let distance = World::distance(origin, position);
                    let distance_cost = distance as f64 * 0.03;
                    for batch in inventory {
                        if batch.count <= 0 {
                            continue;
                        }
                        let (match_, hazard) = self.organisms
                            [self.organism_indices[oid as usize - 1]]
                            .food_chemistry_at(batch.molecule_id as usize);
                        let energy_density = batch.energy / batch.count as f64 / reference_energy;
                        let mut score = match_ * energy_density - hazard - distance_cost;
                        score += self.rng.uniform(-0.08, 0.08) * noise_scale;
                        if best.is_none() || score > best.unwrap().2 {
                            best = Some((position, batch.molecule_id, score));
                        }
                    }
                }
            }
            let heat = self.world.heat_at_peek(position);
            if heat > hottest_value {
                hottest_position = position;
                hottest_value = heat;
            }
        }
        let food = match best {
            Some(candidate) if candidate.2 > -0.1 => Some(candidate),
            _ => None,
        };
        CellObservations {
            food,
            heat_position: hottest_position,
            local_heat: hottest_value,
        }
    }

    fn genome_distance(&mut self, left: u32, right: u32) -> f64 {
        let key = if left <= right {
            (left, right)
        } else {
            (right, left)
        };
        if let Some(&distance) = self.genome_distances.get(&key) {
            return distance;
        }
        let distance = self.genome_by_id(left).distance(self.genome_by_id(right));
        if self.genome_distances.len() >= MAX_GENOME_DISTANCE_CACHE {
            self.genome_distances.clear();
        }
        self.genome_distances.insert(key, distance);
        distance
    }

    fn genome_by_id(&self, genome_id: u32) -> &Genome {
        if let Some(&organism_id) = self.genome_owners.get(genome_id as usize - 1) {
            if organism_id != 0 {
                return self.organisms[self.organism_indices[organism_id as usize - 1]]
                    .genome
                    .as_ref();
            }
        }
        for species in &self.species {
            if species.representative_genome.genome_id == genome_id {
                return &species.representative_genome;
            }
        }
        panic!("unknown genome id {genome_id}")
    }

    /// Best prey among nearby organism ids: returns prey id.
    fn best_prey(&mut self, oid: u32, nearby: &[u32]) -> Option<u32> {
        let origin = self.organism(oid).position;
        let my_mass = self.organism(oid).peek_structural_mass(&self.catalog);
        let my_diet = self.organism(oid).phenotype.diet_signature;
        let my_risk = self.organism(oid).phenotype.risk;
        let threshold = self.config.prey_compatibility_threshold;
        let mut best: Option<(f64, u32)> = None;
        for &other_id in nearby {
            let body_signature = {
                let catalog = &self.catalog;
                self.organisms[self.organism_indices[other_id as usize - 1]].body_signature(catalog)
            };
            let compatibility = genetics::similarity(&my_diet, &body_signature);
            if compatibility < threshold {
                continue;
            }
            let other = self.organism(other_id);
            let other_mass = other.peek_structural_mass(&self.catalog);
            let size_advantage = my_mass as f64 / other_mass.max(1) as f64;
            let mut score = compatibility + 0.25 * size_advantage
                - World::distance(origin, other.position) as f64 * 0.05;
            score += self.rng.uniform(-0.05, 0.05) * (0.25 + my_risk);
            if best.is_none() || score > best.unwrap().0 {
                best = Some((score, other_id));
            }
        }
        best.map(|b| b.1)
    }

    fn is_reproductively_ready(&self, oid: u32) -> bool {
        let organism = self.organism(oid);
        let maturity =
            py_round(organism.phenotype.maturity_age as f64 * self.config.maturity_age_multiplier)
                .max(1);
        organism.alive
            && self.tick as i64 - organism.birth_tick as i64 >= maturity
            && self.tick >= organism.reproduction_cooldown
    }

    fn collect_mate_draws(&mut self, candidates: &[u32], draws: &mut Vec<(u32, f64)>) {
        draws.clear();
        for &mate_id in candidates {
            if self.is_reproductively_ready(mate_id)
                && self.organism(mate_id).phenotype.sexual > 0.05
            {
                draws.push((mate_id, self.rng.uniform(0.0, 0.03)));
            }
        }
    }

    fn best_mate_from_draws(&mut self, oid: u32, draws: &[(u32, f64)]) -> Option<u32> {
        let genome_id = self.organism(oid).genome.genome_id;
        let mut best: Option<(f64, u32)> = None;
        for &(mate_id, noise) in draws {
            let distance = self.genome_distance(genome_id, self.organism(mate_id).genome.genome_id);
            let score = distance + noise;
            if best.is_none() || score < best.unwrap().0 {
                best = Some((score, mate_id));
            }
        }
        best.map(|candidate| candidate.1)
    }

    fn v2_action_delay(&self, oid: u32) -> u32 {
        let slowed = if self.organism(oid).water_status.is_some() {
            2.0
        } else {
            1.0
        };
        ((4.0 / self.organism(oid).phenotype.speed * slowed).ceil() as u32).max(1)
    }

    fn v2_move_cost(&self, oid: u32) -> f64 {
        let mass_ratio = self.organism(oid).peek_structural_mass(&self.catalog) as f64
            / self.reference_body_mass.max(1.0);
        let speed_fraction = (self.organism(oid).phenotype.speed / 4.0).min(1.0);
        self.config.reference_move_cost
            * self.reference_energy
            * mass_ratio
            * (1.0 + speed_fraction * speed_fraction)
            / self.organism(oid).phenotype.move_efficiency
    }

    /// Returns prey value, threat, mate compatibility, social complementarity,
    /// and normalized distance using only currently visible state.
    fn v2_target_metrics(&self, oid: u32, target_id: u32) -> (f32, f32, f32, f32, f32) {
        let actor = self.organism(oid);
        let target = self.organism(target_id);
        let actor_mass = actor.peek_structural_mass(&self.catalog).max(1) as f64;
        let target_mass = target.peek_structural_mass(&self.catalog).max(1) as f64;
        let target_signature = self.catalog.inventory_signature(&target.body);
        let dietary_match =
            genetics::similarity(&actor.phenotype.diet_signature, &target_signature);
        let size_advantage = (actor_mass / target_mass).min(2.0) * 0.5;
        let prey = unit_f32(dietary_match * (0.5 + 0.5 * size_advantage));
        let threat =
            unit_f32(target.phenotype.attack * target_mass / self.reference_body_mass.max(1.0));
        let mate = if self.is_reproductively_ready(target_id) && target.phenotype.sexual > 0.05 {
            unit_f32(1.0 - actor.genome.distance(&target.genome))
        } else {
            0.0
        };
        let social = unit_f32(
            1.0 - genetics::similarity(
                &actor.phenotype.diet_signature,
                &target.phenotype.diet_signature,
            ),
        );
        let distance = unit_f32(
            World::distance(actor.position, target.position) as f64
                / actor.phenotype.sight.max(1) as f64,
        );
        (prey, threat, mate, social, distance)
    }

    fn decide_and_act(&mut self, oid: u32) {
        match self.config.behavior_model {
            BehaviorModel::LegacyLinearMacroV1 => self.decide_and_act_legacy(oid),
            BehaviorModel::LinearIntentV2 | BehaviorModel::RecurrentIntentV2 => {
                self.decide_and_act_v2(oid)
            }
        }
    }

    fn decide_and_act_v2(&mut self, oid: u32) {
        use behavior::intent::*;
        use behavior::observation::*;

        let mut cells_r1 = std::mem::take(&mut self.action_cells_r1);
        self.nearby_cells_into(oid, 1, &mut cells_r1);
        let mut cells_sight = std::mem::take(&mut self.action_cells_sight);
        let mut effective_sight = 1usize;
        let realized_sight = self.organism(oid).phenotype.sight;
        if realized_sight > 1 {
            self.nearby_cells_into(oid, realized_sight, &mut cells_sight);
            let sight_cost = self.config.sight_cost_per_cell
                * self.reference_energy
                * ((cells_sight.len() as i64 - cells_r1.len() as i64).max(0)) as f64;
            if self.organism(oid).chemical_energy() >= sight_cost {
                let spent = self.organism_mut(oid).consume_body_energy(sight_cost);
                let position = self.organism(oid).position;
                self.world.add_heat(position, spent);
                effective_sight = realized_sight;
            }
        }
        let cells = if effective_sight > 1 {
            &cells_sight
        } else {
            &cells_r1
        };
        let mut footprint = std::mem::take(&mut self.v2_footprint);
        self.footprint_into(oid, &mut footprint);
        let origin = self.organism(oid).position;
        let facing = self.organism(oid).facing;

        let mut nearby = std::mem::take(&mut self.action_nearby);
        nearby.clear();
        for &cell in cells {
            if let Some(occupants) = self.world.occupants_at(cell) {
                nearby.extend(occupants.iter().copied());
            }
        }
        nearby.sort_unstable();
        nearby.dedup();
        nearby.retain(|id| {
            *id != oid && self.living.contains(id) && !self.same_bond_component(oid, *id)
        });

        let mut contact = std::mem::take(&mut self.action_contact);
        contact.clear();
        for &cell in &cells_r1 {
            if let Some(occupants) = self.world.occupants_at(cell) {
                contact.extend(occupants.iter().copied());
            }
        }
        contact.sort_unstable();
        contact.dedup();
        contact.retain(|id| {
            *id != oid && self.living.contains(id) && !self.same_bond_component(oid, *id)
        });

        {
            let catalog = &self.catalog;
            self.organisms[self.organism_indices[oid as usize - 1]].ensure_food_chemistry(catalog);
        }

        let mut directional_food = [0.0f32; 8];
        let mut directional_toxin = [0.0f32; 8];
        let mut directional_heat = [0.0f32; 8];
        let mut directional_prey = [0.0f32; 8];
        let mut directional_threat = [0.0f32; 8];
        let mut directional_mate = [0.0f32; 8];
        let mut local_food = 0.0f32;
        let mut local_heat = 0.0f32;
        let mut visible_food = false;
        let mut visible_heat = false;
        let reference_energy = self.reference_energy.max(1e-9);

        for &position in cells {
            let delta = (position.0 - origin.0, position.1 - origin.1);
            let slot = egocentric_slot(facing, delta);
            let distance_discount = 1.0 / (1.0 + World::distance(origin, position) as f64);
            if let Some(inventory) = self.world.deposits.get(&position) {
                for batch in inventory {
                    if batch.count <= 0 {
                        continue;
                    }
                    let (dietary_match, hazard) = self
                        .organism(oid)
                        .food_chemistry_at(batch.molecule_id as usize);
                    let density = batch.energy / batch.count as f64 / reference_energy;
                    let value =
                        unit_f32((dietary_match * density - hazard).max(0.0) * distance_discount);
                    let toxin = unit_f32(hazard.max(0.0) * distance_discount);
                    directional_food[slot] = directional_food[slot].max(value);
                    directional_toxin[slot] = directional_toxin[slot].max(toxin);
                    if footprint.contains(&position) {
                        local_food = local_food.max(value);
                    }
                    visible_food = true;
                }
            }
            let heat =
                unit_f32(self.world.heat_at_peek(position) / reference_energy * distance_discount);
            directional_heat[slot] = directional_heat[slot].max(heat);
            if footprint.contains(&position) {
                local_heat = local_heat.max(heat);
            }
            visible_heat |= heat > 0.0;
        }

        let mut maximum_threat = 0.0f32;
        let mut maximum_prey = 0.0f32;
        let mut best_mate = 0.0f32;
        for &target_id in &nearby {
            let (prey, threat, mate, _, _) = self.v2_target_metrics(oid, target_id);
            let target_position = self.organism(target_id).position;
            let slot = egocentric_slot(
                facing,
                (target_position.0 - origin.0, target_position.1 - origin.1),
            );
            directional_prey[slot] = directional_prey[slot].max(prey);
            directional_threat[slot] = directional_threat[slot].max(threat);
            directional_mate[slot] = directional_mate[slot].max(mate);
            maximum_prey = maximum_prey.max(prey);
            maximum_threat = maximum_threat.max(threat);
            best_mate = best_mate.max(mate);
        }

        let energy_fraction = {
            let catalog = &self.catalog;
            self.organisms[self.organism_indices[oid as usize - 1]].energy_fraction(catalog)
        };
        let mass = self.organism(oid).peek_structural_mass(&self.catalog) as f64;
        let (
            phenotype,
            birth_tick,
            reproduction_cooldown,
            mana,
            maintenance_debt,
            integrity,
            max_integrity,
            toxin_load,
            target_mass,
            in_colony,
            chemical_energy,
        ) = {
            let organism = self.organism(oid);
            (
                Arc::clone(&organism.phenotype),
                organism.birth_tick,
                organism.reproduction_cooldown,
                organism.mana,
                organism.maintenance_debt,
                organism.integrity,
                organism.max_integrity,
                organism.toxin_load,
                organism.target_mass,
                organism.colony_id.is_some(),
                organism.chemical_energy(),
            )
        };
        let age = self.tick.saturating_sub(birth_tick) as f64;
        let age_ratio = age / phenotype.lifespan.max(1) as f64;
        let cooldown_remaining = reproduction_cooldown.saturating_sub(self.tick) as f64;
        let mut observation = ObservationV2::default();
        observation.values[O_RESERVE] = unit_f32(energy_fraction);
        observation.values[O_HUNGER] = unit_f32(1.0 - energy_fraction);
        observation.values[O_MANA] = unit_f32(mana / phenotype.mana_capacity.max(1e-9));
        observation.values[O_MAINTENANCE_DEBT] =
            unit_f32(maintenance_debt / (4.0 * reference_energy));
        observation.values[O_INTEGRITY] = unit_f32(integrity / max_integrity.max(1e-9));
        observation.values[O_TOXIN] = unit_f32(toxin_load / phenotype.toxin_tolerance.max(1e-9));
        observation.values[O_AGE] = unit_f32(age_ratio);
        observation.values[O_SENESCENCE] = unit_f32((age_ratio - 1.0).max(0.0));
        observation.values[O_GROWTH_DEFICIT] = unit_f32(1.0 - mass / target_mass.max(1.0));
        observation.values[O_REPRODUCTIVE_RESERVE] = unit_f32(energy_fraction);
        observation.values[O_REPRODUCTIVE_COOLDOWN] =
            unit_f32(cooldown_remaining / phenotype.maturity_age.max(1) as f64);
        observation.values[O_REPRODUCTIVE_READY] = if self.is_reproductively_ready(oid) {
            1.0
        } else {
            0.0
        };
        observation.values[O_BODY_MASS] = unit_f32(mass / self.reference_body_mass.max(1.0));
        observation.values[O_SPEED] = unit_f32((phenotype.speed - 0.5) / 3.5);
        observation.values[O_SIGHT] =
            unit_f32(effective_sight as f64 / self.config.max_sight.max(1) as f64);
        observation.values[O_COLONY] = if in_colony { 1.0 } else { 0.0 };
        if self.config.dynamic_chemistry_enabled {
            let (local_fit, environmental_toxin) = self.local_chemistry_signals(self.organism(oid));
            observation.values[O_LOCAL_FOOD] = unit_f32(local_food as f64 + 0.5 * local_fit);
            observation.values[O_TOXIN] = unit_f32(
                toxin_load / phenotype.toxin_tolerance.max(1.0e-9)
                    + environmental_toxin * self.config.chemistry_coupling,
            );
        } else {
            observation.values[O_LOCAL_FOOD] = local_food;
        }
        observation.values[O_VISIBLE_FOOD] = directional_food.iter().copied().fold(0.0, f32::max);
        observation.values[O_LOCAL_HEAT] = local_heat;
        observation.values[O_VISIBLE_HEAT] = directional_heat.iter().copied().fold(0.0, f32::max);
        observation.values[O_THREAT] = maximum_threat;
        observation.values[O_PREY] = maximum_prey;
        observation.values[O_MATE] = best_mate;
        observation.values[O_CONTACT_CROWDING] = unit_f32(contact.len() as f64 / 8.0);
        observation.values[O_VISIBLE_CROWDING] =
            unit_f32(nearby.len() as f64 / (8 * effective_sight.max(1)) as f64);
        observation.values[O_FOOD_KNOWN] = if visible_food { 1.0 } else { 0.0 };
        observation.values[O_ORGANISM_KNOWN] = if nearby.is_empty() { 0.0 } else { 1.0 };
        observation.values[O_HEAT_KNOWN] = if visible_heat { 1.0 } else { 0.0 };

        let duration = self.v2_action_delay(oid);
        let last_kind = self.organism(oid).last_intent_kind;
        let mut candidates = std::mem::take(&mut self.v2_candidates);
        let mut pool = std::mem::take(&mut self.v2_candidate_pool);
        candidates.clear();
        pool.clear();
        candidates.push(make_intent_candidate(
            last_kind,
            IntentKind::Wait,
            IntentTarget::None,
            duration,
            0.0,
            0.0,
            reference_energy,
        ));

        if integrity < max_integrity && chemical_energy > 0.0 {
            let cost = chemical_energy.min(reference_energy * 0.005);
            candidates.push(make_intent_candidate(
                last_kind,
                IntentKind::Repair,
                IntentTarget::None,
                duration,
                cost,
                0.0,
                reference_energy,
            ));
        }

        let move_cost = self.v2_move_cost(oid);
        if self.organism(oid).chemical_energy() >= move_cost {
            let area = self.footprint_area(oid);
            for slot in 0..8 {
                let direction = egocentric_direction(facing, slot);
                let destination = (origin.0 + direction.0 as i64, origin.1 + direction.1 as i64);
                if !self.can_place_area(area, destination, oid) {
                    continue;
                }
                let mut candidate = make_intent_candidate(
                    last_kind,
                    IntentKind::Move,
                    IntentTarget::Position(destination),
                    duration,
                    move_cost,
                    0.0,
                    reference_energy,
                );
                candidate.features[C_FOOD] = directional_food[slot];
                candidate.features[C_TOXIN] = directional_toxin[slot];
                candidate.features[C_HEAT] = directional_heat[slot];
                candidate.features[C_PREY] = directional_prey[slot];
                candidate.features[C_THREAT] = directional_threat[slot];
                candidate.features[C_MATE] = directional_mate[slot];
                candidate.features[C_CROWDING] = unit_f32(
                    self.world
                        .occupants_at(destination)
                        .map_or(0, |ids| ids.len()) as f64
                        / 8.0,
                );
                candidate.features[C_FORWARD] = EGOCENTRIC_FORWARD[slot];
                candidate.features[C_RIGHT] = EGOCENTRIC_RIGHT[slot];
                candidate.features[C_DISTANCE] = unit_f32(1.0 / effective_sight.max(1) as f64);
                candidates.push(candidate);
            }
        }

        for &position in &footprint {
            if let Some(inventory) = self.world.deposits.get(&position) {
                for batch in inventory {
                    if batch.count <= 0 {
                        continue;
                    }
                    let (dietary_match, hazard) = self
                        .organism(oid)
                        .food_chemistry_at(batch.molecule_id as usize);
                    let density = batch.energy / batch.count as f64 / reference_energy;
                    let food_value = unit_f32((dietary_match * density - hazard).max(0.0));
                    let count = 2.min(batch.count);
                    let cost = self.config.reference_ingest_cost * reference_energy * count as f64;
                    if self.organism(oid).chemical_energy() < cost {
                        continue;
                    }
                    let mut candidate = make_intent_candidate(
                        last_kind,
                        IntentKind::Ingest,
                        IntentTarget::Food {
                            position,
                            molecule_id: batch.molecule_id,
                        },
                        duration,
                        cost,
                        0.0,
                        reference_energy,
                    );
                    candidate.features[C_FOOD] = food_value;
                    candidate.features[C_TOXIN] = unit_f32(hazard.max(0.0));
                    pool.push(RankedIntentCandidate {
                        salience: food_value - candidate.features[C_TOXIN],
                        tie_key: position_tie_key(position) ^ batch.molecule_id as u64,
                        candidate,
                    });
                }
            }
        }
        append_ranked_candidates(&mut candidates, &mut pool, 4);

        if mana < phenotype.mana_capacity {
            if let Some((&position, heat)) = footprint
                .iter()
                .map(|position| (position, self.world.heat_at_peek(*position)))
                .max_by(|left, right| left.1.total_cmp(&right.1))
            {
                if heat > 1e-9 {
                    let mut candidate = make_intent_candidate(
                        last_kind,
                        IntentKind::AbsorbHeat,
                        IntentTarget::Position(position),
                        duration,
                        0.0,
                        0.0,
                        reference_energy,
                    );
                    candidate.features[C_HEAT] = unit_f32(heat / reference_energy);
                    candidates.push(candidate);
                }
            }
        }
        if toxin_load > phenotype.toxin_tolerance * 0.5 && chemical_energy > 0.0 {
            let cost = chemical_energy.min(reference_energy * 0.01);
            candidates.push(make_intent_candidate(
                last_kind,
                IntentKind::Detox,
                IntentTarget::None,
                duration,
                cost,
                0.0,
                reference_energy,
            ));
        }

        let attack_cost = {
            let mass_ratio = mass / self.reference_body_mass.max(1.0);
            self.config.reference_attack_cost
                * reference_energy
                * mass_ratio
                * phenotype.attack
                * phenotype.attack
                / phenotype.attack_efficiency
        };
        if chemical_energy >= attack_cost {
            for &target_id in &contact {
                let (prey, threat, mate, social, distance) = self.v2_target_metrics(oid, target_id);
                let mut candidate = make_intent_candidate(
                    last_kind,
                    IntentKind::Attack,
                    IntentTarget::Organism(target_id),
                    duration,
                    attack_cost,
                    0.0,
                    reference_energy,
                );
                candidate.features[C_PREY] = prey;
                candidate.features[C_THREAT] = threat;
                candidate.features[C_MATE] = mate;
                candidate.features[C_SOCIAL] = social;
                candidate.features[C_DISTANCE] = distance;
                pool.push(RankedIntentCandidate {
                    salience: prey,
                    tie_key: target_id as u64,
                    candidate,
                });
            }
        }
        append_ranked_candidates(&mut candidates, &mut pool, 4);

        if mana > 1e-9 {
            let mana_cost = (mana * 0.30).min(reference_energy * 0.5);
            for &target_id in &nearby {
                let (prey, threat, mate, social, distance) = self.v2_target_metrics(oid, target_id);
                let mut candidate = make_intent_candidate(
                    last_kind,
                    IntentKind::CastMagic,
                    IntentTarget::Organism(target_id),
                    duration,
                    0.0,
                    mana_cost,
                    reference_energy,
                );
                candidate.features[C_PREY] = prey;
                candidate.features[C_THREAT] = threat;
                candidate.features[C_MATE] = mate;
                candidate.features[C_SOCIAL] = social;
                candidate.features[C_DISTANCE] = distance;
                pool.push(RankedIntentCandidate {
                    salience: prey.max(threat),
                    tie_key: target_id as u64,
                    candidate,
                });
            }
        }
        append_ranked_candidates(&mut candidates, &mut pool, 4);

        if self.is_reproductively_ready(oid) {
            let single_cost = self.config.reference_reproduction_cost
                * self.config.reproduction_cost_multiplier
                * reference_energy
                * mass
                * phenotype.reproduction_fraction
                / self.reference_body_mass.max(1.0);
            if chemical_energy >= single_cost {
                let mut candidate = make_intent_candidate(
                    last_kind,
                    IntentKind::Reproduce,
                    IntentTarget::SelfReproduction,
                    duration,
                    single_cost,
                    0.0,
                    reference_energy,
                );
                candidate.features[C_MATE] =
                    unit_f32(phenotype.asexual.max(self.config.asexual_probability_floor));
                candidates.push(candidate);
            }
            for &target_id in &contact {
                if !self.is_reproductively_ready(target_id)
                    || self.organism(target_id).phenotype.sexual <= 0.05
                {
                    continue;
                }
                let (prey, threat, mate, social, distance) = self.v2_target_metrics(oid, target_id);
                let target_mass =
                    self.organism(target_id).peek_structural_mass(&self.catalog) as f64;
                let total_cost = self.config.reference_reproduction_cost
                    * self.config.reproduction_cost_multiplier
                    * reference_energy
                    * (mass * phenotype.reproduction_fraction
                        + target_mass * self.organism(target_id).phenotype.reproduction_fraction)
                    / self.reference_body_mass.max(1.0);
                let share = total_cost * 0.5;
                if chemical_energy < share || self.organism(target_id).chemical_energy() < share {
                    continue;
                }
                let mut candidate = make_intent_candidate(
                    last_kind,
                    IntentKind::Reproduce,
                    IntentTarget::Organism(target_id),
                    duration,
                    share,
                    0.0,
                    reference_energy,
                );
                candidate.features[C_PREY] = prey;
                candidate.features[C_THREAT] = threat;
                candidate.features[C_MATE] = mate;
                candidate.features[C_SOCIAL] = social;
                candidate.features[C_DISTANCE] = distance;
                pool.push(RankedIntentCandidate {
                    salience: mate,
                    tie_key: target_id as u64,
                    candidate,
                });
            }
            append_ranked_candidates(&mut candidates, &mut pool, 4);
        }

        for &target_id in &contact {
            let edge = if oid < target_id {
                (oid, target_id)
            } else {
                (target_id, oid)
            };
            if self.alliances.contains(&edge) {
                continue;
            }
            let (prey, threat, mate, social, distance) = self.v2_target_metrics(oid, target_id);
            let mut candidate = make_intent_candidate(
                last_kind,
                IntentKind::ProposeAlliance,
                IntentTarget::Organism(target_id),
                duration,
                0.0,
                0.0,
                reference_energy,
            );
            candidate.features[C_PREY] = prey;
            candidate.features[C_THREAT] = threat;
            candidate.features[C_MATE] = mate;
            candidate.features[C_SOCIAL] = social;
            candidate.features[C_DISTANCE] = distance;
            pool.push(RankedIntentCandidate {
                salience: social,
                tie_key: target_id as u64,
                candidate,
            });
        }
        append_ranked_candidates(&mut candidates, &mut pool, 4);
        debug_assert!(candidates.len() <= MAX_INTENT_CANDIDATES);

        let mut current_food_slot = 0u8;
        let mut current_food_signal = directional_food[0];
        for (slot, &signal) in directional_food.iter().enumerate().skip(1) {
            if signal > current_food_signal {
                current_food_slot = slot as u8;
                current_food_signal = signal;
            }
        }
        let (previous_food_slot, previous_food_signal, previous_neural_state) = {
            let organism = self.organism(oid);
            (
                organism.previous_food_slot,
                organism.previous_food_signal,
                organism.neural_state,
            )
        };

        let policy = phenotype
            .intent_policy
            .as_ref()
            .expect("linear V2 organisms must have an intent policy");
        let global_scores = policy.global_scores(&observation);
        let (recurrent_output, next_neural_state, neural_failure) =
            if self.config.behavior_model == BehaviorModel::RecurrentIntentV2 {
                let recurrent = phenotype
                    .recurrent_policy
                    .as_ref()
                    .expect("recurrent organisms must have a recurrent phenotype");
                match recurrent.infer(
                    &observation,
                    self.organism(oid).neural_state,
                    self.config.recurrent_state_lesion,
                ) {
                    Some(output) => (Some(output), output.next_state, false),
                    None => (None, NeuralState::default(), true),
                }
            } else {
                (None, self.organism(oid).neural_state, false)
            };

        let mut scores = std::mem::take(&mut self.v2_scores);
        scores.clear();
        for candidate in &candidates {
            let score = match recurrent_output {
                Some(output) => {
                    policy.score_with_globals(&global_scores, candidate) + output.score(candidate)
                }
                None => policy.score_with_globals(&global_scores, candidate),
            };
            scores.push(if score.is_finite() {
                score
            } else {
                f64::NEG_INFINITY
            });
        }

        if self.config.memory_probe_enabled
            && self.config.behavior_model == BehaviorModel::RecurrentIntentV2
        {
            let recurrent = phenotype
                .recurrent_policy
                .as_ref()
                .expect("recurrent organisms must have a recurrent phenotype");
            if let Some(zero_state_output) =
                recurrent.infer(&observation, NeuralState::default(), false)
            {
                let stateful_index = scores
                    .iter()
                    .enumerate()
                    .max_by(|left, right| left.1.total_cmp(right.1).then(right.0.cmp(&left.0)))
                    .map_or(0, |(index, _)| index);
                let zero_state_index = candidates
                    .iter()
                    .enumerate()
                    .map(|(index, candidate)| {
                        (
                            index,
                            policy.score_with_globals(&global_scores, candidate)
                                + zero_state_output.score(candidate),
                        )
                    })
                    .max_by(|left, right| left.1.total_cmp(&right.1).then(right.0.cmp(&left.0)))
                    .map_or(0, |(index, _)| index);
                let changed = stateful_index != zero_state_index;
                let ambiguous = current_food_signal <= 1.0e-6
                    && previous_food_signal >= 0.05
                    && previous_food_slot < 8;
                let returns_to_previous_food = |candidate: &IntentCandidate| {
                    candidate.kind == IntentKind::Move
                        && matches!(
                            candidate.target,
                            IntentTarget::Position(destination)
                                if egocentric_slot(
                                    facing,
                                    (destination.0 - origin.0, destination.1 - origin.1),
                                ) == previous_food_slot as usize
                        )
                };

                self.stats.memory_probe_decisions += 1;
                self.stats.memory_probe_state_l1_sum += previous_neural_state
                    .values
                    .iter()
                    .map(|value| value.abs() as f64)
                    .sum::<f64>();
                if changed {
                    self.stats.memory_probe_argmax_changes += 1;
                }
                if ambiguous {
                    self.stats.memory_probe_ambiguous_food_events += 1;
                    if changed {
                        self.stats.memory_probe_ambiguous_argmax_changes += 1;
                    }
                    if returns_to_previous_food(&candidates[stateful_index]) {
                        self.stats.memory_probe_stateful_return_choices += 1;
                    }
                    if returns_to_previous_food(&candidates[zero_state_index]) {
                        self.stats.memory_probe_zero_state_return_choices += 1;
                    }
                }
            }
        }

        let temperature = policy.decision_temperature.max(0.05) as f64;
        let maximum = scores.iter().copied().fold(f64::NEG_INFINITY, f64::max);
        let mut weights = std::mem::take(&mut self.action_weights);
        weights.clear();
        weights.extend(
            scores
                .iter()
                .map(|score| (((score - maximum) / temperature).clamp(-30.0, 30.0)).exp()),
        );
        let total: f64 = weights.iter().sum();
        let selected_index = if neural_failure {
            self.stats.neural_numerical_errors += 1;
            self.stats.v2_intent_failures += 1;
            0
        } else if total.is_finite() && total > 0.0 {
            let mut draw = self.rng.f64() * total;
            let mut selected = candidates.len() - 1;
            for (index, weight) in weights.iter().enumerate() {
                draw -= *weight;
                if draw <= 0.0 {
                    selected = index;
                    break;
                }
            }
            selected
        } else {
            self.stats.v2_intent_failures += 1;
            0
        };
        let selected = candidates[selected_index].to_intent(oid);
        let final_kind = self.commit_v2_intent(&selected);
        let update_memory_trace = self.config.memory_probe_enabled;
        {
            let next_action_tick = self.tick + selected.predicted_duration_ticks.max(1);
            let organism = self.organism_mut(oid);
            organism.last_intent_kind = final_kind as u8;
            organism.last_action = v2_last_action_code(final_kind);
            organism.next_action_tick = next_action_tick;
            organism.decision_count += 1;
            organism.neural_state = next_neural_state;
            if update_memory_trace {
                organism.previous_food_slot = current_food_slot;
                organism.previous_food_signal = current_food_signal;
            }
            if neural_failure {
                organism.neural_numerical_errors += 1;
            }
        }
        self.stats.v2_intent_counts[final_kind.as_index()] += 1;
        if final_kind != selected.kind {
            self.stats.v2_intent_failures += 1;
        }

        self.action_cells_r1 = cells_r1;
        self.action_cells_sight = cells_sight;
        self.action_nearby = nearby;
        self.action_contact = contact;
        self.v2_footprint = footprint;
        self.v2_candidates = candidates;
        self.v2_candidate_pool = pool;
        self.v2_scores = scores;
        self.action_weights = weights;
    }

    fn commit_v2_intent(&mut self, intent: &ActionIntent) -> IntentKind {
        let oid = intent.actor_id;
        match (intent.kind, intent.target) {
            (IntentKind::Wait, _) => IntentKind::Wait,
            (IntentKind::Move, IntentTarget::Position(destination)) => {
                let origin = self.organism(oid).position;
                if World::distance(origin, destination) == 1
                    && self.move_organism_exact(
                        oid,
                        (
                            (destination.0 - origin.0) as i32,
                            (destination.1 - origin.1) as i32,
                        ),
                    )
                {
                    IntentKind::Move
                } else {
                    IntentKind::Wait
                }
            }
            (
                IntentKind::Ingest,
                IntentTarget::Food {
                    position,
                    molecule_id,
                },
            ) => {
                if self.footprint_cells(oid).contains(&position) {
                    self.eat(oid, (position, molecule_id, 0.0));
                    IntentKind::Ingest
                } else {
                    IntentKind::Wait
                }
            }
            (IntentKind::Repair, _)
                if self.organism(oid).integrity < self.organism(oid).max_integrity =>
            {
                self.repair(oid);
                IntentKind::Repair
            }
            (IntentKind::AbsorbHeat, IntentTarget::Position(position))
                if self.footprint_cells(oid).contains(&position) =>
            {
                self.absorb_heat(oid, position);
                IntentKind::AbsorbHeat
            }
            (IntentKind::Detox, _) if self.organism(oid).toxin_load > 0.0 => {
                self.active_detox(oid);
                IntentKind::Detox
            }
            (IntentKind::Attack, IntentTarget::Organism(target_id))
                if self.has_organism(target_id) && self.organism(target_id).alive =>
            {
                self.attack(oid, target_id);
                IntentKind::Attack
            }
            (IntentKind::CastMagic, IntentTarget::Organism(target_id))
                if self.has_organism(target_id)
                    && self.organism(target_id).alive
                    && self.organism(oid).mana > 0.0 =>
            {
                self.cast_magic(oid, target_id);
                IntentKind::CastMagic
            }
            (IntentKind::Reproduce, IntentTarget::SelfReproduction)
                if self.is_reproductively_ready(oid) =>
            {
                self.attempt_reproduction(oid, None);
                IntentKind::Reproduce
            }
            (IntentKind::Reproduce, IntentTarget::Organism(target_id))
                if self.has_organism(target_id)
                    && self.is_reproductively_ready(oid)
                    && self.is_reproductively_ready(target_id) =>
            {
                self.attempt_reproduction(oid, Some(target_id));
                IntentKind::Reproduce
            }
            (IntentKind::ProposeAlliance, IntentTarget::Organism(target_id))
                if self.has_organism(target_id) && self.organism(target_id).alive =>
            {
                self.attempt_alliance(oid, target_id);
                IntentKind::ProposeAlliance
            }
            _ => IntentKind::Wait,
        }
    }

    fn decide_and_act_legacy(&mut self, oid: u32) {
        // sight expansion
        let effective_sight;
        let mut cells_r1 = std::mem::take(&mut self.action_cells_r1);
        self.nearby_cells_into(oid, 1, &mut cells_r1);
        let mut cells_sight = std::mem::take(&mut self.action_cells_sight);
        if self.organism(oid).phenotype.sight > 1 {
            let sight = self.organism(oid).phenotype.sight;
            self.nearby_cells_into(oid, sight, &mut cells_sight);
            let sight_cost = self.config.sight_cost_per_cell
                * self.reference_energy
                * ((cells_sight.len() as i64 - cells_r1.len() as i64).max(0)) as f64;
            if self.organism(oid).chemical_energy() >= sight_cost {
                let spent = self.organism_mut(oid).consume_body_energy(sight_cost);
                let position = self.organism(oid).position;
                self.world.add_heat(position, spent);
                effective_sight = sight;
            } else {
                effective_sight = 1;
            }
        } else {
            effective_sight = 1;
        }
        let cells: &[Position] = if effective_sight > 1 {
            &cells_sight
        } else {
            &cells_r1
        };

        let observations = self.observe_cells(oid, cells);
        let food = observations.food;
        let heat_position = observations.heat_position;
        let local_heat = observations.local_heat;
        let mut nearby_ids: FxHashSet<u32> = FxHashSet::default();
        for &cell in cells {
            if let Some(occupants) = self.world.occupants_at(cell) {
                nearby_ids.extend(occupants.iter().copied());
            }
        }
        nearby_ids.remove(&oid);
        let mut nearby = std::mem::take(&mut self.action_nearby);
        nearby.clear();
        nearby.extend(
            nearby_ids
                .into_iter()
                .filter(|id| self.living.contains(id) && !self.same_bond_component(oid, *id)),
        );
        let mut contact_ids: FxHashSet<u32> = FxHashSet::default();
        for &cell in &cells_r1 {
            if let Some(occupants) = self.world.occupants_at(cell) {
                contact_ids.extend(occupants.iter().copied());
            }
        }
        contact_ids.remove(&oid);
        let mut contact = std::mem::take(&mut self.action_contact);
        contact.clear();
        contact.extend(
            contact_ids
                .iter()
                .copied()
                .filter(|id| self.living.contains(id) && !self.same_bond_component(oid, *id)),
        );

        let prey = self.best_prey(oid, &nearby);
        let mut visible_mate_draws = std::mem::take(&mut self.action_visible_mate_draws);
        self.collect_mate_draws(&nearby, &mut visible_mate_draws);
        let visible_mate = self.best_mate_from_draws(oid, &visible_mate_draws);
        let mut contact_mate_draws = std::mem::take(&mut self.action_contact_mate_draws);
        self.collect_mate_draws(&contact, &mut contact_mate_draws);
        let threat_target: Option<u32> = {
            let mut best: Option<(f64, u32)> = None;
            for &id in &nearby {
                let other = self.organism(id);
                let score =
                    other.phenotype.attack * other.peek_structural_mass(&self.catalog) as f64;
                if best.is_none() || score > best.unwrap().0 {
                    best = Some((score, id));
                }
            }
            best.map(|b| b.1)
        };
        let threat = threat_target
            .map(|id| {
                let o = self.organism(id);
                o.phenotype.attack * o.peek_structural_mass(&self.catalog) as f64
            })
            .unwrap_or(0.0);

        let hunger = {
            let catalog = &self.catalog;
            1.0 - self.organisms[self.organism_indices[oid as usize - 1]].energy_fraction(catalog)
        };
        let on_food = match &food {
            Some(f) => self.footprint_cells(oid).contains(&f.0),
            None => false,
        };
        let o = self.organism(oid);
        let local_fit = self.local_chemistry_fit(o);
        let food_signal = food.as_ref().map(|f| f.2.max(0.0)).unwrap_or(0.0);
        let feature_values: [f64; 10] = [
            hunger,
            if self.config.dynamic_chemistry_enabled {
                (food_signal + 0.5 * local_fit).clamp(0.0, 1.0)
            } else {
                food_signal
            },
            (local_heat / self.reference_energy.max(1e-9)).min(1.0),
            (threat / self.reference_body_mass.max(1.0)).min(1.0),
            if prey.is_some() { 1.0 } else { 0.0 },
            (o.toxin_load / o.phenotype.toxin_tolerance.max(1e-9)).min(1.0),
            o.mana / o.phenotype.mana_capacity.max(1e-9),
            [
                if visible_mate.is_some() { 1.0 } else { 0.0 },
                o.phenotype.asexual,
                self.config.asexual_probability_floor,
            ]
            .iter()
            .copied()
            .fold(0.0f64, f64::max),
            (nearby.len() as f64 / 8.0).min(1.0),
            hunger,
        ];

        let mature = self.is_reproductively_ready(oid);
        let prey_touching = prey.map(|p| contact_ids.contains(&p)).unwrap_or(false);
        let visible_mate_touching = visible_mate
            .map(|m| contact_ids.contains(&m))
            .unwrap_or(false);
        let mut eligible = 0u32;
        for a in 0..ACTION_COUNT {
            eligible |= 1 << a;
        }
        if food.is_none() {
            eligible &= !(1 << A_FORAGE);
        }
        if !on_food {
            eligible &= !(1 << A_EAT);
        }
        if local_heat <= 1e-9
            || self.organism(oid).mana >= self.organism(oid).phenotype.mana_capacity
        {
            eligible &= !(1 << A_HEAT);
        }
        if self.organism(oid).toxin_load <= self.organism(oid).phenotype.toxin_tolerance * 0.5 {
            eligible &= !(1 << A_DETOX);
        }
        if prey.is_none() || prey_touching {
            eligible &= !(1 << A_HUNT);
        }
        if !prey_touching {
            eligible &= !(1 << A_ATTACK);
        }
        if threat_target.is_none() {
            eligible &= !(1 << A_FLEE);
        }
        if visible_mate.is_none() || visible_mate_touching {
            eligible &= !(1 << A_SEEK_MATE);
        }
        if prey.is_none() || self.organism(oid).mana <= 1e-9 {
            eligible &= !(1 << A_MAGIC);
        }
        if !mature {
            eligible &= !(1 << A_REPRODUCE);
        }
        if contact.is_empty() {
            eligible &= !(1 << A_ALLY);
        }

        let action = self.sample_action(oid, &feature_values, eligible);
        let contact_mate = if action == A_REPRODUCE {
            self.best_mate_from_draws(oid, &contact_mate_draws)
        } else {
            None
        };
        self.organism_mut(oid).last_action = action as u8 + 1;
        let slowed = if self.organism(oid).water_status.is_some() {
            2.0
        } else {
            1.0
        };
        let base_delay = ((4.0 / self.organism(oid).phenotype.speed * slowed).ceil() as u32).max(1);
        self.organism_mut(oid).next_action_tick = self.tick + base_delay;

        match action {
            A_EAT => {
                if let Some(f) = food {
                    self.eat(oid, f);
                }
            }
            A_HEAT => self.seek_or_absorb_heat(oid, heat_position),
            A_DETOX => self.active_detox(oid),
            A_ATTACK => {
                if let Some(p) = prey {
                    self.attack(oid, p);
                }
            }
            A_MAGIC => {
                if let Some(p) = prey {
                    self.cast_magic(oid, p);
                }
            }
            A_REPRODUCE => self.attempt_reproduction(oid, contact_mate),
            A_ALLY if !contact.is_empty() => {
                let other = contact[self.rng.below(contact.len() as u64) as usize];
                self.attempt_alliance(oid, other);
            }
            A_FORAGE => {
                if let Some(f) = food {
                    self.move_organism(oid, Some(f.0));
                }
            }
            A_HUNT => {
                if let Some(p) = prey {
                    let target = self.organism(p).position;
                    self.move_organism(oid, Some(target));
                }
            }
            A_FLEE => {
                if let Some(t) = threat_target {
                    let threat_pos = self.organism(t).position;
                    self.move_away(oid, threat_pos);
                }
            }
            A_SEEK_MATE => {
                if let Some(m) = visible_mate {
                    let target = self.organism(m).position;
                    self.move_organism(oid, Some(target));
                }
            }
            A_WANDER => {
                self.move_organism(oid, None);
            }
            A_REST => {
                let (integrity, max) = {
                    let o = self.organism(oid);
                    (o.integrity, o.max_integrity)
                };
                if integrity < max {
                    self.repair(oid);
                }
            }
            _ => {}
        }

        self.action_cells_r1 = cells_r1;
        self.action_cells_sight = cells_sight;
        self.action_nearby = nearby;
        self.action_contact = contact;
        self.action_visible_mate_draws = visible_mate_draws;
        self.action_contact_mate_draws = contact_mate_draws;
    }

    fn sample_action(&mut self, oid: u32, features: &[f64; 10], eligible: u32) -> usize {
        let mut scored = std::mem::take(&mut self.action_scores);
        scored.clear();
        {
            let policy = &self.organism(oid).phenotype.policy;
            for &action in ACTION_ORDER_ALPHA.iter() {
                if eligible & (1 << action) == 0 {
                    continue;
                }
                let weights = &policy[action];
                let mut score = 0.0;
                for f in 0..10 {
                    score += weights[f] * features[f];
                }
                if action == A_REPRODUCE {
                    let reserve_factor = (1.0 - features[F_HUNGER]).max(0.0);
                    let reproductive_signal = features[F_MATE].max(0.25);
                    score += self.config.reproduction_action_bonus
                        * reserve_factor
                        * reproductive_signal;
                }
                scored.push((action, score));
            }
        }
        if scored.is_empty() {
            self.action_scores = scored;
            return A_REST;
        }
        let maximum = scored.iter().map(|s| s.1).fold(f64::NEG_INFINITY, f64::max);
        let mut weights = std::mem::take(&mut self.action_weights);
        weights.clear();
        weights.extend(
            scored
                .iter()
                .map(|s| ((s.1 - maximum).clamp(-30.0, 30.0)).exp()),
        );
        let sum: f64 = weights.iter().sum();
        let mut choice = self.rng.f64() * sum;
        let mut selected = scored[scored.len() - 1].0;
        for ((action, _), weight) in scored.iter().zip(weights.iter()) {
            choice -= weight;
            if choice <= 0.0 {
                selected = *action;
                break;
            }
        }
        self.action_scores = scored;
        self.action_weights = weights;
        selected
    }

    // -------------------------------------------------------------- actions

    fn move_organism(&mut self, oid: u32, target: Option<Position>) -> bool {
        let origin = self.organism(oid).position;
        let (mut dx, mut dy) = match target {
            None => {
                const DIRS: [(i32, i32); 8] = [
                    (-1, -1),
                    (0, -1),
                    (1, -1),
                    (-1, 0),
                    (1, 0),
                    (-1, 1),
                    (0, 1),
                    (1, 1),
                ];
                DIRS[self.rng.below(8) as usize]
            }
            Some(target) => {
                let delta = (target.0 - origin.0, target.1 - origin.1);
                let dx = if delta.0 == 0 {
                    0
                } else if delta.0 > 0 {
                    1
                } else {
                    -1
                };
                let dy = if delta.1 == 0 {
                    0
                } else if delta.1 > 0 {
                    1
                } else {
                    -1
                };
                if dx == 0 && dy == 0 {
                    return false;
                }
                // occasionally pick a random distance-reducing step
                let mut options: Vec<(i32, i32)> = vec![(dx, dy)];
                if dx != 0 {
                    options.push((dx, 0));
                }
                if dy != 0 {
                    options.push((0, dy));
                }
                let current_distance = World::distance(origin, target);
                let reducing: Vec<(i32, i32)> = options
                    .iter()
                    .copied()
                    .filter(|&(ox, oy)| {
                        World::distance((origin.0 + ox as i64, origin.1 + oy as i64), target)
                            < current_distance
                    })
                    .collect();
                if !reducing.is_empty() && self.rng.chance(0.30) {
                    let mut sorted = reducing;
                    sorted.sort();
                    sorted[self.rng.below(sorted.len() as u64) as usize]
                } else {
                    (dx, dy)
                }
            }
        };
        let _ = (&mut dx, &mut dy);
        self.move_organism_exact(oid, (dx, dy))
    }

    fn movement_cost_at(&mut self, organism_id: u32, destination: Position) -> (f64, usize) {
        let mass_ratio = self
            .organism(organism_id)
            .peek_structural_mass(&self.catalog) as f64
            / self.reference_body_mass.max(1.0);
        let speed_fraction = (self.organism(organism_id).phenotype.speed / 4.0).min(1.0);
        let mut cost = self.config.reference_move_cost
            * self.reference_energy
            * mass_ratio
            * (1.0 + speed_fraction * speed_fraction)
            / self.organism(organism_id).phenotype.move_efficiency;
        let area = self.footprint_area(organism_id);
        if self.config.biodeposits_enabled {
            let offsets = Arc::clone(&self.footprint_offsets(area));
            let density: f64 = offsets
                .iter()
                .map(|&(offset_x, offset_y)| {
                    self.world.biodeposit_density_at((
                        destination.0 + offset_x as i64,
                        destination.1 + offset_y as i64,
                    ))
                })
                .sum();
            let relative_density = density / self.reference_body_mass.max(1.0);
            cost *= 1.0 + self.config.biodeposit_movement_resistance * relative_density.ln_1p();
        }
        (cost, area)
    }

    fn move_component_exact(&mut self, authority_id: u32, direction: (i32, i32)) -> bool {
        let component_root = self.component_root_for(authority_id);
        let members = self
            .component_members
            .get(&component_root)
            .cloned()
            .unwrap_or_else(|| vec![authority_id]);
        if members.len() <= 1 {
            return false;
        }
        let member_set: FxHashSet<u32> = members.iter().copied().collect();
        let (dx, dy) = direction;
        let mut plans: Vec<ComponentMovePlan> = Vec::with_capacity(members.len());
        for &member_id in &members {
            if !self.has_organism(member_id) {
                return false;
            }
            let origin = self.organism(member_id).position;
            let destination = (origin.0 + dx as i64, origin.1 + dy as i64);
            let (cost, area) = self.movement_cost_at(member_id, destination);
            if self.organism(member_id).chemical_energy() < cost {
                return false;
            }
            let old_cells = self.footprint_cells(member_id);
            let offsets = Arc::clone(&self.footprint_offsets(area));
            let new_cells: Vec<Position> = offsets
                .iter()
                .map(|&(offset_x, offset_y)| {
                    (
                        destination.0 + offset_x as i64,
                        destination.1 + offset_y as i64,
                    )
                })
                .collect();
            self.world.ensure_positions(&new_cells);
            if new_cells.iter().any(|&position| {
                self.world.occupants_at(position).is_some_and(|occupants| {
                    occupants
                        .iter()
                        .any(|occupant| !member_set.contains(occupant))
                })
            }) {
                let fraction = self.config.failed_move_cost_fraction;
                for plan in &plans {
                    let spent = self
                        .organism_mut(plan.member_id)
                        .consume_body_energy(plan.cost * fraction);
                    self.world.add_heat(plan.origin, spent);
                }
                let spent = self
                    .organism_mut(member_id)
                    .consume_body_energy(cost * fraction);
                self.world.add_heat(origin, spent);
                return false;
            }
            plans.push(ComponentMovePlan {
                member_id,
                origin,
                destination,
                cost,
                old_cells,
                new_cells,
            });
        }

        for plan in &plans {
            self.world
                .remove_id_from_occupancy(plan.member_id, &plan.old_cells);
        }
        for plan in &plans {
            let spent = self
                .organism_mut(plan.member_id)
                .consume_body_energy(plan.cost);
            self.world.add_heat(plan.origin, spent);
            let organism = self.organism_mut(plan.member_id);
            organism.position = plan.destination;
            organism.facing = (dx, dy);
            self.world.add_to_occupancy(plan.member_id, &plan.new_cells);
        }
        self.emergence_stats.component_moves += 1;
        true
    }

    fn move_organism_exact(&mut self, oid: u32, direction: (i32, i32)) -> bool {
        let origin = self.organism(oid).position;
        let (dx, dy) = direction;
        if !(-1..=1).contains(&dx) || !(-1..=1).contains(&dy) || (dx == 0 && dy == 0) {
            return false;
        }
        if self.coordinated_components_enabled()
            && self
                .component_members
                .get(&self.component_root_for(oid))
                .is_some_and(|members| members.len() > 1)
        {
            return self.move_component_exact(oid, direction);
        }
        let destination = (origin.0 + dx as i64, origin.1 + dy as i64);
        let (cost, area) = self.movement_cost_at(oid, destination);
        let speed_fraction = (self.organism(oid).phenotype.speed / 4.0).min(1.0);
        if self.organism(oid).chemical_energy() < cost {
            return false;
        }
        if self.config.cellular_emergence_enabled {
            let stretched: Vec<((u32, u32), Bond)> = self
                .bonds
                .iter()
                .filter_map(|(&edge, &bond)| {
                    let other_id = if bond.left == oid {
                        Some(bond.right)
                    } else if bond.right == oid {
                        Some(bond.left)
                    } else {
                        None
                    }?;
                    (self.has_organism(other_id)
                        && World::distance(destination, self.organism(other_id).position) > 1)
                        .then_some((edge, bond))
                })
                .collect();
            for (edge, bond) in stretched {
                let break_probability =
                    (speed_fraction / (0.25 + bond.strength as f64)).clamp(0.0, 1.0);
                if self.rng.chance(break_probability) {
                    self.bonds.remove(&edge);
                    self.emergence_stats.bond_breaks += 1;
                } else {
                    return false;
                }
            }
        }
        let placeable = self.can_place_area(area, destination, oid);
        if !placeable {
            let failed_move_cost_fraction = self.config.failed_move_cost_fraction;
            let spent = self
                .organism_mut(oid)
                .consume_body_energy(cost * failed_move_cost_fraction);
            let position = self.organism(oid).position;
            self.world.add_heat(position, spent);
            return false;
        }
        let spent = self.organism_mut(oid).consume_body_energy(cost);
        let position = self.organism(oid).position;
        self.world.add_heat(position, spent);
        let old_positions = self.footprint_cells(oid);
        self.world.remove_id_from_occupancy(oid, &old_positions);
        {
            let organism = self.organism_mut(oid);
            organism.position = destination;
            organism.facing = (dx, dy);
        }
        let new_positions = self.footprint_cells(oid);
        self.world.add_to_occupancy(oid, &new_positions);
        true
    }

    fn move_away(&mut self, oid: u32, threat: Position) -> bool {
        let position = self.organism(oid).position;
        let (dx, dy) = (threat.0 - position.0, threat.1 - position.1);
        let sx = if dx == 0 {
            0
        } else if dx > 0 {
            1
        } else {
            -1
        };
        let sy = if dy == 0 {
            0
        } else if dy > 0 {
            1
        } else {
            -1
        };
        let away = (position.0 - sx, position.1 - sy);
        self.move_organism(oid, Some(away))
    }

    fn seek_or_absorb_heat(&mut self, oid: u32, target: Position) {
        let on_footprint = self.footprint_cells(oid).contains(&target);
        if on_footprint {
            self.absorb_heat(oid, target);
        } else {
            self.move_organism(oid, Some(target));
        }
    }

    fn eat(&mut self, oid: u32, candidate: (Position, u16, f64)) {
        let (position, molecule_id, _) = candidate;
        let has_molecule = self
            .world
            .deposits
            .get(&position)
            .map(|inv| !inv.is_empty() && inv.iter().any(|b| b.molecule_id == molecule_id))
            .unwrap_or(false);
        if !has_molecule {
            return;
        }
        let transport = self
            .organism(oid)
            .substrate_module_expression(ModulePrimitive::Transport, molecule_id);
        let uptake_limit = 2
            + (transport * self.config.emergence_module_effect * 4.0)
                .floor()
                .clamp(0.0, 4.0) as i64;
        let count = {
            let source = &self.world.deposits.get(&position).unwrap()[self
                .world
                .deposits
                .get(&position)
                .unwrap()
                .iter()
                .position(|b| b.molecule_id == molecule_id)
                .unwrap()];
            uptake_limit.min(source.count)
        };
        let cost = self.config.reference_ingest_cost * self.reference_energy * count as f64;
        if self.organism(oid).chemical_energy() < cost {
            return;
        }
        let spent = self.organism_mut(oid).consume_body_energy(cost);
        let at = self.organism(oid).position;
        self.world.add_heat(at, spent);
        let eaten = {
            let inventory = self.world.deposits.get_mut(&position).unwrap();
            let idx = inventory
                .iter()
                .position(|b| b.molecule_id == molecule_id)
                .unwrap();
            let source = &mut inventory[idx];
            let taken = source.take(count);
            if source.count == 0 {
                inventory.remove(idx);
            }
            (taken, inventory.is_empty())
        };
        if eaten.1 {
            self.world.remove_deposit(position);
        }
        if self.config.biodeposits_enabled {
            let eaten_mass =
                self.catalog.molecules[eaten.0.molecule_id as usize].mass * eaten.0.count;
            self.world.erode_biodeposit(position, eaten_mass as f64);
        }
        let organism = self.organism_mut(oid);
        add_batch(&mut organism.gut, eaten.0);
    }

    fn absorb_heat(&mut self, oid: u32, target: Position) {
        let capacity = self.organism(oid).phenotype.mana_capacity - self.organism(oid).mana;
        if capacity <= 0.0 {
            return;
        }
        let available = self.world.heat_at_peek(target);
        let p = &self.organism(oid).phenotype;
        let gain_target = capacity
            .min(p.heat_absorption * self.reference_energy)
            .min(available * p.mana_efficiency);
        let removed = self.world.remove_heat(&[target], gain_target);
        self.organism_mut(oid).mana += removed;
    }

    fn active_detox(&mut self, oid: u32) {
        let cost = self
            .organism(oid)
            .chemical_energy()
            .min(self.reference_energy * 0.01);
        let spent = self.organism_mut(oid).consume_body_energy(cost);
        let position = self.organism(oid).position;
        self.world.add_heat(position, spent);
        let reference_energy = self.reference_energy;
        let organism = self.organism_mut(oid);
        organism.toxin_load =
            (organism.toxin_load - 3.0 * spent / reference_energy.max(1e-9)).max(0.0);
    }

    fn try_internalize(&mut self, host_id: u32, target_id: u32) -> bool {
        if !self.config.cellular_emergence_enabled
            || !self.has_organism(host_id)
            || !self.has_organism(target_id)
        {
            return false;
        }
        let (engulfment, target_resistance, host_mass, target_mass, guest_count) = {
            let host = self.organism(host_id);
            let target = self.organism(target_id);
            (
                host.genome
                    .emergence
                    .as_ref()
                    .map_or(0.0, |genome| genome.engulfment as f64),
                target
                    .genome
                    .emergence
                    .as_ref()
                    .map_or(1.0, |genome| genome.guest_tolerance as f64),
                host.peek_structural_mass(&self.catalog) as f64,
                target.peek_structural_mass(&self.catalog) as f64,
                host.cellular.as_ref().map_or(0, |state| state.guests.len()),
            )
        };
        if guest_count >= self.config.emergence_max_internal_guests {
            return false;
        }
        let size_factor = (host_mass / target_mass.max(1.0)).clamp(0.0, 2.0) * 0.5;
        let probability = (self.config.emergence_engulfment_rate
            * engulfment
            * (0.5 + 0.5 * (1.0 - target_resistance))
            * size_factor)
            .clamp(0.0, 1.0);
        if probability <= 0.0 || !self.rng.chance(probability) {
            return false;
        }

        let (genome_id, species_id, exchange, mut inventory, mut free_energy, nested) = {
            let target = self.organism_mut(target_id);
            let mut inventory = Vec::new();
            for source in target.inventories() {
                for batch in source.drain(..) {
                    add_batch(&mut inventory, batch);
                }
            }
            target.invalidate_body_cache();
            let free_energy = target.mana;
            target.mana = 0.0;
            let nested = target
                .cellular
                .as_mut()
                .map(|state| std::mem::take(&mut state.guests))
                .unwrap_or_default();
            (
                target.genome.genome_id,
                target.species_id,
                target
                    .genome
                    .emergence
                    .as_ref()
                    .map_or(0.0, |genome| genome.exchange),
                inventory,
                free_energy,
                nested,
            )
        };
        for mut guest in nested {
            for batch in guest.inventory.drain(..) {
                add_batch(&mut inventory, batch);
            }
            free_energy += guest.free_energy;
        }
        self.kill(target_id, last_action::DEAD_PREDATION);
        let guest = InternalGuest {
            source_organism_id: target_id,
            genome_id,
            species_id,
            inventory,
            free_energy,
            exchange,
            age: 0,
        };
        if let Some(cellular) = &mut self.organism_mut(host_id).cellular {
            cellular.guests.push(guest);
            self.emergence_stats.internalizations += 1;
            true
        } else {
            false
        }
    }

    fn physical_cover_ratio(&self, attacker_id: u32, target_id: u32) -> f64 {
        let target_position = self.organism(target_id).position;
        let mut structural_mass = 0.0;
        for dy in -1..=1 {
            for dx in -1..=1 {
                let position = (target_position.0 + dx, target_position.1 + dy);
                structural_mass += self.world.biodeposit_density_at(position);
                if let Some(occupants) = self.world.occupants_at(position) {
                    for &organism_id in occupants {
                        if organism_id == target_id
                            || organism_id == attacker_id
                            || !self.living.contains(&organism_id)
                        {
                            continue;
                        }
                        let organism = self.organism(organism_id);
                        structural_mass += organism.peek_structural_mass(&self.catalog) as f64
                            / organism.phenotype.adult_area.max(1) as f64;
                    }
                }
            }
        }
        structural_mass / self.reference_body_mass.max(1.0)
    }

    fn attack(&mut self, attacker_id: u32, target_id: u32) {
        if self.same_bond_component(attacker_id, target_id) || !self.organism(target_id).alive {
            return;
        }
        let mass_ratio = self
            .organism(attacker_id)
            .peek_structural_mass(&self.catalog) as f64
            / self.reference_body_mass.max(1.0);
        let (attack, attack_efficiency) = {
            let p = &self.organism(attacker_id).phenotype;
            (p.attack, p.attack_efficiency)
        };
        let cost = self.config.reference_attack_cost
            * self.reference_energy
            * mass_ratio
            * attack
            * attack
            / attack_efficiency;
        if self.organism(attacker_id).chemical_energy() < cost {
            return;
        }
        let spent = self.organism_mut(attacker_id).consume_body_energy(cost);
        let position = self.organism(attacker_id).position;
        self.world.add_heat(position, spent);
        let mut shield = if self.organism(target_id).earth_status.is_some() {
            0.5
        } else {
            1.0
        };
        if self.config.biodeposits_enabled {
            let cover_ratio = self.physical_cover_ratio(attacker_id, target_id);
            let concealment_probability =
                1.0 - (-self.config.biodeposit_concealment * cover_ratio).exp();
            self.stats.attacks += 1;
            if concealment_probability > 0.0 && self.rng.chance(concealment_probability) {
                return;
            }
            shield /= 1.0 + self.config.biodeposit_cover_strength * cover_ratio.sqrt();
        } else {
            self.stats.attacks += 1;
        }
        let damage = self.config.attack_damage_multiplier * attack * (0.5 + mass_ratio) * shield;
        self.organism_mut(target_id).integrity -= damage;
        if self.organism(target_id).integrity <= 0.0 {
            if !self.try_internalize(attacker_id, target_id) {
                self.kill(target_id, last_action::DEAD_PREDATION);
            }
            self.organism_mut(attacker_id).kills += 1;
        }
    }

    fn cast_magic(&mut self, caster_id: u32, target_id: u32) {
        if !self.organism(target_id).alive || self.organism(caster_id).mana <= 0.0 {
            return;
        }
        let affinity = self.organism(caster_id).phenotype.magic_affinity;
        let mut channel = 0;
        for axis in 1..4 {
            // Python max(range(4), key=...) keeps the first axis on ties.
            if affinity[axis] > affinity[channel] {
                channel = axis;
            }
        }
        let committed = (self.organism(caster_id).mana * 0.30).min(self.reference_energy * 0.5);
        self.organism_mut(caster_id).mana -= committed;
        let raw = committed * affinity[channel];
        let resistance = self.organism(target_id).phenotype.magic_resistance[channel];
        let effective = raw * (1.0 - resistance);
        let immediate_heat = committed - effective;
        let target_position = self.organism(target_id).position;
        self.world.add_heat(target_position, immediate_heat);
        self.stats.magic_casts += 1;
        match channel {
            0 => {
                // fire
                self.organism_mut(target_id).integrity -=
                    effective / self.reference_energy.max(1e-9) * 4.0;
                self.world.add_heat(target_position, effective);
                if self.organism(target_id).integrity <= 0.0 {
                    self.kill(target_id, last_action::DEAD_FIRE);
                }
            }
            1 | 2 => {
                // water slow, earth ward
                let effect_id = self.next_effect_id;
                self.next_effect_id += 1;
                let duration =
                    (4.0 + effective / self.reference_energy.max(1e-9) * 10.0).round() as i64;
                let duration = duration.max(2) as u32;
                let effect = MagicEffect {
                    effect_id,
                    channel: channel as u8,
                    source_id: caster_id,
                    target_id,
                    energy: effective,
                    expires_tick: self.tick + duration,
                };
                self.effects.insert(effect_id, effect);
                let expires_tick = self.tick + duration;
                let organism = self.organism_mut(target_id);
                if channel == 1 {
                    organism.water_status = Some((expires_tick, effect_id));
                } else {
                    organism.earth_status = Some((expires_tick, effect_id));
                }
            }
            _ => {
                // air: push target one step away from caster
                let caster_position = self.organism(caster_id).position;
                let dx = target_position.0 - caster_position.0;
                let dy = target_position.1 - caster_position.1;
                let push = (
                    if dx == 0 {
                        0
                    } else if dx > 0 {
                        1
                    } else {
                        -1
                    },
                    if dy == 0 {
                        0
                    } else if dy > 0 {
                        1
                    } else {
                        -1
                    },
                );
                let component_move = self.coordinated_components_enabled()
                    && self
                        .component_members
                        .get(&self.component_root_for(target_id))
                        .is_some_and(|members| members.len() > 1);
                if component_move {
                    self.move_component_exact(target_id, push);
                } else {
                    let destination = (
                        target_position.0 + push.0 as i64,
                        target_position.1 + push.1 as i64,
                    );
                    let area = self.footprint_area(target_id);
                    let placeable = self.can_place_area(area, destination, target_id);
                    if placeable {
                        let old = self.footprint_cells(target_id);
                        self.world.remove_id_from_occupancy(target_id, &old);
                        self.organism_mut(target_id).position = destination;
                        let new = self.footprint_cells(target_id);
                        self.world.add_to_occupancy(target_id, &new);
                    }
                }
                self.world
                    .add_heat(self.organism(target_id).position, effective);
            }
        }
    }

    fn repair(&mut self, oid: u32) {
        let cost = self
            .organism(oid)
            .chemical_energy()
            .min(self.reference_energy * 0.005);
        if cost <= 0.0 {
            return;
        }
        let spent = self.organism_mut(oid).consume_body_energy(cost);
        let position = self.organism(oid).position;
        self.world.add_heat(position, spent);
        let reference_energy = self.reference_energy;
        let organism = self.organism_mut(oid);
        organism.integrity =
            (organism.integrity + spent / reference_energy).min(organism.max_integrity);
    }

    // --------------------------------------------------------- reproduction

    fn sexual_success_probability(&mut self, parent_id: u32, mate_id: u32) -> f64 {
        let distance = self.genome_distance(
            self.organism(parent_id).genome.genome_id,
            self.organism(mate_id).genome.genome_id,
        );
        let pf = self.organism(parent_id).phenotype.fertility;
        let mf = self.organism(mate_id).phenotype.fertility;
        let ps = self.organism(parent_id).phenotype.sexual;
        let ms = self.organism(mate_id).phenotype.sexual;
        let mut probability = (pf * mf).sqrt() * (ps * ms).sqrt() * (-4.0 * distance).exp();
        if self.config.sexual_probability_floor_enabled {
            probability = probability.max(self.config.sexual_probability_floor);
        }
        probability.min(1.0)
    }

    fn reproduction_cooldown_ticks(&self, organism: &Organism, asexual: bool) -> u32 {
        let base_cooldown = py_round(organism.phenotype.maturity_age as f64 / 5.0).max(10);
        let adjusted =
            py_round(base_cooldown as f64 * self.config.reproduction_cooldown_multiplier).max(3);
        if !asexual {
            return adjusted as u32;
        }
        py_round(adjusted as f64 / organism.phenotype.asexual_rate).max(3) as u32
    }

    fn preview_reproductive_body(&self, parents: &[u32]) -> Inventory {
        let min_fraction = parents
            .iter()
            .map(|&p| self.organism(p).phenotype.reproduction_fraction)
            .fold(f64::INFINITY, f64::min)
            / parents.len() as f64;
        let mut preview: Inventory = Vec::new();
        for &parent_id in parents {
            for batch in &self.organism(parent_id).body {
                let count = (batch.count as f64 * min_fraction) as i64;
                if count > 0 {
                    let energy = batch.energy * count as f64 / batch.count as f64;
                    add_batch(
                        &mut preview,
                        Batch {
                            molecule_id: batch.molecule_id,
                            count,
                            energy,
                        },
                    );
                }
            }
        }
        if preview.is_empty() {
            let mut richest: Option<(i64, u16, f64)> = None;
            for &parent_id in parents {
                for batch in &self.organism(parent_id).body {
                    let key = (batch.count, batch.molecule_id);
                    if key.0 > 1 && richest.is_none_or(|r| key > (r.0, r.1)) {
                        richest = Some((
                            batch.count,
                            batch.molecule_id,
                            batch.energy / batch.count as f64,
                        ));
                    }
                }
            }
            if let Some((_, molecule_id, unit_energy)) = richest {
                add_batch(
                    &mut preview,
                    Batch {
                        molecule_id,
                        count: 1,
                        energy: unit_energy,
                    },
                );
            }
        }
        preview
    }

    fn extract_reproductive_body(&mut self, parents: &[u32]) -> Inventory {
        for &parent_id in parents {
            self.mark_occupancy_dirty(parent_id);
        }
        let min_fraction = parents
            .iter()
            .map(|&p| self.organism(p).phenotype.reproduction_fraction)
            .fold(f64::INFINITY, f64::min)
            / parents.len() as f64;
        let mut child: Inventory = Vec::new();
        for &parent_id in parents {
            let parent = self.organism_mut(parent_id);
            let mut ids: Vec<u16> = parent.body.iter().map(|b| b.molecule_id).collect();
            ids.sort();
            for molecule_id in ids {
                let source = parent
                    .body
                    .iter_mut()
                    .find(|b| b.molecule_id == molecule_id)
                    .unwrap();
                let count = (source.count as f64 * min_fraction) as i64;
                if count > 0 && source.count - count >= 1 {
                    let taken = source.take(count);
                    add_batch(&mut child, taken);
                }
                let remove = parent
                    .body
                    .iter()
                    .any(|b| b.molecule_id == molecule_id && b.count == 0);
                if remove {
                    parent.body.retain(|b| b.molecule_id != molecule_id);
                }
            }
        }
        if child.is_empty() {
            let richest_parent = *parents
                .iter()
                .max_by_key(|&&p| self.organism(p).body.iter().map(|b| b.count).sum::<i64>())
                .unwrap();
            let richest_id = {
                let body = &self.organism(richest_parent).body;
                body.iter().max_by_key(|b| b.count).map(|b| b.molecule_id)
            };
            if let Some(molecule_id) = richest_id {
                let parent = self.organism_mut(richest_parent);
                let idx = parent
                    .body
                    .iter()
                    .position(|b| b.molecule_id == molecule_id)
                    .unwrap();
                if parent.body[idx].count > 1 {
                    let taken = parent.body[idx].take(1);
                    add_batch(&mut child, taken);
                }
            }
        }
        for &parent_id in parents {
            self.organism_mut(parent_id).invalidate_body_cache();
        }
        child
    }

    fn find_child_position(
        &mut self,
        child: &mut Organism,
        first_parent: Position,
    ) -> Option<Position> {
        self.child_candidates.clear();
        for radius in 1..5i64 {
            for dy in -radius..=radius {
                for dx in -radius..=radius {
                    if dx.abs().max(dy.abs()) == radius {
                        self.child_candidates
                            .push((first_parent.0 + dx, first_parent.1 + dy));
                    }
                }
            }
        }
        let candidates = self.child_candidates.clone();
        candidates
            .into_iter()
            .find(|&position| self.can_place(child, position, child.organism_id))
    }

    fn record_matter_block(&mut self, parents: &[u32]) {
        let fraction = parents
            .iter()
            .map(|&p| self.organism(p).phenotype.reproduction_fraction)
            .fold(f64::INFINITY, f64::min)
            / parents.len().max(1) as f64;
        let mut limiting: Option<(i64, u16)> = None;
        for &parent_id in parents {
            for batch in &self.organism(parent_id).body {
                if (batch.count as f64 * fraction) < 1.0
                    && limiting.is_none_or(|l| (batch.count, batch.molecule_id) > l)
                {
                    limiting = Some((batch.count, batch.molecule_id));
                }
            }
        }
        if let Some((_, molecule_id)) = limiting {
            *self
                .stats
                .reproduction_matter_blocks_by_molecule
                .entry(molecule_id)
                .or_insert(0) += 1;
        }
    }

    fn partition_internal_guest(&mut self, parent_id: u32, child_id: u32) {
        if !self.config.cellular_emergence_enabled
            || !self.has_organism(parent_id)
            || !self.has_organism(child_id)
        {
            return;
        }
        let probability = self
            .organism(parent_id)
            .genome
            .emergence
            .as_ref()
            .map_or(0.0, |genome| genome.guest_tolerance as f64);
        let guest_count = self
            .organism(parent_id)
            .cellular
            .as_ref()
            .map_or(0, |state| state.guests.len());
        if guest_count == 0 || !self.rng.chance(probability) {
            return;
        }
        let index = self.rng.below(guest_count as u64) as usize;
        let guest = self
            .organism_mut(parent_id)
            .cellular
            .as_mut()
            .unwrap()
            .guests
            .swap_remove(index);
        self.organism_mut(child_id)
            .cellular
            .as_mut()
            .unwrap()
            .guests
            .push(guest);
    }

    fn component_propagule_translation(
        &mut self,
        parents: &[u32],
        children: &[Organism],
    ) -> Option<(i64, i64)> {
        let minimum_x = parents
            .iter()
            .map(|&parent| self.organism(parent).position.0)
            .min()?;
        let maximum_x = parents
            .iter()
            .map(|&parent| self.organism(parent).position.0)
            .max()?;
        let minimum_y = parents
            .iter()
            .map(|&parent| self.organism(parent).position.1)
            .min()?;
        let maximum_y = parents
            .iter()
            .map(|&parent| self.organism(parent).position.1)
            .max()?;
        let first_radius = (maximum_x - minimum_x).max(maximum_y - minimum_y).max(1) + 2;
        for radius in first_radius..=first_radius + 12 {
            for translation_y in -radius..=radius {
                for translation_x in -radius..=radius {
                    if translation_x.abs().max(translation_y.abs()) != radius {
                        continue;
                    }
                    let mut occupied = FxHashSet::default();
                    let mut valid = true;
                    for (&parent_id, child) in parents.iter().zip(children) {
                        let parent_position = self.organism(parent_id).position;
                        let position = (
                            parent_position.0 + translation_x,
                            parent_position.1 + translation_y,
                        );
                        let mass = self.catalog.inventory_mass(&child.body) as f64;
                        let ratio = (mass / child.target_mass.max(1.0)).min(1.0);
                        let area = py_round(child.phenotype.adult_area as f64 * ratio)
                            .max(1)
                            .min(child.phenotype.adult_area)
                            as usize;
                        let offsets = Arc::clone(&self.footprint_offsets(area));
                        let cells: Vec<Position> = offsets
                            .iter()
                            .map(|&(offset_x, offset_y)| {
                                (position.0 + offset_x as i64, position.1 + offset_y as i64)
                            })
                            .collect();
                        self.world.ensure_positions(&cells);
                        if cells.iter().any(|cell| {
                            !occupied.insert(*cell) || self.world.occupants_at(*cell).is_some()
                        }) {
                            valid = false;
                            break;
                        }
                    }
                    if valid {
                        return Some((translation_x, translation_y));
                    }
                }
            }
        }
        None
    }

    fn attempt_component_reproduction(&mut self, authority_id: u32) {
        let component_root = self.component_root_for(authority_id);
        let parents = self
            .component_members
            .get(&component_root)
            .cloned()
            .unwrap_or_else(|| vec![authority_id]);
        if parents.len() <= 1 {
            return;
        }
        if parents
            .iter()
            .any(|&parent| !self.has_organism(parent) || !self.is_reproductively_ready(parent))
        {
            self.stats.reproduction_resource_blocks += 1;
            self.stats.reproduction_mate_readiness_blocks += 1;
            return;
        }

        let mut costs = Vec::with_capacity(parents.len());
        for &parent in &parents {
            let planned_mass = self.organism(parent).peek_structural_mass(&self.catalog) as f64
                * self.organism(parent).phenotype.reproduction_fraction;
            let cost = self.config.reference_reproduction_cost
                * self.config.reproduction_cost_multiplier
                * self.reference_energy
                * planned_mass
                / self.reference_body_mass.max(1.0);
            if self.organism(parent).chemical_energy() < cost {
                self.stats.reproduction_resource_blocks += 1;
                self.stats.reproduction_energy_blocks += 1;
                return;
            }
            costs.push(cost);
        }
        for (&parent, &cost) in parents.iter().zip(&costs) {
            let spent = self.organism_mut(parent).consume_body_energy(cost);
            self.world.add_heat(self.organism(parent).position, spent);
            let cooldown = self.reproduction_cooldown_ticks(self.organism(parent), true);
            self.organism_mut(parent).reproduction_cooldown = self.tick + cooldown;
        }
        let log_probability = parents
            .iter()
            .map(|&parent| {
                self.config
                    .asexual_probability_floor
                    .max(
                        self.organism(parent).phenotype.fertility
                            * self.organism(parent).phenotype.asexual,
                    )
                    .clamp(1.0e-12, 1.0)
                    .ln()
            })
            .sum::<f64>()
            / parents.len() as f64;
        if !self.rng.chance(log_probability.exp()) {
            self.stats.failed_reproductions += 1;
            self.stats.reproduction_probability_failures += 1;
            return;
        }

        let mut children = Vec::with_capacity(parents.len());
        for &parent in &parents {
            let body = self.preview_reproductive_body(&[parent]);
            if body.is_empty() {
                self.stats.failed_reproductions += 1;
                self.stats.reproduction_body_matter_blocks += 1;
                self.record_matter_block(&parents);
                return;
            }
            let genome_id = self.claim_genome_id();
            let parent_genome = self.organism(parent).genome.as_ref().clone();
            let genome = Genome::offspring(
                genome_id,
                &[&parent_genome],
                &mut self.rng,
                self.config.mutation_multiplier,
                &self.config,
            );
            let phenotype = Phenotype::sample(&genome, &mut self.rng, &self.config);
            let child_id = self.claim_organism_id();
            let target_mass = (self.catalog.inventory_mass(&body) as f64 * 3.0).max(1.0);
            let mut child = Organism::new(
                child_id,
                self.organism(parent).lineage_id,
                genome,
                phenotype,
                body,
                target_mass,
            );
            child.diet_reactivity_mean = diet_reactivity_mean(&child.phenotype, &self.catalog);
            child.max_integrity =
                (4.0 + child.phenotype.adult_area as f64 * child.phenotype.density * 2.0).max(2.0);
            child.integrity = child.max_integrity;
            child.birth_tick = self.tick;
            child.parent_ids = vec![parent];
            child.generation = self.organism(parent).generation + 1;
            children.push(child);
        }

        let Some(translation) = self.component_propagule_translation(&parents, &children) else {
            self.stats.failed_reproductions += 1;
            self.stats.reproduction_placement_failures += 1;
            return;
        };

        let parent_bonds: Vec<Bond> = self
            .bonds
            .values()
            .copied()
            .filter(|bond| parents.contains(&bond.left) && parents.contains(&bond.right))
            .collect();
        let child_ids: Vec<u32> = children.iter().map(|child| child.organism_id).collect();
        let child_by_parent: FxHashMap<u32, u32> = parents
            .iter()
            .copied()
            .zip(child_ids.iter().copied())
            .collect();

        let mut extracted_bodies: Vec<(u32, Inventory)> = Vec::with_capacity(parents.len());
        for &parent in &parents {
            let extracted = self.extract_reproductive_body(&[parent]);
            if extracted.is_empty() {
                for (rollback_parent, inventory) in extracted_bodies {
                    for batch in inventory {
                        add_batch(&mut self.organism_mut(rollback_parent).body, batch);
                    }
                    self.organism_mut(rollback_parent).invalidate_body_cache();
                }
                self.stats.failed_reproductions += 1;
                self.stats.reproduction_body_matter_blocks += 1;
                return;
            }
            extracted_bodies.push((parent, extracted));
        }

        for (((&parent, child), &child_id), (_, extracted)) in parents
            .iter()
            .zip(&mut children)
            .zip(&child_ids)
            .zip(extracted_bodies)
        {
            child.body = extracted;
            child.invalidate_body_cache();
            child.target_mass = (self.catalog.inventory_mass(&child.body) as f64 * 3.0).max(1.0);
            let parent_position = self.organism(parent).position;
            child.position = (
                parent_position.0 + translation.0,
                parent_position.1 + translation.1,
            );
            let parent_species = vec![self.organism(parent).species_id];
            let genome = child.genome.as_ref().clone();
            child.species_id = self.assign_species(genome, 1, parent_species, Some(child_id));
            child.last_action = last_action::BORN;
        }

        for ((&parent, child), &child_id) in parents.iter().zip(children).zip(&child_ids) {
            let species_id = child.species_id;
            self.genome_owners[child.genome.genome_id as usize - 1] = child_id;
            self.insert_organism(child);
            self.living.insert(child_id);
            self.living_ordered.insert(child_id);
            self.partition_internal_guest(parent, child_id);
            self.organism_mut(parent).offspring_count += 1;
            self.stats.births += 1;
            self.stats.successful_reproductions += 1;
            self.species[species_id as usize - 1].births += 1;
        }
        self.refresh_dirty_occupancy();
        for &child_id in &child_ids {
            let cells = self.footprint_cells(child_id);
            self.world.add_to_occupancy(child_id, &cells);
        }
        for parent_bond in parent_bonds {
            let left = child_by_parent[&parent_bond.left];
            let right = child_by_parent[&parent_bond.right];
            let edge = if left < right {
                (left, right)
            } else {
                (right, left)
            };
            let retention = self
                .organism(parent_bond.left)
                .genome
                .emergence
                .as_ref()
                .map_or(0.0, |genome| genome.bond_retention)
                .min(
                    self.organism(parent_bond.right)
                        .genome
                        .emergence
                        .as_ref()
                        .map_or(0.0, |genome| genome.bond_retention),
                );
            self.bonds.insert(
                edge,
                Bond {
                    left,
                    right,
                    formed_tick: self.tick,
                    strength: (parent_bond.strength * (0.5 + 0.5 * retention)).max(0.01),
                },
            );
            self.emergence_stats.bond_formations += 1;
        }
        self.stats.asexual_reproduction_events += 1;
        self.emergence_stats.propagules += 1;
        self.emergence_stats.propagated_cells += child_ids.len() as u64;
    }

    fn attempt_reproduction(&mut self, parent_id: u32, mate_id: Option<u32>) {
        self.stats.reproduction_attempts += 1;
        if self.coordinated_components_enabled()
            && self
                .component_members
                .get(&self.component_root_for(parent_id))
                .is_some_and(|members| members.len() > 1)
        {
            self.attempt_component_reproduction(parent_id);
            return;
        }
        let parents: Vec<u32> = match mate_id {
            None => vec![parent_id],
            Some(m) => vec![parent_id, m],
        };
        if let Some(m) = mate_id {
            if !self.organism(m).alive || !self.is_reproductively_ready(m) {
                self.stats.reproduction_resource_blocks += 1;
                self.stats.reproduction_mate_readiness_blocks += 1;
                return;
            }
        }
        let count = match mate_id {
            None => 1,
            Some(mate_id) => py_round(
                (self.organism(parent_id).phenotype.offspring_count as f64
                    + self.organism(mate_id).phenotype.offspring_count as f64)
                    / 2.0,
            )
            .max(1),
        };
        let planned_mass: f64 = parents
            .iter()
            .map(|&p| {
                self.organism(p).peek_structural_mass(&self.catalog) as f64
                    * self.organism(p).phenotype.reproduction_fraction
            })
            .sum();
        let total_cost = self.config.reference_reproduction_cost
            * self.config.reproduction_cost_multiplier
            * self.reference_energy
            * planned_mass
            / self.reference_body_mass.max(1.0);
        let share = total_cost / parents.len() as f64;
        for &p in &parents {
            if self.organism(p).chemical_energy() < share {
                self.stats.reproduction_resource_blocks += 1;
                self.stats.reproduction_energy_blocks += 1;
                return;
            }
        }
        for &p in &parents {
            let spent = self.organism_mut(p).consume_body_energy(share);
            let position = self.organism(p).position;
            self.world.add_heat(position, spent);
            let cooldown = self.reproduction_cooldown_ticks(self.organism(p), mate_id.is_none());
            self.organism_mut(p).reproduction_cooldown = self.tick + cooldown;
        }

        let success = match mate_id {
            None => {
                let probability = self.config.asexual_probability_floor.max(
                    self.organism(parent_id).phenotype.fertility
                        * self.organism(parent_id).phenotype.asexual,
                );
                self.rng.chance(probability.min(1.0))
            }
            Some(m) => {
                let probability = self.sexual_success_probability(parent_id, m);
                self.rng.chance(probability)
            }
        };
        if !success {
            self.stats.failed_reproductions += 1;
            self.stats.reproduction_probability_failures += 1;
            return;
        }

        let first_parent_position = self.organism(parents[0]).position;
        let mut created = 0;
        for _ in 0..count {
            let genome_id = self.claim_genome_id();
            let parent_genomes: Vec<Genome> = parents
                .iter()
                .map(|&p| self.organism(p).genome.as_ref().clone())
                .collect();
            let genome = Genome::offspring(
                genome_id,
                &parent_genomes.iter().collect::<Vec<_>>(),
                &mut self.rng,
                self.config.mutation_multiplier,
                &self.config,
            );
            let phenotype = Phenotype::sample(&genome, &mut self.rng, &self.config);
            let child_body = self.preview_reproductive_body(&parents);
            if child_body.is_empty() {
                self.stats.failed_reproductions += 1;
                self.stats.reproduction_resource_blocks += 1;
                self.stats.reproduction_body_matter_blocks += 1;
                self.record_matter_block(&parents);
                break;
            }
            let child_id = self.claim_organism_id();
            let lineage_id = if mate_id.is_none() {
                self.organism(parent_id).lineage_id
            } else {
                child_id
            };
            let generation = parents
                .iter()
                .map(|&p| self.organism(p).generation)
                .max()
                .unwrap()
                + 1;
            let target_mass = (self.catalog.inventory_mass(&child_body) as f64 * 3.0).max(1.0);
            let mut child = Organism::new(
                child_id,
                lineage_id,
                genome.clone(),
                phenotype,
                child_body,
                target_mass,
            );
            child.diet_reactivity_mean = diet_reactivity_mean(&child.phenotype, &self.catalog);
            child.max_integrity =
                (4.0 + child.phenotype.adult_area as f64 * child.phenotype.density * 2.0).max(2.0);
            child.integrity = child.max_integrity;
            child.birth_tick = self.tick;
            child.parent_ids = parents.clone();
            child.generation = generation;
            let placement = self.find_child_position(&mut child, first_parent_position);
            let placement = match placement {
                Some(p) => p,
                None => {
                    self.stats.failed_reproductions += 1;
                    self.stats.reproduction_placement_failures += 1;
                    break;
                }
            };
            let extracted = self.extract_reproductive_body(&parents);
            if extracted.is_empty() {
                self.stats.failed_reproductions += 1;
                self.stats.reproduction_resource_blocks += 1;
                self.stats.reproduction_body_matter_blocks += 1;
                self.record_matter_block(&parents);
                break;
            }
            child.body = extracted;
            child.invalidate_body_cache();
            child.target_mass = target_mass;
            child.position = placement;
            let origin: u8 = if mate_id.is_none() { 1 } else { 2 };
            let parent_species: Vec<u32> = {
                let mut ids: Vec<u32> = parents
                    .iter()
                    .map(|&p| self.organism(p).species_id)
                    .collect();
                ids.sort();
                ids.dedup();
                ids
            };
            child.species_id = self.assign_species(genome, origin, parent_species, Some(child_id));
            let sid = child.species_id;
            child.last_action = last_action::BORN;
            self.genome_owners[child.genome.genome_id as usize - 1] = child_id;
            self.insert_organism(child);
            self.living.insert(child_id);
            self.living_ordered.insert(child_id);
            self.partition_internal_guest(parents[0], child_id);
            self.refresh_dirty_occupancy();
            let cells = self.footprint_cells(child_id);
            self.world.add_to_occupancy(child_id, &cells);
            for &p in &parents {
                self.organism_mut(p).offspring_count += 1;
            }
            self.stats.births += 1;
            self.stats.successful_reproductions += 1;
            self.species[sid as usize - 1].births += 1;
            created += 1;
        }
        if created > 0 {
            if parents.len() > 1 {
                self.stats.sexual_reproduction_events += 1;
            } else {
                self.stats.asexual_reproduction_events += 1;
            }
        }
    }

    // ----------------------------------------------------- social / species

    fn attempt_alliance(&mut self, organism_id: u32, other_id: u32) {
        if self.same_bond_component(organism_id, other_id) {
            return;
        }
        let edge = if organism_id < other_id {
            (organism_id, other_id)
        } else {
            (other_id, organism_id)
        };
        if self.alliances.contains(&edge) {
            return;
        }
        let diet_a = self.organism(organism_id).phenotype.diet_signature;
        let diet_b = self.organism(other_id).phenotype.diet_signature;
        let complement = 1.0 - genetics::similarity(&diet_a, &diet_b);
        let social_a = self.organism(organism_id).phenotype.social;
        let social_b = self.organism(other_id).phenotype.social;
        let probability =
            self.config.alliance_probability + 0.25 * social_a * social_b * complement;
        if !self.rng.chance(probability) {
            return;
        }
        self.alliances.insert(edge);
        self.stats.alliances += 1;
        let (a, b) = (self.organism(organism_id), self.organism(other_id));
        let can_colony = !self.config.replaces_abstract_colonies()
            && a.phenotype.sexual <= self.config.sexual_colony_max
            && b.phenotype.sexual <= self.config.sexual_colony_max
            && a.phenotype.asexual >= self.config.asexual_colony_min
            && b.phenotype.asexual >= self.config.asexual_colony_min
            && a.colony_id.is_none()
            && b.colony_id.is_none();
        if can_colony {
            let colony_id = self.next_colony_id;
            self.next_colony_id += 1;
            let bonus = (0.05 + complement * 0.10).min(self.config.colony_bonus_cap);
            let mut members = FxHashSet::default();
            members.insert(organism_id);
            members.insert(other_id);
            self.colonies.insert(
                colony_id,
                Colony {
                    colony_id,
                    members,
                    bonus,
                    created_tick: self.tick,
                },
            );
            self.stats.colonies += 1;
            self.organism_mut(organism_id).colony_id = Some(colony_id);
            self.organism_mut(other_id).colony_id = Some(colony_id);
        }
    }

    fn create_species(
        &mut self,
        genome: &Genome,
        origin: u8,
        parent_species_ids: Vec<u32>,
        founder_organism_id: Option<u32>,
    ) -> u32 {
        let species_id = self.next_species_id;
        self.next_species_id += 1;
        let color = genetics::species_color(species_id, genome);
        let species = Species {
            species_id,
            representative_genome: genome.clone(),
            color,
            created_tick: self.tick,
            origin,
            parent_species_ids,
            founder_organism_id,
            population: 1,
            births: 0,
            deaths: 0,
        };
        self.species.push(species);
        species_id
    }

    fn assign_species(
        &mut self,
        genome: Genome,
        origin: u8,
        parent_species_ids: Vec<u32>,
        founder_organism_id: Option<u32>,
    ) -> u32 {
        if !self.species.is_empty() {
            let mut closest: Option<(f64, u32)> = None;
            for species in &self.species {
                let distance = genome.distance(&species.representative_genome);
                if closest.is_none_or(|(best, _)| distance < best) {
                    closest = Some((distance, species.species_id));
                }
            }
            if let Some((distance, species_id)) = closest {
                if distance <= self.config.species_distance_threshold {
                    self.species[species_id as usize - 1].population += 1;
                    return species_id;
                }
            }
        }
        self.create_species(&genome, origin, parent_species_ids, founder_organism_id)
    }

    // -------------------------------------------------------------- lifecycle

    fn mark_occupancy_dirty(&mut self, oid: u32) {
        if !self.occupancy_dirty.contains_key(&oid) {
            let cells = self.footprint_cells(oid);
            self.occupancy_dirty.insert(oid, cells);
        }
    }

    fn refresh_dirty_occupancy(&mut self) {
        if self.occupancy_dirty.is_empty() {
            return;
        }
        let dirty: Vec<(u32, Vec<Position>)> = self.occupancy_dirty.drain().collect();
        for (oid, old_positions) in dirty {
            self.world.remove_id_from_occupancy(oid, &old_positions);
            if self.living.contains(&oid) {
                let cells = self.footprint_cells(oid);
                self.world.add_to_occupancy(oid, &cells);
            }
        }
    }

    fn kill(&mut self, oid: u32, cause: u8) {
        if !self.living.contains(&oid) {
            return;
        }
        self.mark_occupancy_dirty(oid);
        self.living.remove(&oid);
        self.living_ordered.remove(&oid);
        if self.config.cellular_emergence_enabled {
            let broken: Vec<(u32, u32)> = self
                .bonds
                .keys()
                .copied()
                .filter(|&(left, right)| left == oid || right == oid)
                .collect();
            for edge in broken {
                self.bonds.remove(&edge);
                self.emergence_stats.bond_breaks += 1;
            }
        }
        let (position, mana) = {
            let organism = self.organism_mut(oid);
            organism.alive = false;
            organism.last_action = cause;
            (organism.position, organism.mana)
        };
        self.world.add_heat(position, mana);
        self.organism_mut(oid).mana = 0.0;
        let mut corpse_inventory: Inventory = Vec::new();
        let mut guest_free_energy = 0.0;
        {
            let organism = self.organism_mut(oid);
            for inventory in organism.inventories() {
                for batch in inventory.drain(..) {
                    add_batch(&mut corpse_inventory, batch);
                }
            }
            if let Some(cellular) = &mut organism.cellular {
                for mut guest in cellular.guests.drain(..) {
                    for batch in guest.inventory.drain(..) {
                        add_batch(&mut corpse_inventory, batch);
                    }
                    guest_free_energy += guest.free_energy;
                }
            }
            organism.invalidate_body_cache();
        }
        self.world.add_heat(position, guest_free_energy);
        if self.config.dynamic_chemistry_enabled {
            let death_positions = self
                .occupancy_dirty
                .get(&oid)
                .cloned()
                .filter(|positions| !positions.is_empty())
                .unwrap_or_else(|| vec![position]);
            let mass = self.catalog.inventory_mass(&corpse_inventory) as f64
                / self.reference_body_mass.max(1.0);
            let share = mass / death_positions.len() as f64;
            for death_position in death_positions {
                let catalyst = share * self.config.byproduct_strength * 0.5;
                let toxin = share * self.config.byproduct_strength * 0.25;
                self.world.add_byproduct(death_position, catalyst, toxin);
                if catalyst > 0.0 || toxin > 0.0 {
                    self.stats.byproduct_emissions += 1;
                }
            }
        }
        if self.config.biodeposits_enabled {
            let death_positions = self
                .occupancy_dirty
                .get(&oid)
                .cloned()
                .filter(|positions| !positions.is_empty())
                .unwrap_or_else(|| vec![position]);
            let structural_mass = self.catalog.inventory_mass(&corpse_inventory) as f64;
            let density_share = structural_mass / death_positions.len() as f64;
            for &death_position in &death_positions {
                self.world.add_biodeposit(death_position, density_share);
            }
            for batch in &corpse_inventory {
                let divisor = death_positions.len() as i64;
                let quotient = batch.count / divisor;
                let remainder = batch.count % divisor;
                let mut remaining_count = batch.count;
                let mut remaining_energy = batch.energy;
                for (index, &death_position) in death_positions.iter().enumerate() {
                    let count = quotient + i64::from((index as i64) < remainder);
                    if count <= 0 {
                        continue;
                    }
                    let energy = if count == remaining_count {
                        remaining_energy
                    } else {
                        batch.energy * count as f64 / batch.count as f64
                    };
                    self.world.deposit_batch_raw(
                        death_position,
                        Batch {
                            molecule_id: batch.molecule_id,
                            count,
                            energy,
                        },
                    );
                    remaining_count -= count;
                    remaining_energy -= energy;
                }
            }
        } else {
            for batch in &corpse_inventory {
                self.world.deposit_batch_raw(position, *batch);
            }
        }
        let corpse_id = self.next_corpse_id;
        self.next_corpse_id += 1;
        self.corpses.insert(
            corpse_id,
            Corpse {
                corpse_id,
                source_id: oid,
                position,
                created_tick: self.tick,
            },
        );
        let species_id = self.organism(oid).species_id;
        if (species_id as usize) <= self.species.len() && species_id > 0 {
            let species = &mut self.species[species_id as usize - 1];
            species.population = (species.population - 1).max(0);
            species.deaths += 1;
        }
        let colony_id = self.organism(oid).colony_id;
        if let Some(cid) = colony_id {
            if let Some(colony) = self.colonies.get_mut(&cid) {
                colony.members.remove(&oid);
                if colony.members.len() < 2 {
                    let members: Vec<u32> = colony.members.iter().copied().collect();
                    self.colonies.remove(&cid);
                    for member_id in members {
                        if self.has_organism(member_id) {
                            self.organism_mut(member_id).colony_id = None;
                        }
                    }
                }
            }
        }
        let dead_record = {
            let organism = self.organism(oid);
            DeadRecord {
                organism_id: oid,
                genome_id: organism.genome.genome_id,
                lineage_id: organism.lineage_id,
                species_id: organism.species_id,
                parent_ids: [
                    organism.parent_ids.first().copied().unwrap_or(0),
                    organism.parent_ids.get(1).copied().unwrap_or(0),
                ],
                parent_count: organism.parent_ids.len().min(2) as u8,
                generation: organism.generation,
                birth_tick: organism.birth_tick,
                death_tick: self.tick,
                position: organism.position,
                cause,
                offspring_count: organism.offspring_count,
                kills: organism.kills,
            }
        };
        self.genome_owners[dead_record.genome_id as usize - 1] = 0;
        self.dead_records.push(dead_record);
        self.remove_organism(oid);
        self.stats.deaths += 1;
    }

    // ---------------------------------------------------------------- audit

    fn dynamic_element_totals(&self) -> Vec<i64> {
        let mut totals = vec![0i64; self.catalog.elements.len()];
        let mut add_inv = |inv: &Inventory| {
            for batch in inv {
                let def = &self.catalog.molecules[batch.molecule_id as usize];
                for (e, &amount) in def.composition.iter().enumerate() {
                    totals[e] += amount as i64 * batch.count;
                }
            }
        };
        for inv in self.world.deposits.values() {
            add_inv(inv);
        }
        for &oid in &self.living {
            let organism = self.organism(oid);
            for inv in organism.all_inventories() {
                add_inv(inv);
            }
            if let Some(cellular) = &organism.cellular {
                for guest in &cellular.guests {
                    add_inv(&guest.inventory);
                }
            }
        }
        // corpses hold empty inventories (all matter returns to deposits)
        let generated = &self.world.generated_elements;
        for (t, g) in totals.iter_mut().zip(generated.iter()) {
            *t -= g;
        }
        totals
    }

    pub fn total_energy(&self) -> f64 {
        let mut chemical = self.world.deposit_energy();
        let mut mana = 0.0;
        for &oid in &self.living {
            let organism = self.organism(oid);
            for inventory in organism.all_inventories() {
                chemical += chemistry::inventory_energy(inventory);
            }
            mana += organism.mana;
            if let Some(cellular) = &organism.cellular {
                for guest in &cellular.guests {
                    chemical += inventory_energy(&guest.inventory);
                    mana += guest.free_energy;
                }
            }
        }
        let effects: f64 = self.effects.values().map(|e| e.energy).sum();
        chemical + mana + effects + self.world.total_heat()
    }

    /// Audit returns (element_error, energy_error); raises via Result when strict.
    pub fn audit(&mut self, strict: bool) -> Result<(Vec<i64>, f64), String> {
        let current = self.dynamic_element_totals();
        let expected = self.initial_elements.clone();
        let element_error: Vec<i64> = current
            .iter()
            .zip(expected.iter())
            .map(|(a, b)| a - b)
            .collect();
        let elements_ok = element_error.iter().all(|&e| e == 0);
        // batch validation
        let validate_inv = |inv: &Inventory| -> Result<(), String> {
            for batch in inv {
                self.catalog.validate_batch(batch)?;
            }
            Ok(())
        };
        for inv in self.world.deposits.values() {
            validate_inv(inv)?;
        }
        for &oid in &self.living {
            let organism = self.organism(oid);
            for inv in organism.all_inventories() {
                validate_inv(inv)?;
            }
            if let Some(cellular) = &organism.cellular {
                for guest in &cellular.guests {
                    validate_inv(&guest.inventory)?;
                }
            }
        }
        let dynamic_energy = self.total_energy() - self.world.generated_energy;
        let error = dynamic_energy - self.initial_energy;
        self.stats.audit_error = error;
        let tolerance = energy_tolerance(self.initial_energy, self.world.generated_energy);
        let energy_ok = error.abs() <= tolerance;
        if strict && (!elements_ok) {
            return Err(format!(
                "matter conservation failed: element deltas {:?}",
                element_error
            ));
        }
        if strict && !energy_ok {
            return Err(format!(
                "energy conservation failed by {:.12e} (tolerance {:.12e})",
                error, tolerance
            ));
        }
        Ok((element_error, error))
    }

    // --------------------------------------------------------------- digest

    pub fn digest(&self) -> u64 {
        fn hash_inventory(h: &mut Fnv, inventory: &Inventory) {
            h.u64(inventory.len() as u64);
            for batch in inventory {
                h.u64(batch.molecule_id as u64);
                h.i64(batch.count);
                h.f64(batch.energy);
            }
        }

        let mut h = Fnv::new();
        h.u64(self.tick as u64);
        if self.config.scheduler == Scheduler::ParallelV3 {
            h.bytes(self.config.scheduler.as_str().as_bytes());
            h.u64(scheduler::PARALLEL_RNG_VERSION as u64);
            h.u64(scheduler::PARALLEL_RESOLVER_VERSION as u64);
        }
        if self.config.behavior_model != BehaviorModel::LegacyLinearMacroV1 {
            h.bytes(self.config.behavior_model.as_str().as_bytes());
            h.u64(behavior::OBSERVATION_SCHEMA_VERSION as u64);
            h.u64(behavior::INTENT_SCHEMA_VERSION as u64);
            h.u64(behavior::BRAIN_SCHEMA_VERSION as u64);
            h.u64(self.config.v2_founder_priors_enabled as u64);
            if self.config.behavior_model == BehaviorModel::RecurrentIntentV2 {
                h.u64(self.config.recurrent_state_lesion as u64);
                h.u64(self.config.memory_probe_enabled as u64);
            }
            h.f64(self.config.brain_cost_multiplier);
            h.f64(self.config.brain_base_cost);
            h.f64(self.config.brain_hidden_cost);
            h.f64(self.config.brain_recurrent_cost);
        }
        self.rng.hash_into(&mut h);
        if self.config.seasons_enabled {
            h.bytes(b"random-environment-seasons-v1");
            h.u64(self.config.season_duration_min as u64);
            h.u64(self.config.season_duration_max as u64);
            h.u64(self.config.season_transition_ticks as u64);
            h.f64(self.config.season_strength);
            self.seasons.hash_into(&mut h);
        }
        if self.config.cellular_emergence_enabled {
            h.bytes(b"stochastic-cellular-affordances-v1");
            h.u64(self.config.emergence_max_modules as u64);
            h.f64(self.config.emergence_structural_mutation_rate);
            h.f64(self.config.emergence_module_cost);
            h.f64(self.config.emergence_module_effect);
            h.f64(self.config.emergence_bond_rate);
            h.f64(self.config.emergence_bond_break_rate);
            h.f64(self.config.emergence_exchange_rate);
            h.f64(self.config.emergence_engulfment_rate);
            h.u64(self.config.emergence_max_internal_guests as u64);
            if self.config.emergence_coordinated_components {
                h.bytes(b"bond-derived-composite-actions-v1");
            }
        }
        if self.config.biodeposits_enabled {
            h.bytes(b"physical-biodeposits-v1");
            h.f64(self.config.biodeposit_decay_rate);
            h.f64(self.config.biodeposit_movement_resistance);
            h.f64(self.config.biodeposit_cover_strength);
            h.f64(self.config.biodeposit_concealment);
        }
        if self.config.dynamic_chemistry_enabled {
            h.bytes(b"dynamic-environmental-chemistry-v1");
            h.u64(self.config.reaction_rule_count as u64);
            h.f64(self.config.environmental_reaction_rate);
            h.f64(self.config.reaction_thermodynamics);
            h.f64(self.config.byproduct_strength);
            h.f64(self.config.byproduct_decay_rate);
            h.f64(self.config.chemistry_coupling);
            h.f64(self.config.guest_niche_coupling);
            h.u64(self.reaction_rules.len() as u64);
            h.f64(self.world.byproduct_scale[0]);
            h.f64(self.world.byproduct_scale[1]);
            let mut byproducts: Vec<(&Position, &[f64; 2])> =
                self.world.byproducts.iter().collect();
            byproducts.sort_unstable_by_key(|(position, _)| **position);
            h.u64(byproducts.len() as u64);
            for (position, value) in byproducts {
                h.i64(position.0);
                h.i64(position.1);
                h.f64(value[0]);
                h.f64(value[1]);
            }
        }
        h.u64(self.organisms.len() as u64);
        for organism in &self.organisms {
            h.u64(organism.organism_id as u64);
            h.u64(organism.alive as u64);
            if !organism.alive {
                continue;
            }
            h.u64(organism.lineage_id as u64);
            organism.genome.hash_into(&mut h);
            organism.phenotype.hash_into(&mut h);
            h.u64(organism.species_id as u64);
            h.u64(organism.parent_ids.len() as u64);
            for &parent_id in &organism.parent_ids {
                h.u64(parent_id as u64);
            }
            h.u64(organism.generation as u64);
            h.u64(organism.birth_tick as u64);
            h.i64(organism.position.0);
            h.i64(organism.position.1);
            hash_inventory(&mut h, &organism.body);
            hash_inventory(&mut h, &organism.gut);
            hash_inventory(&mut h, &organism.waste);
            h.f64(organism.mana);
            h.f64(organism.integrity);
            h.f64(organism.max_integrity);
            h.f64(organism.target_mass);
            h.f64(organism.maintenance_debt);
            h.f64(organism.toxin_load);
            h.u64(organism.reproduction_cooldown as u64);
            h.i64(organism.facing.0 as i64);
            h.i64(organism.facing.1 as i64);
            h.u64(organism.next_action_tick as u64);
            h.u64(organism.last_action as u64);
            if self.config.behavior_model != BehaviorModel::LegacyLinearMacroV1 {
                h.u64(organism.last_intent_kind as u64);
                h.u64(organism.decision_count as u64);
                h.f64(organism.brain_energy_spent);
            }
            if self.config.behavior_model == BehaviorModel::RecurrentIntentV2 {
                h.f64(organism.hidden_brain_energy_spent);
                h.f64(organism.recurrent_brain_energy_spent);
                for &value in &organism.neural_state.values {
                    h.u64(value.to_bits() as u64);
                }
                h.u64(organism.neural_numerical_errors as u64);
            }
            h.u64(organism.offspring_count as u64);
            h.u64(organism.kills as u64);
            h.u64(organism.colony_id.unwrap_or(0) as u64);
            if self.config.cellular_emergence_enabled {
                let cellular = organism
                    .cellular
                    .as_ref()
                    .expect("emergence-enabled organisms must carry cellular state");
                h.u64(cellular.expression.len() as u64);
                for &expression in &cellular.expression {
                    h.u64(expression.to_bits() as u64);
                }
                h.u64(cellular.local_signal.to_bits() as u64);
                h.u64(cellular.emitted_signal.to_bits() as u64);
                h.u64(cellular.guests.len() as u64);
                for guest in &cellular.guests {
                    h.u64(guest.source_organism_id as u64);
                    h.u64(guest.genome_id as u64);
                    h.u64(guest.species_id as u64);
                    hash_inventory(&mut h, &guest.inventory);
                    h.f64(guest.free_energy);
                    h.u64(guest.exchange.to_bits() as u64);
                    h.u64(guest.age as u64);
                }
            }
            for status in [organism.water_status, organism.earth_status] {
                h.u64(status.map_or(0, |value| value.0) as u64);
                h.u64(status.map_or(0, |value| value.1) as u64);
            }
        }
        h.u64(self.dead_records.len() as u64);
        for record in &self.dead_records {
            h.u64(record.organism_id as u64);
            h.u64(record.genome_id as u64);
            h.u64(record.lineage_id as u64);
            h.u64(record.species_id as u64);
            h.u64(record.parent_count as u64);
            for &parent_id in record.parent_ids.iter().take(record.parent_count as usize) {
                h.u64(parent_id as u64);
            }
            h.u64(record.generation as u64);
            h.u64(record.birth_tick as u64);
            h.u64(record.death_tick as u64);
            h.i64(record.position.0);
            h.i64(record.position.1);
            h.u64(record.cause as u64);
            h.u64(record.offspring_count as u64);
            h.u64(record.kills as u64);
        }

        let mut living_ids: Vec<u32> = self.living.iter().copied().collect();
        living_ids.sort_unstable();
        h.u64(living_ids.len() as u64);
        for id in living_ids {
            h.u64(id as u64);
        }

        let mut positions: Vec<&Position> = self.world.deposits.keys().collect();
        positions.sort();
        h.u64(positions.len() as u64);
        for position in positions {
            h.i64(position.0);
            h.i64(position.1);
            hash_inventory(&mut h, &self.world.deposits[position]);
        }
        if self.config.biodeposits_enabled {
            h.f64(self.world.biodeposit_scale);
            let mut biodeposits: Vec<(&Position, &f64)> = self.world.biodeposits.iter().collect();
            biodeposits.sort_unstable_by_key(|(position, _)| **position);
            h.u64(biodeposits.len() as u64);
            for (position, density) in biodeposits {
                h.i64(position.0);
                h.i64(position.1);
                h.f64(*density);
            }
        }
        let mut chunk_keys: Vec<&(i64, i64)> = self.world.chunks.keys().collect();
        chunk_keys.sort();
        h.u64(chunk_keys.len() as u64);
        for key in chunk_keys {
            let chunk = &self.world.chunks[key];
            h.i64(key.0);
            h.i64(key.1);
            h.u64(chunk.has_heat as u64);
            h.u64(chunk.heat.len() as u64);
            for &heat in &chunk.heat {
                h.f64(heat);
            }
        }
        h.u64(self.world.terrain_seed);
        h.u64(self.world.generated_elements.len() as u64);
        for &amount in &self.world.generated_elements {
            h.i64(amount);
        }
        h.f64(self.world.generated_energy);

        h.u64(self.species.len() as u64);
        for species in &self.species {
            h.u64(species.species_id as u64);
            species.representative_genome.hash_into(&mut h);
            h.bytes(&species.color);
            h.u64(species.created_tick as u64);
            h.u64(species.origin as u64);
            h.u64(species.parent_species_ids.len() as u64);
            for &parent_id in &species.parent_species_ids {
                h.u64(parent_id as u64);
            }
            h.u64(species.founder_organism_id.unwrap_or(0) as u64);
            h.i64(species.population);
            h.i64(species.births);
            h.i64(species.deaths);
        }

        let mut effect_ids: Vec<u32> = self.effects.keys().copied().collect();
        effect_ids.sort_unstable();
        h.u64(effect_ids.len() as u64);
        for effect_id in effect_ids {
            let effect = &self.effects[&effect_id];
            h.u64(effect.effect_id as u64);
            h.u64(effect.channel as u64);
            h.u64(effect.source_id as u64);
            h.u64(effect.target_id as u64);
            h.f64(effect.energy);
            h.u64(effect.expires_tick as u64);
        }

        let mut corpse_ids: Vec<u32> = self.corpses.keys().copied().collect();
        corpse_ids.sort_unstable();
        h.u64(corpse_ids.len() as u64);
        for corpse_id in corpse_ids {
            let corpse = &self.corpses[&corpse_id];
            h.u64(corpse.corpse_id as u64);
            h.u64(corpse.source_id as u64);
            h.i64(corpse.position.0);
            h.i64(corpse.position.1);
            h.u64(corpse.created_tick as u64);
        }

        let mut colony_ids: Vec<u32> = self.colonies.keys().copied().collect();
        colony_ids.sort_unstable();
        h.u64(colony_ids.len() as u64);
        for colony_id in colony_ids {
            let colony = &self.colonies[&colony_id];
            h.u64(colony.colony_id as u64);
            h.f64(colony.bonus);
            h.u64(colony.created_tick as u64);
            let mut members: Vec<u32> = colony.members.iter().copied().collect();
            members.sort_unstable();
            h.u64(members.len() as u64);
            for member in members {
                h.u64(member as u64);
            }
        }

        let mut alliances: Vec<(u32, u32)> = self.alliances.iter().copied().collect();
        alliances.sort_unstable();
        h.u64(alliances.len() as u64);
        for (left, right) in alliances {
            h.u64(left as u64);
            h.u64(right as u64);
        }
        if self.config.cellular_emergence_enabled {
            let mut bonds: Vec<((u32, u32), Bond)> = self
                .bonds
                .iter()
                .map(|(&edge, &bond)| (edge, bond))
                .collect();
            bonds.sort_by_key(|(edge, _)| *edge);
            h.u64(bonds.len() as u64);
            for (edge, bond) in bonds {
                h.u64(edge.0 as u64);
                h.u64(edge.1 as u64);
                h.u64(bond.formed_tick as u64);
                h.u64(bond.strength.to_bits() as u64);
            }
            for value in [
                self.emergence_stats.bond_formations,
                self.emergence_stats.bond_breaks,
                self.emergence_stats.energy_exchanges,
                self.emergence_stats.internalizations,
                self.emergence_stats.guest_replications,
                self.emergence_stats.guest_losses,
                self.emergence_stats.component_actions,
                self.emergence_stats.component_moves,
                self.emergence_stats.propagules,
                self.emergence_stats.propagated_cells,
            ] {
                h.u64(value);
            }
        }

        for value in [
            self.stats.births,
            self.stats.deaths,
            self.stats.reproduction_attempts,
            self.stats.reproduction_resource_blocks,
            self.stats.reproduction_mate_readiness_blocks,
            self.stats.reproduction_energy_blocks,
            self.stats.reproduction_body_matter_blocks,
            self.stats.reproduction_probability_failures,
            self.stats.reproduction_placement_failures,
            self.stats.failed_reproductions,
            self.stats.successful_reproductions,
            self.stats.asexual_reproduction_events,
            self.stats.sexual_reproduction_events,
            self.stats.attacks,
            self.stats.magic_casts,
            self.stats.alliances,
            self.stats.colonies,
        ] {
            h.i64(value);
        }
        if self.config.behavior_model != BehaviorModel::LegacyLinearMacroV1 {
            h.f64(self.stats.brain_energy_spent);
            if self.config.behavior_model == BehaviorModel::RecurrentIntentV2 {
                h.f64(self.stats.hidden_brain_energy_spent);
                h.f64(self.stats.recurrent_brain_energy_spent);
                h.u64(self.stats.neural_numerical_errors);
            }
            for &count in &self.stats.v2_intent_counts {
                h.u64(count);
            }
            h.u64(self.stats.v2_intent_failures);
        }
        let mut matter_blocks: Vec<(u16, i64)> = self
            .stats
            .reproduction_matter_blocks_by_molecule
            .iter()
            .map(|(&molecule_id, &count)| (molecule_id, count))
            .collect();
        matter_blocks.sort_unstable();
        for (molecule_id, count) in matter_blocks {
            h.u64(molecule_id as u64);
            h.i64(count);
        }
        for id in [
            self.next_organism_id,
            self.next_genome_id,
            self.next_species_id,
            self.next_effect_id,
            self.next_corpse_id,
            self.next_colony_id,
        ] {
            h.u64(id as u64);
        }
        h.finish()
    }
}

// ---------------------------------------------------------------------------
// PyO3 boundary
// ---------------------------------------------------------------------------

fn add_behavior_metadata<'py>(
    py: Python<'py>,
    dict: &Bound<'py, PyDict>,
    config: &SimConfig,
    effective_worker_count: usize,
) -> PyResult<()> {
    let is_v2 = config.behavior_model != BehaviorModel::LegacyLinearMacroV1;
    dict.set_item("behavior_model", config.behavior_model.as_str())?;
    dict.set_item("scheduler", config.scheduler.as_str())?;
    dict.set_item(
        "scheduler_schema_version",
        if config.scheduler == Scheduler::ParallelV3 {
            3
        } else {
            2
        },
    )?;
    dict.set_item("parallel_workers", config.parallel_workers)?;
    dict.set_item("effective_parallel_workers", effective_worker_count)?;
    dict.set_item(
        "parallel_partition_strategy",
        scheduler::PARALLEL_PARTITION_STRATEGY,
    )?;
    dict.set_item("parallel_rng_version", scheduler::PARALLEL_RNG_VERSION)?;
    dict.set_item(
        "parallel_resolver_version",
        scheduler::PARALLEL_RESOLVER_VERSION,
    )?;
    dict.set_item(
        "observation_schema_version",
        if is_v2 {
            behavior::OBSERVATION_SCHEMA_VERSION
        } else {
            behavior::legacy::OBSERVATION_SCHEMA_VERSION
        },
    )?;
    dict.set_item(
        "intent_schema_version",
        if is_v2 {
            behavior::INTENT_SCHEMA_VERSION
        } else {
            behavior::legacy::ACTION_SCHEMA_VERSION
        },
    )?;
    dict.set_item(
        "brain_schema_version",
        if is_v2 {
            behavior::BRAIN_SCHEMA_VERSION
        } else {
            0
        },
    )?;
    dict.set_item("brain_cost_active", is_v2)?;
    dict.set_item(
        "v2_intent_names",
        IntentKind::ALL
            .iter()
            .map(|kind| kind.as_str())
            .collect::<Vec<_>>(),
    )?;

    let dimensions = PyDict::new(py);
    dimensions.set_item("observations", behavior::observation::OBSERVATION_COUNT)?;
    dimensions.set_item("hidden", behavior::neural::HIDDEN_COUNT)?;
    dimensions.set_item(
        "controller_outputs",
        behavior::neural::CONTROLLER_OUTPUT_COUNT,
    )?;
    dimensions.set_item("neural_loci", behavior::neural::NEURAL_LOCUS_COUNT)?;
    dimensions.set_item(
        "active_loci",
        match config.behavior_model {
            BehaviorModel::LegacyLinearMacroV1 => 0,
            BehaviorModel::LinearIntentV2 => behavior::neural::LINEAR_LOCUS_COUNT,
            BehaviorModel::RecurrentIntentV2 => behavior::neural::NEURAL_LOCUS_COUNT,
        },
    )?;
    dimensions.set_item(
        "candidate_features",
        behavior::intent::CANDIDATE_FEATURE_COUNT,
    )?;
    dimensions.set_item("intent_types", behavior::intent::INTENT_TYPE_COUNT)?;
    dimensions.set_item("max_candidates", behavior::intent::MAX_INTENT_CANDIDATES)?;
    dict.set_item("v2_brain_dimensions", dimensions)?;

    let costs = PyDict::new(py);
    dict.set_item(
        "v2_founder_priors_enabled",
        config.v2_founder_priors_enabled,
    )?;
    dict.set_item("recurrent_state_lesion", config.recurrent_state_lesion)?;
    dict.set_item("memory_probe_enabled", config.memory_probe_enabled)?;
    costs.set_item("multiplier", config.brain_cost_multiplier)?;
    costs.set_item("base", config.brain_base_cost)?;
    costs.set_item("hidden", config.brain_hidden_cost)?;
    costs.set_item("recurrent", config.brain_recurrent_cost)?;
    dict.set_item("v2_brain_cost_coefficients", costs)?;
    Ok(())
}

fn season_profile_dict<'py>(
    py: Python<'py>,
    profile: &SeasonProfile,
) -> PyResult<Bound<'py, PyDict>> {
    let dict = PyDict::new(py);
    dict.set_item(
        "resource_charge_multiplier",
        profile.resource_charge_multiplier,
    )?;
    dict.set_item("decomposition_multiplier", profile.decomposition_multiplier)?;
    dict.set_item(
        "molecule_charge_affinities",
        profile.molecule_charge_affinities.clone(),
    )?;
    Ok(dict)
}

fn season_event_dict<'py>(py: Python<'py>, event: &SeasonEvent) -> PyResult<Bound<'py, PyDict>> {
    let dict = PyDict::new(py);
    dict.set_item("schema_version", 1)?;
    dict.set_item("index", event.index)?;
    dict.set_item("started_tick", event.started_tick)?;
    dict.set_item("transition_end_tick", event.transition_end_tick)?;
    dict.set_item("next_season_tick", event.next_season_tick)?;
    dict.set_item("from", season_profile_dict(py, &event.from)?)?;
    dict.set_item("target", season_profile_dict(py, &event.target)?)?;
    Ok(dict)
}

#[pyclass]
struct KernelSimulation {
    state: KernelState,
    season_event_cursor: usize,
}

#[pymethods]
impl KernelSimulation {
    #[new]
    #[pyo3(signature = (config_dict=None))]
    fn new(config_dict: Option<&Bound<PyDict>>) -> PyResult<Self> {
        let mut config = SimConfig::default();
        if let Some(dict) = config_dict {
            parse_config(dict, &mut config)?;
        }
        let state = KernelState::new(config)
            .map_err(|e| PyRuntimeError::new_err(format!("kernel init failed: {}", e)))?;
        Ok(KernelSimulation {
            state,
            season_event_cursor: 0,
        })
    }

    /// Run n ticks entirely in Rust while pygame/Python can use another thread.
    fn step(&mut self, py: Python<'_>, n_ticks: u32) {
        py.allow_threads(|| self.state.step(n_ticks));
    }

    fn step_one(&mut self, py: Python<'_>) {
        py.allow_threads(|| self.state.step(1));
    }

    fn profile_step<'py>(&mut self, py: Python<'py>, n_ticks: u32) -> PyResult<Bound<'py, PyDict>> {
        let profile = py.allow_threads(|| self.state.profile_step(n_ticks));
        let dict = PyDict::new(py);
        for (name, nanoseconds) in [
            ("heat_diffusion", profile.heat_diffusion_ns),
            ("deposit_production", profile.deposit_production_ns),
            ("effects", profile.effects_ns),
            ("decomposition", profile.decomposition_ns),
            ("organism_loop", profile.organism_loop_ns),
            ("organism_ordering", profile.organism_ordering_ns),
            ("upkeep", profile.upkeep_ns),
            ("digestion", profile.digestion_ns),
            ("decision", profile.decision_ns),
            ("parallel_maintenance", profile.parallel_maintenance_ns),
            ("parallel_prepare", profile.parallel_prepare_ns),
            ("parallel_intent", profile.parallel_intent_ns),
            ("parallel_grouping", profile.parallel_grouping_ns),
            ("parallel_resolution", profile.parallel_resolution_ns),
            ("corpse_expiry", profile.corpse_expiry_ns),
            ("occupancy_refresh", profile.occupancy_refresh_ns),
            ("audit", profile.audit_ns),
            ("total", profile.total_ns),
        ] {
            dict.set_item(name, nanoseconds as f64 / 1_000_000_000.0)?;
        }
        dict.set_item("ticks", n_ticks)?;
        dict.set_item("final_tick", self.state.tick)?;
        dict.set_item("final_population", self.state.population())?;
        Ok(dict)
    }

    /// Apply runtime-safe configuration changes at the next worker barrier.
    fn update_config(&mut self, config_dict: &Bound<PyDict>) -> PyResult<()> {
        for (key, _) in config_dict.iter() {
            let name: String = key.extract()?;
            if !runtime_config_field(&name) {
                return Err(PyValueError::new_err(format!(
                    "{name} cannot change while the kernel is running"
                )));
            }
        }
        let mut config = self.state.config.clone();
        parse_config(config_dict, &mut config)?;
        config
            .validate()
            .map_err(|error| PyRuntimeError::new_err(format!("invalid config update: {error}")))?;
        self.state.config = config;
        Ok(())
    }

    #[getter]
    fn tick(&self) -> u32 {
        self.state.tick()
    }

    #[getter]
    fn population(&self) -> usize {
        self.state.population()
    }

    #[getter]
    fn species_count(&self) -> usize {
        self.state.species.len()
    }

    /// Viewport-oriented immutable snapshot for the asynchronous pygame GUI.
    #[pyo3(signature = (bounds, include_heat=false, include_food=true, selected_id=None))]
    fn gui_snapshot<'py>(
        &mut self,
        py: Python<'py>,
        bounds: (i64, i64, i64, i64),
        include_heat: bool,
        include_food: bool,
        selected_id: Option<u32>,
    ) -> PyResult<Bound<'py, PyDict>> {
        use numpy::PyArray1;

        let (x0, y0, x1, y1) = bounds;
        if x1 <= x0 || y1 <= y0 {
            return Err(PyValueError::new_err("viewport bounds must be ordered"));
        }
        let chunk_size = self.state.config.chunk_size as i64;
        for chunk_x in x0.div_euclid(chunk_size)..=(x1 - 1).div_euclid(chunk_size) {
            for chunk_y in y0.div_euclid(chunk_size)..=(y1 - 1).div_euclid(chunk_size) {
                self.state.world.ensure_chunk(chunk_x, chunk_y);
            }
        }

        let dict = PyDict::new(py);
        add_behavior_metadata(
            py,
            &dict,
            &self.state.config,
            self.state.effective_worker_count(),
        )?;
        dict.set_item("tick", self.state.tick)?;
        dict.set_item("population", self.state.population())?;
        dict.set_item("species_count", self.state.species.len())?;
        dict.set_item("alliances_count", self.state.alliances.len())?;
        dict.set_item("colonies_count", self.state.colonies.len())?;
        dict.set_item("stats", self.stats_dict(py)?)?;
        dict.set_item("season", self.season_state(py, self.season_event_cursor)?)?;
        self.season_event_cursor = self.state.seasons.events.len();

        let mut ids = Vec::new();
        let mut species_ids = Vec::new();
        let mut xs = Vec::new();
        let mut ys = Vec::new();
        let mut areas = Vec::new();
        let mut energy_fractions = Vec::new();
        let mut mana = Vec::new();
        let mut integrity = Vec::new();
        let mut max_integrity = Vec::new();
        let mut generation = Vec::new();
        let mut lineage = Vec::new();
        let mut birth_tick = Vec::new();
        let mut toxin = Vec::new();
        let mut toxin_tolerance = Vec::new();
        let mut colony = Vec::new();
        let mut last_action = Vec::new();
        let mut offspring_count = Vec::new();
        let mut kills = Vec::new();
        let mut decision_count = Vec::new();
        let mut brain_energy_spent = Vec::new();
        let mut hidden_expression_mean = Vec::new();
        let mut recurrent_expression_mean = Vec::new();
        let mut retention_mean = Vec::new();
        let mut neural_numerical_errors = Vec::new();
        let mut neural_state = Vec::new();
        let mut module_count = Vec::new();
        let mut expressed_module_count = Vec::new();
        let mut compartment_count = Vec::new();
        let mut internal_guest_count = Vec::new();
        let mut bond_degree = Vec::new();
        let mut component_id = Vec::new();
        let mut component_size = Vec::new();
        let (component_roots, component_sizes) = self.state.bond_component_facts();
        let mut bond_degrees: FxHashMap<u32, u32> = FxHashMap::default();
        for bond in self.state.bonds.values() {
            *bond_degrees.entry(bond.left).or_default() += 1;
            *bond_degrees.entry(bond.right).or_default() += 1;
        }
        let mut overview_ids = Vec::with_capacity(self.state.living.len());
        let mut overview_species = Vec::with_capacity(self.state.living.len());
        let mut overview_x = Vec::with_capacity(self.state.living.len());
        let mut overview_y = Vec::with_capacity(self.state.living.len());
        let margin = 16;
        for organism_id in self.state.living_ordered.iter().copied() {
            let organism = self.state.organism(organism_id);
            overview_ids.push(organism_id);
            overview_species.push(organism.species_id);
            overview_x.push(organism.position.0);
            overview_y.push(organism.position.1);
            let visible = organism.position.0 >= x0 - margin
                && organism.position.0 < x1 + margin
                && organism.position.1 >= y0 - margin
                && organism.position.1 < y1 + margin;
            if !visible && selected_id != Some(organism_id) {
                continue;
            }
            let mass = organism.peek_structural_mass(&self.state.catalog) as f64;
            let ratio = (mass / organism.target_mass.max(1.0)).min(1.0);
            let area = py_round(organism.phenotype.adult_area as f64 * ratio)
                .max(1)
                .min(organism.phenotype.adult_area);
            let capacity: f64 = organism
                .body
                .iter()
                .map(|batch| {
                    self.state.catalog.molecules[batch.molecule_id as usize].energy_capacity
                        * batch.count as f64
                })
                .sum();
            ids.push(organism_id);
            species_ids.push(organism.species_id);
            xs.push(organism.position.0);
            ys.push(organism.position.1);
            areas.push(area);
            energy_fractions.push(if capacity > 0.0 {
                organism.chemical_energy() / capacity
            } else {
                0.0
            });
            mana.push(organism.mana);
            integrity.push(organism.integrity);
            max_integrity.push(organism.max_integrity);
            generation.push(organism.generation);
            lineage.push(organism.lineage_id);
            birth_tick.push(organism.birth_tick);
            toxin.push(organism.toxin_load);
            toxin_tolerance.push(organism.phenotype.toxin_tolerance);
            colony.push(organism.colony_id.map(i64::from).unwrap_or(-1));
            last_action.push(organism.last_action);
            offspring_count.push(organism.offspring_count);
            kills.push(organism.kills);
            decision_count.push(organism.decision_count);
            brain_energy_spent.push(organism.brain_energy_spent);
            let recurrent = organism.phenotype.recurrent_policy.as_ref();
            hidden_expression_mean
                .push(recurrent.map_or(0.0, |policy| policy.hidden_expression_mean()));
            recurrent_expression_mean
                .push(recurrent.map_or(0.0, |policy| policy.recurrent_expression_mean()));
            retention_mean.push(recurrent.map_or(0.0, |policy| policy.retention_mean()));
            neural_numerical_errors.push(organism.neural_numerical_errors);
            neural_state.extend(organism.neural_state.values);
            let emergence = organism.genome.emergence.as_ref();
            let cellular = organism.cellular.as_ref();
            module_count.push(emergence.map_or(0, |genome| genome.modules.len() as u32));
            expressed_module_count.push(cellular.map_or(0, |state| {
                state
                    .expression
                    .iter()
                    .filter(|&&value| value >= 0.5)
                    .count() as u32
            }));
            compartment_count.push(emergence.map_or(0, |genome| {
                genome
                    .modules
                    .iter()
                    .map(|module| module.compartment_tag)
                    .collect::<FxHashSet<_>>()
                    .len() as u32
            }));
            internal_guest_count.push(cellular.map_or(0, |state| state.guests.len() as u32));
            bond_degree.push(bond_degrees.get(&organism_id).copied().unwrap_or(0));
            let root = component_roots[organism_id as usize];
            component_id.push(root);
            component_size.push(component_sizes.get(&root).copied().unwrap_or(1));
        }
        let organisms = PyDict::new(py);
        organisms.set_item("id", PyArray1::from_vec(py, ids))?;
        organisms.set_item("species_id", PyArray1::from_vec(py, species_ids))?;
        organisms.set_item("x", PyArray1::from_vec(py, xs))?;
        organisms.set_item("y", PyArray1::from_vec(py, ys))?;
        organisms.set_item("area", PyArray1::from_vec(py, areas))?;
        organisms.set_item("energy_fraction", PyArray1::from_vec(py, energy_fractions))?;
        organisms.set_item("mana", PyArray1::from_vec(py, mana))?;
        organisms.set_item("integrity", PyArray1::from_vec(py, integrity))?;
        organisms.set_item("max_integrity", PyArray1::from_vec(py, max_integrity))?;
        organisms.set_item("generation", PyArray1::from_vec(py, generation))?;
        organisms.set_item("lineage_id", PyArray1::from_vec(py, lineage))?;
        organisms.set_item("birth_tick", PyArray1::from_vec(py, birth_tick))?;
        organisms.set_item("toxin_load", PyArray1::from_vec(py, toxin))?;
        organisms.set_item("toxin_tolerance", PyArray1::from_vec(py, toxin_tolerance))?;
        organisms.set_item("colony_id", PyArray1::from_vec(py, colony))?;
        organisms.set_item("last_action", PyArray1::from_vec(py, last_action))?;
        organisms.set_item("offspring_count", PyArray1::from_vec(py, offspring_count))?;
        organisms.set_item("kills", PyArray1::from_vec(py, kills))?;
        organisms.set_item("decision_count", PyArray1::from_vec(py, decision_count))?;
        organisms.set_item(
            "brain_energy_spent",
            PyArray1::from_vec(py, brain_energy_spent),
        )?;
        organisms.set_item(
            "hidden_expression_mean",
            PyArray1::from_vec(py, hidden_expression_mean),
        )?;
        organisms.set_item(
            "recurrent_expression_mean",
            PyArray1::from_vec(py, recurrent_expression_mean),
        )?;
        organisms.set_item("retention_mean", PyArray1::from_vec(py, retention_mean))?;
        organisms.set_item(
            "neural_numerical_errors",
            PyArray1::from_vec(py, neural_numerical_errors),
        )?;
        organisms.set_item("neural_state", PyArray1::from_vec(py, neural_state))?;
        organisms.set_item("module_count", PyArray1::from_vec(py, module_count))?;
        organisms.set_item(
            "expressed_module_count",
            PyArray1::from_vec(py, expressed_module_count),
        )?;
        organisms.set_item(
            "compartment_count",
            PyArray1::from_vec(py, compartment_count),
        )?;
        organisms.set_item(
            "internal_guest_count",
            PyArray1::from_vec(py, internal_guest_count),
        )?;
        organisms.set_item("bond_degree", PyArray1::from_vec(py, bond_degree))?;
        organisms.set_item("component_id", PyArray1::from_vec(py, component_id))?;
        organisms.set_item("component_size", PyArray1::from_vec(py, component_size))?;
        dict.set_item("organisms", organisms)?;

        let bonds = PyDict::new(py);
        let mut bond_left = Vec::new();
        let mut bond_right = Vec::new();
        let mut bond_x1 = Vec::new();
        let mut bond_y1 = Vec::new();
        let mut bond_x2 = Vec::new();
        let mut bond_y2 = Vec::new();
        let mut bond_strength = Vec::new();
        for bond in self.state.bonds.values() {
            if !self.state.has_organism(bond.left) || !self.state.has_organism(bond.right) {
                continue;
            }
            let left = self.state.organism(bond.left).position;
            let right = self.state.organism(bond.right).position;
            let visible = [left, right].iter().any(|position| {
                position.0 >= x0 && position.0 < x1 && position.1 >= y0 && position.1 < y1
            });
            if visible {
                bond_left.push(bond.left);
                bond_right.push(bond.right);
                bond_x1.push(left.0);
                bond_y1.push(left.1);
                bond_x2.push(right.0);
                bond_y2.push(right.1);
                bond_strength.push(bond.strength);
            }
        }
        bonds.set_item("left_id", PyArray1::from_vec(py, bond_left))?;
        bonds.set_item("right_id", PyArray1::from_vec(py, bond_right))?;
        bonds.set_item("x1", PyArray1::from_vec(py, bond_x1))?;
        bonds.set_item("y1", PyArray1::from_vec(py, bond_y1))?;
        bonds.set_item("x2", PyArray1::from_vec(py, bond_x2))?;
        bonds.set_item("y2", PyArray1::from_vec(py, bond_y2))?;
        bonds.set_item("strength", PyArray1::from_vec(py, bond_strength))?;
        dict.set_item("bonds", bonds)?;

        let relations = PyDict::new(py);
        let mut parent_ids = Vec::new();
        let mut living_parent_ids = Vec::new();
        let mut offspring = Vec::new();
        let mut alliance_ids = Vec::new();
        let mut bond_ids = Vec::new();
        if let Some(organism_id) = selected_id.filter(|&id| self.state.has_organism(id)) {
            parent_ids.extend(self.state.organism(organism_id).parent_ids.iter().copied());
            living_parent_ids.extend(
                parent_ids
                    .iter()
                    .copied()
                    .filter(|&id| self.state.living.contains(&id)),
            );
            offspring.extend(
                self.state
                    .living_ordered
                    .iter()
                    .copied()
                    .filter(|&id| self.state.organism(id).parent_ids.contains(&organism_id))
                    .map(|id| (self.state.organism(id).birth_tick, id)),
            );
            offspring.sort_unstable_by(|left, right| right.cmp(left));
            for &(left, right) in &self.state.alliances {
                if left == organism_id && self.state.living.contains(&right) {
                    alliance_ids.push(right);
                } else if right == organism_id && self.state.living.contains(&left) {
                    alliance_ids.push(left);
                }
            }
            for bond in self.state.bonds.values() {
                if bond.left == organism_id && self.state.living.contains(&bond.right) {
                    bond_ids.push(bond.right);
                } else if bond.right == organism_id && self.state.living.contains(&bond.left) {
                    bond_ids.push(bond.left);
                }
            }
        }
        alliance_ids.sort_unstable();
        alliance_ids.dedup();
        bond_ids.sort_unstable();
        bond_ids.dedup();
        relations.set_item("parent_ids", PyArray1::from_vec(py, parent_ids))?;
        relations.set_item(
            "living_parent_ids",
            PyArray1::from_vec(py, living_parent_ids),
        )?;
        relations.set_item(
            "offspring_ids",
            PyArray1::from_vec(
                py,
                offspring.into_iter().map(|(_, id)| id).collect::<Vec<_>>(),
            ),
        )?;
        relations.set_item("alliance_ids", PyArray1::from_vec(py, alliance_ids))?;
        relations.set_item("bond_ids", PyArray1::from_vec(py, bond_ids))?;
        dict.set_item("selected_relations", relations)?;

        let overview = PyDict::new(py);
        overview.set_item("id", PyArray1::from_vec(py, overview_ids))?;
        overview.set_item("species_id", PyArray1::from_vec(py, overview_species))?;
        overview.set_item("x", PyArray1::from_vec(py, overview_x))?;
        overview.set_item("y", PyArray1::from_vec(py, overview_y))?;
        dict.set_item("overview", overview)?;

        let mut deposit_x = Vec::new();
        let mut deposit_y = Vec::new();
        let mut deposit_molecule = Vec::new();
        let mut deposit_units = Vec::new();
        if include_food {
            for (&position, inventory) in &self.state.world.deposits {
                if position.0 < x0 || position.0 >= x1 || position.1 < y0 || position.1 >= y1 {
                    continue;
                }
                if let Some(richest) = inventory
                    .iter()
                    .filter(|batch| batch.count > 0)
                    .max_by(|left, right| left.energy.total_cmp(&right.energy))
                {
                    deposit_x.push(position.0);
                    deposit_y.push(position.1);
                    deposit_molecule.push(richest.molecule_id);
                    deposit_units.push(inventory_count(inventory));
                }
            }
        }
        let deposits = PyDict::new(py);
        deposits.set_item("x", PyArray1::from_vec(py, deposit_x))?;
        deposits.set_item("y", PyArray1::from_vec(py, deposit_y))?;
        deposits.set_item("molecule_id", PyArray1::from_vec(py, deposit_molecule))?;
        deposits.set_item("units", PyArray1::from_vec(py, deposit_units))?;
        dict.set_item("deposits", deposits)?;

        let biodeposits = PyDict::new(py);
        let mut biodeposit_x = Vec::new();
        let mut biodeposit_y = Vec::new();
        let mut biodeposit_density = Vec::new();
        if self.state.config.biodeposits_enabled {
            for (&position, &density) in &self.state.world.biodeposits {
                if position.0 >= x0 && position.0 < x1 && position.1 >= y0 && position.1 < y1 {
                    biodeposit_x.push(position.0);
                    biodeposit_y.push(position.1);
                    biodeposit_density.push(density * self.state.world.biodeposit_scale);
                }
            }
        }
        biodeposits.set_item("x", PyArray1::from_vec(py, biodeposit_x))?;
        biodeposits.set_item("y", PyArray1::from_vec(py, biodeposit_y))?;
        biodeposits.set_item("density", PyArray1::from_vec(py, biodeposit_density))?;
        dict.set_item("biodeposits", biodeposits)?;

        let mut heat_x = Vec::new();
        let mut heat_y = Vec::new();
        let mut heat_value = Vec::new();
        let mut heat_max = 0.0f64;
        if include_heat {
            let mut visible_heat = Vec::new();
            for y in y0..y1 {
                for x in x0..x1 {
                    let value = self.state.world.heat_at_peek((x, y));
                    heat_max = heat_max.max(value);
                    if value > 0.0 {
                        visible_heat.push((x, y, value));
                    }
                }
            }
            let threshold = heat_max * 0.02;
            for (x, y, value) in visible_heat {
                if value > threshold {
                    heat_x.push(x);
                    heat_y.push(y);
                    heat_value.push(value);
                }
            }
        }
        let heat = PyDict::new(py);
        heat.set_item("x", PyArray1::from_vec(py, heat_x))?;
        heat.set_item("y", PyArray1::from_vec(py, heat_y))?;
        heat.set_item("value", PyArray1::from_vec(py, heat_value))?;
        heat.set_item("maximum", heat_max)?;
        dict.set_item("heat", heat)?;

        let mut corpse_x = Vec::new();
        let mut corpse_y = Vec::new();
        for corpse in self.state.corpses.values() {
            if corpse.position.0 >= x0
                && corpse.position.0 < x1
                && corpse.position.1 >= y0
                && corpse.position.1 < y1
            {
                corpse_x.push(corpse.position.0);
                corpse_y.push(corpse.position.1);
            }
        }
        let corpses = PyDict::new(py);
        corpses.set_item("x", PyArray1::from_vec(py, corpse_x))?;
        corpses.set_item("y", PyArray1::from_vec(py, corpse_y))?;
        dict.set_item("corpses", corpses)?;

        let mut chunk_x = Vec::with_capacity(self.state.world.chunks.len());
        let mut chunk_y = Vec::with_capacity(self.state.world.chunks.len());
        let mut chunk_keys: Vec<(i64, i64)> = self.state.world.chunks.keys().copied().collect();
        chunk_keys.sort_unstable();
        for (x, y) in chunk_keys {
            chunk_x.push(x);
            chunk_y.push(y);
        }
        let chunks = PyDict::new(py);
        chunks.set_item("x", PyArray1::from_vec(py, chunk_x))?;
        chunks.set_item("y", PyArray1::from_vec(py, chunk_y))?;
        chunks.set_item("size", chunk_size)?;
        dict.set_item("chunks", chunks)?;

        let species = PyDict::new(py);
        species.set_item(
            "species_id",
            self.state
                .species
                .iter()
                .map(|item| item.species_id)
                .collect::<Vec<_>>(),
        )?;
        species.set_item(
            "population",
            self.state
                .species
                .iter()
                .map(|item| item.population)
                .collect::<Vec<_>>(),
        )?;
        species.set_item(
            "births",
            self.state
                .species
                .iter()
                .map(|item| item.births)
                .collect::<Vec<_>>(),
        )?;
        species.set_item(
            "deaths",
            self.state
                .species
                .iter()
                .map(|item| item.deaths)
                .collect::<Vec<_>>(),
        )?;
        species.set_item(
            "created_tick",
            self.state
                .species
                .iter()
                .map(|item| item.created_tick)
                .collect::<Vec<_>>(),
        )?;
        species.set_item(
            "origin",
            self.state
                .species
                .iter()
                .map(|item| match item.origin {
                    0 => "founder",
                    1 => "mutation",
                    _ => "sexual",
                })
                .collect::<Vec<_>>(),
        )?;
        species.set_item(
            "color",
            self.state
                .species
                .iter()
                .map(|item| (item.color[0], item.color[1], item.color[2]))
                .collect::<Vec<_>>(),
        )?;
        dict.set_item("species", species)?;
        dict.set_item(
            "molecule_colors",
            self.state
                .catalog
                .molecules
                .iter()
                .map(|item| (item.color[0], item.color[1], item.color[2]))
                .collect::<Vec<_>>(),
        )?;
        dict.set_item("action_names", ACTION_NAMES.to_vec())?;
        let last_action_names: Vec<String> = (0..=102u8)
            .map(entities::last_action::name)
            .map(str::to_string)
            .collect();
        dict.set_item("last_action_names", last_action_names)?;
        Ok(dict)
    }

    /// Full state dump for the recorder / GUI.
    fn snapshot<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let dict = PyDict::new(py);
        add_behavior_metadata(
            py,
            &dict,
            &self.state.config,
            self.state.effective_worker_count(),
        )?;
        dict.set_item("tick", self.state.tick)?;
        dict.set_item("population", self.state.population())?;

        // organisms: numpy columns
        use numpy::PyArray1;
        let mut ids: Vec<u32> = Vec::new();
        let mut species_ids: Vec<u32> = Vec::new();
        let mut xs: Vec<i64> = Vec::new();
        let mut ys: Vec<i64> = Vec::new();
        let mut body_mass: Vec<i64> = Vec::new();
        let mut energy: Vec<f64> = Vec::new();
        let mut mana: Vec<f64> = Vec::new();
        let mut integrity: Vec<f64> = Vec::new();
        let mut alive: Vec<bool> = Vec::new();
        let mut last_action: Vec<u8> = Vec::new();
        let mut generation: Vec<u32> = Vec::new();
        let mut lineage: Vec<u32> = Vec::new();
        let mut birth_tick: Vec<u32> = Vec::new();
        let mut toxin: Vec<f64> = Vec::new();
        let mut colony: Vec<i64> = Vec::new();
        let mut decision_count: Vec<u32> = Vec::new();
        let mut offspring_count: Vec<u32> = Vec::new();
        let mut brain_energy_spent: Vec<f64> = Vec::new();
        let mut hidden_expression_mean: Vec<f64> = Vec::new();
        let mut recurrent_expression_mean: Vec<f64> = Vec::new();
        let mut retention_mean: Vec<f64> = Vec::new();
        let mut hidden_expression_genetic_mean: Vec<f64> = Vec::new();
        let mut recurrent_expression_genetic_mean: Vec<f64> = Vec::new();
        let mut recurrent_expression_genetic_spread_mean: Vec<f64> = Vec::new();
        let mut retention_genetic_mean: Vec<f64> = Vec::new();
        let mut neural_numerical_errors: Vec<u32> = Vec::new();
        let mut neural_state: Vec<f32> = Vec::new();
        let mut module_offsets: Vec<u32> = vec![0];
        let mut module_primitives: Vec<u8> = Vec::new();
        let mut module_substrates: Vec<u16> = Vec::new();
        let mut module_compartment_tags: Vec<u8> = Vec::new();
        let mut module_expressions: Vec<f32> = Vec::new();
        let mut internal_guest_count: Vec<u32> = Vec::new();
        let mut guest_offsets: Vec<u32> = vec![0];
        let mut guest_source_ids: Vec<u32> = Vec::new();
        let mut guest_genome_ids: Vec<u32> = Vec::new();
        let mut guest_species_ids: Vec<u32> = Vec::new();
        let mut guest_ages: Vec<u32> = Vec::new();
        let mut guest_energy: Vec<f64> = Vec::new();
        let mut guest_matter_units: Vec<i64> = Vec::new();
        let mut bond_degree: Vec<u32> = Vec::new();
        let mut component_id: Vec<u32> = Vec::new();
        let mut component_size: Vec<u32> = Vec::new();
        let (component_roots, component_sizes) = self.state.bond_component_facts();
        let mut bond_degrees: FxHashMap<u32, u32> = FxHashMap::default();
        for bond in self.state.bonds.values() {
            *bond_degrees.entry(bond.left).or_default() += 1;
            *bond_degrees.entry(bond.right).or_default() += 1;
        }
        for oid in self.state.living_ordered.iter().copied() {
            let o = self.state.organism(oid);
            ids.push(o.organism_id);
            species_ids.push(o.species_id);
            xs.push(o.position.0);
            ys.push(o.position.1);
            body_mass.push(o.peek_structural_mass(&self.state.catalog));
            energy.push(o.chemical_energy());
            mana.push(o.mana);
            integrity.push(o.integrity);
            alive.push(o.alive);
            last_action.push(o.last_action);
            generation.push(o.generation);
            lineage.push(o.lineage_id);
            birth_tick.push(o.birth_tick);
            toxin.push(o.toxin_load);
            colony.push(o.colony_id.map(|c| c as i64).unwrap_or(-1));
            decision_count.push(o.decision_count);
            offspring_count.push(o.offspring_count);
            brain_energy_spent.push(o.brain_energy_spent);
            let recurrent = o.phenotype.recurrent_policy.as_ref();
            hidden_expression_mean
                .push(recurrent.map_or(0.0, |policy| policy.hidden_expression_mean()));
            recurrent_expression_mean
                .push(recurrent.map_or(0.0, |policy| policy.recurrent_expression_mean()));
            retention_mean.push(recurrent.map_or(0.0, |policy| policy.retention_mean()));
            let recurrent_genome = o.genome.recurrent_policy.as_ref();
            hidden_expression_genetic_mean.push(recurrent_genome.map_or(0.0, |policy| {
                policy
                    .hidden_expression
                    .iter()
                    .map(|gene| gene.center as f64)
                    .sum::<f64>()
                    / behavior::neural::HIDDEN_COUNT as f64
            }));
            recurrent_expression_genetic_mean.push(recurrent_genome.map_or(0.0, |policy| {
                policy
                    .recurrent_expression
                    .iter()
                    .map(|gene| gene.center as f64)
                    .sum::<f64>()
                    / behavior::neural::HIDDEN_COUNT as f64
            }));
            recurrent_expression_genetic_spread_mean.push(recurrent_genome.map_or(0.0, |policy| {
                policy
                    .recurrent_expression
                    .iter()
                    .map(|gene| gene.spread as f64)
                    .sum::<f64>()
                    / behavior::neural::HIDDEN_COUNT as f64
            }));
            retention_genetic_mean.push(recurrent_genome.map_or(0.0, |policy| {
                policy
                    .retention
                    .iter()
                    .map(|gene| gene.center as f64)
                    .sum::<f64>()
                    / behavior::neural::HIDDEN_COUNT as f64
            }));
            neural_numerical_errors.push(o.neural_numerical_errors);
            neural_state.extend(o.neural_state.values);
            if let Some(emergence) = &o.genome.emergence {
                for module in &emergence.modules {
                    module_primitives.push(module.primitive as u8);
                    module_substrates.push(module.substrate);
                    module_compartment_tags.push(module.compartment_tag);
                }
            }
            if let Some(cellular) = &o.cellular {
                module_expressions.extend(&cellular.expression);
                internal_guest_count.push(cellular.guests.len() as u32);
                for guest in &cellular.guests {
                    guest_source_ids.push(guest.source_organism_id);
                    guest_genome_ids.push(guest.genome_id);
                    guest_species_ids.push(guest.species_id);
                    guest_ages.push(guest.age);
                    guest_energy.push(inventory_energy(&guest.inventory) + guest.free_energy);
                    guest_matter_units.push(inventory_count(&guest.inventory));
                }
            } else {
                internal_guest_count.push(0);
            }
            guest_offsets.push(guest_source_ids.len() as u32);
            module_offsets.push(module_primitives.len() as u32);
            bond_degree.push(bond_degrees.get(&oid).copied().unwrap_or(0));
            let root = component_roots[oid as usize];
            component_id.push(root);
            component_size.push(component_sizes.get(&root).copied().unwrap_or(1));
        }
        let organisms = PyDict::new(py);
        organisms.set_item("id", PyArray1::from_vec(py, ids))?;
        organisms.set_item("species_id", PyArray1::from_vec(py, species_ids))?;
        organisms.set_item("x", PyArray1::from_vec(py, xs))?;
        organisms.set_item("y", PyArray1::from_vec(py, ys))?;
        organisms.set_item("body_mass", PyArray1::from_vec(py, body_mass))?;
        organisms.set_item("energy", PyArray1::from_vec(py, energy))?;
        organisms.set_item("mana", PyArray1::from_vec(py, mana))?;
        organisms.set_item("integrity", PyArray1::from_vec(py, integrity))?;
        organisms.set_item("alive", PyArray1::from_vec(py, alive))?;
        organisms.set_item("last_action", PyArray1::from_vec(py, last_action))?;
        organisms.set_item("generation", PyArray1::from_vec(py, generation))?;
        organisms.set_item("lineage_id", PyArray1::from_vec(py, lineage))?;
        organisms.set_item("birth_tick", PyArray1::from_vec(py, birth_tick))?;
        organisms.set_item("toxin_load", PyArray1::from_vec(py, toxin))?;
        organisms.set_item("colony_id", PyArray1::from_vec(py, colony))?;
        organisms.set_item("decision_count", PyArray1::from_vec(py, decision_count))?;
        organisms.set_item("offspring_count", PyArray1::from_vec(py, offspring_count))?;
        organisms.set_item(
            "brain_energy_spent",
            PyArray1::from_vec(py, brain_energy_spent),
        )?;
        organisms.set_item(
            "hidden_expression_mean",
            PyArray1::from_vec(py, hidden_expression_mean),
        )?;
        organisms.set_item(
            "recurrent_expression_mean",
            PyArray1::from_vec(py, recurrent_expression_mean),
        )?;
        organisms.set_item("retention_mean", PyArray1::from_vec(py, retention_mean))?;
        organisms.set_item(
            "hidden_expression_genetic_mean",
            PyArray1::from_vec(py, hidden_expression_genetic_mean),
        )?;
        organisms.set_item(
            "recurrent_expression_genetic_mean",
            PyArray1::from_vec(py, recurrent_expression_genetic_mean),
        )?;
        organisms.set_item(
            "recurrent_expression_genetic_spread_mean",
            PyArray1::from_vec(py, recurrent_expression_genetic_spread_mean),
        )?;
        organisms.set_item(
            "retention_genetic_mean",
            PyArray1::from_vec(py, retention_genetic_mean),
        )?;
        organisms.set_item(
            "neural_numerical_errors",
            PyArray1::from_vec(py, neural_numerical_errors),
        )?;
        organisms.set_item("neural_state", PyArray1::from_vec(py, neural_state))?;
        organisms.set_item("module_offsets", PyArray1::from_vec(py, module_offsets))?;
        organisms.set_item(
            "module_primitives",
            PyArray1::from_vec(py, module_primitives),
        )?;
        organisms.set_item(
            "module_substrates",
            PyArray1::from_vec(py, module_substrates),
        )?;
        organisms.set_item(
            "module_compartment_tags",
            PyArray1::from_vec(py, module_compartment_tags),
        )?;
        organisms.set_item(
            "module_expressions",
            PyArray1::from_vec(py, module_expressions),
        )?;
        organisms.set_item(
            "internal_guest_count",
            PyArray1::from_vec(py, internal_guest_count),
        )?;
        organisms.set_item("guest_offsets", PyArray1::from_vec(py, guest_offsets))?;
        organisms.set_item(
            "guest_source_organism_ids",
            PyArray1::from_vec(py, guest_source_ids),
        )?;
        organisms.set_item("guest_genome_ids", PyArray1::from_vec(py, guest_genome_ids))?;
        organisms.set_item(
            "guest_species_ids",
            PyArray1::from_vec(py, guest_species_ids),
        )?;
        organisms.set_item("guest_ages", PyArray1::from_vec(py, guest_ages))?;
        organisms.set_item("guest_energy", PyArray1::from_vec(py, guest_energy))?;
        organisms.set_item(
            "guest_matter_units",
            PyArray1::from_vec(py, guest_matter_units),
        )?;
        organisms.set_item("bond_degree", PyArray1::from_vec(py, bond_degree))?;
        organisms.set_item("component_id", PyArray1::from_vec(py, component_id))?;
        organisms.set_item("component_size", PyArray1::from_vec(py, component_size))?;
        dict.set_item("organisms", organisms)?;

        let bonds = PyDict::new(py);
        let mut bond_left = Vec::new();
        let mut bond_right = Vec::new();
        let mut bond_formed = Vec::new();
        let mut bond_strength = Vec::new();
        let mut ordered_bonds: Vec<((u32, u32), Bond)> = self
            .state
            .bonds
            .iter()
            .map(|(&edge, &bond)| (edge, bond))
            .collect();
        ordered_bonds.sort_by_key(|(edge, _)| *edge);
        for (_, bond) in ordered_bonds {
            bond_left.push(bond.left);
            bond_right.push(bond.right);
            bond_formed.push(bond.formed_tick);
            bond_strength.push(bond.strength);
        }
        bonds.set_item("left_id", PyArray1::from_vec(py, bond_left))?;
        bonds.set_item("right_id", PyArray1::from_vec(py, bond_right))?;
        bonds.set_item("formed_tick", PyArray1::from_vec(py, bond_formed))?;
        bonds.set_item("strength", PyArray1::from_vec(py, bond_strength))?;
        dict.set_item("bonds", bonds)?;

        // species table
        let species_dict = PyDict::new(py);
        let mut s_ids: Vec<u32> = Vec::new();
        let mut s_pop: Vec<i64> = Vec::new();
        let mut s_births: Vec<i64> = Vec::new();
        let mut s_deaths: Vec<i64> = Vec::new();
        let mut s_created: Vec<u32> = Vec::new();
        let mut s_origin: Vec<String> = Vec::new();
        let mut s_color: Vec<(u8, u8, u8)> = Vec::new();
        for species in &self.state.species {
            s_ids.push(species.species_id);
            s_pop.push(species.population);
            s_births.push(species.births);
            s_deaths.push(species.deaths);
            s_created.push(species.created_tick);
            s_origin.push(
                match species.origin {
                    0 => "founder",
                    1 => "mutation",
                    _ => "sexual",
                }
                .to_string(),
            );
            s_color.push((species.color[0], species.color[1], species.color[2]));
        }
        species_dict.set_item("species_id", s_ids)?;
        species_dict.set_item("population", s_pop)?;
        species_dict.set_item("births", s_births)?;
        species_dict.set_item("deaths", s_deaths)?;
        species_dict.set_item("created_tick", s_created)?;
        species_dict.set_item("origin", s_origin)?;
        species_dict.set_item("color", s_color)?;
        dict.set_item("species", species_dict)?;

        // deposits: flattened numpy columns
        let mut d_x: Vec<i64> = Vec::new();
        let mut d_y: Vec<i64> = Vec::new();
        let mut d_mol: Vec<u16> = Vec::new();
        let mut d_count: Vec<i64> = Vec::new();
        let mut d_energy: Vec<f64> = Vec::new();
        let mut positions: Vec<&Position> = self.state.world.deposits.keys().collect();
        positions.sort();
        for position in positions {
            for batch in &self.state.world.deposits[position] {
                d_x.push(position.0);
                d_y.push(position.1);
                d_mol.push(batch.molecule_id);
                d_count.push(batch.count);
                d_energy.push(batch.energy);
            }
        }
        let deposits = PyDict::new(py);
        deposits.set_item("x", PyArray1::from_vec(py, d_x))?;
        deposits.set_item("y", PyArray1::from_vec(py, d_y))?;
        deposits.set_item("molecule_id", PyArray1::from_vec(py, d_mol))?;
        deposits.set_item("count", PyArray1::from_vec(py, d_count))?;
        deposits.set_item("energy", PyArray1::from_vec(py, d_energy))?;
        dict.set_item("deposits", deposits)?;

        let biodeposits = PyDict::new(py);
        let mut biodeposit_entries: Vec<(Position, f64)> = self
            .state
            .world
            .biodeposits
            .iter()
            .map(|(&position, &density)| (position, density * self.state.world.biodeposit_scale))
            .collect();
        biodeposit_entries.sort_unstable_by_key(|entry| entry.0);
        biodeposits.set_item(
            "x",
            PyArray1::from_vec(
                py,
                biodeposit_entries.iter().map(|entry| entry.0 .0).collect(),
            ),
        )?;
        biodeposits.set_item(
            "y",
            PyArray1::from_vec(
                py,
                biodeposit_entries.iter().map(|entry| entry.0 .1).collect(),
            ),
        )?;
        biodeposits.set_item(
            "density",
            PyArray1::from_vec(py, biodeposit_entries.iter().map(|entry| entry.1).collect()),
        )?;
        dict.set_item("biodeposits", biodeposits)?;

        let byproducts = PyDict::new(py);
        let mut byproduct_entries: Vec<(Position, [f64; 2])> = self
            .state
            .world
            .byproducts
            .iter()
            .map(|(&position, &value)| {
                (
                    position,
                    [
                        value[0] * self.state.world.byproduct_scale[0],
                        value[1] * self.state.world.byproduct_scale[1],
                    ],
                )
            })
            .collect();
        byproduct_entries.sort_unstable_by_key(|entry| entry.0);
        byproducts.set_item(
            "x",
            PyArray1::from_vec(
                py,
                byproduct_entries.iter().map(|entry| entry.0 .0).collect(),
            ),
        )?;
        byproducts.set_item(
            "y",
            PyArray1::from_vec(
                py,
                byproduct_entries.iter().map(|entry| entry.0 .1).collect(),
            ),
        )?;
        byproducts.set_item(
            "catalyst",
            PyArray1::from_vec(
                py,
                byproduct_entries.iter().map(|entry| entry.1[0]).collect(),
            ),
        )?;
        byproducts.set_item(
            "toxin",
            PyArray1::from_vec(
                py,
                byproduct_entries.iter().map(|entry| entry.1[1]).collect(),
            ),
        )?;
        dict.set_item("byproducts", byproducts)?;

        dict.set_item("stats", self.stats_dict(py)?)?;
        dict.set_item("season", self.season_state(py, 0)?)?;
        dict.set_item("action_names", ACTION_NAMES.to_vec())?;
        let last_action_names: Vec<String> = (0..=102u8)
            .map(entities::last_action::name)
            .map(str::to_string)
            .collect();
        dict.set_item("last_action_names", last_action_names)?;
        Ok(dict)
    }

    /// Return the current molecule catalog needed to interpret composition rows.
    ///
    /// Molecule IDs are run-local, so a recorder must persist their elemental
    /// compositions alongside any organism inventory observations rather than
    /// asking consumers to regenerate the catalog from the seed.
    fn molecule_catalog<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let dict = PyDict::new(py);
        dict.set_item("schema_version", 1)?;
        dict.set_item("element_count", self.state.catalog.elements.len())?;
        dict.set_item("molecule_count", self.state.catalog.molecules.len())?;

        let elements = PyList::empty(py);
        for (element_id, element) in self.state.catalog.elements.iter().enumerate() {
            let item = PyDict::new(py);
            item.set_item("element_id", element_id)?;
            item.set_item("atomic_mass", element.atomic_mass)?;
            item.set_item("energy_contribution", element.energy_contribution)?;
            elements.append(item)?;
        }
        dict.set_item("elements", elements)?;

        let molecules = PyList::empty(py);
        for molecule in &self.state.catalog.molecules {
            let item = PyDict::new(py);
            item.set_item("molecule_id", molecule.molecule_id)?;
            let composition = PyList::empty(py);
            for &amount in &molecule.composition {
                composition.append(amount)?;
            }
            item.set_item("composition", composition)?;
            item.set_item("mass", molecule.mass)?;
            item.set_item("energy_capacity", molecule.energy_capacity)?;
            molecules.append(item)?;
        }
        dict.set_item("molecules", molecules)?;
        Ok(dict)
    }

    /// Return sparse molecule batches for every living organism.
    ///
    /// Each row represents one non-empty molecule batch in one compartment:
    /// 0 = body, 1 = gut, 2 = waste. The simulation does not allocate this
    /// representation during normal stepping; it is built only when an
    /// observer explicitly requests a composition snapshot.
    fn organism_composition<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        use numpy::PyArray1;

        let mut organism_ids: Vec<u32> = Vec::new();
        let mut compartments: Vec<u8> = Vec::new();
        let mut molecule_ids: Vec<u16> = Vec::new();
        let mut counts: Vec<i64> = Vec::new();
        let mut energies: Vec<f64> = Vec::new();
        for organism_id in self.state.living_ordered.iter().copied() {
            let organism = self.state.organism(organism_id);
            for (compartment, inventory) in [
                (0u8, &organism.body),
                (1u8, &organism.gut),
                (2u8, &organism.waste),
            ] {
                for batch in inventory {
                    if batch.count <= 0 {
                        continue;
                    }
                    organism_ids.push(organism_id);
                    compartments.push(compartment);
                    molecule_ids.push(batch.molecule_id);
                    counts.push(batch.count);
                    energies.push(batch.energy);
                }
            }
        }

        let dict = PyDict::new(py);
        dict.set_item("schema_version", 1)?;
        dict.set_item("tick", self.state.tick)?;
        dict.set_item("organism_id", PyArray1::from_vec(py, organism_ids))?;
        dict.set_item("compartment", PyArray1::from_vec(py, compartments))?;
        dict.set_item("molecule_id", PyArray1::from_vec(py, molecule_ids))?;
        dict.set_item("count", PyArray1::from_vec(py, counts))?;
        dict.set_item("chemical_energy", PyArray1::from_vec(py, energies))?;
        Ok(dict)
    }

    /// Observation-only compression diagnostics for event/cohort engine design.
    fn compressibility_metrics<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let metrics = self.state.compressibility_metrics();
        let dict = PyDict::new(py);
        dict.set_item("tick", self.state.tick)?;
        dict.set_item("population", metrics.population)?;
        dict.set_item("exact_policy_keys", metrics.exact_policy_keys)?;
        dict.set_item("lineage_count", metrics.lineage_count)?;
        dict.set_item("species_count", metrics.species_count)?;
        dict.set_item("rare_lineage_organisms", metrics.rare_lineage_organisms)?;
        dict.set_item("rare_species_organisms", metrics.rare_species_organisms)?;
        dict.set_item("novel_organisms", metrics.novel_organisms)?;
        dict.set_item("physiology_critical", metrics.physiology_critical)?;
        dict.set_item("low_reserve", metrics.low_reserve)?;
        dict.set_item("critical_reserve", metrics.critical_reserve)?;
        dict.set_item("near_integrity_death", metrics.near_integrity_death)?;
        dict.set_item("near_debt_death", metrics.near_debt_death)?;
        dict.set_item("near_toxin_threshold", metrics.near_toxin_threshold)?;
        dict.set_item("post_lifespan", metrics.post_lifespan)?;
        dict.set_item("active_status", metrics.active_status)?;
        dict.set_item("action_due_now", metrics.action_due_now)?;
        dict.set_item("action_due_within_8", metrics.action_due_within_8)?;
        dict.set_item("nonempty_gut", metrics.nonempty_gut)?;
        dict.set_item("colony_members", metrics.colony_members)?;
        dict.set_item("organism_tiles_8", metrics.organism_tiles_8)?;
        dict.set_item("organism_tiles_16", metrics.organism_tiles_16)?;
        dict.set_item("organism_tiles_32", metrics.organism_tiles_32)?;
        dict.set_item("generated_chunks", metrics.generated_chunks)?;
        dict.set_item("active_heat_chunks", metrics.active_heat_chunks)?;
        dict.set_item("active_heat_cells", metrics.active_heat_cells)?;
        dict.set_item("active_deposit_positions", metrics.active_deposit_positions)?;
        dict.set_item("active_deposit_batches", metrics.active_deposit_batches)?;
        dict.set_item("occupied_cells", metrics.occupied_cells)?;

        for (name, summary) in [
            ("lineage_safe", metrics.lineage_safe),
            ("species_safe", metrics.species_safe),
            ("trait_only", metrics.trait_only),
        ] {
            let item = PyDict::new(py);
            item.set_item("protected", summary.protected)?;
            item.set_item("classes", summary.classes)?;
            item.set_item("representatives", summary.representatives)?;
            item.set_item("represented_work", summary.represented_work)?;
            item.set_item(
                "represented_fraction",
                summary.represented_work as f64 / metrics.population.max(1) as f64,
            )?;
            dict.set_item(name, item)?;
        }
        Ok(dict)
    }

    #[pyo3(signature = (after_event=0))]
    fn season_state<'py>(
        &self,
        py: Python<'py>,
        after_event: usize,
    ) -> PyResult<Bound<'py, PyDict>> {
        let season = &self.state.seasons;
        let dict = PyDict::new(py);
        dict.set_item("schema_version", 1)?;
        dict.set_item("enabled", season.enabled)?;
        dict.set_item("index", season.index)?;
        dict.set_item("started_tick", season.started_tick)?;
        dict.set_item("transition_end_tick", season.transition_end_tick)?;
        dict.set_item(
            "next_season_tick",
            season.enabled.then_some(season.next_season_tick),
        )?;
        dict.set_item(
            "transition_progress",
            season.transition_progress(self.state.tick),
        )?;
        dict.set_item(
            "resource_charge_multiplier",
            season.current.resource_charge_multiplier,
        )?;
        dict.set_item(
            "decomposition_multiplier",
            season.current.decomposition_multiplier,
        )?;
        dict.set_item(
            "molecule_charge_affinities",
            season.current.molecule_charge_affinities.clone(),
        )?;
        dict.set_item(
            "from_resource_charge_multiplier",
            season.from.resource_charge_multiplier,
        )?;
        dict.set_item(
            "from_decomposition_multiplier",
            season.from.decomposition_multiplier,
        )?;
        dict.set_item(
            "from_molecule_charge_affinities",
            season.from.molecule_charge_affinities.clone(),
        )?;
        dict.set_item(
            "target_resource_charge_multiplier",
            season.target.resource_charge_multiplier,
        )?;
        dict.set_item(
            "target_decomposition_multiplier",
            season.target.decomposition_multiplier,
        )?;
        dict.set_item(
            "target_molecule_charge_affinities",
            season.target.molecule_charge_affinities.clone(),
        )?;
        let events = PyList::empty(py);
        for event in season.events.iter().skip(after_event) {
            events.append(season_event_dict(py, event)?)?;
        }
        dict.set_item("events", events)?;
        dict.set_item("event_count", season.events.len())?;
        Ok(dict)
    }

    fn stats_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let dict = PyDict::new(py);
        let s = &self.state.stats;
        dict.set_item("births", s.births)?;
        dict.set_item("deaths", s.deaths)?;
        dict.set_item("reproduction_attempts", s.reproduction_attempts)?;
        dict.set_item(
            "reproduction_resource_blocks",
            s.reproduction_resource_blocks,
        )?;
        dict.set_item(
            "reproduction_mate_readiness_blocks",
            s.reproduction_mate_readiness_blocks,
        )?;
        dict.set_item("reproduction_energy_blocks", s.reproduction_energy_blocks)?;
        dict.set_item(
            "reproduction_body_matter_blocks",
            s.reproduction_body_matter_blocks,
        )?;
        dict.set_item(
            "reproduction_probability_failures",
            s.reproduction_probability_failures,
        )?;
        dict.set_item(
            "reproduction_placement_failures",
            s.reproduction_placement_failures,
        )?;
        dict.set_item("failed_reproductions", s.failed_reproductions)?;
        dict.set_item("successful_reproductions", s.successful_reproductions)?;
        dict.set_item("asexual_reproduction_events", s.asexual_reproduction_events)?;
        dict.set_item("sexual_reproduction_events", s.sexual_reproduction_events)?;
        dict.set_item("attacks", s.attacks)?;
        dict.set_item("magic_casts", s.magic_casts)?;
        dict.set_item("alliances", s.alliances)?;
        dict.set_item("colonies", s.colonies)?;
        dict.set_item("brain_energy_spent", s.brain_energy_spent)?;
        dict.set_item("hidden_brain_energy_spent", s.hidden_brain_energy_spent)?;
        dict.set_item(
            "recurrent_brain_energy_spent",
            s.recurrent_brain_energy_spent,
        )?;
        dict.set_item("neural_numerical_errors", s.neural_numerical_errors)?;
        dict.set_item("memory_probe_decisions", s.memory_probe_decisions)?;
        dict.set_item("memory_probe_state_l1_sum", s.memory_probe_state_l1_sum)?;
        dict.set_item("memory_probe_argmax_changes", s.memory_probe_argmax_changes)?;
        dict.set_item(
            "memory_probe_ambiguous_food_events",
            s.memory_probe_ambiguous_food_events,
        )?;
        dict.set_item(
            "memory_probe_ambiguous_argmax_changes",
            s.memory_probe_ambiguous_argmax_changes,
        )?;
        dict.set_item(
            "memory_probe_stateful_return_choices",
            s.memory_probe_stateful_return_choices,
        )?;
        dict.set_item(
            "memory_probe_zero_state_return_choices",
            s.memory_probe_zero_state_return_choices,
        )?;
        dict.set_item("v2_intent_counts", s.v2_intent_counts.to_vec())?;
        dict.set_item("v2_intent_failures", s.v2_intent_failures)?;
        dict.set_item("audit_error", s.audit_error)?;
        dict.set_item(
            "dynamic_chemistry",
            self.state.config.dynamic_chemistry_enabled,
        )?;
        dict.set_item(
            "dynamic_chemistry_enabled",
            self.state.config.dynamic_chemistry_enabled,
        )?;
        dict.set_item(
            "environmental_reaction_rules",
            self.state.reaction_rules.len(),
        )?;
        dict.set_item("environmental_reactions", s.environmental_reactions)?;
        dict.set_item("byproduct_emissions", s.byproduct_emissions)?;
        dict.set_item("total_organisms_ever", self.state.next_organism_id - 1)?;
        let max_generation = self
            .state
            .organisms
            .iter()
            .map(|organism| organism.generation)
            .max()
            .unwrap_or(0);
        dict.set_item("max_generation", max_generation)?;
        dict.set_item("dense_living_slots", self.state.organisms.len())?;
        dict.set_item("dead_records", self.state.dead_records.len())?;
        dict.set_item(
            "genome_distance_cache_entries",
            self.state.genome_distances.len(),
        )?;
        dict.set_item("generated_chunks", self.state.world.chunks.len())?;
        dict.set_item("deposit_positions", self.state.world.deposits.len())?;
        dict.set_item("occupied_cells", self.state.world.occupied_cells)?;
        dict.set_item(
            "species_ids",
            self.state
                .species
                .iter()
                .map(|species| species.species_id)
                .collect::<Vec<_>>(),
        )?;
        dict.set_item(
            "species_populations",
            self.state
                .species
                .iter()
                .map(|species| species.population)
                .collect::<Vec<_>>(),
        )?;
        dict.set_item("seasons_enabled", self.state.seasons.enabled)?;
        dict.set_item("season_index", self.state.seasons.index)?;
        dict.set_item(
            "season_transition_progress",
            self.state.seasons.transition_progress(self.state.tick),
        )?;
        dict.set_item(
            "season_resource_charge_multiplier",
            self.state.seasons.current.resource_charge_multiplier,
        )?;
        dict.set_item(
            "season_decomposition_multiplier",
            self.state.seasons.current.decomposition_multiplier,
        )?;
        let emergence = self.state.emergence_metrics();
        dict.set_item(
            "cellular_affordances_enabled",
            self.state.config.cellular_emergence_enabled,
        )?;
        dict.set_item("module_instances", emergence.module_instances)?;
        dict.set_item(
            "module_primitive_counts",
            emergence.module_primitive_counts.to_vec(),
        )?;
        dict.set_item(
            "compartment_tag_counts",
            emergence.compartment_tag_counts.to_vec(),
        )?;
        dict.set_item(
            "expressed_module_instances",
            emergence.expressed_module_instances,
        )?;
        dict.set_item("compartment_tags_used", emergence.compartment_tags_used)?;
        dict.set_item("physical_bonds", emergence.physical_bonds)?;
        dict.set_item("bonded_cells", emergence.bonded_cells)?;
        dict.set_item("bond_components", emergence.bond_components)?;
        dict.set_item("largest_bond_component", emergence.largest_bond_component)?;
        dict.set_item("internal_guests", emergence.internal_guests)?;
        dict.set_item(
            "regulatory_expression_variance",
            emergence.expression_variance,
        )?;
        dict.set_item(
            "bond_formations",
            self.state.emergence_stats.bond_formations,
        )?;
        dict.set_item("bond_breaks", self.state.emergence_stats.bond_breaks)?;
        dict.set_item(
            "cell_energy_exchanges",
            self.state.emergence_stats.energy_exchanges,
        )?;
        dict.set_item(
            "internalizations",
            self.state.emergence_stats.internalizations,
        )?;
        dict.set_item(
            "guest_replications",
            self.state.emergence_stats.guest_replications,
        )?;
        dict.set_item("guest_losses", self.state.emergence_stats.guest_losses)?;
        dict.set_item(
            "guest_energy_demand",
            self.state.emergence_stats.guest_energy_demand,
        )?;
        dict.set_item(
            "guest_energy_exchange",
            self.state.emergence_stats.guest_energy_exchange,
        )?;
        dict.set_item(
            "guest_net_energy",
            self.state.emergence_stats.guest_energy_exchange
                - self.state.emergence_stats.guest_energy_demand,
        )?;
        dict.set_item(
            "coordinated_components_enabled",
            self.state.coordinated_components_enabled(),
        )?;
        dict.set_item(
            "component_actions",
            self.state.emergence_stats.component_actions,
        )?;
        dict.set_item(
            "component_moves",
            self.state.emergence_stats.component_moves,
        )?;
        dict.set_item(
            "component_propagules",
            self.state.emergence_stats.propagules,
        )?;
        dict.set_item(
            "propagated_cells",
            self.state.emergence_stats.propagated_cells,
        )?;
        dict.set_item("biodeposits_enabled", self.state.config.biodeposits_enabled)?;
        dict.set_item("biodeposit_positions", self.state.world.biodeposits.len())?;
        dict.set_item(
            "biodeposit_total_density",
            self.state.world.total_biodeposit_density(),
        )?;
        dict.set_item(
            "biodeposit_max_density",
            self.state
                .world
                .biodeposits
                .values()
                .copied()
                .fold(0.0f64, f64::max)
                * self.state.world.biodeposit_scale,
        )?;
        dict.set_item("byproduct_positions", self.state.world.byproducts.len())?;
        let (byproduct_catalyst, byproduct_toxin) = self.state.world.total_byproducts();
        dict.set_item("byproduct_total_catalyst", byproduct_catalyst)?;
        dict.set_item("byproduct_total_toxin", byproduct_toxin)?;
        let chemistry = self.state.chemistry_metrics();
        dict.set_item("chemistry_regime_mean", chemistry.regime_mean)?;
        dict.set_item("chemistry_regime_variance", chemistry.regime_variance)?;
        dict.set_item(
            "chemistry_species_association",
            chemistry.species_association,
        )?;
        dict.set_item("chemistry_guest_regime_delta", chemistry.guest_regime_delta)?;
        dict.set_item("chemistry_guest_hosts", chemistry.guest_hosts)?;
        Ok(dict)
    }

    /// Conservation audit: element totals + energy error.
    fn audit<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let (element_error, energy_error) =
            self.state.audit(false).map_err(PyRuntimeError::new_err)?;
        let dict = PyDict::new(py);
        let elements_ok = element_error.iter().all(|&e| e == 0);
        let accounting_scale =
            self.state.initial_energy.abs() + self.state.world.generated_energy.abs();
        let tolerance =
            energy_tolerance(self.state.initial_energy, self.state.world.generated_energy);
        dict.set_item("elements_ok", elements_ok)?;
        dict.set_item("element_deltas", element_error)?;
        dict.set_item("element_totals", self.state.dynamic_element_totals())?;
        dict.set_item(
            "generated_elements",
            self.state.world.generated_elements.clone(),
        )?;
        dict.set_item("energy_total", self.state.total_energy())?;
        dict.set_item("generated_energy", self.state.world.generated_energy)?;
        dict.set_item("initial_energy", self.state.initial_energy)?;
        dict.set_item("energy_error", energy_error)?;
        dict.set_item("energy_accounting_scale", accounting_scale)?;
        dict.set_item(
            "energy_relative_error",
            energy_error.abs() / accounting_scale.max(f64::MIN_POSITIVE),
        )?;
        dict.set_item("energy_tolerance", tolerance)?;
        dict.set_item("energy_ok", energy_error.abs() <= tolerance)?;
        Ok(dict)
    }

    /// FNV-1a state digest for determinism tests.
    fn digest(&self) -> u64 {
        self.state.digest()
    }
}

fn runtime_config_field(name: &str) -> bool {
    matches!(
        name,
        "heat_diffusion"
            | "mana_decay"
            | "primary_production_rate"
            | "deposit_production_rate"
            | "decomposition_rate"
            | "mutation_multiplier"
            | "reaction_rate"
            | "maintenance_cost_multiplier"
            | "byproduct_decay_rate"
            | "chemistry_coupling"
            | "guest_niche_coupling"
            | "reference_move_cost"
            | "reference_attack_cost"
            | "attack_damage_multiplier"
            | "reference_ingest_cost"
            | "reference_reproduction_cost"
            | "reproduction_cost_multiplier"
            | "reproduction_cooldown_multiplier"
            | "maturity_age_multiplier"
            | "reproduction_action_bonus"
            | "asexual_probability_floor"
            | "sexual_probability_floor_enabled"
            | "sexual_probability_floor"
            | "sight_cost_per_cell"
            | "failed_move_cost_fraction"
            | "species_distance_threshold"
            | "prey_compatibility_threshold"
            | "alliance_probability"
            | "colony_bonus_cap"
            | "sexual_colony_max"
            | "asexual_colony_min"
            | "biodeposits_enabled"
            | "biodeposit_decay_rate"
            | "biodeposit_movement_resistance"
            | "biodeposit_cover_strength"
            | "biodeposit_concealment"
            | "max_sight"
            | "audit_every"
    )
}

macro_rules! parse_int {
    ($dict:expr, $name:literal, $field:expr) => {
        if let Some(v) = $dict.get_item($name)? {
            $field = v.extract()?;
        }
    };
}

fn parse_config(dict: &Bound<PyDict>, config: &mut SimConfig) -> PyResult<()> {
    parse_int!(dict, "seed", config.seed);
    if let Some(value) = dict.get_item("behavior_model")? {
        let name: String = value.extract()?;
        config.behavior_model = name.parse().map_err(PyValueError::new_err)?;
    }
    if let Some(value) = dict.get_item("scheduler")? {
        let name: String = value.extract()?;
        config.scheduler = name.parse().map_err(PyValueError::new_err)?;
    }
    parse_int!(dict, "parallel_workers", config.parallel_workers);
    if let Some(value) = dict.get_item("v2_founder_priors_enabled")? {
        config.v2_founder_priors_enabled = value.extract()?;
    }
    if let Some(value) = dict.get_item("recurrent_state_lesion")? {
        config.recurrent_state_lesion = value.extract()?;
    }
    if let Some(value) = dict.get_item("memory_probe_enabled")? {
        config.memory_probe_enabled = value.extract()?;
    }
    if let Some(value) = dict.get_item("seasons_enabled")? {
        config.seasons_enabled = value.extract()?;
    }
    if let Some(value) = dict.get_item("dynamic_chemistry_enabled")? {
        config.dynamic_chemistry_enabled = value.extract()?;
    }
    parse_int!(dict, "reaction_rule_count", config.reaction_rule_count);
    parse_int!(
        dict,
        "environmental_reaction_rate",
        config.environmental_reaction_rate
    );
    parse_int!(
        dict,
        "reaction_thermodynamics",
        config.reaction_thermodynamics
    );
    parse_int!(dict, "byproduct_strength", config.byproduct_strength);
    if let Some(value) = dict.get_item("byproduct_decay_rate")? {
        config.byproduct_decay_rate = value.extract()?;
    }
    if let Some(value) = dict.get_item("chemistry_coupling")? {
        config.chemistry_coupling = value.extract()?;
    }
    if let Some(value) = dict.get_item("guest_niche_coupling")? {
        config.guest_niche_coupling = value.extract()?;
    }
    if let Some(value) = dict.get_item("cellular_emergence_enabled")? {
        config.cellular_emergence_enabled = value.extract()?;
    }
    if let Some(value) = dict.get_item("emergence_coordinated_components")? {
        config.emergence_coordinated_components = value.extract()?;
    }
    if let Some(value) = dict.get_item("biodeposits_enabled")? {
        config.biodeposits_enabled = value.extract()?;
    }
    parse_int!(dict, "season_duration_min", config.season_duration_min);
    parse_int!(dict, "season_duration_max", config.season_duration_max);
    parse_int!(
        dict,
        "season_transition_ticks",
        config.season_transition_ticks
    );
    parse_int!(dict, "season_strength", config.season_strength);
    parse_int!(dict, "emergence_max_modules", config.emergence_max_modules);
    parse_int!(
        dict,
        "emergence_structural_mutation_rate",
        config.emergence_structural_mutation_rate
    );
    parse_int!(dict, "emergence_module_cost", config.emergence_module_cost);
    parse_int!(
        dict,
        "emergence_module_effect",
        config.emergence_module_effect
    );
    parse_int!(dict, "emergence_bond_rate", config.emergence_bond_rate);
    parse_int!(
        dict,
        "emergence_bond_break_rate",
        config.emergence_bond_break_rate
    );
    parse_int!(
        dict,
        "emergence_exchange_rate",
        config.emergence_exchange_rate
    );
    parse_int!(
        dict,
        "emergence_engulfment_rate",
        config.emergence_engulfment_rate
    );
    parse_int!(
        dict,
        "emergence_max_internal_guests",
        config.emergence_max_internal_guests
    );
    parse_int!(dict, "biodeposit_decay_rate", config.biodeposit_decay_rate);
    parse_int!(
        dict,
        "biodeposit_movement_resistance",
        config.biodeposit_movement_resistance
    );
    parse_int!(
        dict,
        "biodeposit_cover_strength",
        config.biodeposit_cover_strength
    );
    parse_int!(
        dict,
        "biodeposit_concealment",
        config.biodeposit_concealment
    );
    parse_int!(dict, "width", config.width);
    parse_int!(dict, "height", config.height);
    parse_int!(dict, "chunk_size", config.chunk_size);
    parse_int!(dict, "founder_count", config.founder_count);
    parse_int!(
        dict,
        "founder_archetype_count",
        config.founder_archetype_count
    );
    parse_int!(dict, "element_count", config.element_count);
    parse_int!(dict, "molecule_count", config.molecule_count);
    parse_int!(
        dict,
        "chemical_signature_dimensions",
        config.chemical_signature_dimensions
    );
    parse_int!(dict, "initial_deposits", config.initial_deposits);
    parse_int!(dict, "initial_batch_min", config.initial_batch_min);
    parse_int!(dict, "initial_batch_max", config.initial_batch_max);
    parse_int!(
        dict,
        "maximum_molecule_units",
        config.maximum_molecule_units
    );
    parse_int!(dict, "heat_diffusion", config.heat_diffusion);
    parse_int!(dict, "mana_decay", config.mana_decay);
    parse_int!(
        dict,
        "primary_production_rate",
        config.primary_production_rate
    );
    parse_int!(
        dict,
        "deposit_production_rate",
        config.deposit_production_rate
    );
    parse_int!(dict, "decomposition_rate", config.decomposition_rate);
    parse_int!(dict, "mutation_multiplier", config.mutation_multiplier);
    parse_int!(dict, "reaction_rate", config.reaction_rate);
    parse_int!(
        dict,
        "maintenance_cost_multiplier",
        config.maintenance_cost_multiplier
    );
    parse_int!(dict, "reference_move_cost", config.reference_move_cost);
    parse_int!(dict, "reference_attack_cost", config.reference_attack_cost);
    parse_int!(
        dict,
        "attack_damage_multiplier",
        config.attack_damage_multiplier
    );
    parse_int!(dict, "reference_ingest_cost", config.reference_ingest_cost);
    parse_int!(
        dict,
        "reference_reproduction_cost",
        config.reference_reproduction_cost
    );
    parse_int!(
        dict,
        "reproduction_cost_multiplier",
        config.reproduction_cost_multiplier
    );
    parse_int!(
        dict,
        "reproduction_cooldown_multiplier",
        config.reproduction_cooldown_multiplier
    );
    parse_int!(
        dict,
        "maturity_age_multiplier",
        config.maturity_age_multiplier
    );
    parse_int!(
        dict,
        "reproduction_action_bonus",
        config.reproduction_action_bonus
    );
    parse_int!(
        dict,
        "asexual_probability_floor",
        config.asexual_probability_floor
    );
    parse_int!(
        dict,
        "sexual_probability_floor",
        config.sexual_probability_floor
    );
    parse_int!(dict, "sight_cost_per_cell", config.sight_cost_per_cell);
    parse_int!(
        dict,
        "failed_move_cost_fraction",
        config.failed_move_cost_fraction
    );
    parse_int!(dict, "brain_cost_multiplier", config.brain_cost_multiplier);
    parse_int!(dict, "brain_base_cost", config.brain_base_cost);
    parse_int!(dict, "brain_hidden_cost", config.brain_hidden_cost);
    parse_int!(dict, "brain_recurrent_cost", config.brain_recurrent_cost);
    parse_int!(
        dict,
        "species_distance_threshold",
        config.species_distance_threshold
    );
    parse_int!(
        dict,
        "prey_compatibility_threshold",
        config.prey_compatibility_threshold
    );
    parse_int!(
        dict,
        "new_species_marker_ticks",
        config.new_species_marker_ticks
    );
    parse_int!(dict, "alliance_probability", config.alliance_probability);
    parse_int!(dict, "colony_bonus_cap", config.colony_bonus_cap);
    parse_int!(dict, "sexual_colony_max", config.sexual_colony_max);
    parse_int!(dict, "asexual_colony_min", config.asexual_colony_min);
    parse_int!(dict, "max_sight", config.max_sight);
    parse_int!(dict, "audit_every", config.audit_every);
    if let Some(v) = dict.get_item("deposit_match_ecology")? {
        config.deposit_match_ecology = v.extract()?;
    }
    if let Some(v) = dict.get_item("sexual_probability_floor_enabled")? {
        config.sexual_probability_floor_enabled = v.extract()?;
    }
    Ok(())
}

#[pymodule]
fn organism_sim_kernel(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<KernelSimulation>()?;
    m.add("ACTIONS", ACTION_NAMES.to_vec())?;
    m.add("FEATURES", genetics::FEATURE_NAMES.to_vec())?;
    m.add(
        "BEHAVIOR_MODELS",
        BehaviorModel::ALL
            .iter()
            .map(|model| model.as_str())
            .collect::<Vec<_>>(),
    )?;
    m.add(
        "V2_INTENTS",
        IntentKind::ALL
            .iter()
            .map(|kind| kind.as_str())
            .collect::<Vec<_>>(),
    )?;
    m.add(
        "V2_OBSERVATION_SCHEMA_VERSION",
        behavior::OBSERVATION_SCHEMA_VERSION,
    )?;
    m.add("V2_INTENT_SCHEMA_VERSION", behavior::INTENT_SCHEMA_VERSION)?;
    m.add("V2_BRAIN_SCHEMA_VERSION", behavior::BRAIN_SCHEMA_VERSION)?;
    m.add("GUILDS", genetics::GUILD_NAMES.to_vec())?;
    m.add("TRAITS", genetics::TRAIT_NAMES.to_vec())?;
    m.add("LAST_ACTION_NAMES", {
        let names: Vec<String> = (0..=13u8)
            .map(entities::last_action::name)
            .map(|s| s.to_string())
            .chain(
                ["dead:attrition", "dead:predation", "dead:fire"]
                    .iter()
                    .map(|s| s.to_string()),
            )
            .collect();
        names
    })?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    let _ = py;
    Ok(())
}

// ---------------------------------------------------------------------------
// Rust tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn test_config(founders: usize) -> SimConfig {
        SimConfig {
            founder_count: founders,
            founder_archetype_count: 8.min(founders),
            audit_every: 0,
            ..SimConfig::default()
        }
    }

    fn v2_test_config(founders: usize) -> SimConfig {
        SimConfig {
            behavior_model: BehaviorModel::LinearIntentV2,
            ..test_config(founders)
        }
    }

    fn recurrent_test_config(founders: usize) -> SimConfig {
        SimConfig {
            behavior_model: BehaviorModel::RecurrentIntentV2,
            ..test_config(founders)
        }
    }

    #[test]
    fn energy_tolerance_scales_with_generated_world_energy() {
        let initial = 27_698.459_065_338_313;
        let generated = 13_245_018.267_647_943;
        let tolerance = energy_tolerance(initial, generated);

        assert!(tolerance >= 1.153_005_723_608_657_7e-5);
        assert_eq!(energy_tolerance(1.0, 0.0), ENERGY_ABSOLUTE_TOLERANCE);
        assert_eq!(
            energy_tolerance(1_000_000.0, 0.0),
            1_000_000.0 * ENERGY_INITIAL_RELATIVE_TOLERANCE
        );
    }

    #[test]
    fn same_seed_determinism() {
        let mut a = KernelState::new(test_config(150)).unwrap();
        let mut b = KernelState::new(test_config(150)).unwrap();
        a.step(60);
        b.step(60);
        assert_eq!(a.digest(), b.digest());
        assert_eq!(a.digest(), 14_019_584_453_586_675_779);
        assert_eq!(a.tick(), 60);
    }

    #[test]
    fn parallel_v3_is_worker_count_invariant_and_conserves() {
        let parallel_config = |parallel_workers| SimConfig {
            behavior_model: BehaviorModel::LinearIntentV2,
            scheduler: Scheduler::ParallelV3,
            parallel_workers,
            ..test_config(120)
        };
        let mut single = KernelState::new(parallel_config(1)).unwrap();
        single.step(80);
        let expected_digest = single.digest();
        let expected_population = single.population();

        for workers in [2, 4, 8, 0] {
            let mut candidate = KernelState::new(parallel_config(workers)).unwrap();
            candidate.step(80);
            assert_eq!(candidate.digest(), expected_digest, "workers={workers}");
            assert_eq!(
                candidate.population(),
                expected_population,
                "workers={workers}"
            );
            let (element_error, energy_error) = candidate.audit(false).unwrap();
            assert!(element_error.iter().all(|&error| error == 0));
            assert!(
                energy_error.abs()
                    <= energy_tolerance(candidate.initial_energy, candidate.world.generated_energy)
            );
        }
    }

    #[test]
    fn parallel_v3_primary_production_is_worker_count_invariant() {
        let config = |parallel_workers| SimConfig {
            behavior_model: BehaviorModel::LinearIntentV2,
            scheduler: Scheduler::ParallelV3,
            parallel_workers,
            primary_production_rate: 0.0025,
            ..test_config(80)
        };
        let mut single = KernelState::new(config(1)).unwrap();
        let mut eight = KernelState::new(config(8)).unwrap();
        single.step(40);
        eight.step(40);

        assert_eq!(single.digest(), eight.digest());
        let (element_error, energy_error) = eight.audit(false).unwrap();
        assert!(element_error.iter().all(|&error| error == 0));
        assert!(
            energy_error.abs()
                <= energy_tolerance(eight.initial_energy, eight.world.generated_energy)
        );
    }

    #[test]
    fn parallel_v3_conflict_components_isolate_only_disjoint_self_actions() {
        let state = KernelState::new(SimConfig {
            behavior_model: BehaviorModel::LinearIntentV2,
            scheduler: Scheduler::ParallelV3,
            parallel_workers: 2,
            ..test_config(3)
        })
        .unwrap();
        let ids: Vec<u32> = state.living_ordered.iter().copied().collect();
        let proposal = |actor_id, kind, target| ParallelProposal {
            actor_id,
            intent: ActionIntent {
                actor_id,
                kind,
                target,
                predicted_duration_ticks: 1,
                predicted_chemical_cost: 0.0,
                predicted_mana_cost: 0.0,
            },
            sight_cost: 0.0,
            next_neural_state: NeuralState::default(),
            current_food_slot: 0,
            current_food_signal: 0.0,
            neural_failure: false,
            memory_probe: MemoryProbeDelta::default(),
        };

        let disjoint = state.parallel_v3_isolated_components(&[
            proposal(ids[0], IntentKind::Wait, IntentTarget::None),
            proposal(ids[1], IntentKind::Repair, IntentTarget::None),
        ]);
        assert_eq!(disjoint, vec![true, true]);

        let targeted = state.parallel_v3_isolated_components(&[
            proposal(ids[0], IntentKind::Attack, IntentTarget::Organism(ids[1])),
            proposal(ids[1], IntentKind::Wait, IntentTarget::None),
        ]);
        assert_eq!(targeted, vec![false, false]);
    }

    #[test]
    fn parallel_v3_rejects_the_legacy_controller() {
        let error = KernelState::new(SimConfig {
            scheduler: Scheduler::ParallelV3,
            ..test_config(10)
        })
        .err()
        .expect("parallel-v3 must reject legacy behavior");
        assert!(error.contains("requires a V2 intent behavior model"));
    }

    #[test]
    fn disabled_season_parameters_do_not_change_ecology() {
        let mut left = KernelState::new(test_config(80)).unwrap();
        let mut right = KernelState::new(SimConfig {
            season_duration_min: 3_150,
            season_duration_max: 3_600,
            season_transition_ticks: 600,
            season_strength: 1.0,
            ..test_config(80)
        })
        .unwrap();
        left.step(100);
        right.step(100);

        assert_eq!(left.digest(), right.digest());
    }

    #[test]
    fn zero_strength_seasons_preserve_neutral_ecology() {
        let mut control = KernelState::new(test_config(80)).unwrap();
        let mut seasonal = KernelState::new(SimConfig {
            seasons_enabled: true,
            season_duration_min: 10,
            season_duration_max: 10,
            season_transition_ticks: 4,
            season_strength: 0.0,
            ..test_config(80)
        })
        .unwrap();
        control.step(40);
        seasonal.step(40);

        assert_eq!(seasonal.seasons.index, 4);
        seasonal.config.seasons_enabled = false;
        assert_eq!(control.digest(), seasonal.digest());
    }

    #[test]
    fn random_seasons_are_deterministic_and_conserve_energy() {
        let config = SimConfig {
            seasons_enabled: true,
            season_duration_min: 10,
            season_duration_max: 15,
            season_transition_ticks: 4,
            season_strength: 0.8,
            ..test_config(80)
        };
        let mut left = KernelState::new(config.clone()).unwrap();
        let mut right = KernelState::new(config).unwrap();
        left.step(50);
        right.step(50);

        assert_eq!(left.digest(), right.digest());
        assert!(left.seasons.index >= 3);
        assert_eq!(left.seasons.events.len(), left.seasons.index as usize + 1);
        assert!(left
            .seasons
            .target
            .molecule_charge_affinities
            .iter()
            .any(|&value| value < 0.99));
        let (element_error, energy_error) = left.audit(false).unwrap();
        assert!(element_error.iter().all(|&error| error == 0));
        assert!(energy_error.abs() <= left.initial_energy.abs().max(1.0) * 1e-9);
    }

    #[test]
    fn bonded_component_moves_rigidly_and_uses_one_action_authority() {
        let mut state = KernelState::new(SimConfig {
            cellular_emergence_enabled: true,
            emergence_coordinated_components: true,
            reference_move_cost: 0.0,
            audit_every: 0,
            ..test_config(2)
        })
        .unwrap();
        let members: Vec<u32> = state.living_ordered.iter().copied().collect();
        let edge = (members[0].min(members[1]), members[0].max(members[1]));
        state.bonds.insert(
            edge,
            Bond {
                left: edge.0,
                right: edge.1,
                formed_tick: 0,
                strength: 1.0,
            },
        );
        state.rebuild_bond_components();
        let before: Vec<Position> = members
            .iter()
            .map(|&member| state.organism(member).position)
            .collect();

        assert!(state.move_organism_exact(members[0], (1, 0)));
        for (&member, position) in members.iter().zip(before) {
            assert_eq!(
                state.organism(member).position,
                (position.0 + 1, position.1)
            );
        }
        assert_eq!(state.emergence_stats.component_moves, 1);
        let blocked_before: Vec<Position> = members
            .iter()
            .map(|&member| state.organism(member).position)
            .collect();
        let obstacle = (blocked_before[0].0 + 1, blocked_before[0].1);
        state.world.add_to_occupancy(999_999, &[obstacle]);
        assert!(!state.move_organism_exact(members[0], (1, 0)));
        assert!(members
            .iter()
            .zip(&blocked_before)
            .all(|(&member, &position)| state.organism(member).position == position));

        state.tick = 1;
        for &member in &members {
            state.organism_mut(member).next_action_tick = 0;
        }
        state.run_coordinated_organism_loop();
        assert_eq!(state.emergence_stats.component_actions, 1);
        assert_eq!(
            state.organism(members[0]).next_action_tick,
            state.organism(members[1]).next_action_tick
        );
    }

    #[test]
    fn bond_loss_fissions_derived_component_without_reclassification() {
        let mut state = KernelState::new(SimConfig {
            cellular_emergence_enabled: true,
            emergence_coordinated_components: true,
            audit_every: 0,
            ..test_config(3)
        })
        .unwrap();
        let members: Vec<u32> = state.living_ordered.iter().copied().collect();
        for pair in members.windows(2) {
            let edge = (pair[0].min(pair[1]), pair[0].max(pair[1]));
            state.bonds.insert(
                edge,
                Bond {
                    left: edge.0,
                    right: edge.1,
                    formed_tick: 0,
                    strength: 1.0,
                },
            );
        }
        state.rebuild_bond_components();
        assert!(members
            .iter()
            .all(|&member| state.component_root_for(member) == members[0]));

        let broken = (members[0].min(members[1]), members[0].max(members[1]));
        state.bonds.remove(&broken);
        state.rebuild_bond_components();
        assert_ne!(
            state.component_root_for(members[0]),
            state.component_root_for(members[1])
        );
        assert_eq!(
            state.component_root_for(members[1]),
            state.component_root_for(members[2])
        );
    }

    #[test]
    fn bonded_component_reproduces_one_complete_bonded_propagule() {
        let mut state = KernelState::new(SimConfig {
            cellular_emergence_enabled: true,
            emergence_coordinated_components: true,
            asexual_probability_floor: 1.0,
            reference_reproduction_cost: 0.0,
            audit_every: 0,
            ..test_config(2)
        })
        .unwrap();
        let parents: Vec<u32> = state.living_ordered.iter().copied().collect();
        let edge = (parents[0].min(parents[1]), parents[0].max(parents[1]));
        state.bonds.insert(
            edge,
            Bond {
                left: edge.0,
                right: edge.1,
                formed_tick: 0,
                strength: 1.0,
            },
        );
        state.tick = 1;
        for &parent in &parents {
            let organism = state.organism_mut(parent);
            organism.birth_tick = 0;
            Arc::make_mut(&mut organism.phenotype).maturity_age = 1;
            Arc::make_mut(&mut organism.phenotype).reproduction_fraction = 0.2;
            organism.reproduction_cooldown = 0;
        }
        state.rebuild_bond_components();
        let population_before = state.population();
        state.attempt_reproduction(parents[0], None);

        assert_eq!(state.population(), population_before + parents.len());
        assert_eq!(state.emergence_stats.propagules, 1);
        assert_eq!(state.emergence_stats.propagated_cells, parents.len() as u64);
        let children: Vec<u32> = state
            .living_ordered
            .iter()
            .copied()
            .filter(|organism_id| !parents.contains(organism_id))
            .collect();
        assert_eq!(children.len(), parents.len());
        assert!(state
            .bonds
            .contains_key(&(children[0].min(children[1]), children[0].max(children[1]))));
        assert!(parents.iter().all(|&parent| {
            children
                .iter()
                .any(|&child| state.organism(child).parent_ids == vec![parent])
        }));
        let (element_error, energy_error) = state.audit(false).unwrap();
        assert!(element_error.iter().all(|&error| error == 0));
        assert!(energy_error.abs() <= state.initial_energy.abs().max(1.0) * 1.0e-9);
    }

    #[test]
    fn physical_biodeposits_are_deterministic_and_conservative() {
        let config = SimConfig {
            biodeposits_enabled: true,
            maintenance_cost_multiplier: 2.0,
            audit_every: 0,
            ..test_config(120)
        };
        let mut left = KernelState::new(config.clone()).unwrap();
        let mut right = KernelState::new(config).unwrap();
        left.step(200);
        right.step(200);
        assert_eq!(left.digest(), right.digest());
        assert!(left.world.total_biodeposit_density() > 0.0);
        let (element_error, energy_error) = left.audit(false).unwrap();
        assert!(element_error.iter().all(|&error| error == 0));
        assert!(energy_error.abs() <= left.initial_energy.abs().max(1.0) * 1.0e-9);
    }

    #[test]
    fn death_biodeposit_reuses_conserved_edible_matter() {
        let mut state = KernelState::new(SimConfig {
            biodeposits_enabled: true,
            biodeposit_decay_rate: 0.0,
            audit_every: 0,
            ..test_config(2)
        })
        .unwrap();
        let organism_id = *state.living_ordered.iter().next().unwrap();
        let position = state.organism(organism_id).position;
        let expected_mass: i64 = state
            .organism(organism_id)
            .all_inventories()
            .iter()
            .map(|inventory| state.catalog.inventory_mass(inventory))
            .sum();

        state.kill(organism_id, last_action::DEAD_ATTRITION);

        assert!((state.world.total_biodeposit_density() - expected_mass as f64).abs() < 1.0e-9);
        assert!(state.world.biodeposit_density_at(position) > 0.0);
        let food_position = *state
            .world
            .biodeposits
            .keys()
            .find(|position| state.world.deposits.contains_key(position))
            .unwrap();
        let molecule_id = state.world.deposits[&food_position][0].molecule_id;
        let density_before = state.world.biodeposit_density_at(food_position);
        let eater_id = *state.living_ordered.iter().next().unwrap();
        state.eat(eater_id, (food_position, molecule_id, 1.0));
        assert!(state.world.biodeposit_density_at(food_position) < density_before);
        let (element_error, energy_error) = state.audit(false).unwrap();
        assert!(element_error.iter().all(|&error| error == 0));
        assert!(energy_error.abs() <= state.initial_energy.abs().max(1.0) * 1.0e-10);
    }

    #[test]
    fn packed_biomass_resists_movement_and_physically_covers_targets() {
        let config = SimConfig {
            biodeposits_enabled: true,
            biodeposit_decay_rate: 0.0,
            biodeposit_concealment: 0.0,
            reference_attack_cost: 0.0,
            audit_every: 0,
            ..test_config(2)
        };
        let mut open = KernelState::new(config.clone()).unwrap();
        let mut covered = KernelState::new(config).unwrap();
        let ids: Vec<u32> = open.living_ordered.iter().copied().collect();
        let (attacker_id, target_id) = (ids[0], ids[1]);
        let target_position = open.organism(target_id).position;
        open.organism_mut(target_id).integrity = 100.0;
        covered.organism_mut(target_id).integrity = 100.0;
        covered
            .world
            .add_biodeposit(target_position, covered.reference_body_mass * 100.0);
        open.attack(attacker_id, target_id);
        covered.attack(attacker_id, target_id);
        assert!(
            covered.organism(target_id).integrity > open.organism(target_id).integrity,
            "packed matter should reduce transmitted attack damage"
        );

        let mut free = KernelState::new(SimConfig {
            biodeposits_enabled: true,
            biodeposit_movement_resistance: 0.0,
            audit_every: 0,
            ..test_config(1)
        })
        .unwrap();
        let mut resisted = KernelState::new(SimConfig {
            biodeposits_enabled: true,
            biodeposit_movement_resistance: 1.0e12,
            audit_every: 0,
            ..test_config(1)
        })
        .unwrap();
        let organism_id = *free.living_ordered.iter().next().unwrap();
        let destination = (
            free.organism(organism_id).position.0 + 1,
            free.organism(organism_id).position.1,
        );
        free.world
            .add_biodeposit(destination, free.reference_body_mass * 100.0);
        resisted
            .world
            .add_biodeposit(destination, resisted.reference_body_mass * 100.0);
        assert!(free.move_organism_exact(organism_id, (1, 0)));
        assert!(!resisted.move_organism_exact(organism_id, (1, 0)));
    }

    #[test]
    fn zero_effect_cellular_affordances_preserve_neutral_ecology() {
        let mut control = KernelState::new(test_config(80)).unwrap();
        let mut treatment = KernelState::new(SimConfig {
            cellular_emergence_enabled: true,
            emergence_module_cost: 0.0,
            emergence_module_effect: 0.0,
            emergence_bond_rate: 0.0,
            emergence_bond_break_rate: 0.0,
            emergence_exchange_rate: 0.0,
            emergence_engulfment_rate: 0.0,
            ..test_config(80)
        })
        .unwrap();
        control.step(60);
        treatment.step(60);

        treatment.config.cellular_emergence_enabled = false;
        for organism in &mut treatment.organisms {
            std::sync::Arc::make_mut(&mut organism.genome).emergence = None;
            organism.cellular = None;
        }
        for species in &mut treatment.species {
            species.representative_genome.emergence = None;
        }
        assert_eq!(control.digest(), treatment.digest());
    }

    #[test]
    fn stochastic_cellular_affordances_are_deterministic_and_conservative() {
        let config = SimConfig {
            cellular_emergence_enabled: true,
            emergence_module_cost: 0.001,
            emergence_bond_rate: 0.05,
            emergence_bond_break_rate: 0.001,
            ..test_config(80)
        };
        let mut left = KernelState::new(config.clone()).unwrap();
        let mut right = KernelState::new(config).unwrap();
        left.step(60);
        right.step(60);

        assert_eq!(left.digest(), right.digest());
        let metrics = left.emergence_metrics();
        assert!(metrics.module_instances >= left.population());
        assert!(metrics.expressed_module_instances > 0);
        assert!(metrics.compartment_tags_used > 0);
        let (element_error, energy_error) = left.audit(false).unwrap();
        assert!(element_error.iter().all(|&error| error == 0));
        assert!(energy_error.abs() <= left.initial_energy.abs().max(1.0) * 1e-9);
    }

    #[test]
    fn chance_governed_internalization_moves_matter_without_creating_it() {
        let mut state = KernelState::new(SimConfig {
            cellular_emergence_enabled: true,
            emergence_engulfment_rate: 100.0,
            emergence_max_internal_guests: 4,
            ..test_config(2)
        })
        .unwrap();
        let ids: Vec<u32> = state.living_ordered.iter().copied().collect();
        let host_id = ids[0];
        let target_id = ids[1];
        std::sync::Arc::make_mut(&mut state.organism_mut(host_id).genome)
            .emergence
            .as_mut()
            .unwrap()
            .engulfment = 1.0;
        std::sync::Arc::make_mut(&mut state.organism_mut(target_id).genome)
            .emergence
            .as_mut()
            .unwrap()
            .guest_tolerance = 0.0;

        assert!(state.try_internalize(host_id, target_id));
        assert!(!state.living.contains(&target_id));
        assert_eq!(
            state
                .organism(host_id)
                .cellular
                .as_ref()
                .unwrap()
                .guests
                .len(),
            1
        );
        assert_eq!(state.emergence_stats.internalizations, 1);
        let (element_error, energy_error) = state.audit(false).unwrap();
        assert!(element_error.iter().all(|&error| error == 0));
        assert!(energy_error.abs() <= state.initial_energy.abs().max(1.0) * 1e-9);
    }

    #[test]
    fn linear_v2_is_deterministic_and_conserves_energy() {
        let mut left = KernelState::new(v2_test_config(80)).unwrap();
        let mut right = KernelState::new(v2_test_config(80)).unwrap();
        left.step(80);
        right.step(80);

        assert_eq!(left.digest(), right.digest());
        assert_eq!(left.digest(), 5_830_744_781_846_748_792);
        assert_eq!(left.tick(), 80);
        assert!(left.stats.brain_energy_spent > 0.0);
        assert!(left.stats.v2_intent_counts.iter().sum::<u64>() > 0);
        assert!(left
            .organisms
            .iter()
            .any(|organism| organism.decision_count > 0 && organism.brain_energy_spent > 0.0));
        let (element_error, energy_error) = left.audit(false).unwrap();
        assert!(element_error.iter().all(|&error| error == 0));
        assert!(energy_error.abs() <= left.initial_energy.abs().max(1.0) * 1e-9);
    }

    #[test]
    fn recurrent_v2_is_deterministic_bounded_and_conserves_energy() {
        let mut left = KernelState::new(recurrent_test_config(80)).unwrap();
        let mut right = KernelState::new(recurrent_test_config(80)).unwrap();
        assert!(left.organisms.iter().all(|organism| {
            organism
                .genome
                .recurrent_policy
                .as_ref()
                .unwrap()
                .recurrent_expression
                .iter()
                .all(|gene| gene.center == 0.0 && gene.spread == 0.0)
                && organism
                    .phenotype
                    .recurrent_policy
                    .as_ref()
                    .unwrap()
                    .recurrent_expression
                    .iter()
                    .all(|&value| value == 0.0)
        }));
        left.step(80);
        right.step(80);

        assert_eq!(left.digest(), right.digest());
        assert_eq!(left.tick(), 80);
        assert!(left.stats.hidden_brain_energy_spent > 0.0);
        assert_eq!(left.stats.neural_numerical_errors, 0);
        assert!(left.organisms.iter().all(|organism| organism
            .neural_state
            .values
            .iter()
            .all(|value| value.is_finite() && (-1.0..=1.0).contains(value))));
        let (element_error, energy_error) = left.audit(false).unwrap();
        assert!(element_error.iter().all(|&error| error == 0));
        assert!(energy_error.abs() <= left.initial_energy.abs().max(1.0) * 1e-9);
    }

    #[test]
    fn recurrent_memory_is_dormant_then_can_distinguish_histories() {
        use behavior::neural::{RecurrentIntentGenome, HIDDEN_COUNT};
        use behavior::observation::ObservationV2;

        let mut rng = Rng::new(17);
        let genome = RecurrentIntentGenome::random(&mut rng);
        let mut phenotype = genome.sample(&mut rng);
        let observation = ObservationV2::default();
        let positive = NeuralState {
            values: [0.5; HIDDEN_COUNT],
        };
        let negative = NeuralState {
            values: [-0.5; HIDDEN_COUNT],
        };

        let dormant_positive = phenotype.infer(&observation, positive, false).unwrap();
        let dormant_negative = phenotype.infer(&observation, negative, false).unwrap();
        assert_eq!(
            dormant_positive.kind_residual,
            dormant_negative.kind_residual
        );
        assert!(phenotype
            .recurrent_expression
            .iter()
            .all(|&value| value == 0.0));

        phenotype.hidden_bias.fill(0.0);
        phenotype
            .input_weights
            .fill([0.0; behavior::observation::OBSERVATION_COUNT]);
        phenotype.hidden_expression.fill(0.0);
        phenotype.hidden_expression[0] = 1.0;
        phenotype.recurrent_weights.fill([0.0; HIDDEN_COUNT]);
        phenotype.recurrent_weights[0][0] = 1.0;
        phenotype.recurrent_expression.fill(0.0);
        phenotype.recurrent_expression[0] = 1.0;
        phenotype.retention.fill(0.0);
        phenotype.kind_output_weights.fill([0.0; HIDDEN_COUNT]);
        phenotype.kind_output_weights[IntentKind::Move.as_index()][0] = 1.0;
        phenotype.feature_output_weights.fill([0.0; HIDDEN_COUNT]);

        let expressed_positive = phenotype.infer(&observation, positive, false).unwrap();
        let expressed_negative = phenotype.infer(&observation, negative, false).unwrap();
        assert!(
            expressed_positive.kind_residual[IntentKind::Move.as_index()]
                > expressed_negative.kind_residual[IntentKind::Move.as_index()]
        );

        let lesioned_positive = phenotype.infer(&observation, positive, true).unwrap();
        let lesioned_negative = phenotype.infer(&observation, negative, true).unwrap();
        assert_eq!(lesioned_positive, lesioned_negative);
        assert_eq!(lesioned_positive.next_state, NeuralState::default());
    }

    #[test]
    fn recurrent_inference_rejects_non_finite_state() {
        use behavior::neural::{RecurrentIntentGenome, HIDDEN_COUNT};
        use behavior::observation::ObservationV2;

        let mut rng = Rng::new(23);
        let phenotype = RecurrentIntentGenome::random(&mut rng).sample(&mut rng);
        let mut state = NeuralState {
            values: [0.0; HIDDEN_COUNT],
        };
        state.values[0] = f32::NAN;
        assert!(phenotype
            .infer(&ObservationV2::default(), state, false)
            .is_none());
    }

    #[test]
    fn memory_probe_is_observational_and_lesion_has_no_state_effect() {
        let mut control = KernelState::new(recurrent_test_config(80)).unwrap();
        let mut probe = KernelState::new(SimConfig {
            memory_probe_enabled: true,
            ..recurrent_test_config(80)
        })
        .unwrap();
        let mut lesion = KernelState::new(SimConfig {
            memory_probe_enabled: true,
            recurrent_state_lesion: true,
            ..recurrent_test_config(80)
        })
        .unwrap();

        control.step(80);
        probe.step(80);
        lesion.step(80);

        assert_eq!(control.population(), probe.population());
        assert_eq!(control.stats.births, probe.stats.births);
        assert_eq!(control.stats.deaths, probe.stats.deaths);
        assert_eq!(control.stats.v2_intent_counts, probe.stats.v2_intent_counts);
        assert!(probe.stats.memory_probe_decisions > 0);
        assert!(probe.stats.memory_probe_state_l1_sum > 0.0);
        assert_eq!(lesion.stats.memory_probe_argmax_changes, 0);
        assert!(lesion
            .organisms
            .iter()
            .all(|organism| organism.neural_state == NeuralState::default()));
    }

    #[test]
    fn recurrent_runtime_failure_waits_and_clears_state() {
        let mut state = KernelState::new(recurrent_test_config(1)).unwrap();
        let oid = *state.living.iter().next().unwrap();
        state.organism_mut(oid).neural_state.values[0] = f32::NAN;

        state.decide_and_act_v2(oid);

        assert_eq!(state.organism(oid).last_intent_kind, IntentKind::Wait as u8);
        assert_eq!(state.organism(oid).neural_state, NeuralState::default());
        assert_eq!(state.organism(oid).neural_numerical_errors, 1);
        assert_eq!(state.stats.neural_numerical_errors, 1);
    }

    #[test]
    fn different_seed_diverges() {
        let mut a = KernelState::new(test_config(80)).unwrap();
        let mut b = KernelState::new(SimConfig {
            seed: 8,
            ..test_config(80)
        })
        .unwrap();
        a.step(30);
        b.step(30);
        assert_ne!(a.digest(), b.digest());
    }

    #[test]
    fn conservation_holds() {
        let mut state = KernelState::new(SimConfig {
            audit_every: 0,
            ..test_config(150)
        })
        .unwrap();
        state.step(120);
        let (element_error, energy_error) = state.audit(false).unwrap();
        assert!(
            element_error.iter().all(|&e| e == 0),
            "matter conservation failed: {:?}",
            element_error
        );
        let relative = energy_error / state.initial_energy.abs().max(1e-9);
        assert!(
            relative.abs() < 1e-6,
            "energy conservation failed: relative {:.3e}",
            relative
        );
    }

    #[test]
    fn hottest_cell_keeps_first_position_on_ties() {
        let state = KernelState::new(test_config(1)).unwrap();
        let cells = [(1_000_000, 1_000_000), (1_000_001, 1_000_000)];
        assert_eq!(state.hottest_cell(&cells), (cells[0], 0.0));
    }

    #[test]
    fn action_sampling_order_matches_python_sorted_actions() {
        let names: Vec<&str> = ACTION_ORDER_ALPHA
            .iter()
            .map(|&action| ACTION_NAMES[action])
            .collect();
        assert_eq!(
            names,
            vec![
                "ally",
                "attack",
                "detox",
                "eat",
                "flee",
                "forage",
                "heat",
                "hunt",
                "magic",
                "reproduce",
                "rest",
                "seek_mate",
                "wander",
            ]
        );
    }

    #[test]
    fn behavior_models_are_versioned_and_executable() {
        assert_eq!(
            "legacy_linear_macro_v1".parse::<BehaviorModel>().unwrap(),
            BehaviorModel::LegacyLinearMacroV1
        );
        assert_eq!(
            "linear_intent_v2".parse::<BehaviorModel>().unwrap(),
            BehaviorModel::LinearIntentV2
        );
        assert_eq!(
            "recurrent_intent_v2".parse::<BehaviorModel>().unwrap(),
            BehaviorModel::RecurrentIntentV2
        );
        assert!("unknown".parse::<BehaviorModel>().is_err());
        assert!(BehaviorModel::LegacyLinearMacroV1.is_implemented());
        assert!(BehaviorModel::LinearIntentV2.is_implemented());
        assert!(BehaviorModel::RecurrentIntentV2.is_implemented());

        let linear = KernelState::new(SimConfig {
            behavior_model: BehaviorModel::LinearIntentV2,
            ..test_config(1)
        })
        .expect("linear V2 execution should be active");
        assert!(linear.organisms.iter().all(|organism| {
            organism.genome.intent_policy.is_some() && organism.phenotype.intent_policy.is_some()
        }));

        let recurrent = KernelState::new(SimConfig {
            behavior_model: BehaviorModel::RecurrentIntentV2,
            ..test_config(1)
        })
        .expect("recurrent V2 execution should be active");
        assert!(recurrent.organisms.iter().all(|organism| {
            organism.genome.intent_policy.is_some()
                && organism.genome.recurrent_policy.is_some()
                && organism.phenotype.intent_policy.is_some()
                && organism.phenotype.recurrent_policy.is_some()
                && organism
                    .phenotype
                    .recurrent_policy
                    .as_ref()
                    .unwrap()
                    .recurrent_expression
                    .iter()
                    .all(|&value| value == 0.0)
                && organism.neural_state == NeuralState::default()
        }));
    }

    #[test]
    fn recurrent_founders_preserve_linear_control_initial_conditions() {
        let linear = KernelState::new(v2_test_config(40)).unwrap();
        let recurrent = KernelState::new(recurrent_test_config(40)).unwrap();
        assert_eq!(linear.population(), recurrent.population());
        for organism_id in &linear.living_ordered {
            let left = linear.organism(*organism_id);
            let right = recurrent.organism(*organism_id);
            assert_eq!(left.position, right.position);
            assert_eq!(left.genome.intent_policy, right.genome.intent_policy);
            assert_eq!(left.phenotype.intent_policy, right.phenotype.intent_policy);
            assert_eq!(left.body.len(), right.body.len());
            for (left_batch, right_batch) in left.body.iter().zip(&right.body) {
                assert_eq!(left_batch.molecule_id, right_batch.molecule_id);
                assert_eq!(left_batch.count, right_batch.count);
                assert_eq!(left_batch.energy.to_bits(), right_batch.energy.to_bits());
            }
            assert_eq!(left.mana.to_bits(), right.mana.to_bits());
            assert_eq!(left.integrity.to_bits(), right.integrity.to_bits());
        }
    }

    #[test]
    fn behavior_scaffold_dimensions_match_approved_design() {
        use behavior::intent::{CANDIDATE_FEATURE_COUNT, INTENT_TYPE_COUNT, MAX_INTENT_CANDIDATES};
        use behavior::neural::{
            IntentBrainGenome, IntentBrainPhenotype, LinearIntentGenome, LinearIntentPhenotype,
            NeuralGene, RecurrentIntentGenome, RecurrentIntentPhenotype, CONTROLLER_OUTPUT_COUNT,
            HIDDEN_COUNT, LINEAR_LOCUS_COUNT, NEURAL_LOCUS_COUNT, RECURRENT_LOCUS_COUNT,
        };
        use behavior::observation::OBSERVATION_COUNT;

        assert_eq!(OBSERVATION_COUNT, 28);
        assert_eq!(HIDDEN_COUNT, 8);
        assert_eq!(INTENT_TYPE_COUNT, 10);
        assert_eq!(CANDIDATE_FEATURE_COUNT, 16);
        assert_eq!(CONTROLLER_OUTPUT_COUNT, 26);
        assert_eq!(MAX_INTENT_CANDIDATES, 33);
        assert_eq!(LINEAR_LOCUS_COUNT, 451);
        assert_eq!(RECURRENT_LOCUS_COUNT, 528);
        assert_eq!(NEURAL_LOCUS_COUNT, 979);
        assert_eq!(std::mem::size_of::<NeuralGene>(), 8);
        assert_eq!(std::mem::size_of::<LinearIntentGenome>(), 3_608);
        assert_eq!(std::mem::size_of::<LinearIntentPhenotype>(), 1_804);
        assert_eq!(std::mem::size_of::<RecurrentIntentGenome>(), 4_224);
        assert_eq!(std::mem::size_of::<RecurrentIntentPhenotype>(), 2_112);
        assert_eq!(
            std::mem::size_of::<Option<Box<LinearIntentGenome>>>(),
            std::mem::size_of::<usize>()
        );
        assert_eq!(
            std::mem::size_of::<Option<Box<RecurrentIntentGenome>>>(),
            std::mem::size_of::<usize>()
        );
        assert_eq!(std::mem::size_of::<IntentBrainGenome>(), 7_832);
        assert_eq!(std::mem::size_of::<IntentBrainPhenotype>(), 3_916);
    }

    #[test]
    fn linear_v2_candidates_are_bounded_finite_and_allocation_reusable() {
        let mut state = KernelState::new(v2_test_config(8)).unwrap();
        let oid = *state.living_ordered.iter().next().unwrap();
        let candidate_capacity = state.v2_candidates.capacity();

        state.decide_and_act_v2(oid);

        assert!(!state.v2_candidates.is_empty());
        assert!(state.v2_candidates.len() <= MAX_INTENT_CANDIDATES);
        assert!(state.v2_candidates.iter().all(|candidate| {
            candidate.features.iter().all(|value| value.is_finite())
                && candidate
                    .features
                    .iter()
                    .all(|value| (-1.0..=1.0).contains(value))
        }));
        assert_eq!(state.organism(oid).decision_count, 1);
        assert!(state.v2_candidates.capacity() >= candidate_capacity);
    }

    #[test]
    fn linear_intent_inheritance_uses_one_coherent_donor_policy() {
        let state = KernelState::new(v2_test_config(2)).unwrap();
        let mut ids: Vec<u32> = state.living.iter().copied().collect();
        ids.sort_unstable();
        let left = state.organism(ids[0]).genome.as_ref();
        let right = state.organism(ids[1]).genome.as_ref();
        let mut rng = Rng::new(91);
        let child = Genome::offspring(999_999, &[left, right], &mut rng, 0.0, &state.config);
        let child_policy = child.intent_policy.as_ref().unwrap();
        assert!(
            child_policy == left.intent_policy.as_ref().unwrap()
                || child_policy == right.intent_policy.as_ref().unwrap()
        );

        let first = Phenotype::sample(&child, &mut rng, &state.config);
        let second = Phenotype::sample(&child, &mut rng, &state.config);
        assert_ne!(first.intent_policy, second.intent_policy);
    }

    #[test]
    fn recurrent_inheritance_uses_one_coherent_brain_donor() {
        let state = KernelState::new(recurrent_test_config(2)).unwrap();
        let mut ids: Vec<u32> = state.living.iter().copied().collect();
        ids.sort_unstable();
        let left = state.organism(ids[0]).genome.as_ref();
        let right = state.organism(ids[1]).genome.as_ref();
        let mut rng = Rng::new(101);
        let child = Genome::offspring(999_998, &[left, right], &mut rng, 0.0, &state.config);
        let matches_left = child.intent_policy == left.intent_policy
            && child.recurrent_policy == left.recurrent_policy;
        let matches_right = child.intent_policy == right.intent_policy
            && child.recurrent_policy == right.recurrent_policy;
        assert!(matches_left || matches_right);
    }

    #[test]
    fn brain_cost_defaults_validate_without_affecting_legacy() {
        let config = test_config(1);
        assert_eq!(config.behavior_model, BehaviorModel::LegacyLinearMacroV1);
        assert!(config.v2_founder_priors_enabled);
        assert_eq!(config.brain_cost_multiplier, 1.0);
        assert_eq!(config.brain_base_cost, 0.001);
        assert_eq!(config.brain_hidden_cost, 0.002);
        assert_eq!(config.brain_recurrent_cost, 0.002);
        config.validate().unwrap();

        let mut invalid = config;
        invalid.brain_recurrent_cost = -0.001;
        assert!(invalid.validate().is_err());
    }

    #[test]
    fn linear_v2_base_brain_cost_is_chemical_only_and_becomes_heat() {
        let mut state = KernelState::new(SimConfig {
            maintenance_cost_multiplier: 0.0,
            mana_decay: 0.0,
            ..v2_test_config(1)
        })
        .unwrap();
        let oid = *state.living.iter().next().unwrap();
        state.organism_mut(oid).mana = state.reference_energy;
        let position = state.organism(oid).position;
        let chemical_before = state.organism(oid).chemical_energy();
        let mana_before = state.organism(oid).mana;
        let heat_before = state.world.heat_at_peek(position);
        let expected = state.reference_energy
            * state.config.brain_cost_multiplier
            * state.config.brain_base_cost;

        state.upkeep(oid);

        let chemical_delta = chemical_before - state.organism(oid).chemical_energy();
        let heat_delta = state.world.heat_at_peek(position) - heat_before;
        assert!((chemical_delta - expected).abs() < 1e-12);
        assert!((heat_delta - expected).abs() < 1e-12);
        assert_eq!(state.organism(oid).mana, mana_before);
        assert!((state.stats.brain_energy_spent - expected).abs() < 1e-12);
        assert!((state.organism(oid).brain_energy_spent - expected).abs() < 1e-12);
    }

    #[test]
    fn recurrent_expression_adds_hidden_and_memory_energy_cost() {
        let mut state = KernelState::new(SimConfig {
            maintenance_cost_multiplier: 0.0,
            mana_decay: 0.0,
            ..recurrent_test_config(1)
        })
        .unwrap();
        let oid = *state.living.iter().next().unwrap();
        {
            let phenotype = Arc::make_mut(&mut state.organism_mut(oid).phenotype);
            let recurrent = phenotype.recurrent_policy.as_mut().unwrap();
            recurrent.hidden_expression.fill(1.0);
            recurrent.recurrent_expression.fill(1.0);
        }
        let position = state.organism(oid).position;
        let chemical_before = state.organism(oid).chemical_energy();
        let heat_before = state.world.heat_at_peek(position);
        let base = state.reference_energy
            * state.config.brain_cost_multiplier
            * state.config.brain_base_cost;
        let hidden = state.reference_energy
            * state.config.brain_cost_multiplier
            * state.config.brain_hidden_cost;
        let recurrent = state.reference_energy
            * state.config.brain_cost_multiplier
            * state.config.brain_recurrent_cost;
        let expected = base + hidden + recurrent;

        state.upkeep(oid);

        let chemical_delta = chemical_before - state.organism(oid).chemical_energy();
        let heat_delta = state.world.heat_at_peek(position) - heat_before;
        assert!((chemical_delta - expected).abs() < 1e-12);
        assert!((heat_delta - expected).abs() < 1e-12);
        assert!((state.stats.hidden_brain_energy_spent - hidden).abs() < 1e-12);
        assert!((state.stats.recurrent_brain_energy_spent - recurrent).abs() < 1e-12);
    }

    #[test]
    fn reproduction_readiness_and_probability_match_python_formulas() {
        let mut state = KernelState::new(test_config(2)).unwrap();
        let mut ids: Vec<u32> = state.living.iter().copied().collect();
        ids.sort_unstable();
        let (parent_id, mate_id) = (ids[0], ids[1]);
        state.config.maturity_age_multiplier = 0.65;
        state.config.sexual_probability_floor_enabled = false;
        state.organism_mut(parent_id).birth_tick = 10;
        Arc::make_mut(&mut state.organism_mut(parent_id).phenotype).maturity_age = 10;
        state.organism_mut(parent_id).reproduction_cooldown = 0;
        state.tick = 15;
        assert!(!state.is_reproductively_ready(parent_id));
        state.tick = 16;
        assert!(state.is_reproductively_ready(parent_id));

        Arc::make_mut(&mut state.organism_mut(parent_id).phenotype).fertility = 0.64;
        Arc::make_mut(&mut state.organism_mut(mate_id).phenotype).fertility = 0.81;
        Arc::make_mut(&mut state.organism_mut(parent_id).phenotype).sexual = 0.49;
        Arc::make_mut(&mut state.organism_mut(mate_id).phenotype).sexual = 0.36;
        let distance = state
            .organism(parent_id)
            .genome
            .distance(&state.organism(mate_id).genome);
        let expected =
            (0.64_f64 * 0.81).sqrt() * (0.49_f64 * 0.36).sqrt() * (-4.0 * distance).exp();
        let actual = state.sexual_success_probability(parent_id, mate_id);
        assert!((actual - expected.min(1.0)).abs() < 1e-15);
    }

    #[test]
    fn successful_asexual_attempt_counts_one_event() {
        let mut state = KernelState::new(test_config(1)).unwrap();
        let parent_id = *state.living.iter().next().unwrap();
        state.tick = 1;
        state.config.asexual_probability_floor = 1.0;
        state.config.reference_reproduction_cost = 0.0;
        {
            let parent = state.organism_mut(parent_id);
            parent.birth_tick = 0;
            Arc::make_mut(&mut parent.phenotype).maturity_age = 1;
            Arc::make_mut(&mut parent.phenotype).reproduction_fraction = 0.2;
            parent.reproduction_cooldown = 0;
            parent.body[0].count = parent.body[0].count.max(10);
            parent.invalidate_body_cache();
        }
        state.attempt_reproduction(parent_id, None);
        assert_eq!(state.stats.births, 1);
        assert_eq!(state.stats.successful_reproductions, 1);
        assert_eq!(state.stats.asexual_reproduction_events, 1);
        assert_eq!(state.stats.sexual_reproduction_events, 0);
    }

    #[test]
    fn compressibility_metrics_are_observational_and_bounded() {
        let mut state = KernelState::new(test_config(120)).unwrap();
        let initial = state.compressibility_metrics();
        assert_eq!(initial.novel_organisms, initial.population);
        assert_eq!(initial.lineage_safe.represented_work, initial.population);
        assert_eq!(initial.species_safe.represented_work, initial.population);

        state.step(100);
        let digest_before = state.digest();
        let metrics = state.compressibility_metrics();
        assert_eq!(state.digest(), digest_before);
        assert!(metrics.exact_policy_keys <= metrics.population);
        for summary in [
            metrics.lineage_safe,
            metrics.species_safe,
            metrics.trait_only,
        ] {
            assert!(summary.protected <= metrics.population);
            assert!(summary.classes <= metrics.population - summary.protected);
            assert!(summary.representatives <= metrics.population - summary.protected);
            assert!(summary.represented_work <= metrics.population);
        }
    }

    #[test]
    fn dense_living_arena_repairs_sparse_indices_on_death() {
        let mut state = KernelState::new(test_config(40)).unwrap();
        let before = state.organisms.len();
        let organism_id = *state.living_ordered.iter().nth(5).unwrap();
        let genome_id = state.organism(organism_id).genome.genome_id;

        state.kill(organism_id, last_action::DEAD_ATTRITION);

        assert_eq!(state.organisms.len(), before - 1);
        assert!(!state.has_organism(organism_id));
        assert_eq!(state.genome_owners[genome_id as usize - 1], 0);
        assert_eq!(state.dead_records.last().unwrap().organism_id, organism_id);
        for &living_id in &state.living_ordered {
            assert_eq!(state.organism(living_id).organism_id, living_id);
        }
    }

    #[test]
    fn environmental_reaction_conserves_elements_and_energy() {
        let mut config = test_config(4);
        config.dynamic_chemistry_enabled = true;
        config.environmental_reaction_rate = 1.0;
        config.reaction_thermodynamics = 0.25;
        let mut state = KernelState::new(config).unwrap();
        let rule = state
            .reaction_rules
            .first()
            .copied()
            .expect("dynamic catalog should contain a reaction rule");
        let position = (0, 0);
        let first_capacity = state.catalog.molecules[rule.a as usize].energy_capacity;
        let second_capacity = state.catalog.molecules[rule.b as usize].energy_capacity;
        state.world.deposit_batch_raw(
            position,
            Batch {
                molecule_id: rule.a,
                count: if rule.a == rule.b { 2 } else { 1 },
                energy: first_capacity * if rule.a == rule.b { 2.0 } else { 1.0 },
            },
        );
        if rule.a != rule.b {
            state.world.deposit_batch_raw(
                position,
                Batch {
                    molecule_id: rule.b,
                    count: 1,
                    energy: second_capacity,
                },
            );
        }
        state.deposit_positions.clear();
        state.deposit_positions.push(position);
        state.reaction_positions.clear();
        state.reaction_positions.push(position);
        let before_elements = state.dynamic_element_totals();
        let before_energy = state.total_energy();
        state.run_environmental_reactions();
        let after_elements = state.dynamic_element_totals();
        let after_energy = state.total_energy();

        assert_eq!(state.stats.environmental_reactions, 1);
        assert_eq!(after_elements, before_elements);
        assert!((after_energy - before_energy).abs() <= 1.0e-9);
        assert!(state.world.deposits[&position]
            .iter()
            .any(|batch| batch.molecule_id == rule.c && batch.count > 0));
    }

    #[test]
    fn dynamic_chemistry_is_deterministic_conservative_and_local() {
        let config = SimConfig {
            dynamic_chemistry_enabled: true,
            environmental_reaction_rate: 0.5,
            ..test_config(60)
        };
        let mut left = KernelState::new(config.clone()).unwrap();
        let mut right = KernelState::new(config).unwrap();
        left.step(80);
        right.step(80);
        assert_eq!(left.digest(), right.digest());
        let (left_elements, left_energy) = left.audit(false).unwrap();
        let (right_elements, right_energy) = right.audit(false).unwrap();
        assert!(left_elements.iter().all(|&error| error == 0));
        assert!(right_elements.iter().all(|&error| error == 0));
        assert!(
            left_energy.abs() <= energy_tolerance(left.initial_energy, left.world.generated_energy)
        );
        assert!(
            right_energy.abs()
                <= energy_tolerance(right.initial_energy, right.world.generated_energy)
        );
        let organism_id = *left.living_ordered.iter().next().unwrap();
        let position = left.organism(organism_id).position;
        left.world.add_byproduct(position, 1.0, 0.0);
        let favorable = left.local_chemistry_fit(left.organism(organism_id));
        left.world.add_byproduct(position, 0.0, 2.0);
        let unfavorable = left.local_chemistry_fit(left.organism(organism_id));
        assert!(favorable > 0.0);
        assert!(unfavorable < favorable);
    }

    #[test]
    fn ecology_stays_alive() {
        let mut state = KernelState::new(test_config(300)).unwrap();
        state.step(300);
        assert!(
            state.population() > 50,
            "population crashed to {}",
            state.population()
        );
        assert!(state.stats.births > 0, "no births occurred");
        assert!(state.stats.deaths > 0, "no deaths occurred");
    }
}
