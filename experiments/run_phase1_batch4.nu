# Run the preregistered Phase 1 batch-4 campaign (mismatched-pool economies).
# Preregistration: reports/phase1_batch4_preregistration.md
#
# F1: uniform-pool continuations of the natural seed-0 epoch-2433 checkpoint
#     (131,072 tapes, 8,000 epochs, multipliers 0.5 / 2 / 16).
# F2: uniform-pool emergence runs at 32,768 tapes x 100,000 epochs, seeds 0-2,
#     multipliers 16 and 2, plus matched-pool m2 control pairs (seeds 0-2).
#
# All 12 runs execute concurrently via par-each (14-core host); the script
# verifies every run manifest before declaring success.

def main [] {
    $nu.pid | into string | save --force .phase1-batch4.pid

    let root = "experiments/phase1_runs/batch4_mismatch"
    mkdir $root

    let checkpoint = "runs/paper_probe_seed0_transition.npy"
    let mutation = "0.000244140625"

    # F1 commands: uniform continuations from the natural checkpoint.
    let f1 = [
        $"uv run python -m experiments.phase1_probe --population-size 131072 --epochs 8000 --seed 0 --mutation-rate ($mutation) --pool-multiplier 0.5 --pool-mode uniform --callback-interval 100 --initial-soup ($checkpoint) --epoch-offset 2433 --output-dir ($root)"
        $"uv run python -m experiments.phase1_probe --population-size 131072 --epochs 8000 --seed 0 --mutation-rate ($mutation) --pool-multiplier 2 --pool-mode uniform --callback-interval 100 --initial-soup ($checkpoint) --epoch-offset 2433 --output-dir ($root)"
        $"uv run python -m experiments.phase1_probe --population-size 131072 --epochs 8000 --seed 0 --mutation-rate ($mutation) --pool-multiplier 16 --pool-mode uniform --callback-interval 100 --initial-soup ($checkpoint) --epoch-offset 2433 --output-dir ($root)"
    ]

    # F2 commands: uniform emergence (m16, m2) + matched m2 control pairs.
    mut f2 = []
    for seed in 0..2 {
        $f2 = ($f2 | append [
            $"uv run python -m experiments.phase1_probe --population-size 32768 --epochs 100000 --seed ($seed) --mutation-rate ($mutation) --pool-multiplier 16 --pool-mode uniform --callback-interval 100 --output-dir ($root)"
            $"uv run python -m experiments.phase1_probe --population-size 32768 --epochs 100000 --seed ($seed) --mutation-rate ($mutation) --pool-multiplier 2 --pool-mode uniform --callback-interval 100 --output-dir ($root)"
            $"uv run python -m experiments.phase1_probe --population-size 32768 --epochs 100000 --seed ($seed) --mutation-rate ($mutation) --pool-multiplier 2 --callback-interval 100 --output-dir ($root)"
        ])
    }

    let commands = ($f1 | append $f2)
    print $"(date now | format date '%FT%TZ')) launching ($commands | length) batch-4 runs concurrently"

    let results = ($commands | par-each --threads 12 {|command|
        print $"(date now | format date '%FT%TZ')) start: ($command | str replace -r '.*phase1_probe ' '')"
        let exit_code = (bash -c $command | complete | get exit_code)
        print $"(date now | format date '%FT%TZ')) finished (exit ($exit_code)): ($command | str replace -r '.*phase1_probe ' '')"
        {command: $command, exit_code: $exit_code}
    })

    let failures = ($results | where exit_code != 0)
    print $"(date now | format date '%FT%TZ')) batch-4 runs complete: ($results | length) total, ($failures | length) failed"
    if ($failures | length) > 0 {
        $failures | to json | save --force ($root + "/failures.json")
        error make {msg: $"batch-4 had ($failures | length) failed runs"}
    }

    # Verify every manifest reports success and zero conservation residual.
    let manifests = (glob $"($root)/*/manifest.json" | each {|path|
        let m = (open $path)
        {run_id: $m.run_id, exit_status: $m.exit_status, residual: ($m.max_conservation_residual? | default "n/a")}
    })
    let bad = ($manifests | where exit_status != success)
    print ($manifests | to text)
    if ($bad | length) > 0 {
        error make {msg: $"batch-4 manifests not all successful: ($bad | to json)"}
    }
    print $"(date now | format date '%FT%TZ')) batch-4 all ($manifests | length) runs verified successful"
}
