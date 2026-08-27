//! Generic stochastic cellular affordances.
//!
//! This module deliberately contains no organism-level labels such as
//! "adaptable", "organelle", or "multicellular". It defines only heritable
//! modules, regulation, physical bonds, and bounded internal guests.

use crate::chemistry::Inventory;
use crate::rng::{Fnv, Rng};

pub const REGULATORY_INPUTS: usize = 6;
pub const RECEPTOR_DIMENSIONS: usize = 4;
pub const COMPARTMENT_TAGS: u8 = 4;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum ModulePrimitive {
    Catalysis = 0,
    Transport = 1,
    Storage = 2,
    Signal = 3,
    Structure = 4,
}

impl ModulePrimitive {
    pub const COUNT: usize = 5;

    fn random(rng: &mut Rng) -> Self {
        match rng.below(Self::COUNT as u64) {
            0 => Self::Catalysis,
            1 => Self::Transport,
            2 => Self::Storage,
            3 => Self::Signal,
            _ => Self::Structure,
        }
    }
}

#[derive(Clone, Debug)]
pub struct ModuleGene {
    pub primitive: ModulePrimitive,
    pub substrate: u16,
    pub compartment_tag: u8,
    pub efficiency: f32,
    pub upkeep: f32,
    pub bias: f32,
    pub regulatory_weights: [f32; REGULATORY_INPUTS],
}

impl ModuleGene {
    fn random(rng: &mut Rng, molecule_count: usize) -> Self {
        let mut regulatory_weights = [0.0; REGULATORY_INPUTS];
        for weight in &mut regulatory_weights {
            *weight = rng.uniform(-1.0, 1.0) as f32;
        }
        Self {
            primitive: ModulePrimitive::random(rng),
            substrate: rng.below(molecule_count as u64) as u16,
            compartment_tag: rng.below(COMPARTMENT_TAGS as u64) as u8,
            efficiency: rng.uniform(0.05, 1.0) as f32,
            upkeep: rng.uniform(0.01, 0.20) as f32,
            bias: rng.uniform(-1.5, 0.5) as f32,
            regulatory_weights,
        }
    }

    fn mutate(&mut self, rng: &mut Rng, rate: f64, magnitude: f64, molecule_count: usize) {
        if rng.chance(rate) {
            self.efficiency =
                (self.efficiency + rng.gauss() as f32 * magnitude as f32).clamp(0.0, 1.5);
        }
        if rng.chance(rate) {
            self.upkeep =
                (self.upkeep + rng.gauss() as f32 * magnitude as f32 * 0.1).clamp(0.001, 0.5);
        }
        if rng.chance(rate) {
            self.bias = (self.bias + rng.gauss() as f32 * magnitude as f32).clamp(-4.0, 4.0);
        }
        for weight in &mut self.regulatory_weights {
            if rng.chance(rate) {
                *weight = (*weight + rng.gauss() as f32 * magnitude as f32).clamp(-4.0, 4.0);
            }
        }
        if rng.chance(rate * 0.25) {
            self.substrate = rng.below(molecule_count as u64) as u16;
        }
        if rng.chance(rate * 0.15) {
            self.compartment_tag = rng.below(COMPARTMENT_TAGS as u64) as u8;
        }
        if rng.chance(rate * 0.08) {
            self.primitive = ModulePrimitive::random(rng);
        }
    }
}

#[derive(Clone, Debug)]
pub struct EmergenceGenome {
    pub modules: Vec<ModuleGene>,
    pub receptor: [f32; RECEPTOR_DIMENSIONS],
    pub exchange: f32,
    pub bond_retention: f32,
    pub engulfment: f32,
    pub guest_tolerance: f32,
}

impl EmergenceGenome {
    pub fn random(rng: &mut Rng, molecule_count: usize, max_modules: usize) -> Self {
        let module_count = (1 + rng.below(max_modules.clamp(1, 4) as u64)) as usize;
        let modules = (0..module_count)
            .map(|_| ModuleGene::random(rng, molecule_count))
            .collect();
        let mut receptor = [0.0; RECEPTOR_DIMENSIONS];
        for value in &mut receptor {
            *value = rng.uniform(-1.0, 1.0) as f32;
        }
        Self {
            modules,
            receptor,
            exchange: rng.f64() as f32,
            bond_retention: rng.f64() as f32,
            engulfment: rng.f64() as f32,
            guest_tolerance: rng.f64() as f32,
        }
    }

    pub fn offspring(
        donor: &Self,
        rng: &mut Rng,
        mutation_rate: f64,
        mutation_magnitude: f64,
        structural_rate: f64,
        molecule_count: usize,
        max_modules: usize,
    ) -> Self {
        let mut child = donor.clone();
        for module in &mut child.modules {
            module.mutate(rng, mutation_rate, mutation_magnitude, molecule_count);
        }
        let structural_rate = structural_rate.clamp(0.0, 1.0);
        if child.modules.len() < max_modules && rng.chance(structural_rate) {
            let duplicated = if child.modules.is_empty() || rng.chance(0.25) {
                ModuleGene::random(rng, molecule_count)
            } else {
                child.modules[rng.below(child.modules.len() as u64) as usize].clone()
            };
            child.modules.push(duplicated);
        }
        if child.modules.len() > 1 && rng.chance(structural_rate) {
            let index = rng.below(child.modules.len() as u64) as usize;
            child.modules.swap_remove(index);
        }
        if child.modules.len() > 1 && rng.chance(structural_rate * 0.5) {
            rng.shuffle(&mut child.modules);
        }
        for value in &mut child.receptor {
            if rng.chance(mutation_rate) {
                *value = (*value + rng.gauss() as f32 * mutation_magnitude as f32).clamp(-1.0, 1.0);
            }
        }
        for value in [
            &mut child.exchange,
            &mut child.bond_retention,
            &mut child.engulfment,
            &mut child.guest_tolerance,
        ] {
            if rng.chance(mutation_rate) {
                *value = (*value + rng.gauss() as f32 * mutation_magnitude as f32).clamp(0.0, 1.0);
            }
        }
        child
    }

