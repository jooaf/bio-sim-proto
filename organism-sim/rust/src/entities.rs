//! Entities: organisms, species, effects, corpses, colonies, stats.
//! Port of `organism_sim.entities`.

use crate::behavior::neural::NeuralState;
use crate::chemistry::{inventory_energy, Catalog, Inventory, Signature};
use crate::emergence::{CellularState, ModulePrimitive, REGULATORY_INPUTS};
use crate::genetics::{Genome, Phenotype};
use rustc_hash::{FxHashMap, FxHashSet};
use std::sync::Arc;

pub type Position = (i64, i64);

/// Last-action encoding for snapshots: 0 = born, 1..=13 = ACTIONS index+1,
/// 100+ = death causes.
pub mod last_action {
    pub const BORN: u8 = 0;
    pub const V2_WAIT: u8 = 20;
    pub const V2_MOVE: u8 = 21;
    pub const V2_INGEST: u8 = 22;
    pub const V2_REPAIR: u8 = 23;
    pub const V2_ABSORB_HEAT: u8 = 24;
    pub const V2_DETOX: u8 = 25;
    pub const V2_ATTACK: u8 = 26;
    pub const V2_CAST_MAGIC: u8 = 27;
    pub const V2_REPRODUCE: u8 = 28;
    pub const V2_PROPOSE_ALLIANCE: u8 = 29;
    pub const DEAD_ATTRITION: u8 = 100;
    pub const DEAD_PREDATION: u8 = 101;
    pub const DEAD_FIRE: u8 = 102;

    pub fn name(code: u8) -> &'static str {
        match code {
            BORN => "born",
            DEAD_ATTRITION => "dead:attrition",
            DEAD_PREDATION => "dead:predation",
            DEAD_FIRE => "dead:fire",
            1..=13 => crate::genetics::ACTION_NAMES[(code - 1) as usize],
            V2_WAIT => "wait",
            V2_MOVE => "move_one_tile",
            V2_INGEST => "ingest",
            V2_REPAIR => "repair",
            V2_ABSORB_HEAT => "absorb_heat",
            V2_DETOX => "detox",
            V2_ATTACK => "physical_attack",
            V2_CAST_MAGIC => "cast_magic",
            V2_REPRODUCE => "reproduce",
            V2_PROPOSE_ALLIANCE => "propose_alliance",
            _ => "unknown",
        }
    }
}

#[derive(Clone, Debug)]
pub struct Organism {
    pub organism_id: u32,
    pub lineage_id: u32,
    pub genome: Arc<Genome>,
    pub phenotype: Arc<Phenotype>,
    pub species_id: u32,
    pub parent_ids: Vec<u32>,
    pub generation: u32,
    pub birth_tick: u32,
    pub position: Position,
    pub body: Inventory,
    pub gut: Inventory,
    pub waste: Inventory,
    pub mana: f64,
    pub integrity: f64,
    pub max_integrity: f64,
    pub target_mass: f64,
    pub maintenance_debt: f64,
    pub toxin_load: f64,
    /// Catalog-derived mean reactivity of the organism's diet signature.
    /// Filled by the kernel when the phenotype is sampled.
    pub diet_reactivity_mean: f64,
    pub reproduction_cooldown: u32,
    pub alive: bool,
    pub facing: (i32, i32),
    pub next_action_tick: u32,
    pub last_action: u8,
    pub last_intent_kind: u8,
    pub decision_count: u32,
    pub brain_energy_spent: f64,
    pub hidden_brain_energy_spent: f64,
    pub recurrent_brain_energy_spent: f64,
    pub neural_state: NeuralState,
    pub neural_numerical_errors: u32,
    /// Analysis-only trace of the strongest food sector at the previous V2 decision.
    pub previous_food_slot: u8,
    pub previous_food_signal: f32,
    pub offspring_count: u32,
    pub kills: u32,
    pub colony_id: Option<u32>,
    pub cellular: Option<CellularState>,
    /// (expires_tick, effect_id) for water/earth magic statuses.
    pub water_status: Option<(u32, u32)>,
    pub earth_status: Option<(u32, u32)>,
    // caches
    cached_structural_mass: Option<i64>,
    cached_energy_capacity: Option<f64>,
    cached_body_signature: Option<Signature>,
    cached_food_chemistry: Option<Vec<(f64, f64)>>,
}

impl Organism {
    pub fn new(
        organism_id: u32,
        lineage_id: u32,
        genome: Genome,
        phenotype: Phenotype,
        body: Inventory,
        target_mass: f64,
    ) -> Organism {
        Organism::new_shared(
            organism_id,
            lineage_id,
            Arc::new(genome),
            Arc::new(phenotype),
            body,
            target_mass,
        )
    }

