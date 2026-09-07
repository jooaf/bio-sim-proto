# Shared commands for macOS and the remote experiment machine.
# Run `just` or `just --list` to see this menu.

set shell := ["nu", "-c"]

remote_host := "jojo@100.80.185.9"
remote_session := "bio-sim"

# List available commands.
default:
    just --list

# Show checkout and tool versions.
status:
    print "== git =="; git status --short --branch; print "== tools =="; nu --version; uv --version; just --version; if ("organism-sim/.venv/bin/python" | path exists) { organism-sim/.venv/bin/python --version }

# Pull source without creating a merge commit.
pull:
    git pull --ff-only

# Create/update the Python environment and native Rust extension for this machine.
setup:
    nu organism-sim/rust/install_release.nu

# Pull source, synchronize dependencies, and rebuild the native extension.
refresh:
    git pull --ff-only; nu organism-sim/rust/install_release.nu

# Run both project test suites.
test:
    uv run --group dev pytest; uv run --project organism-sim --group dev pytest organism-sim/tests

# Run a short native-engine experiment. Usage: just smoke [ticks] [seed]
smoke ticks="100" seed="7":
    uv run --project organism-sim organism-sim-headless --engine rust --ticks {{ticks}} --seed {{seed}} --progress-every 0 --runs-dir organism-sim/runs

# Run the dynamic-chemistry campaign. Usage: just dynamic [ticks] [seeds] [threads]
dynamic ticks="4000" seeds="100,101,102,103,104" threads="4":
    cd organism-sim; nu experiments/run_dynamic_chemistry.nu --ticks {{ticks}} --seeds "{{seeds}}" --threads {{threads}}

# Publish one completed run using BIO_SIM_RESULTS_DESTINATION.
publish run_dir:
    nu tools/publish_experiment.nu "{{run_dir}}"

# Publish one completed run to an explicit local or SSH destination.
publish-to run_dir destination:
    nu tools/publish_experiment.nu "{{run_dir}}" --destination "{{destination}}"

# Start or attach to the local Herdr session on the current machine.
herdr session=remote_session:
    herdr --session "{{session}}"

# Attach local Herdr to the remote machine. Usage: just herdr-remote [target] [session]
herdr-remote target=remote_host session=remote_session:
    herdr --remote "{{target}}" --session "{{session}}"
