//! Genetic V2 controller schemas for the direct linear control and the fixed
//! eight-unit expression-gated recurrent residual.

#![allow(dead_code)]

use super::intent::{
    IntentCandidate, CANDIDATE_FEATURE_COUNT, C_CHEMICAL_COST, C_FOOD, C_HEAT, C_MANA_COST, C_MATE,
    C_PREY, C_SOCIAL, C_THREAT, C_TOXIN, INTENT_TYPE_COUNT,
};
use super::observation::{
    ObservationV2, OBSERVATION_COUNT, O_HUNGER, O_INTEGRITY, O_MANA, O_REPRODUCTIVE_READY,
    O_REPRODUCTIVE_RESERVE, O_TOXIN,
};
use crate::rng::Rng;

pub const HIDDEN_COUNT: usize = 8;
pub const CONTROLLER_OUTPUT_COUNT: usize = INTENT_TYPE_COUNT + CANDIDATE_FEATURE_COUNT;
pub const LINEAR_LOCUS_COUNT: usize = INTENT_TYPE_COUNT
    + INTENT_TYPE_COUNT * OBSERVATION_COUNT
    + INTENT_TYPE_COUNT * CANDIDATE_FEATURE_COUNT
    + 1;
pub const RECURRENT_LOCUS_COUNT: usize = HIDDEN_COUNT
    + HIDDEN_COUNT * OBSERVATION_COUNT
    + HIDDEN_COUNT
    + HIDDEN_COUNT * HIDDEN_COUNT
    + HIDDEN_COUNT
    + HIDDEN_COUNT
    + INTENT_TYPE_COUNT * HIDDEN_COUNT
    + CANDIDATE_FEATURE_COUNT * HIDDEN_COUNT;
pub const NEURAL_LOCUS_COUNT: usize = LINEAR_LOCUS_COUNT + RECURRENT_LOCUS_COUNT;

#[inline]
fn scalar_dot_f32<const N: usize>(left: &[f32; N], right: &[f32; N]) -> f32 {
    let mut total = 0.0;
    for index in 0..N {
        total += left[index] * right[index];
    }
    total
}

#[inline]
fn scalar_dot_f64<const N: usize>(left: &[f32; N], right: &[f32; N]) -> f64 {
    let mut total = 0.0;
    for index in 0..N {
        total += left[index] as f64 * right[index] as f64;
    }
    total
}

#[cfg(all(feature = "simd-neural", target_arch = "aarch64"))]
#[inline]
fn neural_dot_f32<const N: usize>(left: &[f32; N], right: &[f32; N]) -> f32 {
    // SAFETY: NEON is mandatory in AArch64, both slices contain N readable
    // f32 values, and vld1q_f32 permits unaligned loads.
    unsafe { neon_dot_f32(left, right) }
}

#[cfg(not(all(feature = "simd-neural", target_arch = "aarch64")))]
#[inline]
fn neural_dot_f32<const N: usize>(left: &[f32; N], right: &[f32; N]) -> f32 {
    scalar_dot_f32(left, right)
}

#[cfg(all(feature = "simd-neural", target_arch = "aarch64"))]
#[inline]
fn neural_affine_f32<const N: usize>(bias: f32, left: &[f32; N], right: &[f32; N]) -> f32 {
    bias + neural_dot_f32(left, right)
}

#[cfg(not(all(feature = "simd-neural", target_arch = "aarch64")))]
#[inline]
fn neural_affine_f32<const N: usize>(bias: f32, left: &[f32; N], right: &[f32; N]) -> f32 {
    // Start from the bias to preserve the historical scalar accumulation order.
    let mut total = bias;
    for index in 0..N {
        total += left[index] * right[index];
    }
    total
}

#[cfg(all(feature = "simd-neural", target_arch = "aarch64"))]
#[inline]
fn neural_dot_f64<const N: usize>(left: &[f32; N], right: &[f32; N]) -> f64 {
    neural_dot_f32(left, right) as f64
}

#[cfg(not(all(feature = "simd-neural", target_arch = "aarch64")))]
#[inline]
fn neural_dot_f64<const N: usize>(left: &[f32; N], right: &[f32; N]) -> f64 {
    scalar_dot_f64(left, right)
}

