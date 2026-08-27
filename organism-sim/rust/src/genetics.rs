//! Genome / phenotype port of `organism_sim.genetics`.
//!
//! String-keyed trait/feature/action dicts are replaced by fixed index tables:
//!   - traits: 0..TRAIT_COUNT (order mirrors Python TRAIT_RANGES)
//!   - actions: 0..13 (order mirrors Python ACTIONS)
//!   - features: 0..10 (order mirrors Python FEATURES)
//!   - guilds: 0..5

use crate::behavior::neural::{
    LinearIntentGenome, LinearIntentPhenotype, RecurrentIntentGenome, RecurrentIntentPhenotype,
};
use crate::behavior::BehaviorModel;
use crate::chemistry::{signature_similarity, simplex, Signature};
use crate::config::SimConfig;
use crate::emergence::EmergenceGenome;
use crate::rng::{mix64, py_round, Fnv, Rng};

fn fork_recurrent_rng(rng: &Rng, genome_id: u32, domain: u64) -> Rng {
    let mut hash = Fnv::new();
    rng.hash_into(&mut hash);
    hash.u64(genome_id as u64);
    hash.u64(domain);
    Rng::new(mix64(hash.finish()))
}

pub const TRAIT_COUNT: usize = 27;
pub const ACTION_COUNT: usize = 13;
pub const FEATURE_COUNT: usize = 10;
pub const GUILD_COUNT: usize = 5;

pub const ACTION_NAMES: [&str; ACTION_COUNT] = [
    "rest",
    "wander",
    "forage",
    "hunt",
    "flee",
    "seek_mate",
    "eat",
    "heat",
    "detox",
    "attack",
    "magic",
    "reproduce",
    "ally",
];
pub const FEATURE_NAMES: [&str; FEATURE_COUNT] = [
    "hunger",
    "food",
    "heat",
    "threat",
    "prey",
    "toxin",
    "mana",
    "mate",
    "crowding",
    "energy_cost",
];
pub const GUILD_NAMES: [&str; GUILD_COUNT] =
    ["generalist", "grazer", "hunter", "scavenger", "thermophile"];

// Action indices
pub const A_REST: usize = 0;
pub const A_WANDER: usize = 1;
pub const A_FORAGE: usize = 2;
pub const A_HUNT: usize = 3;
pub const A_FLEE: usize = 4;
pub const A_SEEK_MATE: usize = 5;
pub const A_EAT: usize = 6;
pub const A_HEAT: usize = 7;
pub const A_DETOX: usize = 8;
pub const A_ATTACK: usize = 9;
pub const A_MAGIC: usize = 10;
pub const A_REPRODUCE: usize = 11;
pub const A_ALLY: usize = 12;

// Feature indices
pub const F_HUNGER: usize = 0;
pub const F_FOOD: usize = 1;
pub const F_HEAT: usize = 2;
pub const F_THREAT: usize = 3;
pub const F_PREY: usize = 4;
pub const F_MATE: usize = 7;
pub const F_ENERGY_COST: usize = 9;

// Trait indices
pub const T_ADULT_AREA: usize = 0;
pub const T_DENSITY: usize = 1;
pub const T_BASAL: usize = 2;
pub const T_MOVE_EFFICIENCY: usize = 3;
pub const T_SPEED: usize = 4;
pub const T_SIGHT: usize = 5;
pub const T_DIGESTION: usize = 6;
pub const T_ASSIMILATION: usize = 7;
pub const T_HEAT_ABSORPTION: usize = 8;
pub const T_MANA_EFFICIENCY: usize = 9;
pub const T_MANA_CAPACITY: usize = 10;
pub const T_MANA_PREFERENCE: usize = 11;
pub const T_LIFESPAN: usize = 12;
pub const T_MATURITY_FRACTION: usize = 13;
pub const T_ATTACK: usize = 14;
pub const T_ATTACK_EFFICIENCY: usize = 15;
pub const T_TOXIN_TOLERANCE: usize = 16;
pub const T_ASEXUAL: usize = 17;
pub const T_ASEXUAL_RATE: usize = 18;
pub const T_SEXUAL: usize = 19;
pub const T_FERTILITY: usize = 20;
pub const T_OFFSPRING: usize = 21;
pub const T_REPRODUCTION_FRACTION: usize = 22;
pub const T_MUTATION_RATE: usize = 23;
pub const T_MUTATION_MAGNITUDE: usize = 24;
pub const T_RISK: usize = 25;
pub const T_SOCIAL: usize = 26;

pub const TRAIT_NAMES: [&str; TRAIT_COUNT] = [
    "adult_area",
    "density",
    "basal",
    "move_efficiency",
    "speed",
    "sight",
    "digestion",
    "assimilation",
    "heat_absorption",
    "mana_efficiency",
    "mana_capacity",
    "mana_preference",
    "lifespan",
    "maturity_fraction",
    "attack",
    "attack_efficiency",
    "toxin_tolerance",
    "asexual",
    "asexual_rate",
    "sexual",
    "fertility",
    "offspring",
    "reproduction_fraction",
    "mutation_rate",
    "mutation_magnitude",
    "risk",
    "social",
];

