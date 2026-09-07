# Run paired dynamic-environment chemistry experiments.
#
# Conditions are crossed over the same seeds:
#   baseline  - cellular affordances, no seasons, no dynamic chemistry
#   seasons   - cellular affordances + exogenous seasons
#   dynamic   - cellular affordances + organism/environment chemistry
#   both      - seasons + organism/environment chemistry
#
# Examples:
#   nu experiments/run_dynamic_chemistry.nu
#   nu experiments/run_dynamic_chemistry.nu --ticks 100 --seeds 7,8
#   nu experiments/run_dynamic_chemistry.nu --analyze-only

const CONDITIONS = [baseline seasons dynamic both]


def condition-cases [seeds: list<int>] {
    $CONDITIONS | each {|condition|
        $seeds | each {|seed|
            {
                condition: $condition,
                seed: $seed,
                seasons: ($condition == "seasons" or $condition == "both"),
                dynamic: ($condition == "dynamic" or $condition == "both"),
            }
        }
    } | flatten
}


def run-case [root: path, ticks: int, case: record] {
    let output_dir = ($root | path join $case.condition $"seed-($case.seed)")
    mkdir $output_dir
    let common = [
        run organism-sim-headless
        --engine rust
        --ticks $ticks
        --runs-dir $output_dir
        --founders 300
        --genome-seeds 8
        --elements 8
        --molecules 48
        --deposits 2600
        --seed $case.seed
        --mutation-multiplier 1.0
        --maintenance-multiplier 0.75
        --maturity-multiplier 0.65
        --reproduction-drive 1.25
        --reproduction-cost 0.75
        --reproduction-cooldown 0.75
        --asexual-floor 0.20
        --sexual-floor 0.12
        --sexual-floor-enabled
        --decomposition-rate 0.0008
        --heat-diffusion 0.08
        --cellular-emergence
        --set emergence_engulfment_rate=1.0
        --set emergence_exchange_rate=0.10
        --set emergence_module_cost=0.001
        --reaction-rule-count 6
        --environment-reaction-rate 0.04
        --reaction-thermodynamics 0.10
        --byproduct-strength 0.05
        --byproduct-decay 0.02
        --chemistry-coupling 0.75
        --guest-niche-coupling 0.75
        --metrics-every 20
        --detail-every 100
        --snapshot-every 400
        --commit-every 100
        --audit-every 20
        --progress-every 0
    ]
    let with_seasons = if $case.seasons {
        $common | append "--seasons"
    } else {
        $common
    }
    let command = if $case.dynamic {
        $with_seasons | append "--dynamic-chemistry"
    } else {
        $with_seasons
    }
    print $"START condition=($case.condition) seed=($case.seed) ticks=($ticks)"
    let result = (^uv ...$command | complete)
    $result.stdout | save --force ($output_dir | path join "stdout.log")
    $result.stderr | save --force ($output_dir | path join "stderr.log")
    if $result.exit_code != 0 {
        error make {msg: $"condition=($case.condition) seed=($case.seed) failed with exit code ($result.exit_code)"}
    }
    print $"DONE condition=($case.condition) seed=($case.seed)"
}


def absolute [value] {
    if $value < 0 { 0 - $value } else { $value }
}


def read-last-metric [path: path] {
    open $path | lines | last | from json
}


