//! Chunked infinite world: per-chunk heat fields, deposit inventories,
//! occupancy, and on-demand procedural chunk generation. Port of
//! `organism_sim.world` (chunk RNG is the kernel's own xoshiro256++).

use crate::chemistry::{add_batch, Batch, Inventory};
use crate::rng::{mix64, Rng};
use rustc_hash::FxHashMap;

pub type Position = (i64, i64);

#[derive(Clone, Debug)]
pub struct Chunk {
    pub heat: Vec<f64>,
    pub occupancy: Vec<Vec<u32>>,
    pub has_heat: bool,
}

/// Molecule facts the world generator needs (avoids holding a &Catalog).
#[derive(Clone, Debug)]
pub struct GenMolecule {
    pub molecule_id: u16,
    pub energy_capacity: f64,
    pub composition: Vec<u8>,
}

#[derive(Clone)]
pub struct WorldGenParams {
    pub region_width: i64,
    pub region_height: i64,
    pub chunk_size: usize,
    pub initial_deposits: i64,
    pub batch_min: i64,
    pub batch_max: i64,
    pub element_count: usize,
    /// Optional demand histogram over molecule ids (deposit_match_ecology).
    pub molecule_weights: Option<Vec<f64>>,
}

pub struct World {
    pub params: WorldGenParams,
    pub terrain_seed: u64,
    pub chunks: FxHashMap<(i64, i64), Chunk>,
    pub deposits: FxHashMap<Position, Inventory>,
    /// Density values are divided by `biodeposit_scale`, making uniform decay
    /// O(1) per tick instead of a scan over every accumulated site.
    pub biodeposits: FxHashMap<Position, f64>,
    pub biodeposit_scale: f64,
    pub occupied_cells: usize,
    pub generated_elements: Vec<i64>,
    pub generated_energy: f64,
    molecules: Vec<GenMolecule>,
}

impl World {
    pub fn generate(
        params: WorldGenParams,
        molecules: Vec<GenMolecule>,
        terrain_seed: u64,
    ) -> World {
        let element_count = params.element_count;
        let mut world = World {
            params,
            terrain_seed,
            chunks: FxHashMap::default(),
            deposits: FxHashMap::default(),
            biodeposits: FxHashMap::default(),
            biodeposit_scale: 1.0,
            occupied_cells: 0,
            generated_elements: vec![0; element_count],
            generated_energy: 0.0,
            molecules,
        };
        let cs = world.params.chunk_size as i64;
        let cx_max = -(-world.params.region_width / cs);
        let cy_max = -(-world.params.region_height / cs);
        for cx in 0..cx_max {
            for cy in 0..cy_max {
                world.ensure_chunk(cx, cy);
            }
        }
        world
    }

    pub fn chunk_rng(&self, cx: i64, cy: i64) -> Rng {
        let seed = mix64(self.terrain_seed ^ mix64(cx as u64) ^ mix64(cy as u64).wrapping_mul(3));
        Rng::new(seed)
    }

    pub fn ensure_chunk(&mut self, cx: i64, cy: i64) {
        if self.chunks.contains_key(&(cx, cy)) {
            return;
        }
        let size = self.params.chunk_size;
        self.chunks.insert(
            (cx, cy),
            Chunk {
                heat: vec![0.0; size * size],
                occupancy: vec![Vec::new(); size * size],
                has_heat: false,
            },
        );
        self.generate_chunk(cx, cy);
    }