    pub fn new_shared(
        organism_id: u32,
        lineage_id: u32,
        genome: Arc<Genome>,
        phenotype: Arc<Phenotype>,
        body: Inventory,
        target_mass: f64,
    ) -> Organism {
        let cellular = genome
            .emergence
            .as_ref()
            .map(|emergence| CellularState::new(emergence.modules.len()));
        Organism {
            organism_id,
            lineage_id,
            genome,
            phenotype,
            species_id: 0,
            parent_ids: Vec::new(),
            generation: 0,
            birth_tick: 0,
            position: (0, 0),
            body,
            gut: Inventory::new(),
            waste: Inventory::new(),
            mana: 0.0,
            integrity: 1.0,
            max_integrity: 1.0,
            target_mass,
            maintenance_debt: 0.0,
            toxin_load: 0.0,
            diet_reactivity_mean: 0.0,
            reproduction_cooldown: 0,
            alive: true,
            facing: (1, 0),
            next_action_tick: 0,
            last_action: last_action::BORN,
            last_intent_kind: u8::MAX,
            decision_count: 0,
            brain_energy_spent: 0.0,
            hidden_brain_energy_spent: 0.0,
            recurrent_brain_energy_spent: 0.0,
            neural_state: NeuralState::default(),
            neural_numerical_errors: 0,
            previous_food_slot: u8::MAX,
            previous_food_signal: 0.0,
            offspring_count: 0,
            kills: 0,
            colony_id: None,
            cellular,
            water_status: None,
            earth_status: None,
            cached_structural_mass: None,
            cached_energy_capacity: None,
            cached_body_signature: None,
            cached_food_chemistry: None,
        }
    }

    pub fn regulate_cellular(&mut self, inputs: [f32; REGULATORY_INPUTS]) {
        if let (Some(genome), Some(state)) = (&self.genome.emergence, &mut self.cellular) {
            state.regulate(genome, inputs);
        }
    }

    pub fn module_expression(&self, primitive: ModulePrimitive) -> f64 {
        match (&self.genome.emergence, &self.cellular) {
            (Some(genome), Some(state)) => state.primitive_expression(genome, primitive),
            _ => 0.0,
        }
    }

    pub fn substrate_module_expression(&self, primitive: ModulePrimitive, substrate: u16) -> f64 {
        match (&self.genome.emergence, &self.cellular) {
            (Some(genome), Some(state)) => state.substrate_expression(genome, primitive, substrate),
            _ => 0.0,
        }
    }

    pub fn module_upkeep(&self) -> f64 {
        match (&self.genome.emergence, &self.cellular) {
            (Some(genome), Some(state)) => state.upkeep(genome),
            _ => 0.0,
        }
    }

    pub fn inventories(&mut self) -> [&mut Inventory; 3] {
        [&mut self.body, &mut self.gut, &mut self.waste]
    }

    pub fn structural_mass(&mut self, catalog: &Catalog) -> i64 {
        if self.cached_structural_mass.is_none() {
            self.cached_structural_mass = Some(catalog.inventory_mass(&self.body));
        }
        self.cached_structural_mass.unwrap()
    }

    pub fn peek_structural_mass(&self, catalog: &Catalog) -> i64 {
        match self.cached_structural_mass {
            Some(v) => v,
            None => catalog.inventory_mass(&self.body),
        }
    }

    pub fn invalidate_body_cache(&mut self) {
        self.cached_structural_mass = None;
        self.cached_energy_capacity = None;
        self.cached_body_signature = None;
    }

    pub fn area(&mut self, catalog: &Catalog) -> usize {
        let mass = self.structural_mass(catalog) as f64;
        let ratio = (mass / self.target_mass.max(1.0)).min(1.0);
        let adult = self.phenotype.adult_area;
        let rounded = crate::rng::py_round(adult as f64 * ratio).max(1).min(adult);
        rounded as usize
    }

    pub fn chemical_energy(&self) -> f64 {
        inventory_energy(&self.body)
    }

    pub fn energy_capacity(&mut self, catalog: &Catalog) -> f64 {
        if self.cached_energy_capacity.is_none() {
            let mut cap = 0.0;
            for batch in &self.body {
                cap += catalog.molecules[batch.molecule_id as usize].energy_capacity
                    * batch.count as f64;
            }
            self.cached_energy_capacity = Some(cap);
        }
        self.cached_energy_capacity.unwrap()
    }

    pub fn energy_fraction(&mut self, catalog: &Catalog) -> f64 {
        let capacity = self.energy_capacity(catalog);
        if capacity > 0.0 {
            self.chemical_energy() / capacity
        } else {
            0.0
        }
    }

    pub fn add_body_energy(&mut self, amount: f64, catalog: &Catalog) -> f64 {
        let mut remaining = amount.max(0.0);
        for batch in self.body.iter_mut() {
            let capacity =
                catalog.molecules[batch.molecule_id as usize].energy_capacity * batch.count as f64;
            let accepted = remaining.min((capacity - batch.energy).max(0.0));
            batch.energy += accepted;
            remaining -= accepted;
            if remaining <= 1e-15 {
                break;
            }
        }
        amount - remaining
    }

