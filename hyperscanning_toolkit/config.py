from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml


@dataclass
class ChannelConfig:
    """How to select signal/channel columns out of a loaded table.

    mode:
        "regex"    - columns whose name matches `pattern` are channels.
        "explicit" - `columns` is the exact list of channel names.
        "auto"     - every numeric column not in `exclude` is a channel.
    """

    mode: str = "auto"
    pattern: Optional[str] = None
    columns: Optional[List[str]] = None
    exclude: List[str] = field(default_factory=list)


@dataclass
class EpochingConfig:
    """How to restrict a loaded table to the rows of interest before connectivity is computed.

    mode:
        "none"         - use every row as-is.
        "fixed_window" - keep the first N rows that divide evenly into `window_size`-row blocks.
        "event_marker" - keep rows where `start_column`/`end_column` match a paired
                         start/end marker, e.g. StartEvent="NFB3", EndEvent="NFB3_End".
                         `start_pattern`/`end_pattern` are regexes; if both have a capturing
                         group, the captured values must match for the row to be kept.
    """

    mode: str = "none"
    start_column: Optional[str] = None
    end_column: Optional[str] = None
    start_pattern: Optional[str] = None
    end_pattern: Optional[str] = None
    window_size: Optional[int] = None


@dataclass
class DiscoveryConfig:
    """How to find participant files under a data root and label them.

    `session_glob` is a glob (relative to `root`) whose matched directories each
    represent one recording session; the directory's path parts relative to
    `root` are labelled left-to-right using `level_names`.

    `file_glob` finds participant files inside each session directory;
    `filename_subject_regex` pulls the subject/participant id out of each
    filename's stem (first capturing group).
    """

    root: str = "data"
    session_glob: str = "*/dyad_*/session_*"
    level_names: List[str] = field(default_factory=lambda: ["condition", "dyad", "session"])
    file_glob: str = "subject_*.xlsx"
    filename_subject_regex: str = r"subject_(\d+)"


@dataclass
class ThresholdConfig:
    p_threshold: float = 0.05
    r_threshold: float = 0.0


@dataclass
class ToolkitConfig:
    channels: ChannelConfig = field(default_factory=ChannelConfig)
    epoching: EpochingConfig = field(default_factory=EpochingConfig)
    discovery: DiscoveryConfig = field(default_factory=DiscoveryConfig)
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)
    output_dir: str = "outputs"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolkitConfig":
        data = dict(data or {})
        return cls(
            channels=ChannelConfig(**data.get("channels", {})),
            epoching=EpochingConfig(**data.get("epoching", {})),
            discovery=DiscoveryConfig(**data.get("discovery", {})),
            thresholds=ThresholdConfig(**data.get("thresholds", {})),
            output_dir=data.get("output_dir", "outputs"),
        )

    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> "ToolkitConfig":
        """Load a config from YAML. Relative `discovery.root` and `output_dir`
        paths in the file are resolved relative to the config file's own
        directory (not the current working directory), so a config works the
        same regardless of where the CLI is invoked from.
        """
        path = Path(path)
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        cfg = cls.from_dict(data)

        base_dir = path.resolve().parent
        cfg.discovery.root = str(_resolve_relative(cfg.discovery.root, base_dir))
        cfg.output_dir = str(_resolve_relative(cfg.output_dir, base_dir))
        return cfg


def _resolve_relative(value: str, base_dir: Path) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (base_dir / p).resolve()