    fn generate_chunk(&mut self, cx: i64, cy: i64) {
        let mut rng = self.chunk_rng(cx, cy);
        let size = self.params.chunk_size as i64;
        let chunk_area = size * size;
        let region_area = (self.params.region_width * self.params.region_height).max(1);
        let density = self.params.initial_deposits as f64 / region_area as f64;
        let expected = density * chunk_area as f64;
        let count = expected as i64 + if rng.chance(expected % 1.0) { 1 } else { 0 };
        let mut elements = vec![0i64; self.params.element_count];
        let mut energy = 0.0f64;
        for _ in 0..count {
            let x = cx * size + rng.below(size as u64) as i64;
            let y = cy * size + rng.below(size as u64) as i64;
            let molecule = self.pick_molecule(&mut rng);
            let units = rng.randint(self.params.batch_min, self.params.batch_max);
            let charge = rng.uniform(0.45, 1.0);
            let batch = Batch {
                molecule_id: molecule.molecule_id,
                count: units,
                energy: molecule.energy_capacity * units as f64 * charge,
            };
            energy += batch.energy;
            for (e, &amount) in molecule.composition.iter().enumerate() {
                elements[e] += amount as i64 * units;
            }
            self.deposit_batch_raw((x, y), batch);
        }
        let spring_expected = (self.params.initial_deposits / 8).max(1) as f64 * chunk_area as f64
            / region_area as f64;
        let springs = spring_expected as i64
            + if rng.chance(spring_expected % 1.0) {
                1
            } else {
                0
            };
        for _ in 0..springs {
            let x = cx * size + rng.below(size as u64) as i64;
            let y = cy * size + rng.below(size as u64) as i64;
            let amount = rng.uniform(0.1, 2.0);
            self.add_heat((x, y), amount);
            energy += amount;
        }
        for (a, b) in self.generated_elements.iter_mut().zip(elements.iter()) {
            *a += *b;
        }
        self.generated_energy += energy;
    }

    fn pick_molecule(&self, rng: &mut Rng) -> &GenMolecule {
        match &self.params.molecule_weights {
            None => &self.molecules[rng.below(self.molecules.len() as u64) as usize],
            Some(weights) => {
                let total: f64 = weights.iter().sum();
                let mut draw = rng.f64() * total;
                let mut cumulative = 0.0;
                for (molecule, weight) in self.molecules.iter().zip(weights.iter()) {
                    cumulative += *weight;
                    if draw < cumulative {
                        return molecule;
                    }
                }
                // Guard against zero total weight.
                if total <= 0.0 {
                    draw = rng.f64() * self.molecules.len() as f64;
                    return &self.molecules[draw.floor() as usize % self.molecules.len()];
                }
                self.molecules.last().unwrap()
            }
        }
    }

    pub fn set_molecule_weights(&mut self, weights: Vec<f64>) {
        self.params.molecule_weights = Some(weights);
    }

    // ------------------------------------------------------------ coordinates

    #[inline]
    pub fn distance(source: Position, target: Position) -> i64 {
        let dx = target.0 - source.0;
        let dy = target.1 - source.1;
        dx.abs().max(dy.abs())
    }

    #[inline]
    pub fn chunk_of(&self, position: Position) -> (i64, i64) {
        let size = self.params.chunk_size as i64;
        (position.0.div_euclid(size), position.1.div_euclid(size))
    }

    #[inline]
    fn local_index(&self, position: Position) -> usize {
        let size = self.params.chunk_size as i64;
        let lx = position.0.rem_euclid(size);
        let ly = position.1.rem_euclid(size);
        (ly * size + lx) as usize
    }

    pub fn ensure_positions(&mut self, positions: &[Position]) {
        for &(x, y) in positions {
            let key = self.chunk_of((x, y));
            self.ensure_chunk(key.0, key.1);
        }
    }

    // -------------------------------------------------------------- occupancy

    pub fn add_to_occupancy(&mut self, organism_id: u32, positions: &[Position]) {
        self.ensure_positions(positions);
        for &position in positions {
            let key = self.chunk_of(position);
            let index = self.local_index(position);
            let occupants = &mut self.chunks.get_mut(&key).unwrap().occupancy[index];
            if !occupants.contains(&organism_id) {
                if occupants.is_empty() {
                    self.occupied_cells += 1;
                }
                occupants.push(organism_id);
            }
        }
    }

    pub fn remove_id_from_occupancy(&mut self, organism_id: u32, positions: &[Position]) {
        for &position in positions {
            let key = self.chunk_of(position);
            let index = self.local_index(position);
            if let Some(chunk) = self.chunks.get_mut(&key) {
                let occupants = &mut chunk.occupancy[index];
                let was_occupied = !occupants.is_empty();
                occupants.retain(|&id| id != organism_id);
                if was_occupied && occupants.is_empty() {
                    self.occupied_cells -= 1;
                }
            }
        }
    }

    pub fn occupants_at(&self, position: Position) -> Option<&[u32]> {
        let key = self.chunk_of(position);
        let chunk = self.chunks.get(&key)?;
        let occupants = &chunk.occupancy[self.local_index(position)];
        if occupants.is_empty() {
            None
        } else {
            Some(occupants)
        }
    }

