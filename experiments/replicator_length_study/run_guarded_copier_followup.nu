# Guarded-copier v2 random-initialization follow-up.
# Protocol and confirmatory analysis are preregistered in
# GUARDED_COPIER_V2_PREREGISTRATION.md before this script is launched.

let root = ($env.FILE_PWD | path dirname | path dirname)
let runner = ($root | path join 'experiments' 'replicator_length_study' 'run_guarded_copier.py')
let results = ($root | path join 'experiments' 'replicator_length_study' 'results' 'guarded-copier-v2')
let pid_file = ($root | path join '.guarded-copier-v2.pid')
let log_dir = ($root | path join 'logs')
let cases = [
    {credential_length: 2, seeds: (0..19)}
    {credential_length: 3, seeds: (0..19)}
    {credential_length: 4, seeds: (0..19)}
    {credential_length: 5, seeds: (0..19)}
    {credential_length: 6, seeds: (20..119)}
    {credential_length: 7, seeds: (0..19)}
    {credential_length: 8, seeds: (20..119)}
]

mkdir $log_dir
$nu.pid | into string | save --force $pid_file
if not ($results | path exists) {
    mkdir $results
    {
        status: running
        name: guarded-copier-v2
        initialization: random
        preregistration: 'GUARDED_COPIER_V2_PREREGISTRATION.md'
        credentials: [2 3 4 5 6 7 8]
        v2_replicates: 300
        population_size: 256
        tape_length: 16
        mutation_rate: 0.000244140625
        execution_budget: 16
        ticks: 512
        pairing: shuffled_disjoint_ordered_pairs
    } | to json | save --force ($results | path join 'manifest.json')
} else if (open ($results | path join 'manifest.json')).status == 'success' {
    error make {msg: $"Follow-up is already complete: ($results)"}
}

for case in $cases {
    for seed in $case.seeds {
        let output = ($results | path join $"credential-($case.credential_length)-seed-($seed)")
        let replicate_manifest = ($output | path join 'manifest.json')
        if ($replicate_manifest | path exists) and (open $replicate_manifest).status == 'success' {
            print $"Skipping completed credential length ($case.credential_length), seed ($seed)"
        } else {
            if ($output | path exists) {
                print $"Restarting incomplete credential length ($case.credential_length), seed ($seed)"
                rm -rf $output
            }
            print $"Running credential length ($case.credential_length), seed ($seed) -> ($output)"
            ^uv run python $runner --initialization random --credential-length $case.credential_length --population-size 256 --tape-length 16 --ticks 512 --seed $seed --mutation-rate 0.000244140625 --execution-budget 16 --metric-interval 1 --takeover-fraction 0.5 --output-dir $output
            if $env.LAST_EXIT_CODE != 0 {
                {
                    status: failed
                    failed_credential_length: $case.credential_length
                    failed_seed: $seed
                } | to json | save --force ($results | path join 'manifest.json')
                error make {msg: $"Guarded-copier v2 replicate failed: ($output)"}
            }
        }
    }
}
{status: success, name: guarded-copier-v2, initialization: random, v2_replicates: 300} | to json | save --force ($results | path join 'manifest.json')