/// (min, max, logarithmic) per trait — Python TRAIT_RANGES in dict order.
pub const TRAIT_SPECS: [(f64, f64, bool); TRAIT_COUNT] = [
    (1.0, 14.0, false),    // adult_area
    (0.5, 2.0, false),     // density
    (0.006, 0.080, false), // basal
    (0.25, 1.0, false),    // move_efficiency
    (0.5, 4.0, false),     // speed
    (1.0, 6.0, false),     // sight
    (0.15, 0.98, false),   // digestion
    (0.05, 0.75, false),   // assimilation
    (0.005, 0.20, false),  // heat_absorption
    (0.20, 1.0, false),    // mana_efficiency
    (0.5, 16.0, true),     // mana_capacity
    (0.0, 1.0, false),     // mana_preference
    (500.0, 5000.0, true), // lifespan
    (0.10, 0.45, false),   // maturity_fraction
    (0.1, 1.2, false),     // attack
    (0.25, 1.0, false),    // attack_efficiency
    (0.2, 10.0, false),    // toxin_tolerance
    (0.0, 1.0, false),     // asexual
    (0.25, 4.0, false),    // asexual_rate
    (0.0, 1.0, false),     // sexual
    (0.1, 0.95, false),    // fertility
    (1.0, 3.0, false),     // offspring
    (0.08, 0.28, false),   // reproduction_fraction
    (0.005, 0.25, false),  // mutation_rate
    (0.005, 0.12, false),  // mutation_magnitude
    (0.0, 1.0, false),     // risk
    (0.0, 1.0, false),     // social
];

/// Guild windows: (guild, trait) -> (lo_fraction, hi_fraction).
pub fn guild_window(guild: usize, trait_idx: usize) -> Option<(f64, f64)> {
    match (guild, trait_idx) {
        (0, T_DIGESTION) => Some((0.45, 0.85)),
        (0, T_ASSIMILATION) => Some((0.3, 0.7)),
        (1, T_ADULT_AREA) => Some((0.55, 1.0)),
        (1, T_DENSITY) => Some((0.4, 0.9)),
        (1, T_BASAL) => Some((0.3, 0.7)),
        (1, T_MOVE_EFFICIENCY) => Some((0.3, 0.8)),
        (1, T_SPEED) => Some((0.0, 0.3)),
        (1, T_SIGHT) => Some((0.0, 0.25)),
        (1, T_DIGESTION) => Some((0.7, 1.0)),
        (1, T_ASSIMILATION) => Some((0.5, 1.0)),
        (1, T_ATTACK) => Some((0.0, 0.2)),
        (1, T_RISK) => Some((0.0, 0.2)),
        (1, T_SOCIAL) => Some((0.4, 1.0)),
        (1, T_ASEXUAL) => Some((0.5, 1.0)),
        (1, T_FERTILITY) => Some((0.5, 1.0)),
        (1, T_OFFSPRING) => Some((0.4, 1.0)),
        (2, T_ADULT_AREA) => Some((0.25, 0.7)),
        (2, T_BASAL) => Some((0.5, 0.9)),
        (2, T_MOVE_EFFICIENCY) => Some((0.6, 1.0)),
        (2, T_SPEED) => Some((0.6, 1.0)),
        (2, T_SIGHT) => Some((0.6, 1.0)),
        (2, T_DIGESTION) => Some((0.4, 0.8)),
        (2, T_ASSIMILATION) => Some((0.3, 0.7)),
        (2, T_ATTACK) => Some((0.7, 1.0)),
        (2, T_ATTACK_EFFICIENCY) => Some((0.6, 1.0)),
        (2, T_RISK) => Some((0.5, 1.0)),
        (2, T_SEXUAL) => Some((0.5, 1.0)),
        (3, T_ADULT_AREA) => Some((0.0, 0.3)),
        (3, T_BASAL) => Some((0.0, 0.3)),
        (3, T_SPEED) => Some((0.5, 1.0)),
        (3, T_FERTILITY) => Some((0.6, 1.0)),
        (3, T_OFFSPRING) => Some((0.5, 1.0)),
        (3, T_ASEXUAL_RATE) => Some((0.6, 1.0)),
        (3, T_MUTATION_RATE) => Some((0.6, 1.0)),
        (3, T_MATURITY_FRACTION) => Some((0.0, 0.4)),
        (3, T_LIFESPAN) => Some((0.0, 0.3)),
        (4, T_ADULT_AREA) => Some((0.3, 0.8)),
        (4, T_SPEED) => Some((0.0, 0.4)),
        (4, T_HEAT_ABSORPTION) => Some((0.7, 1.0)),
        (4, T_MANA_EFFICIENCY) => Some((0.6, 1.0)),
        (4, T_MANA_CAPACITY) => Some((0.6, 1.0)),
        (4, T_MANA_PREFERENCE) => Some((0.6, 1.0)),
        _ => None,
    }
}