    /// True if no organism other than `ignore` occupies any of `positions`.
    /// (Mirrors World.can_place; footprint positions are precomputed.)
    pub fn area_free(&mut self, positions: &[Position], ignore: u32) -> bool {
        self.ensure_positions(positions);
        for &position in positions {
            if self
                .occupants_at(position)
                .is_some_and(|occupants| occupants.iter().any(|&id| id != ignore))
            {
                return false;
            }
        }
        true
    }

    // --------------------------------------------------------------- deposits

    pub fn deposit_batch_raw(&mut self, position: Position, batch: Batch) {
        if batch.count <= 0 {
            return;
        }
        let key = self.chunk_of(position);
        self.ensure_chunk(key.0, key.1);
        let inventory = self.deposits.entry(position).or_default();
        add_batch(inventory, batch);
    }

    pub fn remove_deposit(&mut self, position: Position) {
        self.deposits.remove(&position);
    }

    #[inline]
    pub fn biodeposit_density_at(&self, position: Position) -> f64 {
        self.biodeposits.get(&position).copied().unwrap_or(0.0) * self.biodeposit_scale
    }

    pub fn add_biodeposit(&mut self, position: Position, structural_mass: f64) {
        if structural_mass > 0.0 {
            *self.biodeposits.entry(position).or_default() +=
                structural_mass / self.biodeposit_scale;
        }
    }

    pub fn erode_biodeposit(&mut self, position: Position, structural_mass: f64) {
        let Some(density) = self.biodeposits.get_mut(&position) else {
            return;
        };
        *density = (*density - structural_mass.max(0.0) / self.biodeposit_scale).max(0.0);
        if *density * self.biodeposit_scale <= 1.0e-9 {
            self.biodeposits.remove(&position);
        }
    }

    pub fn decay_biodeposits(&mut self, rate: f64) {
        if rate <= 0.0 {
            return;
        }
        self.biodeposit_scale *= (1.0 - rate).clamp(0.0, 1.0);
        if self.biodeposit_scale < 1.0e-100 {
            let scale = self.biodeposit_scale;
            self.biodeposits.retain(|_, density| {
                *density *= scale;
                *density > 1.0e-9
            });
            self.biodeposit_scale = 1.0;
        }
    }

    pub fn total_biodeposit_density(&self) -> f64 {
        self.biodeposits.values().sum::<f64>() * self.biodeposit_scale
    }

    // ------------------------------------------------------------------- heat

    pub fn add_heat(&mut self, position: Position, amount: f64) {
        if amount <= 0.0 {
            return;
        }
        let key = self.chunk_of(position);
        self.ensure_chunk(key.0, key.1);
        let idx = self.local_index(position);
        let chunk = self.chunks.get_mut(&key).unwrap();
        chunk.heat[idx] += amount;
        chunk.has_heat = true;
    }

    pub fn heat_at_peek(&self, position: Position) -> f64 {
        let key = self.chunk_of(position);
        match self.chunks.get(&key) {
            Some(chunk) => chunk.heat[self.local_index(position)],
            None => 0.0,
        }
    }

    pub fn remove_heat_at(&mut self, position: Position, amount: f64) -> f64 {
        let key = self.chunk_of(position);
        self.ensure_chunk(key.0, key.1);
        let index = self.local_index(position);
        let available = self.chunks[&key].heat[index];
        let removed = amount.max(0.0).min(available);
        if removed <= 0.0 {
            return 0.0;
        }
        // Preserve the single-cell arithmetic of remove_heat.
        let share = removed * available / available;
        let debit = available.min(share).min(removed);
        self.chunks.get_mut(&key).unwrap().heat[index] -= debit;
        debit
    }

