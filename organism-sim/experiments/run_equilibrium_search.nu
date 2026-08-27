# Run staged searches for a persistent, approximately stationary population.
#
# Examples:
#   nu experiments/run_equilibrium_search.nu --stage screen
#   nu experiments/run_equilibrium_search.nu --stage reproduction
#   nu experiments/run_equilibrium_search.nu --stage fertility
#   nu experiments/run_equilibrium_search.nu --stage production2
#   nu experiments/run_equilibrium_search.nu --stage refine --conditions cost-0p1_floor-0p2
#   nu experiments/run_equilibrium_search.nu --stage confirm --conditions cost-0p1_floor-0p2

def profiles [] {
    [
        {name: standard, deposits: 2600, batch_min: 4, batch_max: 20},
        {name: distributed, deposits: 4900, batch_min: 4, batch_max: 20},
        {name: rich, deposits: 2600, batch_min: 8, batch_max: 40},
    ]
}

def screen-cases [] {
    [0.25 0.40 0.55 0.70] | each {|maintenance|
        profiles | each {|profile|
            70..72 | each {|seed|
                {
                    condition: $"maint-($maintenance | into string | str replace '.' 'p')_($profile.name)",
                    ticks: 3000,
                    seed: $seed,
                    maintenance: $maintenance,
                    deposits: $profile.deposits,
                    batch_min: $profile.batch_min,
                    batch_max: $profile.batch_max,
                }
            }
        } | flatten
    } | flatten
}

def reproduction-cases [] {
    [0.00 0.10 0.20 0.30] | each {|cost|
        [0.20 0.35] | each {|floor|
            70..72 | each {|seed|
                {
                    condition: $"cost-($cost | into string | str replace '.' 'p')_floor-($floor | into string | str replace '.' 'p')",
                    ticks: 3000,
                    seed: $seed,
                    maintenance: 0.55,
                    deposits: 4900,
                    batch_min: 4,
                    batch_max: 20,
                    reproduction_cost: $cost,
                    asexual_floor: $floor,
                }
            }
        } | flatten
    } | flatten
}

def fertility-cases [] {
    [0.00 0.10 0.20] | each {|cost|
        [0.50 0.70 0.90] | each {|floor|
            70..72 | each {|seed|
                {
                    condition: $"cost-($cost | into string | str replace '.' 'p')_floor-($floor | into string | str replace '.' 'p')",
                    ticks: 3000,
                    seed: $seed,
                    maintenance: 0.55,
                    deposits: 4900,
                    batch_min: 4,
                    batch_max: 20,
                    reproduction_cost: $cost,
                    asexual_floor: $floor,
                }
            }
        } | flatten
    } | flatten
}

def production-cases [] {
    [0.005 0.01 0.025 0.05] | each {|production|
        [0.40 0.55 0.70] | each {|maintenance|
            70..72 | each {|seed|
                {
                    condition: $"production-($production | into string | str replace '.' 'p')_maint-($maintenance | into string | str replace '.' 'p')",
                    ticks: 3000,
                    seed: $seed,
                    maintenance: $maintenance,
                    deposits: 4900,
                    batch_min: 4,
                    batch_max: 20,
                    reproduction_cost: 0.20,
                    asexual_floor: 0.50,
                    primary_production: $production,
                }
            }
        } | flatten
    } | flatten
}