/// Shared r/K strategy axis (trait -> signed strength).
pub fn strategy_strength(trait_idx: usize) -> Option<f64> {
    match trait_idx {
        T_ADULT_AREA => Some(1.0),
        T_LIFESPAN => Some(1.0),
        T_MATURITY_FRACTION => Some(0.5),
        T_BASAL => Some(0.6),
        T_OFFSPRING => Some(-1.0),
        T_FERTILITY => Some(-0.5),
        _ => None,
    }
}

/// Guild policy priors: (guild, action, feature, center).
pub const GUILD_POLICY_PRIORS: [(usize, usize, usize, f64); 12] = [
    (0, A_FORAGE, F_HUNGER, 1.0),
    (1, A_FORAGE, F_HUNGER, 1.4),
    (1, A_FORAGE, F_FOOD, 0.9),
    (1, A_EAT, F_FOOD, 1.6),
    (1, A_HEAT, F_HEAT, 0.8),
    (1, A_REST, F_ENERGY_COST, 0.5),
    (2, A_HUNT, F_PREY, 1.4),
    (2, A_ATTACK, F_PREY, 0.9),
    (2, A_FLEE, F_THREAT, 1.2),
    (2, A_REPRODUCE, F_MATE, 0.4),
    (3, A_WANDER, F_HUNGER, 0.4),
    (3, A_FORAGE, F_FOOD, 1.2),
    // (scavenger flee/reproduce and thermophile priors continue below)
];

pub const GUILD_POLICY_PRIORS2: [(usize, usize, usize, f64); 5] = [
    (3, A_FLEE, F_THREAT, 1.3),
    (3, A_REPRODUCE, F_MATE, 1.0),
    (4, A_HEAT, F_HEAT, 1.6),
    (4, A_EAT, F_FOOD, 1.2),
    (4, A_REST, F_ENERGY_COST, 0.7),
];

/// Compact gene: range/log info comes from static tables (min/max are constant
/// per gene kind in the Python prototype too).
#[derive(Clone, Copy, Debug)]
pub struct Gene {
    pub center: f64,
    pub spread: f64,
}

/// Gene kind spec: (min, max, logarithmic).
#[derive(Clone, Copy, Debug)]
pub struct GeneSpec(pub f64, pub f64, pub bool);

pub const TRAIT_GENE_SPECS: [GeneSpec; TRAIT_COUNT] = {
    let mut out = [GeneSpec(0.0, 1.0, false); TRAIT_COUNT];
    let mut i = 0;
    while i < TRAIT_COUNT {
        out[i] = GeneSpec(TRAIT_SPECS[i].0, TRAIT_SPECS[i].1, TRAIT_SPECS[i].2);
        i += 1;
    }
    out
};

pub const VECTOR_GENE_SPEC: GeneSpec = GeneSpec(0.0, 1.0, false);
pub const POLICY_GENE_SPEC: GeneSpec = GeneSpec(-3.0, 3.0, false);

impl Gene {
    pub fn sample(&self, rng: &mut Rng, spec: GeneSpec) -> f64 {
        let GeneSpec(min, max, log) = spec;
        let value = if log {
            let lower = (1e-12f64.max(min)).ln();
            let upper = min.max(max).ln();
            let center = min.max(self.center).ln();
            let sampled = (center + rng.gauss() * self.spread).min(upper).max(lower);
            sampled.exp()
        } else {
            self.center + rng.gauss() * self.spread
        };
        value.min(max).max(min)
    }

    pub fn mutated(&self, rng: &mut Rng, spec: GeneSpec, rate: f64, magnitude: f64) -> Gene {
        if !rng.chance(rate) {
            return *self;
        }
        let GeneSpec(min, max, log) = spec;
        let span = max - min;
        let center = if log {
            (self.center * (rng.gauss() * magnitude).exp())
                .min(max)
                .max(min)
        } else {
            (self.center + rng.gauss() * (span * magnitude))
                .min(max)
                .max(min)
        };
        let spread_limit = if log { 1.0 } else { span * 0.5 };
        let spread = (self.spread * (rng.gauss() * magnitude).exp())
            .min(spread_limit)
            .max(0.0);
        Gene { center, spread }
    }

    pub fn blend(genes: &[Gene], rng: &mut Rng, spec: GeneSpec) -> Gene {
        let GeneSpec(min, _max, log) = spec;
        let chosen = genes[rng.below(genes.len() as u64) as usize];
        if rng.chance(0.55) {
            return chosen;
        }
        let (center, spread) = if log {
            let transformed: Vec<f64> = genes.iter().map(|g| min.max(g.center).ln()).collect();
            let tc: f64 = transformed.iter().sum::<f64>() / transformed.len() as f64;
            let center = tc.exp();
            let disagreement = transformed.iter().map(|v| (v - tc).powi(2)).sum::<f64>()
                / transformed.len() as f64;
            let spread = ((genes.iter().map(|g| g.spread * g.spread).sum::<f64>()
                / genes.len() as f64)
                + disagreement)
                .sqrt()
                .min(1.0);
            (center, spread)
        } else {
            let center = genes.iter().map(|g| g.center).sum::<f64>() / genes.len() as f64;
            let disagreement = genes
                .iter()
                .map(|g| (g.center - center).powi(2))
                .sum::<f64>()
                / genes.len() as f64;
            let spread = ((genes.iter().map(|g| g.spread * g.spread).sum::<f64>()
                / genes.len() as f64)
                + disagreement)
                .sqrt();
            (center, spread)
        };
        Gene { center, spread }
    }
}

