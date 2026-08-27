#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required to build/install the Rust kernel" >&2
  exit 1
fi

uv sync --project "$ROOT" --group dev
# This script installs a machine-local research build, so allow LLVM to use
# the host CPU's instruction set. Override RUSTFLAGS to build a portable wheel.
export RUSTFLAGS="${RUSTFLAGS:--C target-cpu=native}"
FEATURES="${ORGANISM_SIM_RUST_FEATURES:-python-module,simd-neural}"
uv run --project "$ROOT" --group dev maturin develop \
  --manifest-path "$ROOT/rust/Cargo.toml" \
  --release \
  --features "$FEATURES" \
  --uv
