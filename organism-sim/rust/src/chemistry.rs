//! Procedural chemistry catalog: elements, molecules, batches, inventories.
//! Faithful port of `organism_sim.chemistry` (same formulas and thresholds).

use crate::config::SimConfig;
use crate::rng::Rng;
use rustc_hash::FxHashMap;

pub type Signature = [f64; 4];

pub fn simplex(values: [f64; 4]) -> Signature {
    let mut raw = [0.0f64; 4];
    for i in 0..4 {
        raw[i] = 1e-9_f64.max(values[i]);
    }
    let total: f64 = raw.iter().sum();
    let mut out = [0.0f64; 4];
    for i in 0..4 {
        out[i] = raw[i] / total;
    }
    out
}

pub fn signature_similarity(left: &Signature, right: &Signature) -> f64 {
    let diff = (0..4).map(|i| (left[i] - right[i]).abs()).sum::<f64>();
    (1.0 - 0.5 * diff).max(0.0)
}

#[derive(Clone, Debug)]
pub struct ElementDef {
    pub atomic_mass: i64,
    pub energy_contribution: f64,
    pub bond_capacity: i64,
    pub polarity: f64,
    pub reactivity: f64,
    pub rigidity: f64,
    pub signature: Signature,
    pub color: [u8; 3],
}

#[derive(Clone, Debug)]
pub struct MoleculeDef {
    pub molecule_id: u16,
    pub composition: Vec<u8>,
    pub mass: i64,
    pub energy_capacity: f64,
    pub signature: Signature,
    #[allow(dead_code)]
    pub polarity: f64,
    pub reactivity: f64,
    pub stability: f64,
    #[allow(dead_code)]
    pub rigidity: f64,
    pub permeability: f64,
    pub complexity: f64,
    #[allow(dead_code)]
    pub color: [u8; 3],
}

#[derive(Clone, Copy, Debug)]
pub struct Batch {
    pub molecule_id: u16,
    pub count: i64,
    pub energy: f64,
}

impl Batch {
    /// Python MoleculeBatch.take: proportional-energy removal.
    pub fn take(&mut self, count: i64) -> Batch {
        let count = count.max(0).min(self.count);
        if count == 0 {
            return Batch {
                molecule_id: self.molecule_id,
                count: 0,
                energy: 0.0,
            };
        }
        let taken_energy = self.energy * count as f64 / self.count as f64;
        self.count -= count;
        self.energy -= taken_energy;
        if self.count == 0 {
            self.energy = 0.0;
        }
        Batch {
            molecule_id: self.molecule_id,
            count,
            energy: taken_energy,
        }
    }
}

/// A recombinational environmental reaction `A + B -> C`.
///
/// Validity is guaranteed by construction: `composition(C) ==
/// composition(A) + composition(B)` exactly, so executing a reaction
/// conserves every element vector, and (with the kernel's energy
/// bookkeeping) total chemical energy plus released heat.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ReactionRule {
    pub a: u16,
    pub b: u16,
    pub c: u16,
}

/// Inventory kept sorted by molecule_id (Python used insertion-ordered dicts;
/// sorted order is deterministic and matches every `sorted()`/`min()` use).
pub type Inventory = Vec<Batch>;

pub fn add_batch(inv: &mut Inventory, batch: Batch) {
    if batch.count <= 0 {
        return;
    }
    match inv.binary_search_by(|b| b.molecule_id.cmp(&batch.molecule_id)) {
        Ok(pos) => {
            inv[pos].count += batch.count;
            inv[pos].energy += batch.energy;
        }
        Err(pos) => inv.insert(pos, batch),
    }
}

pub fn inventory_count(inv: &Inventory) -> i64 {
    inv.iter().map(|b| b.count).sum()
}

pub fn inventory_energy(inv: &Inventory) -> f64 {
    inv.iter().map(|b| b.energy).sum()
}

