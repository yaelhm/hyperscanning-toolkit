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

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from .config import DiscoveryConfig

CLEANED_SEP = "__"
CLEANED_SUFFIX = f"{CLEANED_SEP}cleaned.csv"


@dataclass
class ParticipantFile:
    path: Path
    subject_id: str


@dataclass
class DuplicateSubjectFile:
    """A file that was skipped because its subject_id already matched another file in the same session."""
    path: Path
    subject_id: str
    kept_path: Path


@dataclass
class SessionRecord:
    levels: Dict[str, str]
    session_dir: Path
    files: List[ParticipantFile]
    duplicate_files: List[DuplicateSubjectFile] = field(default_factory=list)

    @property
    def label(self) -> str:
        return "/".join(self.levels.values())


def discover_sessions(cfg: DiscoveryConfig) -> List[SessionRecord]:
    """Find session directories under cfg.root and the participant files in each.

    A session directory's path relative to `root` is split into parts and
    labelled left-to-right using `cfg.level_names` (e.g. condition/dyad/session).

    If two or more files in the same session resolve to the same subject_id
    (an ambiguous `filename_subject_regex` for that dataset), the first file
    found (sorted order) is kept and every later colliding file is skipped
    with a printed warning and recorded in `SessionRecord.duplicate_files`,
    rather than silently overwriting each other downstream.
    """
    root = Path(cfg.root)
    if not root.exists():
        return []

    subject_regex = re.compile(cfg.filename_subject_regex)
    records: List[SessionRecord] = []

    for session_dir in sorted(root.glob(cfg.session_glob)):
        if not session_dir.is_dir():
            continue

        rel_parts = session_dir.relative_to(root).parts
        levels = dict(zip(cfg.level_names, rel_parts))

        files: List[ParticipantFile] = []
        duplicates: List[DuplicateSubjectFile] = []
        seen: Dict[str, Path] = {}
        for f in sorted(session_dir.glob(cfg.file_glob)):
            m = subject_regex.search(f.stem)
            if not m:
                continue
            subject_id = m.group(1)
            if subject_id in seen:
                print(
                    f"  WARNING: duplicate subject_id {subject_id!r} in "
                    f"{'/'.join(levels.values())}: keeping {seen[subject_id].name}, "
                    f"skipping {f.name}"
                )
                duplicates.append(DuplicateSubjectFile(path=f, subject_id=subject_id, kept_path=seen[subject_id]))
                continue
            files.append(ParticipantFile(path=f, subject_id=subject_id))
            seen[subject_id] = f

        if files or duplicates:
            records.append(SessionRecord(levels=levels, session_dir=session_dir, files=files, duplicate_files=duplicates))

    return records


def cleaned_filename(levels: Dict[str, str], subject_id: str) -> str:
    parts = list(levels.values()) + [f"subject_{subject_id}"]
    return CLEANED_SEP.join(parts) + CLEANED_SUFFIX


def parse_cleaned_filename(filename: str, level_names: List[str]):
    """Inverse of cleaned_filename. Returns (levels, subject_id) or None if it doesn't match."""
    if not filename.endswith(CLEANED_SUFFIX):
        return None
    stem = filename[: -len(CLEANED_SUFFIX)]
    parts = stem.split(CLEANED_SEP)
    if len(parts) != len(level_names) + 1:
        return None
    *level_values, subject_part = parts
    m = re.match(r"subject_(.+)", subject_part)
    if not m:
        return None
    return dict(zip(level_names, level_values)), m.group(1)