    pub fn consume_body_energy(&mut self, amount: f64) -> f64 {
        let mut remaining = amount.max(0.0);
        let mut consumed = 0.0;
        for batch in self.body.iter_mut() {
            let debit = batch.energy.min(remaining);
            batch.energy -= debit;
            remaining -= debit;
            consumed += debit;
            if remaining <= 1e-15 {
                break;
            }
        }
        consumed
    }

    pub fn body_signature(&mut self, catalog: &Catalog) -> Signature {
        if self.cached_body_signature.is_none() {
            self.cached_body_signature = Some(catalog.inventory_signature(&self.body));
        }
        self.cached_body_signature.unwrap()
    }

    pub fn all_inventories(&self) -> [&Inventory; 3] {
        [&self.body, &self.gut, &self.waste]
    }

    /// Cache (match, hazard) per molecule id from the immutable phenotype.
    pub fn ensure_food_chemistry(&mut self, catalog: &Catalog) {
        if self.cached_food_chemistry.is_none() {
            self.cached_food_chemistry = Some(build_food_chemistry(&self.phenotype, catalog));
        }
    }

    #[inline]
    pub fn food_chemistry_at(&self, molecule_id: usize) -> (f64, f64) {
        self.cached_food_chemistry
            .as_ref()
            .expect("food chemistry must be initialized")[molecule_id]
    }
}

pub fn build_food_chemistry(phenotype: &Phenotype, catalog: &Catalog) -> Vec<(f64, f64)> {
    let tolerance = phenotype.toxin_tolerance.max(0.1);
    catalog
        .molecules
        .iter()
        .map(|def| {
            let m = crate::genetics::similarity(&def.signature, &phenotype.diet_signature);
            let dot: f64 = (0..4)
                .map(|i| def.signature[i] * phenotype.toxin_sensitivity[i])
                .sum();
            (m, def.reactivity * dot / tolerance)
        })
        .collect()
}

#[derive(Clone, Debug)]
pub struct Species {
    pub species_id: u32,
    pub representative_genome: Genome,
    pub color: [u8; 3],
    pub created_tick: u32,
    pub origin: u8, // 0 founder, 1 mutation, 2 sexual
    pub parent_species_ids: Vec<u32>,
    pub founder_organism_id: Option<u32>,
    pub population: i64,
    pub births: i64,
    pub deaths: i64,
}

#[derive(Clone, Debug)]
pub struct MagicEffect {
    pub effect_id: u32,
    pub channel: u8,
    pub source_id: u32,
    pub target_id: u32,
    pub energy: f64,
    pub expires_tick: u32,
}

#[derive(Clone, Debug)]
pub struct Corpse {
    pub corpse_id: u32,
    pub source_id: u32,
    pub position: Position,
    pub created_tick: u32,
}

#[derive(Clone, Debug)]
pub struct Colony {
    pub colony_id: u32,
    pub members: FxHashSet<u32>,
    pub bonus: f64,
    pub created_tick: u32,
}

#[derive(Clone, Debug, Default)]
pub struct Stats {
    pub births: i64,
    pub deaths: i64,
    pub reproduction_attempts: i64,
    pub reproduction_resource_blocks: i64,
    pub reproduction_mate_readiness_blocks: i64,
    pub reproduction_energy_blocks: i64,
    pub reproduction_body_matter_blocks: i64,
    pub reproduction_matter_blocks_by_molecule: FxHashMap<u16, i64>,
    pub reproduction_probability_failures: i64,
    pub reproduction_placement_failures: i64,
    pub failed_reproductions: i64,
    pub successful_reproductions: i64,
    pub asexual_reproduction_events: i64,
    pub sexual_reproduction_events: i64,
    pub attacks: i64,
    pub magic_casts: i64,
    pub alliances: i64,
    pub colonies: i64,
    pub brain_energy_spent: f64,
    pub hidden_brain_energy_spent: f64,
    pub recurrent_brain_energy_spent: f64,
    pub neural_numerical_errors: u64,
    pub memory_probe_decisions: u64,
    pub memory_probe_state_l1_sum: f64,
    pub memory_probe_argmax_changes: u64,
    pub memory_probe_ambiguous_food_events: u64,
    pub memory_probe_ambiguous_argmax_changes: u64,
    pub memory_probe_stateful_return_choices: u64,
    pub memory_probe_zero_state_return_choices: u64,
    pub v2_intent_counts: [u64; crate::behavior::intent::INTENT_TYPE_COUNT],
    pub v2_intent_failures: u64,
    pub audit_error: f64,
    pub environmental_reactions: u64,
    pub byproduct_emissions: u64,
}
