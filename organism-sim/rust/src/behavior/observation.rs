//! Fixed V2 observation schema. The kernel owns allocation-conscious
//! construction because it has authoritative access to world and organism state.

#![allow(dead_code)]

pub const OBSERVATION_COUNT: usize = 28;

pub const O_RESERVE: usize = 0;
pub const O_HUNGER: usize = 1;
pub const O_MANA: usize = 2;
pub const O_MAINTENANCE_DEBT: usize = 3;
pub const O_INTEGRITY: usize = 4;
pub const O_TOXIN: usize = 5;
pub const O_AGE: usize = 6;
pub const O_SENESCENCE: usize = 7;
pub const O_GROWTH_DEFICIT: usize = 8;
pub const O_REPRODUCTIVE_RESERVE: usize = 9;
pub const O_REPRODUCTIVE_COOLDOWN: usize = 10;
pub const O_REPRODUCTIVE_READY: usize = 11;
pub const O_BODY_MASS: usize = 12;
pub const O_SPEED: usize = 13;
pub const O_SIGHT: usize = 14;
pub const O_COLONY: usize = 15;
pub const O_LOCAL_FOOD: usize = 16;
pub const O_VISIBLE_FOOD: usize = 17;
pub const O_LOCAL_HEAT: usize = 18;
pub const O_VISIBLE_HEAT: usize = 19;
pub const O_THREAT: usize = 20;
pub const O_PREY: usize = 21;
pub const O_MATE: usize = 22;
pub const O_CONTACT_CROWDING: usize = 23;
pub const O_VISIBLE_CROWDING: usize = 24;
pub const O_FOOD_KNOWN: usize = 25;
pub const O_ORGANISM_KNOWN: usize = 26;
pub const O_HEAT_KNOWN: usize = 27;

#[derive(Clone, Debug, PartialEq)]
pub struct ObservationV2 {
    pub values: [f32; OBSERVATION_COUNT],
}

impl Default for ObservationV2 {
    fn default() -> Self {
        ObservationV2 {
            values: [0.0; OBSERVATION_COUNT],
        }
    }
}