#[derive(Clone, Debug)]
pub struct Genome {
    pub genome_id: u32,
    pub parent_genome_ids: Vec<u32>,
    pub traits: [Gene; TRAIT_COUNT],
    pub diet_signature: [Gene; 4],
    pub toxin_sensitivity: [Gene; 4],
    pub magic_affinity: [Gene; 4],
    pub magic_resistance: [Gene; 4],
    pub policy: [[Gene; FEATURE_COUNT]; ACTION_COUNT],
    pub intent_policy: Option<Box<LinearIntentGenome>>,
    pub recurrent_policy: Option<Box<RecurrentIntentGenome>>,
    pub emergence: Option<Box<EmergenceGenome>>,
    pub guild: u8,
}

impl Genome {
    pub fn random(
        genome_id: u32,
        rng: &mut Rng,
        guild: usize,
        diet_anchor: Option<Signature>,
        config: &SimConfig,
    ) -> Genome {
        let strategy = rng.uniform(-1.0, 1.0);
        let mut traits = [Gene {
            center: 0.0,
            spread: 0.0,
        }; TRAIT_COUNT];
        for (t, gene) in traits.iter_mut().enumerate() {
            let (minimum, maximum, log) = TRAIT_SPECS[t];
            let (lo_frac, hi_frac) = guild_window(guild, t).unwrap_or((0.0, 1.0));
            let lo = minimum + (maximum - minimum) * lo_frac;
            let hi = minimum + (maximum - minimum) * hi_frac;
            let mut center = rng.uniform(lo, hi);
            if let Some(strength) = strategy_strength(t) {
                let pole = if strength > 0.0 { maximum } else { minimum };
                center += 0.35 * strength * strategy * (pole - center);
                center = center.min(maximum).max(minimum);
            }
            let spread = if log {
                rng.uniform(0.01, 0.15)
            } else {
                (maximum - minimum) * rng.uniform(0.01, 0.10)
            };
            *gene = Gene { center, spread };
        }

        let anchor = match diet_anchor {
            Some(a) => a,
            None => {
                if guild == 0 {
                    [0.25, 0.25, 0.25, 0.25]
                } else {
                    simplex([
                        rng.f64() + 0.05,
                        rng.f64() + 0.05,
                        rng.f64() + 0.05,
                        rng.f64() + 0.05,
                    ])
                }
            }
        };
        let mut diet_signature = [Gene {
            center: 0.0,
            spread: 0.0,
        }; 4];
        for axis in 0..4 {
            diet_signature[axis] = Gene {
                center: (anchor[axis] + rng.uniform(-0.06, 0.06)).clamp(0.0, 1.0),
                spread: rng.uniform(0.01, 0.10),
            };
        }
        let mut toxin_sensitivity = [Gene {
            center: 0.0,
            spread: 0.0,
        }; 4];
        for gene in &mut toxin_sensitivity {
            *gene = Gene {
                center: rng.f64(),
                spread: rng.uniform(0.01, 0.12),
            };
        }
        let mut affinity_weights = [0.0f64; 4];
        for w in affinity_weights.iter_mut() {
            *w = rng.uniform(0.05, 1.0);
        }
        let affinity_total: f64 = affinity_weights.iter().sum();
        let mut magic_affinity = [Gene {
            center: 0.0,
            spread: 0.0,
        }; 4];
        let mut magic_resistance = [Gene {
            center: 0.0,
            spread: 0.0,
        }; 4];
        for axis in 0..4 {
            magic_affinity[axis] = Gene {
                center: affinity_weights[axis] / affinity_total,
                spread: rng.uniform(0.01, 0.12),
            };
            magic_resistance[axis] = Gene {
                center: (rng.uniform(0.05, 0.75)
                    * (1.15 - affinity_weights[axis] / affinity_total))
                    .min(0.9),
                spread: rng.uniform(0.01, 0.12),
            };
        }

        let mut policy = [[Gene {
            center: 0.0,
            spread: 0.0,
        }; FEATURE_COUNT]; ACTION_COUNT];
        for row in policy.iter_mut() {
            for gene in row.iter_mut() {
                *gene = Gene {
                    center: rng.uniform(-1.2, 1.2),
                    spread: rng.uniform(0.01, 0.15),
                };
            }
        }
        let overrides: [(usize, usize, f64, f64); 6] = [
            (A_EAT, F_FOOD, 0.8, 1.8),
            (A_FORAGE, F_HUNGER, 0.5, 1.5),
            (A_HUNT, F_PREY, 0.5, 1.5),
            (A_FLEE, F_THREAT, 0.7, 1.7),
            (A_SEEK_MATE, F_MATE, 0.5, 1.5),
            (A_HEAT, F_HEAT, 0.2, 1.4),
        ];
        for (a, f, lo, hi) in overrides {
            policy[a][f] = Gene {
                center: rng.uniform(lo, hi),
                spread: 0.08,
            };
        }
        for &(g, a, f, center) in GUILD_POLICY_PRIORS
            .iter()
            .chain(GUILD_POLICY_PRIORS2.iter())
        {
            if g == guild {
                policy[a][f] = Gene {
                    center: center + rng.uniform(-0.1, 0.1),
                    spread: 0.08,
                };
            }
        }

        let intent_policy = if config.behavior_model == BehaviorModel::LegacyLinearMacroV1 {
            None
        } else {
            Some(Box::new(LinearIntentGenome::random(
                rng,
                guild,
                config.v2_founder_priors_enabled,
            )))
        };
        let recurrent_policy = if config.behavior_model == BehaviorModel::RecurrentIntentV2 {
            let mut recurrent_rng = fork_recurrent_rng(rng, genome_id, 0x5245_4355_525F_4745);
            Some(Box::new(RecurrentIntentGenome::random(&mut recurrent_rng)))
        } else {
            None
        };
        let emergence = config.cellular_emergence_enabled.then(|| {
            let mut emergence_rng = fork_recurrent_rng(rng, genome_id, 0x4345_4C4C_554C_4152);
            Box::new(EmergenceGenome::random(
                &mut emergence_rng,
                config.molecule_count,
                config.emergence_max_modules,
            ))
        });

        Genome {
            genome_id,
            parent_genome_ids: Vec::new(),
            traits,
            diet_signature,
            toxin_sensitivity,
            magic_affinity,
            magic_resistance,
            policy,
            intent_policy,
            recurrent_policy,
            emergence,
            guild: guild as u8,
        }
    }

