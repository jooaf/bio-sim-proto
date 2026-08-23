# Run the preregistered Phase 1 new-experiment batch (auto-loop batch 1).
# Experiment A: long-window 4,096-tape emergence (conserved + no-conservation control).
# Experiment B: conserved continuation of the natural Phase 0 seed-0 checkpoint.
# Experiment C: windowed-flow metabolic trace campaign.
# Preregistration: reports/phase1_newexperiments_preregistration.md

def check-exit [label: string] {
    if $env.LAST_EXIT_CODE != 0 {
        error make {msg: $"($label) failed with exit code ($env.LAST_EXIT_CODE)"}
    }
}

def phase1-case [
    output_dir: string,
    population_size: int,
    epochs: int,
    multiplier: float,
    seed: int,
    initial_soup?: string,
    epoch_offset: int = 0,
] {
    let soup_args = if $initial_soup != null { ["--initial-soup" $initial_soup "--epoch-offset" ($epoch_offset | into string)] } else { [] }
    print $"(date now | format date '%FT%TZ')) A/conserved n=($population_size) epochs=($epochs) m=($multiplier) seed=($seed) soup=($initial_soup)"
    ^uv run python -m experiments.phase1_probe --population-size $population_size --epochs $epochs --seed $seed --mutation-rate 0.000244140625 --pool-multiplier $multiplier --callback-interval 100 ...$soup_args --output-dir $output_dir
    check-exit "phase1 case"
}

def paper-case [
    output: string,
    population_size: int,
    epochs: int,
    seed: int,
    callback_interval: int = 100,
    initial_soup?: string,
    epoch_offset: int = 0,
] {
    let soup_args = if $initial_soup != null { ["--initial-soup" $initial_soup "--epoch-offset" ($epoch_offset | into string)] } else { [] }
    print $"(date now | format date '%FT%TZ')) control n=($population_size) epochs=($epochs) seed=($seed) soup=($initial_soup)"
    ^uv run python -m experiments.paper_probe --population-size $population_size --epochs $epochs --seed $seed --mutation-rate 0.000244140625 --callback-interval $callback_interval ...$soup_args --output $output
    check-exit "paper control case"
}

def trace-case [
    output_dir: string,
    multiplier: float,
    seed: int,
] {
    print $"(date now | format date '%FT%TZ')) C/trace m=($multiplier) seed=($seed)"
    ^uv run python -m experiments.metabolic_trace_probe --population-size 256 --epochs 20000 --seed $seed --mutation-rate 0.000244140625 --pool-multiplier $multiplier --callback-interval 100 --sample-denominator 64 --max-events 250000 --flow-window 2000 --output-dir $output_dir
    check-exit "trace case"
}

def main [
    --stage: string = "all"  # all | A | B | C | B-control
] {
    $nu.pid | into string | save --force .phase1-newexperiments.pid

    if $stage in ["all" "A"] {
        let root = "experiments/phase1_runs/longwindow"
        mkdir $root
        for multiplier in [0.5 2.0 16.0] {
            for seed in 0..4 {
                phase1-case $root 4096 100000 $multiplier $seed
            }
        }
        mkdir reports/phase1_newexperiments
        for seed in 0..4 {
            paper-case $"reports/phase1_newexperiments/A_control_n4096_s($seed).csv" 4096 100000 $seed
        }
    }

    if $stage in ["all" "B-control"] {
        let checkpoint = "runs/paper_probe_seed0_transition.npy"
        mkdir reports/phase1_newexperiments
        paper-case "reports/phase1_newexperiments/B_control_continuation.csv" 131072 8000 0 100 $checkpoint 2433
    }

    if $stage in ["all" "B"] {
        let root = "experiments/phase1_runs/continuation"
        mkdir $root
        let checkpoint = "runs/paper_probe_seed0_transition.npy"
        # Random-soup baseline at matched scale for B4 (no offset, fresh init).
        phase1-case $root 131072 8000 2.0 0
        for multiplier in [0.5 2.0 16.0] {
            phase1-case $root 131072 8000 $multiplier 0 $checkpoint 2433
        }
    }

    if $stage in ["all" "C"] {
        let root = "experiments/phase1_runs/metabolic_trace_windows"
        mkdir $root
        for multiplier in [0.5 2.0 16.0] {
            for seed in 0..2 {
                trace-case $root $multiplier $seed
            }
        }
    }

    print $"(date now | format date '%FT%TZ')) stage=($stage) complete"
}
