# Run the preregistered Phase 1 mechanism sweep and bounded scale follow-up.

def run-case [
    output_dir: string,
    population_size: int,
    epochs: int,
    multiplier: float,
    seed: int,
] {
    print $"Running Phase 1: n=($population_size), epochs=($epochs), multiplier=($multiplier), seed=($seed)"
    ^uv run python -m experiments.phase1_probe --population-size $population_size --epochs $epochs --seed $seed --mutation-rate 0.000244140625 --pool-multiplier $multiplier --callback-interval 100 --output-dir $output_dir
    if $env.LAST_EXIT_CODE != 0 {
        error make {msg: $"Phase 1 case failed with exit code ($env.LAST_EXIT_CODE)"}
    }
}


def main [] {
    $nu.pid | into string | save --force .phase1-campaign.pid

    let mechanism_root = "experiments/phase1_runs/mechanism"
    let scale_root = "experiments/phase1_runs/scale"
    mkdir $mechanism_root $scale_root

    for multiplier in [0.1 0.5 2.0 16.0 256.0] {
        for seed in 0..4 {
            run-case $mechanism_root 256 20000 $multiplier $seed
        }
    }

    # Exact global-pool access is serial. This 4,096-tape matrix is large enough
    # to test scale persistence while remaining bounded and reproducible.
    for multiplier in [0.5 2.0 16.0] {
        for seed in 0..2 {
            run-case $scale_root 4096 20000 $multiplier $seed
        }
    }
}