#[derive(Clone, Debug)]
pub struct Catalog {
    pub elements: Vec<ElementDef>,
    pub molecules: Vec<MoleculeDef>,
    /// 1.0 - stability, precomputed per molecule.
    pub instability: Vec<f64>,
    /// Lower-median of molecule energy capacities.
    pub reference_energy: f64,
}

impl Catalog {
    pub fn generate(config: &SimConfig, rng: &mut Rng) -> Catalog {
        let mut elements: Vec<ElementDef> = Vec::with_capacity(config.element_count);
        for _ in 0..config.element_count {
            let vals = [
                rng.f64() + 0.05,
                rng.f64() + 0.05,
                rng.f64() + 0.05,
                rng.f64() + 0.05,
            ];
            elements.push(ElementDef {
                atomic_mass: rng.randint(1, 12),
                energy_contribution: rng.uniform(0.7, 1.5),
                bond_capacity: rng.randint(1, 4),
                polarity: rng.f64(),
                reactivity: rng.f64(),
                rigidity: rng.f64(),
                signature: simplex(vals),
                color: [
                    rng.randint(70, 245) as u8,
                    rng.randint(70, 245) as u8,
                    rng.randint(70, 245) as u8,
                ],
            });
        }

        let n_elements = config.element_count;
        let mut compositions: Vec<Vec<u8>> = Vec::with_capacity(config.molecule_count);
        let mut seen: std::collections::HashSet<Vec<u8>> = std::collections::HashSet::new();
        for e in 0..n_elements {
            let mut comp = vec![0u8; n_elements];
            comp[e] = 1;
            seen.insert(comp.clone());
            compositions.push(comp);
        }

        // Reserve a small deterministic closure of simple dimer products when
        // dynamic chemistry is enabled. This guarantees that the bounded
        // catalog contains real, element-conserving reactions without adding
        // molecule ids at runtime. The feature remains absent from this path
        // when it is disabled.
        if config.dynamic_chemistry_enabled && config.reaction_rule_count > 0 {
            let mut closure = Vec::new();
            for e in 0..n_elements {
                let mut comp = vec![0u8; n_elements];
                comp[e] = 2;
                closure.push(comp);
            }
            for left in 0..n_elements {
                for right in (left + 1)..n_elements {
                    let mut comp = vec![0u8; n_elements];
                    comp[left] = 1;
                    comp[right] = 1;
                    closure.push(comp);
                }
            }
            for comp in closure {
                if compositions.len() >= config.molecule_count {
                    break;
                }
                if seen.insert(comp.clone()) {
                    compositions.push(comp);
                }
            }
        }

        let mut attempts = 0i64;
        while compositions.len() < config.molecule_count
            && attempts < config.molecule_count as i64 * 100
        {
            attempts += 1;
            let units = rng.randint(2, config.maximum_molecule_units);
            let mut counts = vec![0u8; n_elements];
            for _ in 0..units {
                let e = rng.below(n_elements as u64) as usize;
                counts[e] += 1;
            }
            if seen.contains(&counts) {
                continue;
            }
            let total_bonds: i64 = counts
                .iter()
                .enumerate()
                .map(|(e, &c)| elements[e].bond_capacity * c as i64)
                .sum();
            if total_bonds < 2 * (units - 1) {
                continue;
            }
            seen.insert(counts.clone());
            compositions.push(counts);
        }

        let molecules: Vec<MoleculeDef> = compositions
            .into_iter()
            .enumerate()
            .map(|(id, comp)| derive_molecule(id as u16, &comp, &elements, rng))
            .collect();

        let mut capacities: Vec<f64> = molecules.iter().map(|m| m.energy_capacity).collect();
        capacities.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let reference_energy = capacities[capacities.len() / 2];
        let instability = molecules.iter().map(|m| 1.0 - m.stability).collect();
        Catalog {
            elements,
            molecules,
            instability,
            reference_energy,
        }
    }