    pub fn receptor_similarity(&self, other: &Self) -> f64 {
        let squared = self
            .receptor
            .iter()
            .zip(other.receptor)
            .map(|(&left, right)| (left as f64 - right as f64).powi(2))
            .sum::<f64>();
        (-squared).exp()
    }

    pub fn hash_into(&self, hash: &mut Fnv) {
        hash.u64(self.modules.len() as u64);
        for module in &self.modules {
            hash.u64(module.primitive as u64);
            hash.u64(module.substrate as u64);
            hash.u64(module.compartment_tag as u64);
            hash.u64(module.efficiency.to_bits() as u64);
            hash.u64(module.upkeep.to_bits() as u64);
            hash.u64(module.bias.to_bits() as u64);
            for &weight in &module.regulatory_weights {
                hash.u64(weight.to_bits() as u64);
            }
        }
        for &value in &self.receptor {
            hash.u64(value.to_bits() as u64);
        }
        hash.u64(self.exchange.to_bits() as u64);
        hash.u64(self.bond_retention.to_bits() as u64);
        hash.u64(self.engulfment.to_bits() as u64);
        hash.u64(self.guest_tolerance.to_bits() as u64);
    }
}

#[derive(Clone, Debug)]
pub struct InternalGuest {
    pub source_organism_id: u32,
    pub genome_id: u32,
    pub species_id: u32,
    pub inventory: Inventory,
    pub free_energy: f64,
    pub exchange: f32,
    pub age: u32,
}

#[derive(Clone, Debug)]
pub struct CellularState {
    pub expression: Vec<f32>,
    pub local_signal: f32,
    pub emitted_signal: f32,
    pub guests: Vec<InternalGuest>,
}

impl CellularState {
    pub fn new(module_count: usize) -> Self {
        Self {
            expression: vec![0.0; module_count],
            local_signal: 0.0,
            emitted_signal: 0.0,
            guests: Vec::new(),
        }
    }

    pub fn regulate(&mut self, genome: &EmergenceGenome, inputs: [f32; REGULATORY_INPUTS]) {
        if self.expression.len() != genome.modules.len() {
            self.expression.resize(genome.modules.len(), 0.0);
        }
        self.emitted_signal = 0.0;
        for (expression, module) in self.expression.iter_mut().zip(&genome.modules) {
            let activation = module.bias
                + module
                    .regulatory_weights
                    .iter()
                    .zip(inputs)
                    .map(|(weight, input)| *weight * input)
                    .sum::<f32>();
            *expression = 1.0 / (1.0 + (-activation.clamp(-12.0, 12.0)).exp());
            if module.primitive == ModulePrimitive::Signal {
                self.emitted_signal += *expression * module.efficiency;
            }
        }
        self.emitted_signal = self.emitted_signal.clamp(0.0, 1.0);
    }

    pub fn primitive_expression(
        &self,
        genome: &EmergenceGenome,
        primitive: ModulePrimitive,
    ) -> f64 {
        self.expression
            .iter()
            .zip(&genome.modules)
            .filter(|(_, module)| module.primitive == primitive)
            .map(|(&expression, module)| expression as f64 * module.efficiency as f64)
            .sum()
    }

    pub fn substrate_expression(
        &self,
        genome: &EmergenceGenome,
        primitive: ModulePrimitive,
        substrate: u16,
    ) -> f64 {
        self.expression
            .iter()
            .zip(&genome.modules)
            .filter(|(_, module)| module.primitive == primitive && module.substrate == substrate)
            .map(|(&expression, module)| expression as f64 * module.efficiency as f64)
            .sum()
    }

    pub fn upkeep(&self, genome: &EmergenceGenome) -> f64 {
        self.expression
            .iter()
            .zip(&genome.modules)
            .map(|(&expression, module)| expression as f64 * module.upkeep as f64)
            .sum()
    }
}

#[derive(Clone, Copy, Debug)]
pub struct Bond {
    pub left: u32,
    pub right: u32,
    pub formed_tick: u32,
    pub strength: f32,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn structural_mutation_is_bounded_and_deterministic() {
        let mut founder_rng = Rng::new(7);
        let founder = EmergenceGenome::random(&mut founder_rng, 48, 12);
        let mut left_rng = Rng::new(9);
        let mut right_rng = Rng::new(9);
        let left = EmergenceGenome::offspring(&founder, &mut left_rng, 0.8, 0.3, 1.0, 48, 12);
        let right = EmergenceGenome::offspring(&founder, &mut right_rng, 0.8, 0.3, 1.0, 48, 12);
        assert!((1..=12).contains(&left.modules.len()));
        let mut left_hash = Fnv::new();
        let mut right_hash = Fnv::new();
        left.hash_into(&mut left_hash);
        right.hash_into(&mut right_hash);
        assert_eq!(left_hash.finish(), right_hash.finish());
    }
}
