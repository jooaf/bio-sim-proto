# Aggregate the compact artifacts from guarded-copier-v1 without altering them.
def main [] {
    let root = ($env.FILE_PWD | path dirname | path dirname)
    let results = ($root | path join 'experiments' 'replicator_length_study' 'results' 'guarded-copier-v1')
    let summaries = (glob ($results | path join 'random' '*' 'summary.json') | each { |path|
        let data = open $path
        {
            credential_length: $data.protocol.credential_length
            functional_information_bits: $data.protocol.functional_information_bits
            functional_basin_density: $data.protocol.functional_basin_density
            seed: $data.protocol.seed
            initial_functional_count: $data.aggregate.initial_functional_count
            first_functional_tick: $data.aggregate.first_functional_tick
            takeover_tick: $data.aggregate.takeover_tick
            final_functional_count: $data.aggregate.final_functional_count
            copy_events: $data.aggregate.copy_events
        }
    })
    let summary = ($summaries | group-by credential_length | transpose credential rows | each { |group|
        let rows = $group.rows
        {
            credential_length: ($group.credential | into int)
            functional_information_bits: $rows.0.functional_information_bits
            functional_basin_density: $rows.0.functional_basin_density
            replicates: ($rows | length)
            initial_functional_replicates: ($rows | where initial_functional_count > 0 | length)
            any_functional_replicates: ($rows | where first_functional_tick != null | length)
            takeover_replicates: ($rows | where takeover_tick != null | length)
            mean_initial_functional_count: (($rows.initial_functional_count | math avg) | into float)
            mean_final_functional_count: (($rows.final_functional_count | math avg) | into float)
            mean_copy_events: (($rows.copy_events | math avg) | into float)
        }
    } | sort-by credential_length)

    $summary | to csv | save --force ($results | path join 'random_summary.csv')
    let table_rows = ($summary | each { |row|
        $"| ($row.credential_length) | ($row.functional_information_bits) | ($row.functional_basin_density) | ($row.initial_functional_replicates)/($row.replicates) | ($row.any_functional_replicates)/($row.replicates) | ($row.takeover_replicates)/($row.replicates) | ($row.mean_final_functional_count | math round --precision 2) |"
    } | str join (char newline))
    [
        '# Guarded-copier v1 — random-initialization results'
        ''
        'Each condition has 20 seeds, 256 tapes of 16 four-symbol bytes, shuffled disjoint ordered pairs, 512 ticks, mutation rate 1/4096 per byte per tick, and an instruction budget of 16. The sole intervention is credential length. A functional tape must contain COPY plus the fixed credential, so basin density is exactly `4^-(credential_length + 1)`.'
        ''
        '| Credential length | Functional information (bits) | Basin density | Functional at initialization | Functional at any tick | >=50% takeover | Mean final functional tapes |'
        '|---:|---:|---:|---:|---:|---:|---:|'
        $table_rows
        ''
        '“Functional at any tick” includes the initial soup. This is a controlled result for the guarded-copier family, not a cross-language estimate.'
        ''
        'Seeded validation completed before these runs: all 80 seeded replicates recorded one or more exact-copy events.'
    ] | str join (char newline) | save --force ($results | path join 'RANDOM_RESULTS.md')
}