    pub fn offspring(
        genome_id: u32,
        parents: &[&Genome],
        rng: &mut Rng,
        mutation_multiplier: f64,
        config: &SimConfig,
    ) -> Genome {
        let inherited_rate: f64 = parents
            .iter()
            .map(|p| p.traits[T_MUTATION_RATE].center)
            .sum::<f64>()
            / parents.len() as f64;
        let inherited_magnitude: f64 = parents
            .iter()
            .map(|p| p.traits[T_MUTATION_MAGNITUDE].center)
            .sum::<f64>()
            / parents.len() as f64;
        let rate = (inherited_rate * mutation_multiplier).min(0.8);
        let magnitude = (inherited_magnitude * mutation_multiplier).min(0.35);

        let pick = |i: usize| parents[i];
        let mut traits = [Gene {
            center: 0.0,
            spread: 0.0,
        }; TRAIT_COUNT];
        for (t, gene) in traits.iter_mut().enumerate() {
            let genes: Vec<Gene> = (0..parents.len()).map(|i| pick(i).traits[t]).collect();
            *gene = Gene::blend(&genes, rng, TRAIT_GENE_SPECS[t]).mutated(
                rng,
                TRAIT_GENE_SPECS[t],
                rate,
                magnitude,
            );
        }

        fn blend_vector<F>(
            parents: &[&Genome],
            rng: &mut Rng,
            rate: f64,
            magnitude: f64,
            get: F,
        ) -> [Gene; 4]
        where
            F: Fn(&Genome) -> [Gene; 4],
        {
            let vectors: Vec<[Gene; 4]> = parents.iter().map(|p| get(p)).collect();
            let mut out = [Gene {
                center: 0.0,
                spread: 0.0,
            }; 4];
            for axis in 0..4 {
                let genes: Vec<Gene> = vectors.iter().map(|v| v[axis]).collect();
                out[axis] = Gene::blend(&genes, rng, VECTOR_GENE_SPEC).mutated(
                    rng,
                    VECTOR_GENE_SPEC,
                    rate,
                    magnitude,
                );
            }
            out
        }
        let diet_signature = blend_vector(parents, rng, rate, magnitude, |g| g.diet_signature);
        let toxin_sensitivity =
            blend_vector(parents, rng, rate, magnitude, |g| g.toxin_sensitivity);
        let magic_affinity = blend_vector(parents, rng, rate, magnitude, |g| g.magic_affinity);
        let magic_resistance = blend_vector(parents, rng, rate, magnitude, |g| g.magic_resistance);

        let mut policy = [[Gene {
            center: 0.0,
            spread: 0.0,
        }; FEATURE_COUNT]; ACTION_COUNT];
        for (action, row) in policy.iter_mut().enumerate() {
            for (feature, gene) in row.iter_mut().enumerate() {
                let genes: Vec<Gene> = (0..parents.len())
                    .map(|i| pick(i).policy[action][feature])
                    .collect();
                *gene = Gene::blend(&genes, rng, POLICY_GENE_SPEC).mutated(
                    rng,
                    POLICY_GENE_SPEC,
                    rate,
                    magnitude,
                );
            }
        }

        let (intent_policy, recurrent_policy) = if config.behavior_model
            == BehaviorModel::LegacyLinearMacroV1
        {
            (None, None)
        } else {
            let donor = parents[rng.below(parents.len() as u64) as usize];
            let intent_policy = donor
                .intent_policy
                .as_ref()
                .expect("V2 parents must carry an intent policy")
                .mutated(rng, rate, magnitude);
            let recurrent_policy = if config.behavior_model == BehaviorModel::RecurrentIntentV2 {
                let mut recurrent_rng = fork_recurrent_rng(rng, genome_id, 0x5245_4355_525F_4D55);
                Some(Box::new(
                    donor
                        .recurrent_policy
                        .as_ref()
                        .expect("recurrent parents must carry a recurrent policy")
                        .mutated(&mut recurrent_rng, rate, magnitude),
                ))
            } else {
                None
            };
            (Some(Box::new(intent_policy)), recurrent_policy)
        };
        let emergence = if config.cellular_emergence_enabled {
            let mut emergence_rng = fork_recurrent_rng(rng, genome_id, 0x4345_4C4C_554C_4D55);
            let donor = parents[emergence_rng.below(parents.len() as u64) as usize]
                .emergence
                .as_ref()
                .expect("emergence-enabled parents must carry cellular genes");
            Some(Box::new(EmergenceGenome::offspring(
                donor,
                &mut emergence_rng,
                rate,
                magnitude,
                config.emergence_structural_mutation_rate * mutation_multiplier,
                config.molecule_count,
                config.emergence_max_modules,
            )))
        } else {
            None
        };
        let guild = if parents.iter().all(|p| p.guild == parents[0].guild) {
            parents[0].guild
        } else {
            0
        };
        Genome {
            genome_id,
            parent_genome_ids: parents.iter().map(|p| p.genome_id).collect(),
            traits,
            diet_signature,
            toxin_sensitivity,
            magic_affinity,
            magic_resistance,
            policy,
            intent_policy,
            recurrent_policy,
            emergence,
            guild,
        }
    }

