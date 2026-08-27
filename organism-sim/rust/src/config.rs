//! Simulation configuration, mirroring `organism_sim.config.SimulationConfig`.
//! Field names and defaults match the Python prototype except for explicitly
//! versioned Rust-only behavior scaffold fields.

use crate::behavior::BehaviorModel;
use crate::scheduler::Scheduler;

#[derive(Clone, Debug)]
pub struct SimConfig {
    pub seed: i64,
    pub behavior_model: BehaviorModel,
    pub scheduler: Scheduler,
    /// Zero selects Rayon's machine-local default worker count.
    pub parallel_workers: usize,
    // width/height describe only the founder spawn region; the world extends
    // without bound as chunks are generated on demand.
    pub width: i64,
    pub height: i64,
    pub chunk_size: usize,
    pub founder_count: usize,
    pub founder_archetype_count: usize,
    pub element_count: usize,
    pub molecule_count: usize,
    pub chemical_signature_dimensions: i64,
    pub initial_deposits: i64,
    pub initial_batch_min: i64,
    pub initial_batch_max: i64,
    pub maximum_molecule_units: i64,

    pub heat_diffusion: f64,
    pub mana_decay: f64,
    pub primary_production_rate: f64,
    pub deposit_production_rate: f64,
    pub deposit_match_ecology: bool,
    pub decomposition_rate: f64,
    pub mutation_multiplier: f64,
    pub reaction_rate: f64,
    pub maintenance_cost_multiplier: f64,

    pub seasons_enabled: bool,
    pub season_duration_min: u32,
    pub season_duration_max: u32,
    pub season_transition_ticks: u32,
    pub season_strength: f64,

    pub cellular_emergence_enabled: bool,
    pub emergence_max_modules: usize,
    pub emergence_structural_mutation_rate: f64,
    pub emergence_module_cost: f64,
    pub emergence_module_effect: f64,
    pub emergence_bond_rate: f64,
    pub emergence_bond_break_rate: f64,
    pub emergence_exchange_rate: f64,
    pub emergence_engulfment_rate: f64,
    pub emergence_max_internal_guests: usize,
    pub emergence_coordinated_components: bool,

    pub biodeposits_enabled: bool,
    pub biodeposit_decay_rate: f64,
    pub biodeposit_movement_resistance: f64,
    pub biodeposit_cover_strength: f64,
    pub biodeposit_concealment: f64,

    pub reference_move_cost: f64,
    pub reference_attack_cost: f64,
    pub attack_damage_multiplier: f64,
    pub reference_ingest_cost: f64,
    pub reference_reproduction_cost: f64,
    pub reproduction_cost_multiplier: f64,
    pub reproduction_cooldown_multiplier: f64,
    pub maturity_age_multiplier: f64,
    pub reproduction_action_bonus: f64,
    pub asexual_probability_floor: f64,
    pub sexual_probability_floor_enabled: bool,
    pub sexual_probability_floor: f64,
    pub sight_cost_per_cell: f64,
    pub failed_move_cost_fraction: f64,

    // V2 behavior scaffold. These are startup-only and have no effect while
    // the legacy controller is selected.
    pub v2_founder_priors_enabled: bool,
    pub recurrent_state_lesion: bool,
    /// Enables observational counterfactual memory telemetry without affecting actions.
    pub memory_probe_enabled: bool,
    pub brain_cost_multiplier: f64,
    pub brain_base_cost: f64,
    pub brain_hidden_cost: f64,
    pub brain_recurrent_cost: f64,

    pub species_distance_threshold: f64,
    pub prey_compatibility_threshold: f64,
    pub new_species_marker_ticks: i64,
    pub alliance_probability: f64,
    pub colony_bonus_cap: f64,
    pub sexual_colony_max: f64,
    pub asexual_colony_min: f64,

    pub max_sight: usize,
    pub audit_every: u32,
}

