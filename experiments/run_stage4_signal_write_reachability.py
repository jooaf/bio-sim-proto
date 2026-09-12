"""Run the preregistered fully connected signal-write positive control."""

from __future__ import annotations

import argparse
from pathlib import Path

from experiments.run_stage4_signal_write import run_campaign

SEEDS = range(202609280, 202609285)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "config", nargs="?", type=Path,
        default=Path("experiments/configs/stage4_signal_write_reachability.toml"),
    )
    parser.add_argument(
        "--output-root", type=Path,
        default=Path("sweeps/stage4_signal_write_reachability"),
    )
    args = parser.parse_args()
    print(run_campaign(args.config, args.output_root, SEEDS))


if __name__ == "__main__":
    main()
