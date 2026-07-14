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

---

End-to-end test proving the toolkit is data-agnostic: it uses made-up
column names, a made-up epoch-marker scheme, and a made-up folder layout
that have nothing to do with the fNIRS/NFB lab example.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hyperscanning_toolkit import __version__
from hyperscanning_toolkit.config import ToolkitConfig
from hyperscanning_toolkit.pipeline import run_all

N_ROWS = 50
N_VALID = 40  # first N_VALID rows carry a matching start/end marker pair


def _make_participant_df(rng: np.random.Generator, base_signal: np.ndarray) -> pd.DataFrame:
    sig_x = base_signal + rng.normal(scale=0.01, size=N_ROWS)
    sig_y = sig_x + rng.normal(scale=0.01, size=N_ROWS)  # strongly correlated with sig_x
    sig_z = -sig_x + rng.normal(scale=0.01, size=N_ROWS)  # anti-correlated with sig_x

    marker_start = ["EPOCH1" if i < N_VALID else "" for i in range(N_ROWS)]
    marker_end = ["EPOCH1_END" if i < N_VALID else "" for i in range(N_ROWS)]

    return pd.DataFrame({
        "sig_x": sig_x,
        "sig_y": sig_y,
        "sig_z": sig_z,
        "marker_start": marker_start,
        "marker_end": marker_end,
    })


@pytest.fixture
def dataset_root(tmp_path: Path) -> Path:
    rng = np.random.default_rng(42)
    base_signal = np.linspace(0, 10, N_ROWS)

    session_dir = tmp_path / "data" / "GroupA" / "pair_0001" / "rec_01"
    session_dir.mkdir(parents=True)

    df_a = _make_participant_df(rng, base_signal)
    df_b = _make_participant_df(rng, base_signal)  # correlated with A too -> inter-brain edges

    df_a.to_csv(session_dir / "participant_alpha.csv", index=False)
    df_b.to_csv(session_dir / "participant_beta.csv", index=False)

    return tmp_path


@pytest.fixture
def cfg(dataset_root: Path) -> ToolkitConfig:
    return ToolkitConfig.from_dict({
        "channels": {"mode": "auto", "exclude": ["marker_start", "marker_end"]},
        "epoching": {
            "mode": "event_marker",
            "start_column": "marker_start",
            "end_column": "marker_end",
            "start_pattern": r"^EPOCH(\d+)$",
            "end_pattern": r"^EPOCH(\d+)_END$",
        },
        "discovery": {
            "root": str(dataset_root / "data"),
            "session_glob": "*/pair_*/rec_*",
            "level_names": ["group", "pair", "recording"],
            "file_glob": "participant_*.csv",
            "filename_subject_regex": r"participant_(\w+)",
        },
        "thresholds": {"p_threshold": 0.05, "r_threshold": 0.0},
        "output_dir": str(dataset_root / "outputs"),
    })


def test_pipeline_is_data_agnostic(dataset_root: Path, cfg: ToolkitConfig):
    result = run_all(cfg)

    out = dataset_root / "outputs"

    # Step "inspect": found the right channels for a non-fNIRS column scheme.
    inspection = pd.read_csv(out / "channel_inspection" / "valid_channels_all_sessions.csv")
    assert len(inspection) == 2
    assert set(inspection["n_channels"]) == {3}

    # Step "extract": event-marker epoching kept exactly the valid rows.
    epoch_summary = pd.read_csv(out / "cleaned_epochs" / "epoch_summary.csv")
    assert len(epoch_summary) == 2
    assert (epoch_summary["n_kept_rows"] == N_VALID).all()

    cleaned_files = sorted((out / "cleaned_epochs").glob("*__cleaned.csv"))
    assert len(cleaned_files) == 2

    # Step "graphs": one intra-brain graph per participant, one inter-brain pair.
    intra_df = result["intra"]
    inter_df = result["inter"]
    assert len(intra_df) == 2
    assert len(inter_df) == 1

    # sig_x/sig_y are positively correlated by construction -> at least one
    # significant intra-brain edge per participant.
    assert (intra_df["number_of_edges"] > 0).all()
    # sig_x is shared (with noise) between participants -> at least one
    # significant inter-brain edge.
    assert (inter_df["number_of_edges"] > 0).all()

    intra_dir = out / "graphs" / "intra" / "GroupA" / "pair_0001" / "rec_01"
    subject_dirs = sorted(p for p in intra_dir.iterdir() if p.is_dir())
    assert len(subject_dirs) == 2
    for subject_dir in subject_dirs:
        adj = pd.read_csv(subject_dir / "adjacency_matrix.csv", index_col=0)
        assert adj.shape == (3, 3)
        for fname in ("all_tested_edges.csv", "edge_table.csv", "graph_metrics.csv", "node_metrics.csv", "run_metadata.json"):
            assert (subject_dir / fname).exists()
        metadata = json.loads((subject_dir / "run_metadata.json").read_text())
        assert metadata["toolkit_version"] == __version__
        assert metadata["graph_type"] == "intra"
        assert metadata["connectivity_method"] == "pearson_correlation"

    inter_dir = out / "graphs" / "inter" / "GroupA" / "pair_0001" / "rec_01"
    pair_dirs = list(inter_dir.iterdir())
    assert len(pair_dirs) == 1
    adj = pd.read_csv(pair_dirs[0] / "adjacency_matrix.csv", index_col=0)
    assert adj.shape == (6, 6)  # 3 channels x 2 participants
    inter_metadata = json.loads((pair_dirs[0] / "run_metadata.json").read_text())
    assert inter_metadata["graph_type"] == "inter"
    assert inter_metadata["participant_count"] == 2

    # Run summary carries the version and sane aggregate counts.
    run_summary = result["summary"]
    assert run_summary.toolkit_version == __version__
    assert run_summary.n_intra_graphs == 2
    assert run_summary.n_inter_graphs == 1