impl Default for SimConfig {
    fn default() -> Self {
        SimConfig {
            seed: 7,
            behavior_model: BehaviorModel::default(),
            scheduler: Scheduler::default(),
            parallel_workers: 0,
            width: 128,
            height: 128,
            chunk_size: 32,
            founder_count: 300,
            founder_archetype_count: 8,
            element_count: 8,
            molecule_count: 48,
            chemical_signature_dimensions: 4,
            initial_deposits: 2600,
            initial_batch_min: 4,
            initial_batch_max: 20,
            maximum_molecule_units: 12,
            heat_diffusion: 0.08,
            mana_decay: 0.002,
            primary_production_rate: 0.0,
            deposit_production_rate: 0.10,
            deposit_match_ecology: false,
            decomposition_rate: 0.0008,
            mutation_multiplier: 1.0,
            reaction_rate: 1.0,
            maintenance_cost_multiplier: 0.75,
            seasons_enabled: false,
            season_duration_min: 500,
            season_duration_max: 1500,
            season_transition_ticks: 100,
            season_strength: 0.65,
            cellular_emergence_enabled: false,
            emergence_max_modules: 12,
            emergence_structural_mutation_rate: 0.02,
            emergence_module_cost: 0.002,
            emergence_module_effect: 0.25,
            emergence_bond_rate: 0.01,
            emergence_bond_break_rate: 0.002,
            emergence_exchange_rate: 0.02,
            emergence_engulfment_rate: 0.01,
            emergence_max_internal_guests: 4,
            emergence_coordinated_components: true,
            biodeposits_enabled: false,
            biodeposit_decay_rate: 0.001,
            biodeposit_movement_resistance: 0.25,
            biodeposit_cover_strength: 0.35,
            biodeposit_concealment: 0.10,
            reference_move_cost: 0.010,
            reference_attack_cost: 0.020,
            attack_damage_multiplier: 2.0,
            reference_ingest_cost: 0.002,
            reference_reproduction_cost: 0.100,
            reproduction_cost_multiplier: 0.50,
            reproduction_cooldown_multiplier: 0.75,
            maturity_age_multiplier: 0.65,
            reproduction_action_bonus: 1.25,
            asexual_probability_floor: 0.20,
            sexual_probability_floor_enabled: true,
            sexual_probability_floor: 0.12,
            sight_cost_per_cell: 0.0005,
            failed_move_cost_fraction: 0.25,
            v2_founder_priors_enabled: true,
            recurrent_state_lesion: false,
            memory_probe_enabled: false,
            brain_cost_multiplier: 1.0,
            brain_base_cost: 0.001,
            brain_hidden_cost: 0.002,
            brain_recurrent_cost: 0.002,
            species_distance_threshold: 0.22,
            prey_compatibility_threshold: 0.35,
            new_species_marker_ticks: 500,
            alliance_probability: 0.015,
            colony_bonus_cap: 0.15,
            sexual_colony_max: 0.25,
            asexual_colony_min: 0.35,
            max_sight: 6,
            audit_every: 20,
        }
    }
}

impl SimConfig {
    pub fn replaces_abstract_colonies(&self) -> bool {
        self.cellular_emergence_enabled
            && (self.emergence_module_effect > 0.0
                || self.emergence_bond_rate > 0.0
                || self.emergence_exchange_rate > 0.0
                || self.emergence_engulfment_rate > 0.0)
    }

