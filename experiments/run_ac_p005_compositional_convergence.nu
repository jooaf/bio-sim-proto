# Run the preregistered AC-P005 held-out compositional-convergence replication.

def main [] {
    $nu.pid | into string | save --force .ac-p005.pid
    let root = "sweeps/ac_p005_compositional_convergence/runs"
    mkdir $root
    let commands = (202615000..202615019 | each {|seed|
        $"env NUMBA_NUM_THREADS=1 uv run python -m experiments.phase1_probe --population-size 32768 --epochs 100000 --seed ($seed) --mutation-rate 0.000244140625 --pool-multiplier 16 --callback-interval 100 --functional-observation --prospective-control-observation --output-dir ($root)"
    })
    print $"(date now | format date '%FT%TZ') launching/resuming ($commands | length) AC-P005 runs with six workers"
    let results = ($commands | par-each --threads 6 {|command|
        let completed = (bash -c $command | complete)
        {command: $command, exit_code: $completed.exit_code, stderr: $completed.stderr}
    })
    let failures = ($results | where exit_code != 0)
    if not ($failures | is-empty) {
        $failures | to json | save --force "sweeps/ac_p005_compositional_convergence/failures.json"
        error make {msg: $"AC-P005 had ($failures | length) failed runs"}
    }
    let manifests = (glob $"($root)/*/manifest.json" | each {|path| open $path})
    if (($manifests | length) != 20) or (not ($manifests | all {|m| $m.exit_status == "success" and $m.max_conservation_residual == 0})) {
        error make {msg: "AC-P005 manifest verification failed"}
    }
    rm --force .ac-p005.pid
    print $"verified ($manifests | length) successful AC-P005 runs"
}
