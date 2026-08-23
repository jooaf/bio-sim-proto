# P0.7: bounded paper-scale time-to-emergence replicates for seeds 1–3.
def main [] {
    $nu.pid | into string | save --force .batch.pid

    for seed in 1..3 {
        let output = $"reports/p0_7_reference_seed_($seed).csv"
        let checkpoint = $"runs/p0_7_reference_seed_($seed)_transition.npy"
        if ($output | path exists) {
            print $"Skipping existing ($output)"
        } else {
            print $"Running P0.7 reference mutation, seed ($seed) -> ($output)"
            ^uv run soup-paper-probe --population-size 131072 --epochs 16000 --seed $seed --mutation-rate 0.000244140625 --callback-interval 128 --output $output --checkpoint $checkpoint
            if $env.LAST_EXIT_CODE != 0 {
                error make {msg: $"P0.7 seed ($seed) failed with exit code ($env.LAST_EXIT_CODE)"}
            }
        }
    }
}
