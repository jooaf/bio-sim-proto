# Build and install the machine-local optimized Rust kernel.
#
# Use --scalar-neural to retain the exact pre-SIMD recurrent floating-point path.
def main [
    --scalar-neural # Disable the AArch64 NEON neural dot-product feature.
] {
    let root = ($env.FILE_PWD | path dirname)
    if (which uv | is-empty) {
        error make {msg: "uv is required to build/install the Rust kernel"}
    }

    uv sync --project $root --group dev
    let rustflags = ($env.RUSTFLAGS? | default "-C target-cpu=native")
    let manifest = ($root | path join "rust" "Cargo.toml")
    let features = if $scalar_neural {
        "python-module"
    } else {
        "python-module,simd-neural"
    }
    with-env {RUSTFLAGS: $rustflags} {
        uv run --project $root --group dev maturin develop --manifest-path $manifest --release --features $features --uv
    }
}
