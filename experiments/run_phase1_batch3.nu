# Run the preregistered Phase 1 batch-3 campaign (E1 32,768-tape runs).
# Preregistration: reports/phase1_batch3_preregistration.md

def check-exit [label: string] {
    if $env.LAST_EXIT_CODE != 0 {
        error make {msg: $"($label) failed with exit code ($env.LAST_EXIT_CODE)"}
    }
}

def main [] {
    $nu.pid | into string | save --force .phase1-batch3.pid

    let root = "experiments/phase1_runs/batch3_scale"
    mkdir $root
    mkdir reports/phase1_newexperiments

    for seed in 0..4 {
        print $"(date now | format date '%FT%TZ')) E1/m16 n=32768 epochs=100000 seed=($seed)"
        ^uv run python -m experiments.phase1_probe --population-size 32768 --epochs 100000 --seed $seed --mutation-rate 0.000244140625 --pool-multiplier 16.0 --callback-interval 100 --output-dir $root
        check-exit "batch3 m16 case"
    }

    for seed in 0..4 {
        print $"(date now | format date '%FT%TZ')) E1/control n=32768 epochs=100000 seed=($seed)"
        ^uv run python -m experiments.paper_probe --population-size 32768 --epochs 100000 --seed $seed --mutation-rate 0.000244140625 --callback-interval 100 --output $"reports/phase1_newexperiments/E1_control_n32768_s($seed).csv"
        check-exit "batch3 control case"
    }

    print $"(date now | format date '%FT%TZ')) batch3 E1 complete"
}
