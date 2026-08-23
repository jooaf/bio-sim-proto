# Run the preregistered Phase 1 batch-2 campaign (D1 population-scale runs).
# Preregistration: reports/phase1_batch2_preregistration.md

def check-exit [label: string] {
    if $env.LAST_EXIT_CODE != 0 {
        error make {msg: $"($label) failed with exit code ($env.LAST_EXIT_CODE)"}
    }
}

def main [] {
    $nu.pid | into string | save --force .phase1-batch2.pid

    let root = "experiments/phase1_runs/batch2_scale"
    mkdir $root
    mkdir reports/phase1_newexperiments

    # m16 conserved first (shadows control; the scale-isolating arm).
    for seed in 0..4 {
        print $"(date now | format date '%FT%TZ')) D1/m16 n=16384 epochs=50000 seed=($seed)"
        ^uv run python -m experiments.phase1_probe --population-size 16384 --epochs 50000 --seed $seed --mutation-rate 0.000244140625 --pool-multiplier 16.0 --callback-interval 100 --output-dir $root
        check-exit "batch2 m16 case"
    }

    for seed in 0..4 {
        print $"(date now | format date '%FT%TZ')) D1/control n=16384 epochs=50000 seed=($seed)"
        ^uv run python -m experiments.paper_probe --population-size 16384 --epochs 50000 --seed $seed --mutation-rate 0.000244140625 --callback-interval 100 --output $"reports/phase1_newexperiments/D1_control_n16384_s($seed).csv"
        check-exit "batch2 control case"
    }

    print $"(date now | format date '%FT%TZ')) batch2 D1 complete"
}
