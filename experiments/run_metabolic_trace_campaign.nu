# Run the preregistered Phase 1 token-path and burst-tracing matrix.

def main [] {
    $nu.pid | into string | save --force .phase1-metabolic-trace.pid
    let output_dir = "experiments/phase1_runs/metabolic_trace"
    mkdir $output_dir
    for multiplier in [0.5 2.0 16.0] {
        for seed in 0..2 {
            print $"Tracing metabolic paths: multiplier=($multiplier), seed=($seed)"
            ^uv run python -m experiments.metabolic_trace_probe --population-size 256 --epochs 20000 --seed $seed --mutation-rate 0.000244140625 --pool-multiplier $multiplier --callback-interval 100 --sample-denominator 64 --max-events 250000 --output-dir $output_dir
            if $env.LAST_EXIT_CODE != 0 {
                error make {msg: $"Metabolic trace failed with exit code ($env.LAST_EXIT_CODE)"}
            }
        }
    }
}
