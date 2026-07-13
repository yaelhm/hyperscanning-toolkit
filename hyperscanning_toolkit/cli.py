from __future__ import annotations

import argparse
import sys

from .config import ToolkitConfig
from .pipeline import run_all, run_extract, run_graphs, run_inspect


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hyperscanning-toolkit")
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
