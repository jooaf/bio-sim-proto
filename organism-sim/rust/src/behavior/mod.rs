//! Versioned behavior schemas.
//!
//! The legacy macro controller, direct linear V2 intent controller, and fixed
//! recurrent V2 residual are isolated startup-selected treatments.

pub(crate) mod intent;
pub(crate) mod legacy;
pub(crate) mod neural;
pub(crate) mod observation;

use std::fmt;
use std::str::FromStr;

pub const OBSERVATION_SCHEMA_VERSION: u16 = 2;
pub const INTENT_SCHEMA_VERSION: u16 = 2;
pub const BRAIN_SCHEMA_VERSION: u16 = 1;

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum BehaviorModel {
    #[default]
    LegacyLinearMacroV1,
    LinearIntentV2,
    RecurrentIntentV2,
}

impl BehaviorModel {
    pub const ALL: [BehaviorModel; 3] = [
        BehaviorModel::LegacyLinearMacroV1,
        BehaviorModel::LinearIntentV2,
        BehaviorModel::RecurrentIntentV2,
    ];

    pub const fn as_str(self) -> &'static str {
        match self {
            BehaviorModel::LegacyLinearMacroV1 => "legacy_linear_macro_v1",
            BehaviorModel::LinearIntentV2 => "linear_intent_v2",
            BehaviorModel::RecurrentIntentV2 => "recurrent_intent_v2",
        }
    }

    pub const fn is_implemented(self) -> bool {
        matches!(
            self,
            BehaviorModel::LegacyLinearMacroV1
                | BehaviorModel::LinearIntentV2
                | BehaviorModel::RecurrentIntentV2
        )
    }
}

impl fmt::Display for BehaviorModel {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.as_str())
    }
}

impl FromStr for BehaviorModel {
    type Err = String;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        match value {
            "legacy_linear_macro_v1" => Ok(BehaviorModel::LegacyLinearMacroV1),
            "linear_intent_v2" => Ok(BehaviorModel::LinearIntentV2),
            "recurrent_intent_v2" => Ok(BehaviorModel::RecurrentIntentV2),
            _ => Err(format!(
                "unknown behavior_model {value:?}; expected one of: {}",
                BehaviorModel::ALL
                    .iter()
                    .map(|model| model.as_str())
                    .collect::<Vec<_>>()
                    .join(", ")
            )),
        }
    }
}
