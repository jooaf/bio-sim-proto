# Run the targeted paper-scale mutation-rate pilot sequentially.
def main [] {
    let cases = [
        {name: "zero", rate: 0.0},
        {name: "reference", rate: 0.000244140625},
        {name: "high", rate: 0.0078125},
    ]
    for case in $cases {
        let output = $"reports/paper_mutation_($case.name)_seed0.csv"
        let checkpoint = $"runs/paper_mutation_($case.name)_seed0_transition.npy"
        if ($output | path exists) {
            print $"Skipping existing ($output)"
        } else {
            print $"Running mutation_rate=($case.rate) -> ($output)"
            uv run soup-paper-probe --population-size 131072 --epochs 16000 --seed 0 --mutation-rate $case.rate --callback-interval 128 --output $output --checkpoint $checkpoint
        }
    }
}
