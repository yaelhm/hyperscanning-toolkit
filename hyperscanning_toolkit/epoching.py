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
from typing import List, Optional, Tuple

import pandas as pd

from .config import EpochingConfig


def extract_epochs(df: pd.DataFrame, cfg: EpochingConfig) -> Tuple[Optional[pd.DataFrame], List[str]]:
    """Restrict `df` to the rows of interest for connectivity analysis.

    Returns (filtered_df, epoch_names). filtered_df is None if no rows survive.
    """
    if cfg.mode == "none":
        return df, []

    if cfg.mode == "fixed_window":
        if not cfg.window_size or cfg.window_size <= 0:
            raise ValueError("epoching.mode == 'fixed_window' requires a positive 'window_size'")
        n_rows = (len(df) // cfg.window_size) * cfg.window_size
        if n_rows == 0:
            return None, []
        return df.iloc[:n_rows].copy(), []

    if cfg.mode == "event_marker":
        return _extract_event_marker_epochs(df, cfg)

    raise ValueError(f"Unknown epoching.mode: {cfg.mode!r}")


def _extract_event_marker_epochs(df: pd.DataFrame, cfg: EpochingConfig):
    if not cfg.start_column or not cfg.end_column or not cfg.start_pattern or not cfg.end_pattern:
        raise ValueError(
            "epoching.mode == 'event_marker' requires start_column, end_column, "
            "start_pattern and end_pattern"
        )
    if cfg.start_column not in df.columns or cfg.end_column not in df.columns:
        print(f"    WARNING: {cfg.start_column!r}/{cfg.end_column!r} columns not found.")
        return None, []

    start_re = re.compile(cfg.start_pattern)
    end_re = re.compile(cfg.end_pattern)

    valid_rows = []
    epoch_names_found = set()

    for idx, row in df.iterrows():
        start_val = str(row[cfg.start_column]) if pd.notna(row[cfg.start_column]) else ""
        end_val = str(row[cfg.end_column]) if pd.notna(row[cfg.end_column]) else ""

        m_start = start_re.match(start_val)
        if not m_start:
            continue
        m_end = end_re.match(end_val)
        if not m_end:
            continue

        # If both patterns capture a group (e.g. an epoch number), they must agree.
        if m_start.groups() and m_end.groups() and m_start.group(1) != m_end.group(1):
            continue

        valid_rows.append(idx)
        epoch_names_found.add(start_val)

    if not valid_rows:
        return None, []

    filtered_df = df.loc[valid_rows].copy()
    return filtered_df, sorted(epoch_names_found)
