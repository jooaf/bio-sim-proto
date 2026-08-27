# Run a paired sexual-floor × maintenance factorial screen.
#
# Examples:
#   nu experiments/run_improvement_screen.nu
#   nu experiments/run_improvement_screen.nu --ticks 100

def run-case [
    root: path,
    ticks: int,
    condition: string,
    maintenance: float,
    sexual_floor: float,
    enabled: bool,
    seed: int,
] {
    let output_dir = ($root | path join $condition)
    mkdir $output_dir
    let common = [
        run organism-sim-headless
        --ticks $ticks
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
        --sexual-floor $sexual_floor
        --decomposition-rate 0.0008
        --heat-diffusion 0.08
        --detail-every 20
        --snapshot-every 100
        --commit-every 50
    ]
    let command = if $enabled {
        $common | append "--sexual-floor-enabled"
    } else {
        $common | append "--no-sexual-floor-enabled"
    }
    print $"START condition=($condition) seed=($seed)"
    let result = (^uv ...$command | complete)
    $result.stdout | save --force ($output_dir | path join $"seed-($seed).stdout.log")
    $result.stderr | save --force ($output_dir | path join $"seed-($seed).stderr.log")
    if $result.exit_code != 0 {
        error make {msg: $"condition=($condition) seed=($seed) failed with exit code ($result.exit_code)"}
    }
    print $"DONE condition=($condition) seed=($seed)"
}

def main [
    --ticks: int = 2500,
    --root: path = "experiment_results/improvement_screen/runs",
    --threads: int = 8,
] {
    mkdir $root
    let floors = [
        {label: "floor-off", value: 0.0, enabled: false},
        {label: "floor-0p12", value: 0.12, enabled: true},
        {label: "floor-0p30", value: 0.30, enabled: true},
        {label: "floor-0p50", value: 0.50, enabled: true},
    ]
    let cases = [0.75 1.0]
        | each {|maintenance|
            $floors | each {|floor|
                40..44 | each {|seed|
                    {
                        condition: $"maint-($maintenance | into string | str replace '.' 'p')_($floor.label)",
                        maintenance: $maintenance,
                        sexual_floor: $floor.value,
                        enabled: $floor.enabled,
                        seed: $seed,
                    }
                }
            }
        }
        | flatten
        | flatten

    print $"Running ($cases | length) paired experiments with ($threads) workers"
    $cases | par-each --threads $threads {|case|
        run-case $root $ticks $case.condition $case.maintenance $case.sexual_floor $case.enabled $case.seed
    } | ignore
    print "Improvement screen complete"
}