    pub fn validate(&self) -> Result<(), String> {
        if self.parallel_workers > 256 {
            return Err("parallel_workers must be zero (auto) or at most 256".into());
        }
        if self.scheduler == Scheduler::ParallelV3 {
            if self.behavior_model == BehaviorModel::LegacyLinearMacroV1 {
                return Err("parallel-v3 requires a V2 intent behavior model".into());
            }
            if self.cellular_emergence_enabled && self.emergence_coordinated_components {
                return Err(
                    "parallel-v3 does not yet support coordinated cellular components".into(),
                );
            }
        }
        if self.width < 16 || self.height < 16 {
            return Err("founder-region dimensions must be at least 16".into());
        }
        if !(8..=128).contains(&self.chunk_size) {
            return Err("chunk_size must be between 8 and 128".into());
        }
        if !(2..=16).contains(&self.element_count) {
            return Err("element_count must be between 2 and 16".into());
        }
        if self.molecule_count < self.element_count {
            return Err("molecule_count must include monatomic fallbacks".into());
        }
        if self.molecule_count > u16::MAX as usize {
            return Err("molecule_count must fit in a 16-bit molecule id".into());
        }
        if self.initial_deposits < 0 {
            return Err("initial_deposits must be nonnegative".into());
        }
        if self.initial_batch_min < 1 || self.initial_batch_max < self.initial_batch_min {
            return Err("initial batch bounds must be positive and ordered".into());
        }
        if !(2..=u8::MAX as i64).contains(&self.maximum_molecule_units) {
            return Err("maximum_molecule_units must be in [2, 255]".into());
        }
        if self.founder_count < 1 {
            return Err("founder_count must be positive".into());
        }
        if self.founder_archetype_count < 1 {
            return Err("founder_archetype_count must be positive".into());
        }
        if !(0.0..=0.25).contains(&self.heat_diffusion) {
            return Err("heat_diffusion must be in [0, 0.25]".into());
        }
        if !(0.0..=1.0).contains(&self.primary_production_rate) {
            return Err("primary_production_rate must be in [0, 1]".into());
        }
        if self.season_duration_min < 1 || self.season_duration_max < self.season_duration_min {
            return Err("season duration bounds must be positive and ordered".into());
        }
        if self.season_transition_ticks > self.season_duration_min {
            return Err("season_transition_ticks must not exceed season_duration_min".into());
        }
        if !self.season_strength.is_finite() || !(0.0..=1.0).contains(&self.season_strength) {
            return Err("season_strength must be finite and in [0, 1]".into());
        }
        if !(1..=64).contains(&self.emergence_max_modules) {
            return Err("emergence_max_modules must be in [1, 64]".into());
        }
        if self.emergence_max_internal_guests > 32 {
            return Err("emergence_max_internal_guests must be in [0, 32]".into());
        }
        for (name, value) in [
            ("mana_decay", self.mana_decay),
            ("deposit_production_rate", self.deposit_production_rate),
            ("decomposition_rate", self.decomposition_rate),
            ("mutation_multiplier", self.mutation_multiplier),
            ("reaction_rate", self.reaction_rate),
            (
                "maintenance_cost_multiplier",
                self.maintenance_cost_multiplier,
            ),
            ("attack_damage_multiplier", self.attack_damage_multiplier),
            (
                "reproduction_cost_multiplier",
                self.reproduction_cost_multiplier,
            ),
            (
                "reproduction_cooldown_multiplier",
                self.reproduction_cooldown_multiplier,
            ),
            ("reproduction_action_bonus", self.reproduction_action_bonus),
            ("sight_cost_per_cell", self.sight_cost_per_cell),
            ("failed_move_cost_fraction", self.failed_move_cost_fraction),
            ("brain_cost_multiplier", self.brain_cost_multiplier),
            ("brain_base_cost", self.brain_base_cost),
            ("brain_hidden_cost", self.brain_hidden_cost),
            ("brain_recurrent_cost", self.brain_recurrent_cost),
            (
                "emergence_structural_mutation_rate",
                self.emergence_structural_mutation_rate,
            ),
            ("emergence_module_cost", self.emergence_module_cost),
            ("emergence_module_effect", self.emergence_module_effect),
            ("emergence_bond_rate", self.emergence_bond_rate),
            ("emergence_bond_break_rate", self.emergence_bond_break_rate),
            ("emergence_exchange_rate", self.emergence_exchange_rate),
            ("emergence_engulfment_rate", self.emergence_engulfment_rate),
            ("biodeposit_decay_rate", self.biodeposit_decay_rate),
            (
                "biodeposit_movement_resistance",
                self.biodeposit_movement_resistance,
            ),
            ("biodeposit_cover_strength", self.biodeposit_cover_strength),
            ("biodeposit_concealment", self.biodeposit_concealment),
            ("alliance_probability", self.alliance_probability),
            ("colony_bonus_cap", self.colony_bonus_cap),
        ] {
            if !value.is_finite() || value < 0.0 {
                return Err(format!("{name} must be finite and nonnegative"));
            }
        }
        for (name, value) in [
            ("asexual_probability_floor", self.asexual_probability_floor),
            ("sexual_probability_floor", self.sexual_probability_floor),
            (
                "species_distance_threshold",
                self.species_distance_threshold,
            ),
            (
                "prey_compatibility_threshold",
                self.prey_compatibility_threshold,
            ),
            ("sexual_colony_max", self.sexual_colony_max),
            ("asexual_colony_min", self.asexual_colony_min),
        ] {
            if !(0.0..=1.0).contains(&value) {
                return Err(format!("{name} must be in [0, 1]"));
            }
        }
        if !self.maturity_age_multiplier.is_finite() || self.maturity_age_multiplier <= 0.0 {
            return Err("maturity_age_multiplier must be finite and positive".into());
        }
        for (name, value) in [
            ("reference_move_cost", self.reference_move_cost),
            ("reference_attack_cost", self.reference_attack_cost),
            ("reference_ingest_cost", self.reference_ingest_cost),
            (
                "reference_reproduction_cost",
                self.reference_reproduction_cost,
            ),
        ] {
            if !value.is_finite() || value < 0.0 {
                return Err(format!("{name} must be finite and nonnegative"));
            }
        }
        if self.chemical_signature_dimensions != 4 {
            return Err("the prototype currently uses four signature dimensions".into());
        }
        if self.max_sight < 1 || self.max_sight > 64 {
            return Err("max_sight must be in [1, 64]".into());
        }
        Ok(())
    }
}
