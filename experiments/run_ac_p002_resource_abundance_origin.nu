# Run the preregistered AC-P002 held-out resource-abundance comparison.

def main [] {
    $nu.pid | into string | save --force .ac-p002.pid
    let root = "sweeps/ac_p002_resource_abundance_origin/runs"
    mkdir $root
    let commands = (202613000..202613019 | each {|seed| [
        $"env NUMBA_NUM_THREADS=1 uv run python -m experiments.phase1_probe --population-size 32768 --epochs 100000 --seed ($seed) --mutation-rate 0.000244140625 --pool-multiplier 2 --callback-interval 100 --functional-observation --output-dir ($root)"
        $"env NUMBA_NUM_THREADS=1 uv run python -m experiments.phase1_probe --population-size 32768 --epochs 100000 --seed ($seed) --mutation-rate 0.000244140625 --pool-multiplier 16 --callback-interval 100 --functional-observation --output-dir ($root)"
    ]} | flatten)
    print $"(date now | format date '%FT%TZ') launching/resuming ($commands | length) AC-P002 runs with seven workers"
    let results = ($commands | par-each --threads 7 {|command|
        let completed = (bash -c $command | complete)
        {command: $command, exit_code: $completed.exit_code, stderr: $completed.stderr}
    })
    let failures = ($results | where exit_code != 0)
    if not ($failures | is-empty) {
        $failures | to json | save --force "sweeps/ac_p002_resource_abundance_origin/failures.json"
        error make {msg: $"AC-P002 had ($failures | length) failed runs"}
    }
    let manifests = (glob $"($root)/*/manifest.json" | each {|path| open $path})
    if (($manifests | length) != 40) or (not ($manifests | all {|m| $m.exit_status == "success" and $m.max_conservation_residual == 0})) {
        error make {msg: "AC-P002 manifest verification failed"}
    }
    rm --force .ac-p002.pid
    print $"verified ($manifests | length) successful AC-P002 runs"
}