def read-run [manifest_path: path] {
    let manifest = open $manifest_path
    let run_dir = ($manifest_path | path dirname)
    let audit = open ($run_dir | path join $manifest.audit)
    let metric = read-last-metric ($run_dir | path join $manifest.metrics)
    let condition = ($run_dir | path dirname | path dirname | path basename)
    {
        condition: $condition,
        seed: $manifest.seed,
        final_tick: $manifest.final_tick,
        final_population: $manifest.final_population,
        final_species: $manifest.final_species_count,
        max_generation: $metric.max_generation,
        births: $metric.births,
        deaths: $metric.deaths,
        average_tps: $manifest.average_ticks_per_second,
        extinct: ($manifest.final_population == 0),
        elements_ok: $audit.elements_ok,
        energy_error_abs: (absolute $audit.energy_error),
        energy_relative_error: $audit.energy_relative_error,
        environmental_reactions: $metric.environmental_reactions,
        reaction_rules: $metric.environmental_reaction_rules,
        byproduct_emissions: $metric.byproduct_emissions,
        byproduct_positions: $metric.byproduct_positions,
        total_catalyst: $metric.byproduct_total_catalyst,
        total_toxin: $metric.byproduct_total_toxin,
        internalizations: $metric.internalizations,
        internal_guests: $metric.internal_guests,
        guest_hosts: $metric.chemistry_guest_hosts,
        guest_energy_demand: $metric.guest_energy_demand,
        guest_energy_exchange: $metric.guest_energy_exchange,
        guest_net_energy: $metric.guest_net_energy,
        chemistry_regime_variance: $metric.chemistry_regime_variance,
        chemistry_species_association: $metric.chemistry_species_association,
        chemistry_guest_regime_delta: $metric.chemistry_guest_regime_delta,
    }
}


def mean [values] {
    if ($values | is-empty) { 0.0 } else { $values | math avg }
}


def summarize [root: path] {
    let manifests = (glob ($root | path join "**" "manifest.json"))
    if ($manifests | is-empty) {
        error make {msg: $"no manifests found below ($root)"}
    }
    let rows = ($manifests | each {|manifest| read-run $manifest } | sort-by condition seed)
    let summary = ($CONDITIONS | each {|condition|
        let subset = ($rows | where condition == $condition)
        let count = $subset | length
        {
            condition: $condition,
            runs: $count,
            extinction_fraction: (($subset | where extinct | length) / $count),
            final_population_mean: (mean ($subset | get final_population)),
            final_species_mean: (mean ($subset | get final_species)),
            max_generation_mean: (mean ($subset | get max_generation)),
            births_mean: (mean ($subset | get births)),
            deaths_mean: (mean ($subset | get deaths)),
            average_tps_mean: (mean ($subset | get average_tps)),
            reaction_count_mean: (mean ($subset | get environmental_reactions)),
            byproduct_positions_mean: (mean ($subset | get byproduct_positions)),
            total_catalyst_mean: (mean ($subset | get total_catalyst)),
            total_toxin_mean: (mean ($subset | get total_toxin)),
            internalizations_mean: (mean ($subset | get internalizations)),
            internal_guests_mean: (mean ($subset | get internal_guests)),
            guest_net_energy_mean: (mean ($subset | get guest_net_energy)),
            chemistry_species_association_mean: (mean ($subset | get chemistry_species_association)),
            chemistry_guest_regime_delta_mean: (mean ($subset | get chemistry_guest_regime_delta)),
            max_energy_error: (($subset | get energy_error_abs | math max)),
            element_failures: ($subset | where elements_ok == false | length),
        }
    })
    let results_dir = ($root | path dirname)
    $rows | to csv | save --force ($results_dir | path join "run_summary.csv")
    $summary | to csv | save --force ($results_dir | path join "group_summary.csv")
    print "==== per-run summary ===="
    print ($rows | select condition seed final_population final_species max_generation environmental_reactions internalizations chemistry_species_association chemistry_guest_regime_delta energy_error_abs elements_ok)
    print "==== group summary ===="
    print $summary
}


def main [
    --ticks: int = 4000,
    --root: path = "experiment_results/dynamic_chemistry/runs",
    --threads: int = 4,
    --seeds: string = "100,101,102,103,104",
    --analyze-only,
] {
    let seed_values = ($seeds | split row "," | each {|seed| $seed | str trim | into int })
    if ($seed_values | is-empty) {
        error make {msg: "--seeds must contain at least one integer"}
    }
    mkdir $root
    if not $analyze_only {
        let cases = condition-cases $seed_values
        print $"Running ($cases | length) paired dynamic-chemistry cases with ($threads) workers"
        $cases | par-each --threads $threads {|case|
            run-case $root $ticks $case
        } | ignore
        print "Dynamic-chemistry runs complete"
    }
    summarize $root
}
