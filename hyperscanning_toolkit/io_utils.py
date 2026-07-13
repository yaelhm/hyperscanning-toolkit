from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


def load_table(path: Path) -> Optional[pd.DataFrame]:
    """Load a .csv/.xlsx/.xls file into a DataFrame, or None on failure."""
    try:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            return pd.read_csv(path)
        if suffix in (".xlsx", ".xls"):
            return pd.read_excel(path, engine="openpyxl" if suffix == ".xlsx" else None)
        print(f"    ERROR: Unsupported file type {path.suffix} ({path.name})")
        return None
    except Exception as e:
        print(f"    ERROR loading {path.name}: {e}")
        return None
