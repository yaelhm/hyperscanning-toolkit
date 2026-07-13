from __future__ import annotations

import re
from typing import List

import pandas as pd

from .config import ChannelConfig


def select_channels(df: pd.DataFrame, cfg: ChannelConfig) -> List[str]:
    """Return the ordered list of column names in `df` that count as signal channels."""
    if cfg.mode == "explicit":
        if not cfg.columns:
            raise ValueError("channels.mode == 'explicit' requires 'columns' to be set")
        return [c for c in cfg.columns if c in df.columns]

    if cfg.mode == "regex":
        if not cfg.pattern:
            raise ValueError("channels.mode == 'regex' requires 'pattern' to be set")
        regex = re.compile(cfg.pattern)
        return [c for c in df.columns if regex.match(str(c))]

    if cfg.mode == "auto":
        exclude = set(cfg.exclude)
        return [
            c for c in df.columns
            if c not in exclude and pd.api.types.is_numeric_dtype(df[c])
        ]

    raise ValueError(f"Unknown channels.mode: {cfg.mode!r}")
