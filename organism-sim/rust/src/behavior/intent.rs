//! V2 candidate and action-intent schemas. The kernel generates bounded
//! candidates and remains authoritative for validation and commitment.

#![allow(dead_code)]

use crate::world::Position;

pub const INTENT_TYPE_COUNT: usize = 10;
pub const CANDIDATE_FEATURE_COUNT: usize = 16;
pub const MAX_INTENT_CANDIDATES: usize = 33;

pub const C_CHEMICAL_COST: usize = 0;
pub const C_MANA_COST: usize = 1;
pub const C_DURATION: usize = 2;
pub const C_FOOD: usize = 3;
pub const C_TOXIN: usize = 4;
pub const C_HEAT: usize = 5;
pub const C_PREY: usize = 6;
pub const C_THREAT: usize = 7;
pub const C_MATE: usize = 8;
pub const C_SOCIAL: usize = 9;
pub const C_CROWDING: usize = 10;
pub const C_FORWARD: usize = 11;
pub const C_RIGHT: usize = 12;
pub const C_DISTANCE: usize = 13;
pub const C_TARGET_KNOWN: usize = 14;
pub const C_PERSISTENCE: usize = 15;

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
#[repr(u8)]
pub enum IntentKind {
    Wait = 0,
    Move = 1,
    Ingest = 2,
    Repair = 3,
    AbsorbHeat = 4,
    Detox = 5,
    Attack = 6,
    CastMagic = 7,
    Reproduce = 8,
    ProposeAlliance = 9,
}

impl IntentKind {
    pub const ALL: [IntentKind; INTENT_TYPE_COUNT] = [
        IntentKind::Wait,
        IntentKind::Move,
        IntentKind::Ingest,
        IntentKind::Repair,
        IntentKind::AbsorbHeat,
        IntentKind::Detox,
        IntentKind::Attack,
        IntentKind::CastMagic,
        IntentKind::Reproduce,
        IntentKind::ProposeAlliance,
    ];

    pub const fn as_index(self) -> usize {
        self as usize
    }

    pub const fn as_str(self) -> &'static str {
        match self {
            IntentKind::Wait => "wait",
            IntentKind::Move => "move_one_tile",
            IntentKind::Ingest => "ingest",
            IntentKind::Repair => "repair",
            IntentKind::AbsorbHeat => "absorb_heat",
            IntentKind::Detox => "detox",
            IntentKind::Attack => "physical_attack",
            IntentKind::CastMagic => "cast_magic",
            IntentKind::Reproduce => "reproduce",
            IntentKind::ProposeAlliance => "propose_alliance",
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum IntentTarget {
    None,
    Position(Position),
    Organism(u32),
    Food {
        position: Position,
        molecule_id: u16,
    },
    SelfReproduction,
}

#[derive(Clone, Debug, PartialEq)]
pub struct IntentCandidate {
    pub kind: IntentKind,
    pub target: IntentTarget,
    pub features: [f32; CANDIDATE_FEATURE_COUNT],
    pub predicted_duration_ticks: u32,
    pub predicted_chemical_cost: f64,
    pub predicted_mana_cost: f64,
}

impl IntentCandidate {
    pub fn to_intent(&self, actor_id: u32) -> ActionIntent {
        ActionIntent {
            actor_id,
            kind: self.kind,
            target: self.target,
            predicted_duration_ticks: self.predicted_duration_ticks,
            predicted_chemical_cost: self.predicted_chemical_cost,
            predicted_mana_cost: self.predicted_mana_cost,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ActionIntent {
    pub actor_id: u32,
    pub kind: IntentKind,
    pub target: IntentTarget,
    pub predicted_duration_ticks: u32,
    pub predicted_chemical_cost: f64,
    pub predicted_mana_cost: f64,
}
