# Predeclared guarded-copier within-family intervention.
# Seeded validation is completed before random initialization. Every condition
# has the same population, tape length, mutation process, instruction budget,
# tick count, pairing protocol, and 20 replicate seeds. Only credential length
# changes, which changes the exact functional basin density.

def main [phase: string = 'all'] {
    let root = ($env.FILE_PWD | path dirname | path dirname)
    let runner = ($root | path join 'experiments' 'replicator_length_study' 'run_guarded_copier.py')
    let results = ($root | path join 'experiments' 'replicator_length_study' 'results' 'guarded-copier-v1')
    let pid_file = ($root | path join '.guarded-copier-intervention.pid')
    let cases = [2 4 6 8]
    let replicate_seeds = 0..19

    if $phase not-in ['seeded' 'random' 'all'] {
        error make {msg: 'phase must be seeded, random, or all'}
    }
    $nu.pid | into string | save --force $pid_file
    if not ($results | path exists) {
        mkdir $results
    }
    {
        status: running
        name: guarded-copier-v1
        phase: $phase
        phases: [seeded-validation random-initialization]
        credentials: $cases
        replicates_per_condition: 20
        population_size: 256
        tape_length: 16
        mutation_rate: 0.000244140625
        execution_budget: 16
        ticks: 512
    } | to json | save --force ($results | path join 'manifest.json')

    let initializations = if $phase == 'all' { [seeded random] } else { [$phase] }
    for initialization in $initializations {
        for credential_length in $cases {
            for seed in $replicate_seeds {
                let output = ($results | path join $initialization $"credential-($credential_length)-seed-($seed)")
                let seeded_args = if $initialization == 'seeded' { ['--seeded-copies' '2'] } else { [] }
                ^uv run python $runner --initialization $initialization --credential-length $credential_length --population-size 256 --tape-length 16 --ticks 512 --seed $seed --mutation-rate 0.000244140625 --execution-budget 16 --metric-interval 1 --takeover-fraction 0.5 ...$seeded_args --output-dir $output
                if $env.LAST_EXIT_CODE != 0 {
                    {status: failed, failed_initialization: $initialization, failed_credential_length: $credential_length, failed_seed: $seed} | to json | save --force ($results | path join 'manifest.json')
                    error make {msg: $"Guarded-copier replicate failed: ($output)"}
                }
            }
        }
    }
    {status: success, name: guarded-copier-v1, phase: $phase} | to json | save --force ($results | path join 'manifest.json')
}