    pub fn inventory_mass(&self, inv: &Inventory) -> i64 {
        inv.iter()
            .map(|b| self.molecules[b.molecule_id as usize].mass * b.count)
            .sum()
    }

    pub fn inventory_signature(&self, inv: &Inventory) -> Signature {
        let mut weighted = [0.0f64; 4];
        let mut total_mass = 0.0f64;
        for batch in inv {
            let def = &self.molecules[batch.molecule_id as usize];
            let weight = def.mass as f64 * batch.count as f64;
            total_mass += weight;
            for (accumulator, signature) in weighted.iter_mut().zip(def.signature) {
                *accumulator += weight * signature;
            }
        }
        if total_mass <= 0.0 {
            return [0.25, 0.25, 0.25, 0.25];
        }
        simplex([
            weighted[0] / total_mass,
            weighted[1] / total_mass,
            weighted[2] / total_mass,
            weighted[3] / total_mass,
        ])
    }

    /// Deterministically derive up to `max_rules` recombinational
    /// environmental reactions from the catalog.
    ///
    /// A rule `(a, b, c)` is valid iff `composition(c) ==
    /// composition(a) + composition(b)` exactly (element vectors, per unit),
    /// so executing it conserves every element. Pairs satisfy `a <= b`
    /// (dimerization allowed); results are deterministic for a given
    /// catalog and `max_rules`.
    pub fn reaction_rules(&self, max_rules: usize) -> Vec<ReactionRule> {
        if max_rules == 0 || self.molecules.len() < 3 {
            return Vec::new();
        }
        let mut by_composition: FxHashMap<Vec<u16>, u16> = FxHashMap::default();
        for molecule in &self.molecules {
            by_composition.insert(
                molecule
                    .composition
                    .iter()
                    .map(|&amount| amount as u16)
                    .collect(),
                molecule.molecule_id,
            );
        }
        let n = self.molecules.len();
        let mut rules = Vec::with_capacity(max_rules);
        'outer: for a in 0..n {
            for b in a..n {
                let sum = sum_compositions(
                    &self.molecules[a].composition,
                    &self.molecules[b].composition,
                );
                if let Some(&c) = by_composition.get(&sum) {
                    if c != a as u16 && c != b as u16 {
                        rules.push(ReactionRule {
                            a: a as u16,
                            b: b as u16,
                            c,
                        });
                        if rules.len() == max_rules {
                            break 'outer;
                        }
                    }
                }
            }
        }
        rules
    }

    pub fn validate_batch(&self, batch: &Batch) -> Result<(), String> {
        if batch.count < 0 || batch.energy < -1e-12 {
            return Err(format!("negative molecule batch: {}", batch.molecule_id));
        }
        let capacity =
            batch.count as f64 * self.molecules[batch.molecule_id as usize].energy_capacity;
        if batch.energy > capacity + 1e-9 {
            return Err(format!(
                "molecule batch exceeds energy capacity: mol={} energy={} cap={}",
                batch.molecule_id, batch.energy, capacity
            ));
        }
        Ok(())
    }
}

fn sum_compositions(left: &[u8], right: &[u8]) -> Vec<u16> {
    left.iter()
        .zip(right)
        .map(|(&x, &y)| x as u16 + y as u16)
        .collect()
}