    /// Mean normalized center distance (traits + diet/affinity/resistance vectors).
    pub fn distance(&self, other: &Genome) -> f64 {
        let mut total = 0.0f64;
        let mut count = 0usize;
        for (trait_index, &(min, max, _)) in TRAIT_SPECS.iter().enumerate() {
            let span = max - min;
            total +=
                (self.traits[trait_index].center - other.traits[trait_index].center).abs() / span;
            count += 1;
        }
        for (left, right) in [
            (&self.diet_signature, &other.diet_signature),
            (&self.magic_affinity, &other.magic_affinity),
            (&self.magic_resistance, &other.magic_resistance),
        ] {
            for axis in 0..4 {
                total += (left[axis].center - right[axis].center).abs();
                count += 1;
            }
        }
        total / count as f64
    }

    pub fn hash_into(&self, h: &mut crate::rng::Fnv) {
        h.u64(self.genome_id as u64);
        h.u64(self.parent_genome_ids.len() as u64);
        for &parent_id in &self.parent_genome_ids {
            h.u64(parent_id as u64);
        }
        h.u64(self.guild as u64);
        for t in 0..TRAIT_COUNT {
            h.f64(self.traits[t].center);
            h.f64(self.traits[t].spread);
        }
        for v in [
            &self.diet_signature,
            &self.toxin_sensitivity,
            &self.magic_affinity,
            &self.magic_resistance,
        ] {
            for gene in v {
                h.f64(gene.center);
                h.f64(gene.spread);
            }
        }
        for row in &self.policy {
            for gene in row {
                h.f64(gene.center);
                h.f64(gene.spread);
            }
        }
        if let Some(policy) = &self.intent_policy {
            for gene in &policy.kind_bias {
                h.u64(gene.center.to_bits() as u64);
                h.u64(gene.spread.to_bits() as u64);
            }
            for row in &policy.global_weights {
                for gene in row {
                    h.u64(gene.center.to_bits() as u64);
                    h.u64(gene.spread.to_bits() as u64);
                }
            }
            for row in &policy.candidate_weights {
                for gene in row {
                    h.u64(gene.center.to_bits() as u64);
                    h.u64(gene.spread.to_bits() as u64);
                }
            }
            h.u64(policy.decision_temperature.center.to_bits() as u64);
            h.u64(policy.decision_temperature.spread.to_bits() as u64);
        }
        if let Some(emergence) = &self.emergence {
            emergence.hash_into(h);
        }
        if let Some(policy) = &self.recurrent_policy {
            let mut hash_gene = |gene: &crate::behavior::neural::NeuralGene| {
                h.u64(gene.center.to_bits() as u64);
                h.u64(gene.spread.to_bits() as u64);
            };
            for gene in &policy.hidden_bias {
                hash_gene(gene);
            }
            for row in &policy.input_weights {
                for gene in row {
                    hash_gene(gene);
                }
            }
            for gene in &policy.hidden_expression {
                hash_gene(gene);
            }
            for row in &policy.recurrent_weights {
                for gene in row {
                    hash_gene(gene);
                }
            }
            for gene in &policy.recurrent_expression {
                hash_gene(gene);
            }
            for gene in &policy.retention {
                hash_gene(gene);
            }
            for row in &policy.kind_output_weights {
                for gene in row {
                    hash_gene(gene);
                }
            }
            for row in &policy.feature_output_weights {
                for gene in row {
                    hash_gene(gene);
                }
            }
        }
    }
}

