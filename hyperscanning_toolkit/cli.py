"""
Hyperscanning Toolkit

Copyright (c) 2026 Dr. Yael Hodaya Moshe.

Lead Developer:
    Dr. Yael Hodaya Moshe

Developed in collaboration with the Social Neuroscience Lab.

Scientific Supervision:
    Dr. Hila Gvirts
    Dr. Anat Dahan

This file is part of the Hyperscanning Toolkit.
"""

from __future__ import annotations

import argparse
import sys

from ._version import __version__
from .config import ToolkitConfig
from .pipeline import run_all, run_extract, run_graphs, run_inspect


ATTRIBUTION_BLOCK = (
    "Lead Developer: Dr. Yael Hodaya Moshe\n"
    "Scientific Supervision: Dr. Hila Gvirts and Dr. Anat Dahan"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hyperscanning-toolkit",
        epilog=ATTRIBUTION_BLOCK,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"hyperscanning-toolkit {__version__}")
    parser.add_argument("--config", required=True, help="Path to a YAML config file")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("inspect", help="Scan the data root and report channels/rows per file")
    subparsers.add_parser("extract", help="Apply the configured epoching strategy and save cleaned CSVs")
    subparsers.add_parser("graphs", help="Build inter-brain and intra-brain graphs from cleaned CSVs")
    subparsers.add_parser("run", help="Run inspect -> extract -> graphs in sequence")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    print(f"Hyperscanning Toolkit v{__version__}")
    print(ATTRIBUTION_BLOCK)
    cfg = ToolkitConfig.from_yaml(args.config)

    if args.command == "inspect":
        run_inspect(cfg)
    elif args.command == "extract":
        run_extract(cfg)
    elif args.command == "graphs":
        run_graphs(cfg)
    elif args.command == "run":
        run_all(cfg)
    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
