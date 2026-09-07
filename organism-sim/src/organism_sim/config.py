from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from math import isfinite


class BehaviorModel(StrEnum):
    LEGACY_LINEAR_MACRO_V1 = "legacy_linear_macro_v1"
    LINEAR_INTENT_V2 = "linear_intent_v2"
    RECURRENT_INTENT_V2 = "recurrent_intent_v2"


class Scheduler(StrEnum):
    SERIAL_V2 = "serial-v2"
    PARALLEL_V3 = "parallel-v3"


@dataclass(slots=True)
class SimulationConfig:
    """All prototype constants live here so the UI can expose them."""

    seed: int = 7
    behavior_model: BehaviorModel = BehaviorModel.LEGACY_LINEAR_MACRO_V1
    scheduler: Scheduler = Scheduler.SERIAL_V2
    parallel_workers: int = 0
    # width/height now describe only the founder spawn region; the world itself
    # extends without bound in every direction as chunks are generated on demand.
    width: int = 128
    height: int = 128
    chunk_size: int = 32
    founder_count: int = 300
    founder_archetype_count: int = 8
    element_count: int = 8
    molecule_count: int = 48
    chemical_signature_dimensions: int = 4
    initial_deposits: int = 2600
    initial_batch_min: int = 4
    initial_batch_max: int = 20
    maximum_molecule_units: int = 12

    ticks_per_second: float = 20.0
    heat_diffusion: float = 0.08
    mana_decay: float = 0.002
    primary_production_rate: float = 0.0
    deposit_production_rate: float = 0.10
    deposit_match_ecology: bool = False
    decomposition_rate: float = 0.0008
    mutation_multiplier: float = 1.0
    reaction_rate: float = 1.0
    maintenance_cost_multiplier: float = 0.75

    # Rust-only exogenous environment schedule. Seasons change resource-energy
    # availability, never species fitness or controller behavior directly.
    seasons_enabled: bool = False
    season_duration_min: int = 500
    season_duration_max: int = 1500
    season_transition_ticks: int = 100
    season_strength: float = 0.65

    # Generic stochastic cellular affordances. No higher-level state or fitness
    # label is assigned; connected groups and internal guests remain physical facts.
    cellular_emergence_enabled: bool = False
    emergence_max_modules: int = 12
    emergence_structural_mutation_rate: float = 0.02
    emergence_module_cost: float = 0.002
    emergence_module_effect: float = 0.25
    emergence_bond_rate: float = 0.01
    emergence_bond_break_rate: float = 0.002
    emergence_exchange_rate: float = 0.02
    emergence_engulfment_rate: float = 0.01
    emergence_max_internal_guests: int = 4
    emergence_coordinated_components: bool = True

    # Rust-only physical packing left by dead biomass. Matter remains in the
    # ordinary edible deposit inventory; this field records its spatial structure.
    biodeposits_enabled: bool = False
    biodeposit_decay_rate: float = 0.001
    biodeposit_movement_resistance: float = 0.25
    biodeposit_cover_strength: float = 0.35
    biodeposit_concealment: float = 0.10

    # Rust-only dynamic chemistry: organism metabolic byproducts become local
    # environmental conditions (catalyst/toxin fields) that feed back into
    # digestion efficiency, internal-guest upkeep, and niche fit. These are
    # scalar conditions, not ledgered matter or energy, so conservation is
    # unaffected. Organisms influence the environment; the environment
    # influences organisms.
    dynamic_chemistry_enabled: bool = False
    reaction_rule_count: int = 6
    environmental_reaction_rate: float = 0.02
    reaction_thermodynamics: float = 0.10
    byproduct_strength: float = 0.02
    byproduct_decay_rate: float = 0.02
    chemistry_coupling: float = 0.50
    guest_niche_coupling: float = 0.50

    reference_move_cost: float = 0.010
    reference_attack_cost: float = 0.020
    attack_damage_multiplier: float = 2.0
    reference_ingest_cost: float = 0.002
    reference_reproduction_cost: float = 0.100
    reproduction_cost_multiplier: float = 0.50
    reproduction_cooldown_multiplier: float = 0.75
    maturity_age_multiplier: float = 0.65
    reproduction_action_bonus: float = 1.25
    asexual_probability_floor: float = 0.20
    sexual_probability_floor_enabled: bool = True
    sexual_probability_floor: float = 0.12
    sight_cost_per_cell: float = 0.0005
    failed_move_cost_fraction: float = 0.25

    # Startup-only V2 behavior and observational-analysis controls.
    v2_founder_priors_enabled: bool = True
    recurrent_state_lesion: bool = False
    memory_probe_enabled: bool = False
    brain_cost_multiplier: float = 1.0
    brain_base_cost: float = 0.001
    brain_hidden_cost: float = 0.002
    brain_recurrent_cost: float = 0.002

    species_distance_threshold: float = 0.22
    prey_compatibility_threshold: float = 0.35
    new_species_marker_ticks: int = 500
    alliance_probability: float = 0.015
    colony_bonus_cap: float = 0.15
    sexual_colony_max: float = 0.25
    asexual_colony_min: float = 0.35

    tile_pixels: int = 6
    panel_width: int = 390
    max_sight: int = 6
    render_fps: int = 30
    audit_every: int = 20
    recording_metrics_interval: int = 5
    recording_detail_interval: int = 20
    recording_snapshot_interval: int = 50
    recording_commit_interval: int = 50

    def evolved(self, **changes: object) -> SimulationConfig:
        return replace(self, **changes)

    def validate(self) -> None:
        if not isinstance(self.behavior_model, BehaviorModel):
            raise TypeError("behavior_model must be a BehaviorModel")
        if not isinstance(self.scheduler, Scheduler):
            raise TypeError("scheduler must be a Scheduler")
        if not 0 <= self.parallel_workers <= 256:
            raise ValueError("parallel_workers must be zero (auto) or at most 256")
        if self.scheduler == Scheduler.PARALLEL_V3:
            if self.behavior_model == BehaviorModel.LEGACY_LINEAR_MACRO_V1:
                raise ValueError("parallel-v3 requires a V2 intent behavior model")
            if self.cellular_emergence_enabled and self.emergence_coordinated_components:
                raise ValueError(
                    "parallel-v3 does not yet support coordinated cellular components"
                )
        if not isinstance(self.v2_founder_priors_enabled, bool):
            raise TypeError("v2_founder_priors_enabled must be a boolean")
        if not isinstance(self.recurrent_state_lesion, bool):
            raise TypeError("recurrent_state_lesion must be a boolean")
        if not isinstance(self.memory_probe_enabled, bool):
            raise TypeError("memory_probe_enabled must be a boolean")
        if not isinstance(self.seasons_enabled, bool):
            raise TypeError("seasons_enabled must be a boolean")
        if not isinstance(self.cellular_emergence_enabled, bool):
            raise TypeError("cellular_emergence_enabled must be a boolean")
        if not isinstance(self.emergence_coordinated_components, bool):
            raise TypeError("emergence_coordinated_components must be a boolean")
        if not isinstance(self.biodeposits_enabled, bool):
            raise TypeError("biodeposits_enabled must be a boolean")
        if not isinstance(self.dynamic_chemistry_enabled, bool):
            raise TypeError("dynamic_chemistry_enabled must be a boolean")
        if not 0 <= self.reaction_rule_count <= 32:
            raise ValueError("reaction_rule_count must be in [0, 32]")
        if not isfinite(self.environmental_reaction_rate) or not 0.0 <= self.environmental_reaction_rate <= 1.0:
            raise ValueError("environmental_reaction_rate must be finite and in [0, 1]")
        if not isfinite(self.reaction_thermodynamics) or not 0.0 <= self.reaction_thermodynamics <= 0.5:
            raise ValueError("reaction_thermodynamics must be finite and in [0, 0.5]")
        if not 1 <= self.emergence_max_modules <= 64:
            raise ValueError("emergence_max_modules must be in [1, 64]")
        if not 0 <= self.emergence_max_internal_guests <= 32:
            raise ValueError("emergence_max_internal_guests must be in [0, 32]")
        for name, value in (
            ("emergence_structural_mutation_rate", self.emergence_structural_mutation_rate),
            ("emergence_module_cost", self.emergence_module_cost),
            ("emergence_module_effect", self.emergence_module_effect),
            ("emergence_bond_rate", self.emergence_bond_rate),
            ("emergence_bond_break_rate", self.emergence_bond_break_rate),
            ("emergence_exchange_rate", self.emergence_exchange_rate),
            ("emergence_engulfment_rate", self.emergence_engulfment_rate),
            ("environmental_reaction_rate", self.environmental_reaction_rate),
            ("byproduct_strength", self.byproduct_strength),
            ("biodeposit_decay_rate", self.biodeposit_decay_rate),
            ("biodeposit_movement_resistance", self.biodeposit_movement_resistance),
            ("biodeposit_cover_strength", self.biodeposit_cover_strength),
            ("biodeposit_concealment", self.biodeposit_concealment),
        ):
            if not isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if self.season_duration_min < 1:
            raise ValueError("season_duration_min must be positive")
        if self.season_duration_max < self.season_duration_min:
            raise ValueError("season duration bounds must be ordered")
        if not 0 <= self.season_transition_ticks <= self.season_duration_min:
            raise ValueError(
                "season_transition_ticks must be between zero and season_duration_min"
            )
        if not isfinite(self.season_strength) or not 0.0 <= self.season_strength <= 1.0:
            raise ValueError("season_strength must be finite and in [0, 1]")
        for name, value in (
            ("brain_cost_multiplier", self.brain_cost_multiplier),
            ("brain_base_cost", self.brain_base_cost),
            ("brain_hidden_cost", self.brain_hidden_cost),
            ("brain_recurrent_cost", self.brain_recurrent_cost),
        ):
            if not isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if self.width < 16 or self.height < 16:
            raise ValueError("founder-region dimensions must be at least 16")
        if not 8 <= self.chunk_size <= 128:
            raise ValueError("chunk_size must be between 8 and 128")
        if not 2 <= self.element_count <= 16:
            raise ValueError("element_count must be between 2 and 16")
        if self.molecule_count < self.element_count:
            raise ValueError("molecule_count must include monatomic fallbacks")
        if self.founder_count < 1:
            raise ValueError("founder_count must be positive")
        if self.founder_archetype_count < 1:
            raise ValueError("founder_archetype_count must be positive")
        if not 0.0 <= self.heat_diffusion <= 0.25:
            raise ValueError("heat_diffusion must be in [0, 0.25]")
        if self.chemical_signature_dimensions != 4:
            raise ValueError("the prototype currently uses four signature dimensions")
        if not 0.0 <= self.primary_production_rate <= 1.0:
            raise ValueError("primary_production_rate must be in [0, 1]")
        if self.deposit_production_rate < 0.0:
            raise ValueError("deposit_production_rate must be nonnegative")
        if not isfinite(self.byproduct_decay_rate) or not 0.0 <= self.byproduct_decay_rate <= 1.0:
            raise ValueError("byproduct_decay_rate must be finite and in [0, 1]")
        if not isinstance(self.deposit_match_ecology, bool):
            raise TypeError("deposit_match_ecology must be a boolean")
        if not 0.0 <= self.asexual_probability_floor <= 1.0:
            raise ValueError("asexual_probability_floor must be in [0, 1]")
        if not isinstance(self.sexual_probability_floor_enabled, bool):
            raise TypeError("sexual_probability_floor_enabled must be a boolean")
        if not 0.0 <= self.sexual_probability_floor <= 1.0:
            raise ValueError("sexual_probability_floor must be in [0, 1]")
        if self.maintenance_cost_multiplier < 0.0:
            raise ValueError("maintenance_cost_multiplier must be nonnegative")
        if self.attack_damage_multiplier < 0.0:
            raise ValueError("attack_damage_multiplier must be nonnegative")
        if self.new_species_marker_ticks < 0:
            raise ValueError("new_species_marker_ticks must be nonnegative")
        if not 0.0 <= self.prey_compatibility_threshold <= 1.0:
            raise ValueError("prey_compatibility_threshold must be in [0, 1]")
        if not 0.0 <= self.chemistry_coupling <= 1.0:
            raise ValueError("chemistry_coupling must be in [0, 1]")
        if not 0.0 <= self.guest_niche_coupling <= 1.0:
            raise ValueError("guest_niche_coupling must be in [0, 1]")
        if self.reproduction_cost_multiplier < 0.0:
            raise ValueError("reproduction_cost_multiplier must be nonnegative")
        if self.reproduction_cooldown_multiplier < 0.0:
            raise ValueError("reproduction_cooldown_multiplier must be nonnegative")
        if self.maturity_age_multiplier <= 0.0:
            raise ValueError("maturity_age_multiplier must be positive")
        if self.reproduction_action_bonus < 0.0:
            raise ValueError("reproduction_action_bonus must be nonnegative")
        if self.render_fps < 1:
            raise ValueError("render_fps must be positive")
        if self.recording_metrics_interval < 1:
            raise ValueError("recording_metrics_interval must be positive")
        if self.recording_detail_interval < 1:
            raise ValueError("recording_detail_interval must be positive")
        if self.recording_snapshot_interval < 1:
            raise ValueError("recording_snapshot_interval must be positive")
        if self.recording_commit_interval < 1:
            raise ValueError("recording_commit_interval must be positive")