fn hsv_to_rgb(h: f64, s: f64, v: f64) -> (f64, f64, f64) {
    let i = (h * 6.0).floor();
    let f = h * 6.0 - i;
    let p = v * (1.0 - s);
    let q = v * (1.0 - f * s);
    let t = v * (1.0 - (1.0 - f) * s);
    match (i as i64) % 6 {
        0 => (v, t, p),
        1 => (q, v, p),
        2 => (p, v, t),
        3 => (p, q, v),
        4 => (t, p, v),
        _ => (v, p, q),
    }
}

pub fn species_color(species_id: u32, genome: &Genome) -> [u8; 3] {
    let diet_hue: f64 = genome
        .diet_signature
        .iter()
        .enumerate()
        .map(|(i, g)| g.center * (0.15 + 0.2 * i as f64))
        .sum();
    let hue = (species_id as f64 * 0.61803398875 + diet_hue * 0.25) % 1.0;
    let attack_norm = (genome.traits[T_ATTACK].center / 1.2).clamp(0.0, 1.0);
    let saturation = 0.5 + 0.3 * attack_norm;
    let (r, g, b) = hsv_to_rgb(hue, saturation, 0.88);
    [
        (45.0 + r * 200.0) as u8,
        (45.0 + g * 200.0) as u8,
        (45.0 + b * 200.0) as u8,
    ]
}

#[derive(Clone, Debug)]
pub struct Phenotype {
    pub adult_area: i64,
    pub density: f64,
    pub basal: f64,
    pub move_efficiency: f64,
    pub speed: f64,
    pub sight: usize,
    pub digestion: f64,
    pub assimilation: f64,
    pub heat_absorption: f64,
    pub mana_efficiency: f64,
    pub mana_capacity: f64,
    pub mana_preference: f64,
    pub lifespan: i64,
    pub maturity_age: i64,
    pub attack: f64,
    pub attack_efficiency: f64,
    pub toxin_tolerance: f64,
    pub asexual: f64,
    pub asexual_rate: f64,
    pub sexual: f64,
    pub fertility: f64,
    pub offspring_count: i64,
    pub reproduction_fraction: f64,
    pub risk: f64,
    pub social: f64,
    pub diet_signature: Signature,
    pub toxin_sensitivity: Signature,
    pub magic_affinity: Signature,
    pub magic_resistance: Signature,
    pub policy: [[f64; FEATURE_COUNT]; ACTION_COUNT],
    pub intent_policy: Option<Box<LinearIntentPhenotype>>,
    pub recurrent_policy: Option<Box<RecurrentIntentPhenotype>>,
}

impl Phenotype {
    pub fn hash_into(&self, h: &mut crate::rng::Fnv) {
        h.i64(self.adult_area);
        h.f64(self.density);
        h.f64(self.basal);
        h.f64(self.move_efficiency);
        h.f64(self.speed);
        h.u64(self.sight as u64);
        h.f64(self.digestion);
        h.f64(self.assimilation);
        h.f64(self.heat_absorption);
        h.f64(self.mana_efficiency);
        h.f64(self.mana_capacity);
        h.f64(self.mana_preference);
        h.i64(self.lifespan);
        h.i64(self.maturity_age);
        h.f64(self.attack);
        h.f64(self.attack_efficiency);
        h.f64(self.toxin_tolerance);
        h.f64(self.asexual);
        h.f64(self.asexual_rate);
        h.f64(self.sexual);
        h.f64(self.fertility);
        h.i64(self.offspring_count);
        h.f64(self.reproduction_fraction);
        h.f64(self.risk);
        h.f64(self.social);
        for vector in [
            &self.diet_signature,
            &self.toxin_sensitivity,
            &self.magic_affinity,
            &self.magic_resistance,
        ] {
            for &value in vector {
                h.f64(value);
            }
        }
        for row in &self.policy {
            for &value in row {
                h.f64(value);
            }
        }
        if let Some(policy) = &self.intent_policy {
            for &value in &policy.kind_bias {
                h.u64(value.to_bits() as u64);
            }
            for row in &policy.global_weights {
                for &value in row {
                    h.u64(value.to_bits() as u64);
                }
            }
            for row in &policy.candidate_weights {
                for &value in row {
                    h.u64(value.to_bits() as u64);
                }
            }
            h.u64(policy.decision_temperature.to_bits() as u64);
        }
        if let Some(policy) = &self.recurrent_policy {
            for &value in &policy.hidden_bias {
                h.u64(value.to_bits() as u64);
            }
            for row in &policy.input_weights {
                for &value in row {
                    h.u64(value.to_bits() as u64);
                }
            }
            for &value in &policy.hidden_expression {
                h.u64(value.to_bits() as u64);
            }
            for row in &policy.recurrent_weights {
                for &value in row {
                    h.u64(value.to_bits() as u64);
                }
            }
            for &value in &policy.recurrent_expression {
                h.u64(value.to_bits() as u64);
            }
            for &value in &policy.retention {
                h.u64(value.to_bits() as u64);
            }
            for row in &policy.kind_output_weights {
                for &value in row {
                    h.u64(value.to_bits() as u64);
                }
            }
            for row in &policy.feature_output_weights {
                for &value in row {
                    h.u64(value.to_bits() as u64);
                }
            }
        }
    }

