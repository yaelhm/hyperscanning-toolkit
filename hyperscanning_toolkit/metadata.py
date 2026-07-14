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

import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from ._version import __version__


def _package_version(module_name: str) -> str:
    try:
        from importlib.metadata import version
        return version(module_name)
    except Exception:
        try:
            mod = __import__(module_name)
            return getattr(mod, "__version__", "unknown")
        except Exception:
            return "unknown"


def _git_commit() -> Optional[str]:
    """Short git commit hash of the toolkit's own repo, if it is one. None otherwise -- never raises."""
    try:
        repo_dir = Path(__file__).resolve().parent.parent
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_dir, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_environment_info() -> dict:
    """Environment/dependency versions, computed once per run and shared across all graphs."""
    return {
        "python_version": platform.python_version(),
        "operating_system": platform.platform(),
        "numpy_version": _package_version("numpy"),
        "scipy_version": _package_version("scipy"),
        "networkx_version": _package_version("networkx"),
        "pandas_version": _package_version("pandas"),
        "hyperscanning_toolkit_version": __version__,
        "hyperscanning_toolkit_git_commit": _git_commit(),
    }


def get_run_context() -> dict:
    """Facts about *how* this process was invoked, computed once per run."""
    return {
        "command_used": " ".join(sys.argv),
    }


def build_graph_run_metadata(
    cfg,
    run_context: dict,
    environment_info: dict,
    graph_type: str,
    session_identifier: str,
    channels_by_participant: Dict[str, List[str]],
    output_directory: Path,
) -> dict:
    """Assemble the full run_metadata.json contents for one graph output directory.

    `channels_by_participant` maps a participant label (e.g. "subject_baby") to the
    ordered list of channel names tested for that participant -- one entry for intra-brain
    graphs, two for inter-brain graphs.
    """
    from datetime import datetime

    now = datetime.now()

    return {
        "toolkit_version": environment_info["hyperscanning_toolkit_version"],
        "hyperscanning_toolkit_git_commit": environment_info["hyperscanning_toolkit_git_commit"],
        "execution_date": now.strftime("%Y-%m-%d"),
        "execution_time": now.strftime("%H:%M:%S"),
        "command_used": run_context["command_used"],
        "configuration_file": cfg.config_path,
        "graph_type": graph_type,
        "session_identifier": session_identifier,
        "participant_count": len(channels_by_participant),
        "number_of_channels": {p: len(chs) for p, chs in channels_by_participant.items()},
        "channels": channels_by_participant,
        "connectivity_method": "pearson_correlation",
        "threshold_parameters": {
            "p_threshold": cfg.thresholds.p_threshold,
            "r_threshold": cfg.thresholds.r_threshold,
        },
        "channel_selection": {
            "mode": cfg.channels.mode,
            "pattern": cfg.channels.pattern,
            "columns": cfg.channels.columns,
            "exclude": cfg.channels.exclude,
        },
        "epoching": {
            "mode": cfg.epoching.mode,
            "window_size": cfg.epoching.window_size,
        },
        "python_version": environment_info["python_version"],
        "operating_system": environment_info["operating_system"],
        "numpy_version": environment_info["numpy_version"],
        "scipy_version": environment_info["scipy_version"],
        "networkx_version": environment_info["networkx_version"],
        "pandas_version": environment_info["pandas_version"],
        "output_directory": str(output_directory),
    }


def write_run_metadata(metadata: dict, output_dir: Path) -> None:
    """Write run_metadata.json into output_dir. Lightweight, human-readable (indented) JSON."""
    with open(output_dir / "run_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=str)
