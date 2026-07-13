from __future__ import annotations

from itertools import combinations
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

from .config import ThresholdConfig

EDGE_COLUMNS = ["source", "target", "weight", "raw_r", "p_value", "significant"]


def _correlate(ts1: np.ndarray, ts2: np.ndarray) -> Optional[Tuple[float, float]]:
    min_len = min(len(ts1), len(ts2))
    if min_len < 3:
        return None
    try:
        r, p_value = pearsonr(ts1[:min_len], ts2[:min_len])
    except Exception as e:
        print(f"    WARNING: Could not compute correlation: {e}")
        return None
    return float(r), float(p_value)


def _finalize_edge_table(all_edges: list, thresholds: ThresholdConfig) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if not all_edges:
        empty = pd.DataFrame(columns=EDGE_COLUMNS)
        return empty, empty.copy()

    edge_table = pd.DataFrame(all_edges)
    edge_table["significant"] = (
        (edge_table["p_value"] < thresholds.p_threshold)
        & (edge_table["raw_r"] > thresholds.r_threshold)
    )
    edge_table["weight"] = edge_table["raw_r"].where(edge_table["significant"], other=0.0)
    edge_table = edge_table[EDGE_COLUMNS]
    significant_edges = edge_table[edge_table["significant"]].copy()
    return edge_table, significant_edges


def compute_interbrain_connectivity(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    channels1: List[str],
    channels2: List[str],
    label1: str,
    label2: str,
    thresholds: ThresholdConfig,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Fully connected inter-brain/inter-participant connectivity: all channels1 x channels2 pairs."""
    all_edges = []
    for ch1 in channels1:
        ts1 = df1[ch1].values
        for ch2 in channels2:
            ts2 = df2[ch2].values
            res = _correlate(ts1, ts2)
            if res is None:
                continue
            r, p_value = res
            all_edges.append({
                "source": f"{label1}_{ch1}",
                "target": f"{label2}_{ch2}",
                "raw_r": r,
                "p_value": p_value,
            })
    return _finalize_edge_table(all_edges, thresholds)


def compute_intrabrain_connectivity(
    df: pd.DataFrame,
    channels: List[str],
    label: str,
    thresholds: ThresholdConfig,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Within-participant connectivity: all unique channel_i x channel_j pairs, i < j."""
    all_edges = []
    for ch1, ch2 in combinations(channels, 2):
        res = _correlate(df[ch1].values, df[ch2].values)
        if res is None:
            continue
        r, p_value = res
        all_edges.append({
            "source": f"{label}_{ch1}",
            "target": f"{label}_{ch2}",
            "raw_r": r,
            "p_value": p_value,
        })
    return _finalize_edge_table(all_edges, thresholds)
