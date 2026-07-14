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

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ._version import __version__


@dataclass
class RunSummary:
    """Aggregate counters for one end-to-end pipeline run (inspect + extract + graphs).

    Discovery-derived fields (n_discovered_sessions, n_participant_files,
    duplicate_subjects) are *set* fresh each time discovery runs rather than
    accumulated, since run_inspect/run_extract/run_graphs each independently
    call discover_sessions() on the same data and would otherwise double-count.
    """

    toolkit_version: str = __version__
    start_time: float = field(default_factory=time.perf_counter)
    end_time: Optional[float] = None

    n_discovered_sessions: int = 0
    n_participant_files: int = 0
    n_processed_sessions: int = 0
    n_skipped_sessions: int = 0

    n_intra_graphs: int = 0
    n_inter_graphs: int = 0

    n_failed_correlations: int = 0
    n_nan_files: int = 0
    n_constant_channels: int = 0

    duplicate_subjects: List[Dict[str, Any]] = field(default_factory=list)
    nan_file_details: List[Dict[str, Any]] = field(default_factory=list)
    constant_channel_details: List[Dict[str, Any]] = field(default_factory=list)
    skipped_session_details: List[Dict[str, Any]] = field(default_factory=list)

    def finish(self) -> None:
        self.end_time = time.perf_counter()

    @property
    def total_runtime_seconds(self) -> float:
        end = self.end_time if self.end_time is not None else time.perf_counter()
        return end - self.start_time

    def set_discovery(self, sessions) -> None:
        """Refresh discovery-derived counts/details from a discover_sessions() result."""
        self.n_discovered_sessions = len(sessions)
        self.n_participant_files = sum(len(s.files) for s in sessions)
        self.duplicate_subjects = [
            {
                "session": s.label,
                "subject_id": d.subject_id,
                "kept_file": d.kept_path.name,
                "skipped_file": d.path.name,
            }
            for s in sessions
            for d in s.duplicate_files
        ]

    def record_channel_quality(self, levels: Dict[str, str], subject_id: str, quality: dict) -> None:
        label = "/".join(list(levels.values()) + [f"subject_{subject_id}"])
        if quality["all_channels_nan"]:
            self.n_nan_files += 1
            self.nan_file_details.append({"session": label, "subject": subject_id, **levels})
        for ch in quality["constant_channels"]:
            self.n_constant_channels += 1
            self.constant_channel_details.append({"session": label, "subject": subject_id, "channel": ch, **levels})

    def record_skipped_session(self, levels: Dict[str, str], reason: str) -> None:
        self.n_skipped_sessions += 1
        self.skipped_session_details.append({"session": "/".join(levels.values()), "reason": reason})

    def to_dict(self) -> dict:
        return {
            "toolkit_version": self.toolkit_version,
            "total_runtime_seconds": self.total_runtime_seconds,
            "n_discovered_sessions": self.n_discovered_sessions,
            "n_participant_files": self.n_participant_files,
            "n_processed_sessions": self.n_processed_sessions,
            "n_skipped_sessions": self.n_skipped_sessions,
            "n_intra_graphs": self.n_intra_graphs,
            "n_inter_graphs": self.n_inter_graphs,
            "n_failed_correlations": self.n_failed_correlations,
            "n_nan_files": self.n_nan_files,
            "n_constant_channels": self.n_constant_channels,
            "n_duplicate_subjects": len(self.duplicate_subjects),
        }

    def render(self) -> str:
        lines = [
            "",
            "=" * 70,
            "RUN SUMMARY",
            "=" * 70,
            f"Toolkit version           : {self.toolkit_version}",
            f"Discovered sessions       : {self.n_discovered_sessions}",
            f"Processed sessions        : {self.n_processed_sessions}",
            f"Skipped sessions          : {self.n_skipped_sessions}",
            f"Participant files         : {self.n_participant_files}",
            f"Intra-brain graphs built  : {self.n_intra_graphs}",
            f"Inter-brain graphs built  : {self.n_inter_graphs}",
            f"Failed correlations       : {self.n_failed_correlations}",
            f"All-NaN participant files : {self.n_nan_files}",
            f"Constant (zero-variance) channels : {self.n_constant_channels}",
            f"Duplicate subject_id files skipped: {len(self.duplicate_subjects)}",
            f"Total runtime              : {self.total_runtime_seconds:.2f}s",
            "=" * 70,
        ]
        if self.duplicate_subjects:
            lines.append("Duplicate subjects:")
            for d in self.duplicate_subjects:
                lines.append(f"  - {d['session']}: subject_id={d['subject_id']!r} "
                              f"kept={d['kept_file']} skipped={d['skipped_file']}")
        if self.nan_file_details:
            lines.append("All-NaN participant files:")
            for d in self.nan_file_details:
                lines.append(f"  - {d['session']}")
        if self.constant_channel_details:
            lines.append(f"Constant channels ({len(self.constant_channel_details)} total):")
            for d in self.constant_channel_details[:20]:
                lines.append(f"  - {d['session']} / {d['channel']}")
            if len(self.constant_channel_details) > 20:
                lines.append(f"  ... and {len(self.constant_channel_details) - 20} more")
        if self.skipped_session_details:
            lines.append("Skipped sessions:")
            for d in self.skipped_session_details:
                lines.append(f"  - {d['session']}: {d['reason']}")
        return "\n".join(lines)
