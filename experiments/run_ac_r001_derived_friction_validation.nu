# Run the preregistered AC-R001 derived-friction mechanics validation.

def main [] {
    $nu.pid | into string | save --force .ac-r001-validation.pid
    let root = "sweeps/ac_r001_derived_friction_validation/runs"
    mkdir $root
    let rate = "0.27555027572734614"
    mut commands = []
    for seed in 202610010..202610014 {
        $commands = ($commands | append [
            $"uv run python -m experiments.phase1_probe --population-size 32768 --epochs 5000 --seed ($seed) --mutation-rate 0.000244140625 --pool-multiplier 2 --pool-mode excluded_list --pool-exclude-symbols 0,44,60,91,93,125 --callback-interval 100 --output-dir ($root)"
            $"uv run python -m experiments.phase1_probe --population-size 32768 --epochs 5000 --seed ($seed) --mutation-rate 0.000244140625 --pool-multiplier 2 --friction-rejection-rate ($rate) --callback-interval 100 --output-dir ($root)"
        ])
    }
    let results = ($commands | par-each --threads 10 {|command|
        let completed = (bash -c $command | complete)
        {command: $command, exit_code: $completed.exit_code, stderr: $completed.stderr}
    })
    let failures = ($results | where exit_code != 0)
    if not ($failures | is-empty) {
        $failures | to json | save --force "sweeps/ac_r001_derived_friction_validation/failures.json"
        error make {msg: $"AC-R001 had ($failures | length) failed runs"}
    }
    let manifests = (glob $"($root)/*/manifest.json" | each {|path| open $path})
    if (($manifests | length) != 10) or (not ($manifests | all {|m| $m.exit_status == "success" and $m.max_conservation_residual == 0})) {
        error make {msg: "AC-R001 manifest verification failed"}
    }
    rm --force .ac-r001-validation.pid
    print $"verified ($manifests | length) successful validation runs"
}