#[cfg(all(feature = "simd-neural", target_arch = "aarch64"))]
#[target_feature(enable = "neon")]
unsafe fn neon_dot_f32<const N: usize>(left: &[f32; N], right: &[f32; N]) -> f32 {
    use std::arch::aarch64::{vaddvq_f32, vdupq_n_f32, vfmaq_f32, vld1q_f32};

    let vectorized = N - N % 4;
    let mut accumulator = vdupq_n_f32(0.0);
    let mut index = 0;
    while index < vectorized {
        let left_values = vld1q_f32(left.as_ptr().add(index));
        let right_values = vld1q_f32(right.as_ptr().add(index));
        accumulator = vfmaq_f32(accumulator, left_values, right_values);
        index += 4;
    }
    let mut total = vaddvq_f32(accumulator);
    while index < N {
        total += left[index] * right[index];
        index += 1;
    }
    total
}

#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct NeuralGene {
    pub center: f32,
    pub spread: f32,
}

impl NeuralGene {
    fn sample(self, rng: &mut Rng, minimum: f32, maximum: f32, logarithmic: bool) -> f32 {
        let value = if logarithmic {
            let lower = minimum.max(1e-6).ln();
            let upper = maximum.ln();
            let center = self.center.max(minimum).ln();
            (center + rng.gauss() as f32 * self.spread)
                .clamp(lower, upper)
                .exp()
        } else {
            self.center + rng.gauss() as f32 * self.spread
        };
        value.clamp(minimum, maximum)
    }

