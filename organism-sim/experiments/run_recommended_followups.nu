# Run the preregistered organism-sim follow-up experiments.
#
# Examples:
#   nu experiments/run_recommended_followups.nu --batch persistence
#   nu experiments/run_recommended_followups.nu --batch resource
#   nu experiments/run_recommended_followups.nu --batch founders
#   nu experiments/run_recommended_followups.nu --batch all

def run-case [
    root: path,
    study: string,
    condition: string,
    ticks: int,
    seed: int,
    reproduction_cost: float,
    deposits: int,
    archetypes: int,
] {
    let output_dir = ($root | path join $study $condition)
    mkdir $output_dir
    print $"START study=($study) condition=($condition) seed=($seed) ticks=($ticks)"
    let result = (^uv run organism-sim-headless
        --ticks $ticks
        --runs-dir $output_dir
        --founders 300
        --genome-seeds $archetypes
        --elements 8
        --molecules 48
        --deposits $deposits
        --seed $seed
        --mutation-multiplier 1.0
        --maintenance-multiplier 0.75
        --maturity-multiplier 0.65
        --reproduction-drive 1.25
        --reproduction-cost $reproduction_cost
        --reproduction-cooldown 0.75
        --asexual-floor 0.20
        --sexual-floor 0.12
        --sexual-floor-enabled
        --decomposition-rate 0.0008
        --heat-diffusion 0.08
        --detail-every 20
        --snapshot-every 100
        --commit-every 50
        | complete)
    $result.stdout | save --force ($output_dir | path join $"seed-($seed).stdout.log")
    $result.stderr | save --force ($output_dir | path join $"seed-($seed).stderr.log")
    if $result.exit_code != 0 {
        error make {msg: $"study=($study) condition=($condition) seed=($seed) failed with exit code ($result.exit_code)"}
    }
    print $"DONE study=($study) condition=($condition) seed=($seed)"
}

def persistence-cases [] {
    50..59 | each {|seed|
        {
            study: "persistence",
            condition: "maint-0p75_floor-0p12",
            ticks: 10000,
            seed: $seed,
            reproduction_cost: 0.75,
            deposits: 2600,
            archetypes: 8,
        }
    }
}

def resource-cases [] {
    [0.50 0.75] | each {|cost|
        [2600 4900] | each {|deposits|
            60..64 | each {|seed|
                {
                    study: "resource_factorial",
                    condition: $"cost-($cost | into string | str replace '.' 'p')_deposits-($deposits)",
                    ticks: 2500,
                    seed: $seed,
                    reproduction_cost: $cost,
                    deposits: $deposits,
                    archetypes: 8,
                }
            }
        }
    } | flatten | flatten
}

def founder-cases [] {
    [8 21] | each {|archetypes|
        65..69 | each {|seed|
            {
                study: "founder_archetypes",
                condition: $"archetypes-($archetypes)",
                ticks: 2500,
                seed: $seed,
                reproduction_cost: 0.75,
                deposits: 2600,
                archetypes: $archetypes,
            }
        }
    } | flatten
}

def main [
    --batch: string = "all",
    --root: path = "experiment_results/recommended_followups/runs",
    --threads: int = 8,
] {
    let cases = match $batch {
        "persistence" => { persistence-cases },
        "resource" => { resource-cases },
        "founders" => { founder-cases },
        "all" => { persistence-cases | append (resource-cases) | append (founder-cases) },
        _ => { error make {msg: $"unknown batch: ($batch)"} },
    }
    print $"Running ($cases | length) ($batch) follow-up experiments with ($threads) workers"
    $cases | par-each --threads $threads {|case|
        run-case $root $case.study $case.condition $case.ticks $case.seed $case.reproduction_cost $case.deposits $case.archetypes
    } | ignore
    print $"Follow-up batch complete: ($batch)"
}
