# Run the preregistered AC-I001 held-out functional-origin confirmation.

def main [] {
    $nu.pid | into string | save --force .ac-i001-confirmation.pid
    let root = "sweeps/ac_i001_origin_filter_confirmation/runs"
    mkdir $root
    let rate = "0.27555027572734614"
    mut commands = []
    for seed in 202611000..202611019 {
        $commands = ($commands | append [
            $"env NUMBA_NUM_THREADS=1 uv run python -m experiments.phase1_probe --population-size 32768 --epochs 100000 --seed ($seed) --mutation-rate 0.000244140625 --pool-multiplier 2 --callback-interval 100 --functional-observation --output-dir ($root)"
            $"env NUMBA_NUM_THREADS=1 uv run python -m experiments.phase1_probe --population-size 32768 --epochs 100000 --seed ($seed) --mutation-rate 0.000244140625 --pool-multiplier 2 --pool-mode excluded_list --pool-exclude-symbols 0,44,60,91,93,125 --callback-interval 100 --functional-observation --output-dir ($root)"
            $"env NUMBA_NUM_THREADS=1 uv run python -m experiments.phase1_probe --population-size 32768 --epochs 100000 --seed ($seed) --mutation-rate 0.000244140625 --pool-multiplier 2 --friction-rejection-rate ($rate) --callback-interval 100 --functional-observation --output-dir ($root)"
        ])
    }
    print $"(date now | format date '%FT%TZ') launching/resuming ($commands | length) confirmation runs with seven workers"
    let results = ($commands | par-each --threads 7 {|command|
        let completed = (bash -c $command | complete)
        {command: $command, exit_code: $completed.exit_code, stderr: $completed.stderr}
    })
    let failures = ($results | where exit_code != 0)
    if not ($failures | is-empty) {
        $failures | to json | save --force "sweeps/ac_i001_origin_filter_confirmation/failures.json"
        error make {msg: $"AC-I001 confirmation had ($failures | length) failed runs"}
    }
    let manifests = (glob $"($root)/*/manifest.json" | each {|path| open $path})
    if (($manifests | length) != 60) or (not ($manifests | all {|m| $m.exit_status == "success" and $m.max_conservation_residual == 0})) {
        error make {msg: "AC-I001 confirmation manifest verification failed"}
    }
    rm --force .ac-i001-confirmation.pid
    print $"verified ($manifests | length) successful confirmation runs"
}
