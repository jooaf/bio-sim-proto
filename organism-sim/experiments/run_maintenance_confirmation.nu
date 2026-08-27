# Confirm the maintenance effect at the default 0.12 sexual floor on five new seeds.

def run-case [root: path, maintenance: float, seed: int] {
    let condition = $"maint-($maintenance | into string | str replace '.' 'p')_floor-0p12"
    let output_dir = ($root | path join $condition)
    mkdir $output_dir
    print $"START confirmation condition=($condition) seed=($seed)"
    let result = (^uv run organism-sim-headless
        --ticks 2500
        --runs-dir $output_dir
        --founders 300
        --genome-seeds 8
        --elements 8
        --molecules 48
        --deposits 2600
        --seed $seed
        --mutation-multiplier 1.0
        --maintenance-multiplier $maintenance
        --maturity-multiplier 0.65
        --reproduction-drive 1.25
        --reproduction-cost 0.75
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
        error make {msg: $"condition=($condition) seed=($seed) failed with exit code ($result.exit_code)"}
    }
    print $"DONE confirmation condition=($condition) seed=($seed)"
}

def main [
    --root: path = "experiment_results/improvement_screen/runs",
    --threads: int = 8,
] {
    let cases = [0.75 1.0] | each {|maintenance|
        45..49 | each {|seed| {maintenance: $maintenance, seed: $seed}}
    } | flatten
    $cases | par-each --threads $threads {|case|
        run-case $root $case.maintenance $case.seed
    } | ignore
    print "Maintenance confirmation complete"
}
