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

from typing import List

import numpy as np
import pandas as pd


def scan_channel_quality(df: pd.DataFrame, channels: List[str]) -> dict:
    """Inspect channel columns for data-quality issues *before* connectivity is computed.

    Purely diagnostic: does not filter or alter `channels` — every channel is still
    passed to correlation unchanged, so this cannot change any mathematical result.

    Returns:
        {
            "constant_channels": [...],  # has finite data, but zero variance
            "nan_channels": [...],       # 100% non-finite (NaN/Inf) values
            "all_channels_nan": bool,    # every requested channel is fully non-finite
        }
    """
    constant_channels = []
    nan_channels = []

    for ch in channels:
        if ch not in df.columns:
            continue
        values = pd.to_numeric(df[ch], errors="coerce").values
        finite = np.isfinite(values)
        if not finite.any():
            nan_channels.append(ch)
            continue
        finite_vals = values[finite]
        # Use numpy's standard relative+absolute tolerance rather than exact equality:
        # a "constant" signal that has round-tripped through CSV text or any floating-point
        # arithmetic will have a std of ~1e-16 (machine epsilon), not exactly 0.0.
        if np.allclose(finite_vals, finite_vals[0]):
            constant_channels.append(ch)

    all_channels_nan = len(channels) > 0 and len(nan_channels) == len(channels)

    return {
        "constant_channels": constant_channels,
        "nan_channels": nan_channels,
        "all_channels_nan": all_channels_nan,
    }


def count_failed_pairs(edge_table: pd.DataFrame, expected_n_pairs: int) -> int:
    """Number of channel pairs that did not yield a usable correlation.

    Two ways a pair can fail, given connectivity._correlate()'s behavior:
      - it's entirely absent from edge_table (an exception was raised, e.g. too few
        finite samples or a fully non-finite pair), OR
      - it's present but raw_r is NaN (scipy returns (nan, nan) without raising for a
        zero-variance / constant-input pair).
    """
    if expected_n_pairs == 0:
        return 0
    missing = expected_n_pairs - len(edge_table)
    nan_present = int(edge_table["raw_r"].isna().sum()) if len(edge_table) else 0
    return int(missing) + nan_present
