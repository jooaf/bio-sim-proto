# Publish one completed experiment directory to append-only central storage.
#
# The destination can be local or an rsync-over-SSH location. Uploads first go
# to a deterministic partial directory and are renamed only after rsync exits
# successfully, so consumers never see an incomplete final directory.
#
# Examples:
#   $env.BIO_SIM_RESULTS_DESTINATION = "jojo@100.80.185.9:/home/jojo/bio-sim-results"
#   nu tools/publish_experiment.nu organism-sim/runs/<run-id>
#   nu tools/publish_experiment.nu organism-sim/runs/<run-id> --destination /home/jojo/bio-sim-results

def safe-component [value: string] {
    $value | str replace --all --regex '[^A-Za-z0-9._-]' '-'
}

def require-success [result: record, action: string] {
    if $result.exit_code != 0 {
        error make {msg: $"($action) failed: ($result.stderr | str trim)"}
    }
}

def git-metadata [] {
    let probe = (^git rev-parse --show-toplevel | complete)
    if $probe.exit_code != 0 {
        return {commit: null, branch: null, dirty: null}
    }
    let root = ($probe.stdout | str trim)
    let commit = (^git -C $root rev-parse HEAD | str trim)
    let branch = (^git -C $root branch --show-current | str trim)
    let status = (^git -C $root status --porcelain | str trim)
    {commit: $commit, branch: $branch, dirty: ($status | is-not-empty)}
}

def publish-local [source: path, destination: path, machine: string, run_name: string] {
    let parent = ($destination | path expand | path join $machine)
    let final = ($parent | path join $run_name)
    let partial = ($parent | path join $".($run_name).partial")
    if ($final | path exists) {
        error make {msg: $"published experiment already exists: ($final)"}
    }
    mkdir $parent
    let transfer = (^rsync -a --partial --human-readable --progress $"($source)/" $"($partial)/" | complete)
    require-success $transfer "local rsync"
    mv $partial $final
    $final
}

def publish-remote [source: path, destination: string, machine: string, run_name: string] {
    let parsed = ($destination | parse --regex '^(?<host>[^:]+):(?<root>/.*)$')
    if ($parsed | length) != 1 {
        error make {msg: "remote destination must look like user@host:/absolute/path"}
    }
    let host = ($parsed | first | get host)
    let root = ($parsed | first | get root)
    if $root !~ '^/[A-Za-z0-9._/-]+$' {
        error make {msg: "remote results path contains unsupported characters"}
    }
    let parent = $"($root)/($machine)"
    let final = $"($parent)/($run_name)"
    let partial = $"($parent)/.($run_name).partial"

    let exists = (^ssh $host test -e $final | complete)
    if $exists.exit_code == 0 {
        error make {msg: $"published experiment already exists: ($host):($final)"}
    }
    require-success (^ssh $host mkdir -p -- $parent | complete) "create remote results directory"
    require-success (^rsync -a --partial --human-readable --progress $"($source)/" $"($host):($partial)/" | complete) "remote rsync"
    require-success (^ssh $host mv -- $partial $final | complete) "finalize remote experiment"
    $"($host):($final)"
}

def main [
    run_dir: path,                 # Completed experiment/run directory to publish.
    --destination: string,         # Local path or user@host:/absolute/path; defaults to BIO_SIM_RESULTS_DESTINATION.
] {
    if (which rsync | is-empty) {
        error make {msg: "rsync is required"}
    }
    let source = ($run_dir | path expand)
    if not ($source | path exists) or ($source | path type) != "dir" {
        error make {msg: $"run directory does not exist: ($source)"}
    }
    let target = ($destination | default $env.BIO_SIM_RESULTS_DESTINATION? | default "")
    if ($target | str trim | is-empty) {
        error make {msg: "set --destination or BIO_SIM_RESULTS_DESTINATION"}
    }

    let machine = (safe-component (sys host | get hostname))
    let run_name = (safe-component ($source | path basename))
    let metadata = {
        schema_version: 1,
        published_at: (date now),
        source_machine: $machine,
        source_directory: $source,
        git: (git-metadata),
    }
    $metadata | to json --indent 2 | save --force ($source | path join "PUBLISHED.json")

    let published = if $target =~ '^[^:]+:/.*$' {
        publish-remote $source $target $machine $run_name
    } else {
        publish-local $source $target $machine $run_name
    }
    print $"Published ($source) -> ($published)"
}
