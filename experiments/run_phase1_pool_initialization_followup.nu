# Exploratory P1.6 follow-up selected after the replicated scarcity campaign.

def main [] {
    $nu.pid | into string | save --force .phase1-pool-init.pid
    let output_dir = "experiments/phase1_runs/pool_initialization"
    mkdir $output_dir
    for multiplier in [0.1 0.5] {
        for seed in 0..4 {
            print $"Running uniform-pool follow-up: multiplier=($multiplier), seed=($seed)"
            ^uv run python -m experiments.phase1_probe --population-size 256 --epochs 20000 --seed $seed --mutation-rate 0.000244140625 --pool-multiplier $multiplier --pool-mode uniform --callback-interval 100 --output-dir $output_dir
            if $env.LAST_EXIT_CODE != 0 {
                error make {msg: $"Uniform-pool case failed with exit code ($env.LAST_EXIT_CODE)"}
            }
        }
    }
}
