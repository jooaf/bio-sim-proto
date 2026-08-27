//! Versioned tick schedulers and deterministic decision-stream derivation.

use crate::rng::{mix64, Rng};
use std::fmt;
use std::str::FromStr;

pub const PARALLEL_RNG_VERSION: u16 = 2;
pub const PARALLEL_RESOLVER_VERSION: u16 = 2;
pub const DECISION_SUBSYSTEM: u64 = 1;
pub const MAINTENANCE_SUBSYSTEM: u64 = 2;
pub const PARALLEL_PARTITION_STRATEGY: &str = "rayon-maintenance-intents-components-v2";

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum Scheduler {
    #[default]
    SerialV2,
    ParallelV3,
}

impl Scheduler {
    pub const ALL: [Scheduler; 2] = [Scheduler::SerialV2, Scheduler::ParallelV3];

    pub const fn as_str(self) -> &'static str {
        match self {
            Scheduler::SerialV2 => "serial-v2",
            Scheduler::ParallelV3 => "parallel-v3",
        }
    }
}

impl fmt::Display for Scheduler {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.as_str())
    }
}

impl FromStr for Scheduler {
    type Err = String;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        match value {
            "serial-v2" => Ok(Scheduler::SerialV2),
            "parallel-v3" => Ok(Scheduler::ParallelV3),
            _ => Err(format!(
                "unknown scheduler {value:?}; expected one of: {}",
                Scheduler::ALL
                    .iter()
                    .map(|scheduler| scheduler.as_str())
                    .collect::<Vec<_>>()
                    .join(", ")
            )),
        }
    }
}

/// A phase-local stream. It is independent of Rayon worker count, work
/// stealing, and the order in which other organisms are evaluated.
pub fn phase_rng(run_seed: i64, tick: u32, organism_id: u32, ordinal: u32, subsystem: u64) -> Rng {
    let mut seed = mix64(run_seed as u64 ^ 0xD3C1_5100_0000_0003);
    for value in [
        PARALLEL_RNG_VERSION as u64,
        tick as u64,
        organism_id as u64,
        ordinal as u64,
        subsystem,
    ] {
        seed = mix64(seed ^ mix64(value));
    }
    Rng::new(seed)
}

pub fn decision_rng(run_seed: i64, tick: u32, organism_id: u32, decision_ordinal: u32) -> Rng {
    phase_rng(
        run_seed,
        tick,
        organism_id,
        decision_ordinal,
        DECISION_SUBSYSTEM,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn decision_streams_are_stable_and_partitioned() {
        let mut left = decision_rng(7, 11, 13, 2);
        let mut same = decision_rng(7, 11, 13, 2);
        let mut other_actor = decision_rng(7, 11, 14, 2);
        for _ in 0..16 {
            assert_eq!(left.next_u64(), same.next_u64());
        }
        assert_ne!(
            decision_rng(7, 11, 13, 2).next_u64(),
            other_actor.next_u64()
        );
        assert_ne!(
            phase_rng(7, 11, 13, 2, DECISION_SUBSYSTEM).next_u64(),
            phase_rng(7, 11, 13, 2, MAINTENANCE_SUBSYSTEM).next_u64(),
        );
    }
}