def condition-settings [name: string] {
    let maintenance_condition = $name | parse --regex '^maint-(?<maintenance>[0-9]+p[0-9]+)_(?<profile>standard|distributed|rich)$'
    if not ($maintenance_condition | is-empty) {
        let profile = profiles | where name == $maintenance_condition.profile.0 | first
        return {
            maintenance: ($maintenance_condition.maintenance.0 | str replace 'p' '.' | into float),
            deposits: $profile.deposits,
            batch_min: $profile.batch_min,
            batch_max: $profile.batch_max,
            reproduction_cost: 0.50,
            asexual_floor: 0.20,
        }
    }
    let production_condition = $name | parse --regex '^production-(?<production>[0-9]+p[0-9]+)_maint-(?<maintenance>[0-9]+p[0-9]+)$'
    if not ($production_condition | is-empty) {
        return {
            maintenance: ($production_condition.maintenance.0 | str replace 'p' '.' | into float),
            deposits: 4900,
            batch_min: 4,
            batch_max: 20,
            reproduction_cost: 0.20,
            asexual_floor: 0.50,
            primary_production: ($production_condition.production.0 | str replace 'p' '.' | into float),
        }
    }
    let reproduction_condition = $name | parse --regex '^cost-(?<cost>[0-9]+p[0-9]+)_floor-(?<floor>[0-9]+p[0-9]+)$'
    if not ($reproduction_condition | is-empty) {
        return {
            maintenance: 0.55,
            deposits: 4900,
            batch_min: 4,
            batch_max: 20,
            reproduction_cost: ($reproduction_condition.cost.0 | str replace 'p' '.' | into float),
            asexual_floor: ($reproduction_condition.floor.0 | str replace 'p' '.' | into float),
        }
    }
    error make {msg: $"invalid condition name: ($name)"}
}

def selected-cases [stage: string, names: list<string>] {
    let seeds = if $stage == "refine" { 73..77 } else { 78..87 }
    let ticks = if $stage == "refine" { 6000 } else { 10000 }
    $names | each {|name|
        let settings = condition-settings $name
        $seeds | each {|seed|
            $settings | merge {condition: $name, ticks: $ticks, seed: $seed}
        }
    } | flatten
}

def run-case [root: path, stage: string, case: record] {
    let reproduction_cost = $case.reproduction_cost? | default 0.50
    let asexual_floor = $case.asexual_floor? | default 0.20
    let primary_production = $case.primary_production? | default 0.0
    let output_dir = $root | path join $stage $case.condition
    mkdir $output_dir
    print $"START stage=($stage) condition=($case.condition) seed=($case.seed) ticks=($case.ticks)"
    let result = (^uv run organism-sim-headless
        --ticks $case.ticks
        --runs-dir $output_dir
        --founders 300
        --genome-seeds 8
        --elements 8
        --molecules 48
        --deposits $case.deposits
        --seed $case.seed
        --maintenance-multiplier $case.maintenance
        --reproduction-cost $reproduction_cost
        --reproduction-cooldown 0.75
        --maturity-multiplier 0.65
        --reproduction-drive 1.25
        --asexual-floor $asexual_floor
        --sexual-floor-enabled
        --sexual-floor 0.12
        --decomposition-rate 0.0008
        --heat-diffusion 0.08
        --detail-every 50
        --snapshot-every 250
        --commit-every 100
        --set $"initial_batch_min=($case.batch_min)"
        --set $"initial_batch_max=($case.batch_max)"
        --set $"primary_production_rate=($primary_production)"
        | complete)
    $result.stdout | save --force ($output_dir | path join $"seed-($case.seed).stdout.log")
    $result.stderr | save --force ($output_dir | path join $"seed-($case.seed).stderr.log")
    if $result.exit_code != 0 {
        error make {msg: $"stage=($stage) condition=($case.condition) seed=($case.seed) failed"}
    }
    print $"DONE stage=($stage) condition=($case.condition) seed=($case.seed)"
}

def main [
    --stage: string = "screen",
    --conditions: string = "",
    --root: path = "experiment_results/equilibrium_search/runs",
    --threads: int = 8,
] {
    let selected = $conditions | split row ',' | where {|name| not ($name | is-empty) }
    let cases = match $stage {
        "screen" => { screen-cases },
        "reproduction" => { reproduction-cases },
        "fertility" => { fertility-cases },
        "production2" => { production-cases },
        "refine" | "confirm" => {
            if ($selected | is-empty) {
                error make {msg: $"--conditions is required for stage ($stage)"}
            }
            selected-cases $stage $selected
        },
        _ => { error make {msg: $"unknown stage: ($stage)"} },
    }
    print $"Running ($cases | length) ($stage) cases with ($threads) workers"
    $cases | par-each --threads $threads {|case| run-case $root $stage $case } | ignore
    print $"Completed equilibrium-search stage: ($stage)"
}
