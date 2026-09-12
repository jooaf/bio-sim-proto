# Run the preregistered AC-I001 mechanics-only friction calibration.

def main [] {
    $nu.pid | into string | save --force .ac-i001-calibration.pid
    let root = "sweeps/ac_i001_friction_calibration/runs"
    mkdir $root
    let mutation = "0.000244140625"
    let seeds = 202610000..202610004
    let rates = [0.01 0.02 0.03 0.05 0.08]
    mut commands = []
    for seed in $seeds {
        $commands = ($commands | append $"uv run python -m experiments.phase1_probe --population-size 32768 --epochs 5000 --seed ($seed) --mutation-rate ($mutation) --pool-multiplier 2 --pool-mode excluded_list --pool-exclude-symbols 0,44,60,91,93,125 --callback-interval 100 --output-dir ($root)")
        for rate in $rates {
            $commands = ($commands | append $"uv run python -m experiments.phase1_probe --population-size 32768 --epochs 5000 --seed ($seed) --mutation-rate ($mutation) --pool-multiplier 2 --friction-rejection-rate ($rate) --callback-interval 100 --output-dir ($root)")
        }
    }
    print $"(date now | format date '%FT%TZ') launching ($commands | length) calibration runs"
    let results = ($commands | par-each --threads 10 {|command|
        let completed = (bash -c $command | complete)
        {command: $command, exit_code: $completed.exit_code, stderr: $completed.stderr}
    })
    let failures = ($results | where exit_code != 0)
    if not ($failures | is-empty) {
        $failures | to json | save --force "sweeps/ac_i001_friction_calibration/failures.json"
        error make {msg: $"AC-I001 calibration had ($failures | length) failed runs"}
    }
    let manifests = (glob $"($root)/*/manifest.json" | each {|path| open $path})
    if (($manifests | length) != 30) or (not ($manifests | all {|m| $m.exit_status == "success" and $m.max_conservation_residual == 0})) {
        error make {msg: "AC-I001 calibration manifest verification failed"}
    }
    rm --force .ac-i001-calibration.pid
    print $"verified ($manifests | length) successful calibration runs"
}
