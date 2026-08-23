# Run the preregistered conservation-aware SKI multiplier matrix.

def main [] {
    $nu.pid | into string | save --force .phase1-ski-validation.pid
    ^uv run soup-run sweep experiments/sweeps/p1_ski_validation.toml
    if $env.LAST_EXIT_CODE != 0 {
        error make {msg: $"SKI validation sweep failed with exit code ($env.LAST_EXIT_CODE)"}
    }
}
