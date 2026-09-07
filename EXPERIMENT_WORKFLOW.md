# Multi-machine experiment workflow

Use GitHub for source, experiment definitions, configuration, lockfiles, and
compact Markdown reports. Keep generated run data outside Git in one append-only
results directory.

## Machine setup

Clone and build on each experiment machine:

```nu
git clone git@github.com:jooaf/bio-sim-proto.git
cd bio-sim-proto
nu organism-sim/rust/install_release.nu
```

The installer runs `uv sync` and builds the optimized Rust extension for the
current machine. The project selects Python 3.13 because its current PyO3 release
does not support Python 3.14; `uv` downloads 3.13 when necessary. Never copy
`.venv`, `target`, or native extension files between macOS ARM and Linux x86-64.

Before starting a campaign, update and verify the checkout:

```nu
git pull --ff-only
if (git status --porcelain | str trim | is-not-empty) {
    error make {msg: "working tree is dirty"}
}
```

Run experiments from `organism-sim` so their relative output paths remain
consistent:

```nu
cd organism-sim
nu experiments/run_dynamic_chemistry.nu
```

## Central results

The initial central store is the experiment machine:

```text
/home/jojo/bio-sim-results/<source-machine>/<run-id>/
```

Published directories are append-only. The publishing utility refuses to
replace an existing run ID and uses a hidden `.partial` directory until transfer
completion.

From the Mac:

```nu
$env.BIO_SIM_RESULTS_DESTINATION = "jojo@100.80.185.9:/home/jojo/bio-sim-results"
nu tools/publish_experiment.nu organism-sim/runs/<run-id>
```

From the experiment machine itself:

```nu
$env.BIO_SIM_RESULTS_DESTINATION = "/home/jojo/bio-sim-results"
nu tools/publish_experiment.nu organism-sim/runs/<run-id>
```

You can also pass `--destination` explicitly. Every publication includes a
`PUBLISHED.json` file containing source-machine, timestamp, Git commit, branch,
and dirty-tree status. Publish from a clean checkout whenever possible.

The central directory is not a backup. Back it up separately before relying on
it as the sole copy of important results.
