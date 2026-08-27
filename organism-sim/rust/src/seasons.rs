//! Deterministic exogenous seasons for the native kernel.
//!
//! Seasons only alter environmental energy cycling. They never inspect species,
//! genomes, phenotypes, actions, or fitness.

use crate::config::SimConfig;
use crate::rng::{Fnv, Rng};

#[derive(Clone, Debug)]
pub struct SeasonProfile {
    pub resource_charge_multiplier: f64,
    pub decomposition_multiplier: f64,
    pub molecule_charge_affinities: Vec<f64>,
}

impl SeasonProfile {
    fn neutral(molecule_count: usize) -> Self {
        Self {
            resource_charge_multiplier: 1.0,
            decomposition_multiplier: 1.0,
            molecule_charge_affinities: vec![1.0; molecule_count],
        }
    }

    fn random(molecule_count: usize, strength: f64, rng: &mut Rng) -> Self {
        let climate = rng.uniform(-1.0, 1.0);
        let resource_charge_multiplier = 1.0 + 0.6 * strength * climate;
        let decomposition_multiplier = 1.0 - 0.4 * strength * climate;
        let affinity_floor = 1.0 - 0.9 * strength;
        let affinity_ceiling = 1.0 + 0.9 * strength;
        let mut molecule_charge_affinities: Vec<f64> = (0..molecule_count)
            .map(|_| rng.uniform(affinity_floor, affinity_ceiling))
            .collect();
        let affinity_mean =
            molecule_charge_affinities.iter().sum::<f64>() / molecule_count.max(1) as f64;
        for affinity in &mut molecule_charge_affinities {
            *affinity /= affinity_mean;
        }
        Self {
            resource_charge_multiplier,
            decomposition_multiplier,
            molecule_charge_affinities,
        }
    }
}

#[derive(Clone, Debug)]
pub struct SeasonEvent {
    pub index: u32,
    pub started_tick: u32,
    pub transition_end_tick: u32,
    pub next_season_tick: u32,
    pub from: SeasonProfile,
    pub target: SeasonProfile,
}

#[derive(Debug)]
pub struct SeasonState {
    pub enabled: bool,
    pub index: u32,
    pub started_tick: u32,
    pub transition_end_tick: u32,
    pub next_season_tick: u32,
    pub current: SeasonProfile,
    pub from: SeasonProfile,
    pub target: SeasonProfile,
    pub events: Vec<SeasonEvent>,
    rng: Rng,
}

impl SeasonState {
    pub fn new(config: &SimConfig, mut rng: Rng) -> Self {
        let neutral = SeasonProfile::neutral(config.molecule_count);
        if !config.seasons_enabled {
            return Self {
                enabled: false,
                index: 0,
                started_tick: 0,
                transition_end_tick: 0,
                next_season_tick: u32::MAX,
                current: neutral.clone(),
                from: neutral.clone(),
                target: neutral.clone(),
                events: vec![SeasonEvent {
                    index: 0,
                    started_tick: 0,
                    transition_end_tick: 0,
                    next_season_tick: u32::MAX,
                    from: neutral.clone(),
                    target: neutral,
                }],
                rng,
            };
        }

        let target = SeasonProfile::random(config.molecule_count, config.season_strength, &mut rng);
        let duration = Self::sample_duration(config, &mut rng);
        Self {
            enabled: true,
            index: 0,
            started_tick: 0,
            transition_end_tick: 0,
            next_season_tick: duration,
            current: target.clone(),
            from: target.clone(),
            target: target.clone(),
            events: vec![SeasonEvent {
                index: 0,
                started_tick: 0,
                transition_end_tick: 0,
                next_season_tick: duration,
                from: target.clone(),
                target,
            }],
            rng,
        }
    }

    fn sample_duration(config: &SimConfig, rng: &mut Rng) -> u32 {
        rng.randint(
            config.season_duration_min as i64,
            config.season_duration_max as i64,
        ) as u32
    }