    fn mutated(
        self,
        rng: &mut Rng,
        minimum: f32,
        maximum: f32,
        rate: f64,
        magnitude: f64,
    ) -> NeuralGene {
        if !rng.chance(rate) {
            return self;
        }
        let span = maximum - minimum;
        let center =
            (self.center + rng.gauss() as f32 * span * magnitude as f32).clamp(minimum, maximum);
        let epsilon = span * 1e-4;
        let spread = (((self.spread + epsilon) * (rng.gauss() as f32 * magnitude as f32).exp())
            - epsilon)
            .clamp(0.0, span * 0.5);
        NeuralGene { center, spread }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct LinearIntentGenome {
    pub kind_bias: [NeuralGene; INTENT_TYPE_COUNT],
    pub global_weights: [[NeuralGene; OBSERVATION_COUNT]; INTENT_TYPE_COUNT],
    pub candidate_weights: [[NeuralGene; CANDIDATE_FEATURE_COUNT]; INTENT_TYPE_COUNT],
    pub decision_temperature: NeuralGene,
}

#[derive(Clone, Debug, PartialEq)]
pub struct LinearIntentPhenotype {
    pub kind_bias: [f32; INTENT_TYPE_COUNT],
    pub global_weights: [[f32; OBSERVATION_COUNT]; INTENT_TYPE_COUNT],
    pub candidate_weights: [[f32; CANDIDATE_FEATURE_COUNT]; INTENT_TYPE_COUNT],
    pub decision_temperature: f32,
}

impl LinearIntentPhenotype {
    pub fn global_scores(&self, observation: &ObservationV2) -> [f64; INTENT_TYPE_COUNT] {
        let mut scores = [0.0; INTENT_TYPE_COUNT];
        for (kind, score) in scores.iter_mut().enumerate() {
            *score = self.kind_bias[kind] as f64
                + neural_dot_f64(&self.global_weights[kind], &observation.values);
        }
        scores
    }

    pub fn score_with_globals(
        &self,
        global_scores: &[f64; INTENT_TYPE_COUNT],
        candidate: &IntentCandidate,
    ) -> f64 {
        let kind = candidate.kind.as_index();
        global_scores[kind] + neural_dot_f64(&self.candidate_weights[kind], &candidate.features)
    }

    pub fn score(&self, observation: &ObservationV2, candidate: &IntentCandidate) -> f64 {
        self.score_with_globals(&self.global_scores(observation), candidate)
    }
}

impl LinearIntentGenome {
    pub fn random(rng: &mut Rng, guild: usize, founder_priors_enabled: bool) -> LinearIntentGenome {
        let base = NeuralGene {
            center: 0.0,
            spread: 0.03,
        };
        let mut genome = LinearIntentGenome {
            kind_bias: [base; INTENT_TYPE_COUNT],
            global_weights: [[base; OBSERVATION_COUNT]; INTENT_TYPE_COUNT],
            candidate_weights: [[base; CANDIDATE_FEATURE_COUNT]; INTENT_TYPE_COUNT],
            decision_temperature: NeuralGene {
                center: 1.0,
                spread: 0.04,
            },
        };
        for gene in &mut genome.kind_bias {
            gene.center = rng.uniform(-0.15, 0.15) as f32;
        }
        for row in &mut genome.global_weights {
            for gene in row {
                gene.center = rng.uniform(-0.12, 0.12) as f32;
            }
        }
        for row in &mut genome.candidate_weights {
            for gene in row {
                gene.center = rng.uniform(-0.12, 0.12) as f32;
            }
        }
        if !founder_priors_enabled {
            return genome;
        }

        use super::intent::IntentKind;
        let k = |kind: IntentKind| kind.as_index();
        genome.kind_bias[k(IntentKind::Wait)].center -= 0.20;
        genome.kind_bias[k(IntentKind::Move)].center += 0.25;
        genome.kind_bias[k(IntentKind::Ingest)].center += 0.70;
        genome.kind_bias[k(IntentKind::Repair)].center -= 0.25;
        genome.kind_bias[k(IntentKind::AbsorbHeat)].center -= 0.10;
        genome.kind_bias[k(IntentKind::Detox)].center -= 0.30;
        genome.kind_bias[k(IntentKind::CastMagic)].center -= 0.45;
        genome.kind_bias[k(IntentKind::ProposeAlliance)].center -= 0.35;

        genome.global_weights[k(IntentKind::Move)][O_HUNGER].center += 0.7;
        genome.candidate_weights[k(IntentKind::Move)][C_FOOD].center += 2.8;
        genome.candidate_weights[k(IntentKind::Move)][C_HEAT].center += 0.5;
        genome.candidate_weights[k(IntentKind::Move)][C_THREAT].center -= 2.0;
        genome.candidate_weights[k(IntentKind::Move)][C_CHEMICAL_COST].center -= 1.0;

        genome.global_weights[k(IntentKind::Ingest)][O_HUNGER].center += 2.5;
        genome.candidate_weights[k(IntentKind::Ingest)][C_FOOD].center += 3.2;
        genome.candidate_weights[k(IntentKind::Ingest)][C_TOXIN].center -= 3.0;
        genome.candidate_weights[k(IntentKind::Ingest)][C_CHEMICAL_COST].center -= 0.8;

        genome.kind_bias[k(IntentKind::Repair)].center += 1.2;
        genome.global_weights[k(IntentKind::Repair)][O_INTEGRITY].center -= 2.2;
        genome.global_weights[k(IntentKind::AbsorbHeat)][O_MANA].center -= 1.8;
        genome.candidate_weights[k(IntentKind::AbsorbHeat)][C_HEAT].center += 2.2;
        genome.global_weights[k(IntentKind::Detox)][O_TOXIN].center += 3.0;

        genome.candidate_weights[k(IntentKind::Attack)][C_PREY].center += 2.6;
        genome.candidate_weights[k(IntentKind::Attack)][C_THREAT].center -= 0.8;
        genome.candidate_weights[k(IntentKind::Attack)][C_CHEMICAL_COST].center -= 0.7;
        genome.global_weights[k(IntentKind::CastMagic)][O_MANA].center += 1.0;
        genome.candidate_weights[k(IntentKind::CastMagic)][C_PREY].center += 1.8;
        genome.candidate_weights[k(IntentKind::CastMagic)][C_MANA_COST].center -= 0.5;

        genome.global_weights[k(IntentKind::Reproduce)][O_REPRODUCTIVE_READY].center += 2.0;
        genome.global_weights[k(IntentKind::Reproduce)][O_REPRODUCTIVE_RESERVE].center += 1.5;
        genome.candidate_weights[k(IntentKind::Reproduce)][C_MATE].center += 1.2;
        genome.candidate_weights[k(IntentKind::Reproduce)][C_CHEMICAL_COST].center -= 0.8;
        genome.candidate_weights[k(IntentKind::ProposeAlliance)][C_SOCIAL].center += 2.0;

        // Retain weak ecological archetype biases without scripting a target.
        match guild {
            1 => {
                genome.candidate_weights[k(IntentKind::Move)][C_FOOD].center += 0.5;
                genome.candidate_weights[k(IntentKind::Attack)][C_PREY].center -= 0.8;
            }
            2 => {
                genome.candidate_weights[k(IntentKind::Move)][C_PREY].center += 0.8;
                genome.candidate_weights[k(IntentKind::Attack)][C_PREY].center += 0.8;
            }
            3 => {
                genome.kind_bias[k(IntentKind::Move)].center += 0.25;
                genome.candidate_weights[k(IntentKind::Move)][C_THREAT].center -= 0.5;
            }
            4 => {
                genome.candidate_weights[k(IntentKind::Move)][C_HEAT].center += 1.0;
                genome.candidate_weights[k(IntentKind::AbsorbHeat)][C_HEAT].center += 0.8;
            }
            _ => {}
        }
        genome
    }

    pub fn mutated(&self, rng: &mut Rng, rate: f64, magnitude: f64) -> LinearIntentGenome {
        let mut child = self.clone();
        for gene in &mut child.kind_bias {
            *gene = gene.mutated(rng, -3.0, 3.0, rate, magnitude);
        }
        for row in &mut child.global_weights {
            for gene in row {
                *gene = gene.mutated(rng, -3.0, 3.0, rate, magnitude);
            }
        }
        for row in &mut child.candidate_weights {
            for gene in row {
                *gene = gene.mutated(rng, -3.0, 3.0, rate, magnitude);
            }
        }
        child.decision_temperature = child
            .decision_temperature
            .mutated(rng, 0.05, 2.0, rate, magnitude);
        child
    }

    pub fn sample(&self, rng: &mut Rng) -> LinearIntentPhenotype {
        let mut phenotype = LinearIntentPhenotype {
            kind_bias: [0.0; INTENT_TYPE_COUNT],
            global_weights: [[0.0; OBSERVATION_COUNT]; INTENT_TYPE_COUNT],
            candidate_weights: [[0.0; CANDIDATE_FEATURE_COUNT]; INTENT_TYPE_COUNT],
            decision_temperature: 1.0,
        };
        for (value, gene) in phenotype.kind_bias.iter_mut().zip(&self.kind_bias) {
            *value = gene.sample(rng, -3.0, 3.0, false);
        }
        for (values, genes) in phenotype
            .global_weights
            .iter_mut()
            .zip(&self.global_weights)
        {
            for (value, gene) in values.iter_mut().zip(genes) {
                *value = gene.sample(rng, -3.0, 3.0, false);
            }
        }
        for (values, genes) in phenotype
            .candidate_weights
            .iter_mut()
            .zip(&self.candidate_weights)
        {
            for (value, gene) in values.iter_mut().zip(genes) {
                *value = gene.sample(rng, -3.0, 3.0, false);
            }
        }
        phenotype.decision_temperature = self.decision_temperature.sample(rng, 0.05, 2.0, true);
        phenotype
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct RecurrentIntentGenome {
    pub hidden_bias: [NeuralGene; HIDDEN_COUNT],
    pub input_weights: [[NeuralGene; OBSERVATION_COUNT]; HIDDEN_COUNT],
    pub hidden_expression: [NeuralGene; HIDDEN_COUNT],
    pub recurrent_weights: [[NeuralGene; HIDDEN_COUNT]; HIDDEN_COUNT],
    pub recurrent_expression: [NeuralGene; HIDDEN_COUNT],
    pub retention: [NeuralGene; HIDDEN_COUNT],
    pub kind_output_weights: [[NeuralGene; HIDDEN_COUNT]; INTENT_TYPE_COUNT],
    pub feature_output_weights: [[NeuralGene; HIDDEN_COUNT]; CANDIDATE_FEATURE_COUNT],
}

#[derive(Clone, Debug, PartialEq)]
pub struct RecurrentIntentPhenotype {
    pub hidden_bias: [f32; HIDDEN_COUNT],
    pub input_weights: [[f32; OBSERVATION_COUNT]; HIDDEN_COUNT],
    pub hidden_expression: [f32; HIDDEN_COUNT],
    pub recurrent_weights: [[f32; HIDDEN_COUNT]; HIDDEN_COUNT],
    pub recurrent_expression: [f32; HIDDEN_COUNT],
    pub retention: [f32; HIDDEN_COUNT],
    pub kind_output_weights: [[f32; HIDDEN_COUNT]; INTENT_TYPE_COUNT],
    pub feature_output_weights: [[f32; HIDDEN_COUNT]; CANDIDATE_FEATURE_COUNT],
}

#[derive(Clone, Debug, PartialEq)]
pub struct IntentBrainGenome {
    pub linear: LinearIntentGenome,
    pub recurrent: RecurrentIntentGenome,
}

#[derive(Clone, Debug, PartialEq)]
pub struct IntentBrainPhenotype {
    pub linear: LinearIntentPhenotype,
    pub recurrent: RecurrentIntentPhenotype,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct NeuralState {
    pub values: [f32; HIDDEN_COUNT],
}

impl Default for NeuralState {
    fn default() -> Self {
        NeuralState {
            values: [0.0; HIDDEN_COUNT],
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct RecurrentOutput {
    pub kind_residual: [f32; INTENT_TYPE_COUNT],
    pub feature_residual: [f32; CANDIDATE_FEATURE_COUNT],
    pub next_state: NeuralState,
}

impl RecurrentOutput {
    pub fn score(&self, candidate: &IntentCandidate) -> f64 {
        let kind = candidate.kind.as_index();
        self.kind_residual[kind] as f64
            + neural_dot_f64(&self.feature_residual, &candidate.features)
    }
}

impl RecurrentIntentGenome {
    pub fn random(rng: &mut Rng) -> RecurrentIntentGenome {
        let weight = NeuralGene {
            center: 0.0,
            spread: 0.03,
        };
        let output = NeuralGene {
            center: 0.0,
            spread: 0.01,
        };
        let mut genome = RecurrentIntentGenome {
            hidden_bias: [weight; HIDDEN_COUNT],
            input_weights: [[weight; OBSERVATION_COUNT]; HIDDEN_COUNT],
            hidden_expression: [NeuralGene {
                center: 0.15,
                spread: 0.02,
            }; HIDDEN_COUNT],
            recurrent_weights: [[weight; HIDDEN_COUNT]; HIDDEN_COUNT],
            recurrent_expression: [NeuralGene {
                center: 0.0,
                spread: 0.0,
            }; HIDDEN_COUNT],
            retention: [NeuralGene {
                center: 0.0,
                spread: 0.0,
            }; HIDDEN_COUNT],
            kind_output_weights: [[output; HIDDEN_COUNT]; INTENT_TYPE_COUNT],
            feature_output_weights: [[output; HIDDEN_COUNT]; CANDIDATE_FEATURE_COUNT],
        };
        for gene in &mut genome.hidden_bias {
            gene.center = rng.uniform(-0.05, 0.05) as f32;
        }
        for row in &mut genome.input_weights {
            for gene in row {
                gene.center = rng.uniform(-0.15, 0.15) as f32;
            }
        }
        for row in &mut genome.recurrent_weights {
            for gene in row {
                gene.center = rng.uniform(-0.05, 0.05) as f32;
                gene.spread = 0.02;
            }
        }
        for row in &mut genome.kind_output_weights {
            for gene in row {
                gene.center = rng.uniform(-0.02, 0.02) as f32;
            }
        }
        for row in &mut genome.feature_output_weights {
            for gene in row {
                gene.center = rng.uniform(-0.02, 0.02) as f32;
            }
        }
        genome
    }

    pub fn silence_memory(&mut self) {
        self.recurrent_expression.fill(NeuralGene {
            center: 0.0,
            spread: 0.0,
        });
        self.retention.fill(NeuralGene {
            center: 0.0,
            spread: 0.0,
        });
    }

    pub fn mutated(&self, rng: &mut Rng, rate: f64, magnitude: f64) -> RecurrentIntentGenome {
        let mut child = self.clone();
        for gene in &mut child.hidden_bias {
            *gene = gene.mutated(rng, -3.0, 3.0, rate, magnitude);
        }
        for row in &mut child.input_weights {
            for gene in row {
                *gene = gene.mutated(rng, -3.0, 3.0, rate, magnitude);
            }
        }
        for gene in &mut child.hidden_expression {
            *gene = gene.mutated(rng, 0.0, 1.0, rate, magnitude);
        }
        for row in &mut child.recurrent_weights {
            for gene in row {
                *gene = gene.mutated(rng, -3.0, 3.0, rate, magnitude);
            }
        }
        for gene in &mut child.recurrent_expression {
            *gene = gene.mutated(rng, 0.0, 1.0, rate, magnitude);
        }
        for gene in &mut child.retention {
            *gene = gene.mutated(rng, 0.0, 0.995, rate, magnitude);
        }
        for row in &mut child.kind_output_weights {
            for gene in row {
                *gene = gene.mutated(rng, -3.0, 3.0, rate, magnitude);
            }
        }
        for row in &mut child.feature_output_weights {
            for gene in row {
                *gene = gene.mutated(rng, -3.0, 3.0, rate, magnitude);
            }
        }
        child
    }

    pub fn sample(&self, rng: &mut Rng) -> RecurrentIntentPhenotype {
        let mut phenotype = RecurrentIntentPhenotype {
            hidden_bias: [0.0; HIDDEN_COUNT],
            input_weights: [[0.0; OBSERVATION_COUNT]; HIDDEN_COUNT],
            hidden_expression: [0.0; HIDDEN_COUNT],
            recurrent_weights: [[0.0; HIDDEN_COUNT]; HIDDEN_COUNT],
            recurrent_expression: [0.0; HIDDEN_COUNT],
            retention: [0.0; HIDDEN_COUNT],
            kind_output_weights: [[0.0; HIDDEN_COUNT]; INTENT_TYPE_COUNT],
            feature_output_weights: [[0.0; HIDDEN_COUNT]; CANDIDATE_FEATURE_COUNT],
        };
        for (value, gene) in phenotype.hidden_bias.iter_mut().zip(&self.hidden_bias) {
            *value = gene.sample(rng, -3.0, 3.0, false);
        }
        for (values, genes) in phenotype.input_weights.iter_mut().zip(&self.input_weights) {
            for (value, gene) in values.iter_mut().zip(genes) {
                *value = gene.sample(rng, -3.0, 3.0, false);
            }
        }
        for (value, gene) in phenotype
            .hidden_expression
            .iter_mut()
            .zip(&self.hidden_expression)
        {
            *value = gene.sample(rng, 0.0, 1.0, false);
        }
        for (values, genes) in phenotype
            .recurrent_weights
            .iter_mut()
            .zip(&self.recurrent_weights)
        {
            for (value, gene) in values.iter_mut().zip(genes) {
                *value = gene.sample(rng, -3.0, 3.0, false);
            }
        }
        for (value, gene) in phenotype
            .recurrent_expression
            .iter_mut()
            .zip(&self.recurrent_expression)
        {
            *value = gene.sample(rng, 0.0, 1.0, false);
        }
        for (value, gene) in phenotype.retention.iter_mut().zip(&self.retention) {
            *value = gene.sample(rng, 0.0, 0.995, false);
        }
        for (values, genes) in phenotype
            .kind_output_weights
            .iter_mut()
            .zip(&self.kind_output_weights)
        {
            for (value, gene) in values.iter_mut().zip(genes) {
                *value = gene.sample(rng, -3.0, 3.0, false);
            }
        }
        for (values, genes) in phenotype
            .feature_output_weights
            .iter_mut()
            .zip(&self.feature_output_weights)
        {
            for (value, gene) in values.iter_mut().zip(genes) {
                *value = gene.sample(rng, -3.0, 3.0, false);
            }
        }
        phenotype
    }
}

impl RecurrentIntentPhenotype {
    pub fn hidden_expression_mean(&self) -> f64 {
        self.hidden_expression
            .iter()
            .map(|&value| value as f64)
            .sum::<f64>()
            / HIDDEN_COUNT as f64
    }

    pub fn recurrent_expression_mean(&self) -> f64 {
        self.hidden_expression
            .iter()
            .zip(&self.recurrent_expression)
            .map(|(&hidden, &recurrent)| hidden as f64 * recurrent as f64)
            .sum::<f64>()
            / HIDDEN_COUNT as f64
    }

    pub fn retention_mean(&self) -> f64 {
        self.retention
            .iter()
            .map(|&value| value as f64)
            .sum::<f64>()
            / HIDDEN_COUNT as f64
    }

    pub fn infer(
        &self,
        observation: &ObservationV2,
        previous: NeuralState,
        lesion_state: bool,
    ) -> Option<RecurrentOutput> {
        if observation.values.iter().any(|value| !value.is_finite())
            || previous.values.iter().any(|value| !value.is_finite())
        {
            return None;
        }
        let previous_values = if lesion_state {
            [0.0; HIDDEN_COUNT]
        } else {
            previous.values
        };
        let mut active = [0.0f32; HIDDEN_COUNT];
        let mut next_state = [0.0f32; HIDDEN_COUNT];
        for hidden in 0..HIDDEN_COUNT {
            let mut pre = neural_affine_f32(
                self.hidden_bias[hidden],
                &self.input_weights[hidden],
                &observation.values,
            );
            if !lesion_state && self.recurrent_expression[hidden] != 0.0 {
                let recurrent = neural_dot_f32(&self.recurrent_weights[hidden], &previous_values);
                pre += self.recurrent_expression[hidden] * recurrent;
            }
            active[hidden] = self.hidden_expression[hidden] * pre.tanh();
            next_state[hidden] = if lesion_state {
                0.0
            } else {
                (self.retention[hidden] * previous_values[hidden]
                    + (1.0 - self.retention[hidden]) * active[hidden])
                    .clamp(-1.0, 1.0)
            };
        }

        let mut kind_residual = [0.0f32; INTENT_TYPE_COUNT];
        for (kind, output) in kind_residual.iter_mut().enumerate() {
            *output = neural_dot_f32(&self.kind_output_weights[kind], &active);
        }
        let mut feature_residual = [0.0f32; CANDIDATE_FEATURE_COUNT];
        for (feature, output) in feature_residual.iter_mut().enumerate() {
            *output = neural_dot_f32(&self.feature_output_weights[feature], &active);
        }
        if active
            .iter()
            .chain(&next_state)
            .any(|value| !value.is_finite())
            || kind_residual.iter().any(|value| !value.is_finite())
            || feature_residual.iter().any(|value| !value.is_finite())
        {
            return None;
        }
        Some(RecurrentOutput {
            kind_residual,
            feature_residual,
            next_state: NeuralState { values: next_state },
        })
    }
}

#[cfg(test)]
mod microbench {
    use super::*;
    use crate::behavior::intent::{IntentKind, IntentTarget, MAX_INTENT_CANDIDATES};
    use std::hint::black_box;
    use std::time::Instant;

    const DECISIONS: usize = 200_000;

    fn fixtures() -> (
        LinearIntentPhenotype,
        RecurrentIntentPhenotype,
        ObservationV2,
        Vec<IntentCandidate>,
    ) {
        let mut linear = LinearIntentPhenotype {
            kind_bias: [0.0; INTENT_TYPE_COUNT],
            global_weights: [[0.0; OBSERVATION_COUNT]; INTENT_TYPE_COUNT],
            candidate_weights: [[0.0; CANDIDATE_FEATURE_COUNT]; INTENT_TYPE_COUNT],
            decision_temperature: 0.7,
        };
        for (kind, bias) in linear.kind_bias.iter_mut().enumerate() {
            *bias = kind as f32 * 0.013 - 0.05;
            for (index, weight) in linear.global_weights[kind].iter_mut().enumerate() {
                *weight = ((kind * OBSERVATION_COUNT + index) as f32 * 0.017).sin();
            }
            for (index, weight) in linear.candidate_weights[kind].iter_mut().enumerate() {
                *weight = ((kind * CANDIDATE_FEATURE_COUNT + index) as f32 * 0.023).cos();
            }
        }

        let mut observation = ObservationV2::default();
        for (index, value) in observation.values.iter_mut().enumerate() {
            *value = (index as f32 * 0.031).sin();
        }

        let candidates = (0..MAX_INTENT_CANDIDATES)
            .map(|candidate_index| {
                let mut features = [0.0; CANDIDATE_FEATURE_COUNT];
                for (feature_index, value) in features.iter_mut().enumerate() {
                    *value = ((candidate_index * CANDIDATE_FEATURE_COUNT + feature_index) as f32
                        * 0.019)
                        .cos();
                }
                IntentCandidate {
                    kind: IntentKind::ALL[candidate_index % INTENT_TYPE_COUNT],
                    target: IntentTarget::None,
                    features,
                    predicted_duration_ticks: 1,
                    predicted_chemical_cost: 0.0,
                    predicted_mana_cost: 0.0,
                }
            })
            .collect();

        let mut recurrent = RecurrentIntentPhenotype {
            hidden_bias: [0.0; HIDDEN_COUNT],
            input_weights: [[0.0; OBSERVATION_COUNT]; HIDDEN_COUNT],
            hidden_expression: [0.5; HIDDEN_COUNT],
            recurrent_weights: [[0.0; HIDDEN_COUNT]; HIDDEN_COUNT],
            recurrent_expression: [0.25; HIDDEN_COUNT],
            retention: [0.4; HIDDEN_COUNT],
            kind_output_weights: [[0.0; HIDDEN_COUNT]; INTENT_TYPE_COUNT],
            feature_output_weights: [[0.0; HIDDEN_COUNT]; CANDIDATE_FEATURE_COUNT],
        };
        for hidden in 0..HIDDEN_COUNT {
            recurrent.hidden_bias[hidden] = hidden as f32 * 0.007;
            for input in 0..OBSERVATION_COUNT {
                recurrent.input_weights[hidden][input] =
                    ((hidden * OBSERVATION_COUNT + input) as f32 * 0.011).sin();
            }
            for previous in 0..HIDDEN_COUNT {
                recurrent.recurrent_weights[hidden][previous] =
                    ((hidden * HIDDEN_COUNT + previous) as f32 * 0.029).cos();
            }
        }
        for kind in 0..INTENT_TYPE_COUNT {
            for hidden in 0..HIDDEN_COUNT {
                recurrent.kind_output_weights[kind][hidden] =
                    ((kind * HIDDEN_COUNT + hidden) as f32 * 0.037).sin();
            }
        }
        for feature in 0..CANDIDATE_FEATURE_COUNT {
            for hidden in 0..HIDDEN_COUNT {
                recurrent.feature_output_weights[feature][hidden] =
                    ((feature * HIDDEN_COUNT + hidden) as f32 * 0.041).cos();
            }
        }
        (linear, recurrent, observation, candidates)
    }

    #[test]
    fn neural_dot_and_cached_scores_stay_within_contract() {
        let (linear, recurrent, observation, candidates) = fixtures();
        let globals = linear.global_scores(&observation);
        for candidate in &candidates {
            let kind = candidate.kind.as_index();
            let scalar = linear.kind_bias[kind] as f64
                + scalar_dot_f64(&linear.global_weights[kind], &observation.values)
                + scalar_dot_f64(&linear.candidate_weights[kind], &candidate.features);
            let optimized = linear.score_with_globals(&globals, candidate);
            #[cfg(all(feature = "simd-neural", target_arch = "aarch64"))]
            assert!((optimized - scalar).abs() <= 2.0e-5);
            #[cfg(not(all(feature = "simd-neural", target_arch = "aarch64")))]
            assert_eq!(optimized.to_bits(), scalar.to_bits());
        }

        let scalar = scalar_dot_f32(&recurrent.input_weights[0], &observation.values);
        let optimized = neural_dot_f32(&recurrent.input_weights[0], &observation.values);
        assert!((optimized - scalar).abs() <= 2.0e-5);
    }

    #[test]
    #[ignore = "manual release-mode microbenchmark"]
    fn neural_kernels_release_microbenchmark() {
        let (linear, recurrent, observation, candidates) = fixtures();
        let candidate_count = DECISIONS * candidates.len();

        let started = Instant::now();
        let mut linear_checksum = 0.0;
        for _ in 0..DECISIONS {
            let globals = linear.global_scores(black_box(&observation));
            for candidate in &candidates {
                linear_checksum +=
                    black_box(linear.score_with_globals(black_box(&globals), black_box(candidate)));
            }
        }
        let linear_elapsed = started.elapsed();

        let started = Instant::now();
        let mut recurrent_checksum = 0.0;
        let mut state = NeuralState::default();
        for _ in 0..DECISIONS {
            let output = recurrent
                .infer(black_box(&observation), black_box(state), false)
                .expect("finite fixture");
            state = output.next_state;
            for candidate in &candidates {
                recurrent_checksum += black_box(output.score(black_box(candidate)));
            }
        }
        let recurrent_elapsed = started.elapsed();

        assert!(linear_checksum.is_finite());
        assert!(recurrent_checksum.is_finite());
        println!(
            "neural_microbench decisions={DECISIONS} candidates={candidate_count} \
             linear_ns_per_candidate={:.3} recurrent_ns_per_decision={:.3} \
             recurrent_ns_per_candidate={:.3} checksums=({linear_checksum:.6},{recurrent_checksum:.6})",
            linear_elapsed.as_nanos() as f64 / candidate_count as f64,
            recurrent_elapsed.as_nanos() as f64 / DECISIONS as f64,
            recurrent_elapsed.as_nanos() as f64 / candidate_count as f64,
        );
    }
}