fn derive_molecule(
    molecule_id: u16,
    composition: &[u8],
    elements: &[ElementDef],
    rng: &mut Rng,
) -> MoleculeDef {
    let units: i64 = composition.iter().map(|&c| c as i64).sum();
    let weights: Vec<f64> = composition
        .iter()
        .map(|&c| c as f64 / units as f64)
        .collect();
    let mass: i64 = composition
        .iter()
        .zip(elements)
        .map(|(&c, e)| c as i64 * e.atomic_mass)
        .sum();
    let capacity: f64 = composition
        .iter()
        .zip(elements)
        .map(|(&c, e)| c as f64 * e.energy_contribution)
        .sum();

    let mut sig_vals = [0.0f64; 4];
    for (axis, value) in sig_vals.iter_mut().enumerate() {
        let base: f64 = weights
            .iter()
            .zip(elements)
            .map(|(&w, e)| w * e.signature[axis])
            .sum();
        *value = base + rng.uniform(-0.04, 0.04);
    }
    let signature = simplex(sig_vals);

    let diversity = composition.iter().filter(|&&c| c > 0).count() as f64 / elements.len() as f64;
    fn weighted<F>(weights: &[f64], elements: &[ElementDef], f: F) -> f64
    where
        F: Fn(&ElementDef) -> f64,
    {
        weights.iter().zip(elements).map(|(&w, e)| w * f(e)).sum()
    }
    let polarity =
        (weighted(&weights, elements, |e| e.polarity) + rng.uniform(-0.08, 0.08)).clamp(0.0, 1.0);
    let reactivity = (weighted(&weights, elements, |e| e.reactivity)
        + 0.15 * diversity
        + rng.uniform(-0.08, 0.08))
    .clamp(0.0, 1.0);
    let rigidity =
        (weighted(&weights, elements, |e| e.rigidity) + rng.uniform(-0.08, 0.08)).clamp(0.0, 1.0);
    let stability =
        (0.75 - 0.45 * reactivity + 0.25 * rigidity + rng.uniform(-0.08, 0.08)).clamp(0.0, 1.0);
    let complexity = ((units - 1) as f64 / 11.0 + diversity * 0.25).min(1.0);
    let permeability = (1.0 - 0.65 * complexity + 0.15 * polarity).clamp(0.05, 1.0);
    let mut color = [0u8; 3];
    for (channel, value) in color.iter_mut().enumerate() {
        let v: f64 = weights
            .iter()
            .zip(elements)
            .map(|(&w, e)| w * e.color[channel] as f64)
            .sum();
        *value = v.clamp(35.0, 255.0) as u8;
    }

    MoleculeDef {
        molecule_id,
        composition: composition.to_vec(),
        mass,
        energy_capacity: capacity,
        signature,
        polarity,
        reactivity,
        stability,
        rigidity,
        permeability,
        complexity,
        color,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_catalog() -> Catalog {
        let config = SimConfig {
            dynamic_chemistry_enabled: true,
            ..SimConfig::default()
        };
        let mut rng = Rng::new(42);
        Catalog::generate(&config, &mut rng)
    }

    #[test]
    fn reaction_rules_are_element_conserving_and_deterministic() {
        let catalog = test_catalog();
        let rules = catalog.reaction_rules(6);
        assert!(!rules.is_empty());
        assert_eq!(rules, catalog.reaction_rules(6));
        for rule in &rules {
            let a = &catalog.molecules[rule.a as usize].composition;
            let b = &catalog.molecules[rule.b as usize].composition;
            let c = &catalog.molecules[rule.c as usize].composition;
            assert_eq!(c.len(), a.len());
            for e in 0..c.len() {
                assert_eq!(c[e], a[e] + b[e], "element {} in rule {:?}", e, rule);
            }
            assert_ne!(rule.c, rule.a);
            assert_ne!(rule.c, rule.b);
            assert!(rule.a <= rule.b);
        }
    }

    #[test]
    fn reaction_rules_respect_max_and_empty_cases() {
        let catalog = test_catalog();
        assert!(catalog.reaction_rules(0).is_empty());
        let full = catalog.reaction_rules(32);
        for max in [1usize, 2, 3, 4, 8, 32] {
            assert!(catalog.reaction_rules(max).len() <= max);
        }
        assert_eq!(catalog.reaction_rules(32), full);
        assert_eq!(
            catalog.reaction_rules(8),
            full.iter().take(8).cloned().collect::<Vec<_>>()
        );
    }
}