    pub fn sample(genome: &Genome, rng: &mut Rng, config: &crate::config::SimConfig) -> Phenotype {
        let mut sampled = [0.0f64; TRAIT_COUNT];
        for t in 0..TRAIT_COUNT {
            sampled[t] = genome.traits[t].sample(rng, TRAIT_GENE_SPECS[t]);
        }
        let mut norm4 = |genes: &[Gene; 4]| -> Signature {
            simplex([
                genes[0].sample(rng, VECTOR_GENE_SPEC) + 0.01,
                genes[1].sample(rng, VECTOR_GENE_SPEC) + 0.01,
                genes[2].sample(rng, VECTOR_GENE_SPEC) + 0.01,
                genes[3].sample(rng, VECTOR_GENE_SPEC) + 0.01,
            ])
        };
        let diet = norm4(&genome.diet_signature);
        let sensitivity = norm4(&genome.toxin_sensitivity);
        let affinity = norm4(&genome.magic_affinity);
        let mut resistance = [0.0f64; 4];
        for (axis, value) in resistance.iter_mut().enumerate() {
            *value = genome.magic_resistance[axis]
                .sample(rng, VECTOR_GENE_SPEC)
                .min(0.95);
        }
        let mut policy = [[0.0f64; FEATURE_COUNT]; ACTION_COUNT];
        for (action, row) in policy.iter_mut().enumerate() {
            for (feature, value) in row.iter_mut().enumerate() {
                *value = genome.policy[action][feature].sample(rng, POLICY_GENE_SPEC);
            }
        }
        let intent_policy = genome
            .intent_policy
            .as_ref()
            .map(|policy| Box::new(policy.sample(rng)));
        let recurrent_policy = genome.recurrent_policy.as_ref().map(|policy| {
            let mut recurrent_rng =
                fork_recurrent_rng(rng, genome.genome_id, 0x5245_4355_525F_4445);
            Box::new(policy.sample(&mut recurrent_rng))
        });
        let lifespan = py_round(sampled[T_LIFESPAN]).max(1);
        Phenotype {
            adult_area: py_round(sampled[T_ADULT_AREA]).max(1),
            density: sampled[T_DENSITY],
            basal: sampled[T_BASAL],
            move_efficiency: sampled[T_MOVE_EFFICIENCY],
            speed: sampled[T_SPEED],
            sight: (py_round(sampled[T_SIGHT]).max(1) as usize).min(config.max_sight),
            digestion: sampled[T_DIGESTION],
            assimilation: sampled[T_ASSIMILATION],
            heat_absorption: sampled[T_HEAT_ABSORPTION],
            mana_efficiency: sampled[T_MANA_EFFICIENCY],
            mana_capacity: sampled[T_MANA_CAPACITY],
            mana_preference: sampled[T_MANA_PREFERENCE],
            lifespan,
            maturity_age: py_round(lifespan as f64 * sampled[T_MATURITY_FRACTION]).max(1),
            attack: sampled[T_ATTACK],
            attack_efficiency: sampled[T_ATTACK_EFFICIENCY],
            toxin_tolerance: sampled[T_TOXIN_TOLERANCE],
            asexual: sampled[T_ASEXUAL],
            asexual_rate: sampled[T_ASEXUAL_RATE],
            sexual: sampled[T_SEXUAL],
            fertility: sampled[T_FERTILITY],
            offspring_count: py_round(sampled[T_OFFSPRING]).max(1),
            reproduction_fraction: sampled[T_REPRODUCTION_FRACTION],
            risk: sampled[T_RISK],
            social: sampled[T_SOCIAL],
            diet_signature: diet,
            toxin_sensitivity: sensitivity,
            magic_affinity: affinity,
            magic_resistance: resistance,
            policy,
            intent_policy,
            recurrent_policy,
        }
    }
}

pub fn similarity(a: &Signature, b: &Signature) -> f64 {
    signature_similarity(a, b)
}