    /// Advance an O(molecule_count) interpolation once per tick.
    pub fn advance(&mut self, tick: u32, config: &SimConfig) -> bool {
        if !self.enabled {
            return false;
        }
        let mut changed = false;
        if tick >= self.next_season_tick {
            self.index = self.index.saturating_add(1);
            self.started_tick = tick;
            self.from = self.current.clone();
            self.target =
                SeasonProfile::random(config.molecule_count, config.season_strength, &mut self.rng);
            self.transition_end_tick = tick.saturating_add(config.season_transition_ticks);
            self.next_season_tick =
                tick.saturating_add(Self::sample_duration(config, &mut self.rng));
            self.events.push(SeasonEvent {
                index: self.index,
                started_tick: self.started_tick,
                transition_end_tick: self.transition_end_tick,
                next_season_tick: self.next_season_tick,
                from: self.from.clone(),
                target: self.target.clone(),
            });
            changed = true;
        }

        let blend = self.transition_progress(tick);
        self.current.resource_charge_multiplier = lerp(
            self.from.resource_charge_multiplier,
            self.target.resource_charge_multiplier,
            blend,
        );
        self.current.decomposition_multiplier = lerp(
            self.from.decomposition_multiplier,
            self.target.decomposition_multiplier,
            blend,
        );
        for ((current, from), target) in self
            .current
            .molecule_charge_affinities
            .iter_mut()
            .zip(&self.from.molecule_charge_affinities)
            .zip(&self.target.molecule_charge_affinities)
        {
            *current = lerp(*from, *target, blend);
        }
        changed
    }

    pub fn transition_progress(&self, tick: u32) -> f64 {
        if self.transition_end_tick <= self.started_tick || tick >= self.transition_end_tick {
            1.0
        } else {
            (tick.saturating_sub(self.started_tick) as f64
                / (self.transition_end_tick - self.started_tick) as f64)
                .clamp(0.0, 1.0)
        }
    }

    pub fn hash_into(&self, hash: &mut Fnv) {
        hash.u64(self.index as u64);
        hash.u64(self.started_tick as u64);
        hash.u64(self.transition_end_tick as u64);
        hash.u64(self.next_season_tick as u64);
        for profile in [&self.current, &self.from, &self.target] {
            hash.f64(profile.resource_charge_multiplier);
            hash.f64(profile.decomposition_multiplier);
            hash.u64(profile.molecule_charge_affinities.len() as u64);
            for &affinity in &profile.molecule_charge_affinities {
                hash.f64(affinity);
            }
        }
        hash.u64(self.events.len() as u64);
        self.rng.hash_into(hash);
    }
}

#[inline]
fn lerp(from: f64, target: f64, amount: f64) -> f64 {
    from + (target - from) * amount
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn disabled_seasons_are_neutral() {
        let config = SimConfig::default();
        let mut seasons = SeasonState::new(&config, Rng::new(5));
        assert!(!seasons.advance(10_000, &config));
        assert_eq!(seasons.current.resource_charge_multiplier, 1.0);
        assert!(seasons
            .current
            .molecule_charge_affinities
            .iter()
            .all(|&value| value == 1.0));
    }

    #[test]
    fn transitions_are_deterministic_and_bounded() {
        let config = SimConfig {
            seasons_enabled: true,
            season_duration_min: 10,
            season_duration_max: 10,
            season_transition_ticks: 4,
            season_strength: 1.0,
            ..SimConfig::default()
        };
        let mut left = SeasonState::new(&config, Rng::new(9));
        let mut right = SeasonState::new(&config, Rng::new(9));
        for tick in 1..=25 {
            assert_eq!(left.advance(tick, &config), right.advance(tick, &config));
            assert_eq!(
                left.current.resource_charge_multiplier.to_bits(),
                right.current.resource_charge_multiplier.to_bits()
            );
        }
        assert_eq!(left.index, 2);
        assert!((0.4..=1.6).contains(&left.target.resource_charge_multiplier));
        assert!((0.6..=1.4).contains(&left.target.decomposition_multiplier));
        assert!(left
            .target
            .molecule_charge_affinities
            .iter()
            .all(|&value| value > 0.0));
        let mean = left.target.molecule_charge_affinities.iter().sum::<f64>()
            / left.target.molecule_charge_affinities.len() as f64;
        assert!((mean - 1.0).abs() < 1.0e-12);
    }
}