    pub fn remove_heat(&mut self, positions: &[Position], amount: f64) -> f64 {
        self.ensure_positions(positions);
        let mut cells: Vec<((i64, i64), usize, f64)> = Vec::with_capacity(positions.len());
        let mut available = 0.0f64;
        for &position in positions {
            let key = self.chunk_of(position);
            let idx = self.local_index(position);
            let cell_heat = self.chunks.get(&key).unwrap().heat[idx];
            available += cell_heat;
            cells.push((key, idx, cell_heat));
        }
        let removed = amount.max(0.0).min(available);
        if removed <= 0.0 {
            return 0.0;
        }
        let mut remaining = removed;
        for (key, idx, cell_heat) in &cells {
            let share = removed * *cell_heat / available;
            let debit = cell_heat.min(share).min(remaining);
            let chunk = self.chunks.get_mut(key).unwrap();
            chunk.heat[*idx] -= debit;
            remaining -= debit;
        }
        if remaining > 1e-12 {
            let (key, idx, _) = cells[0];
            let chunk = self.chunks.get_mut(&key).unwrap();
            let debit = chunk.heat[idx].min(remaining);
            chunk.heat[idx] -= debit;
            remaining -= debit;
        }
        removed - remaining.max(0.0)
    }

    /// Chunk-by-chunk heat diffusion with no-flux edges toward ungenerated
    /// space. Exactly mirrors World.diffuse_heat.
    pub fn diffuse_heat(
        &mut self,
        rate: f64,
        sources: &mut Vec<((i64, i64), Vec<f64>)>,
        source_index: &mut FxHashMap<(i64, i64), usize>,
        scratch: &mut Vec<f64>,
    ) {
        if rate <= 0.0 {
            return;
        }
        // Active set: chunks with heat plus their existing 4-neighbours.
        let mut active: rustc_hash::FxHashSet<(i64, i64)> = rustc_hash::FxHashSet::default();
        let keys: Vec<(i64, i64)> = self
            .chunks
            .iter()
            .filter(|(_, c)| c.has_heat)
            .map(|(k, _)| *k)
            .collect();
        for &(cx, cy) in &keys {
            active.insert((cx, cy));
            for nk in [(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)] {
                if self.chunks.contains_key(&nk) {
                    active.insert(nk);
                }
            }
        }
        if active.is_empty() {
            return;
        }
        sources.clear();
        source_index.clear();
        let size = self.params.chunk_size;
        for &key in &active {
            source_index.insert(key, sources.len());
            let heat = self.chunks[&key].heat.clone();
            sources.push((key, heat));
        }
        scratch.clear();
        scratch.resize(size * size, 0.0);
        for source_position in 0..sources.len() {
            let (key, src) = &sources[source_position];
            let (cx, cy) = *key;
            let up = source_index
                .get(&(cx, cy - 1))
                .map(|&index| &sources[index].1);
            let down = source_index
                .get(&(cx, cy + 1))
                .map(|&index| &sources[index].1);
            let left = source_index
                .get(&(cx - 1, cy))
                .map(|&index| &sources[index].1);
            let right = source_index
                .get(&(cx + 1, cy))
                .map(|&index| &sources[index].1);
            for ly in 0..size {
                for lx in 0..size {
                    let s = src[ly * size + lx];
                    let mut value = (1.0 - 4.0 * rate) * s;
                    // in-chunk neighbours with no-flux fallback at map edge
                    let up_v = if ly > 0 {
                        src[(ly - 1) * size + lx]
                    } else {
                        up.map(|u| u[(size - 1) * size + lx]).unwrap_or(s)
                    };
                    let down_v = if ly + 1 < size {
                        src[(ly + 1) * size + lx]
                    } else {
                        down.map(|d| d[lx]).unwrap_or(s)
                    };
                    let left_v = if lx > 0 {
                        src[ly * size + lx - 1]
                    } else {
                        left.map(|l| l[ly * size + size - 1]).unwrap_or(s)
                    };
                    let right_v = if lx + 1 < size {
                        src[ly * size + lx + 1]
                    } else {
                        right.map(|r| r[ly * size]).unwrap_or(s)
                    };
                    value += rate * (up_v + down_v + left_v + right_v);
                    scratch[ly * size + lx] = value.max(0.0);
                }
            }
            let chunk = self.chunks.get_mut(key).unwrap();
            chunk.heat.copy_from_slice(scratch);
            chunk.has_heat = chunk.heat.iter().any(|&v| v != 0.0);
        }
    }

    pub fn total_heat(&self) -> f64 {
        let mut total = 0.0f64;
        for chunk in self.chunks.values() {
            if chunk.has_heat {
                total += chunk.heat.iter().sum::<f64>();
            }
        }
        total
    }

    pub fn deposit_energy(&self) -> f64 {
        let mut total = 0.0;
        for inventory in self.deposits.values() {
            for batch in inventory {
                total += batch.energy;
            }
        }
        total
    }
}
