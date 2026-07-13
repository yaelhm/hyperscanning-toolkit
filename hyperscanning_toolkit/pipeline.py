from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Dict, Optional

import networkx as nx
import pandas as pd

from .channels import select_channels
from .config import ToolkitConfig
from .connectivity import compute_interbrain_connectivity, compute_intrabrain_connectivity
from .discovery import CLEANED_SUFFIX, cleaned_filename, discover_sessions, parse_cleaned_filename
from .epoching import extract_epochs
from .graphs import (
    build_graph,
    compute_interbrain_graph_metrics,
    compute_intrabrain_graph_metrics,
    compute_node_metrics,
    visualize_bipartite_graph,
    visualize_intrabrain_graph,
)
from .io_utils import load_table


def run_inspect(cfg: ToolkitConfig) -> pd.DataFrame:
    """Scan the data root and report, per participant file, how many channels/rows it has."""
    sessions = discover_sessions(cfg.discovery)
    if not sessions:
        print(f"No session folders found under {cfg.discovery.root!r} matching {cfg.discovery.session_glob!r}")

    rows = []
    for session in sessions:
        for pf in session.files:
            df = load_table(pf.path)
            if df is None:
                continue
            channels = select_channels(df, cfg.channels)
            print(f"{session.label}/subject_{pf.subject_id}: {df.shape[0]} rows x {df.shape[1]} cols, "
                  f"{len(channels)} channel(s)")
            rows.append({
                **session.levels,
                "subject": pf.subject_id,
                "file": pf.path.name,
                "n_rows": df.shape[0],
                "n_columns": df.shape[1],
                "n_channels": len(channels),
                "channels": "|".join(channels),
            })

    result = pd.DataFrame(rows)
    out_dir = Path(cfg.output_dir) / "channel_inspection"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "valid_channels_all_sessions.csv"
    result.to_csv(out_file, index=False)
    print(f"\nSaved: {out_file}")
    return result


def run_extract(cfg: ToolkitConfig) -> pd.DataFrame:
    """Apply the configured epoching strategy to every participant file and save cleaned CSVs."""
    sessions = discover_sessions(cfg.discovery)
    out_dir = Path(cfg.output_dir) / "cleaned_epochs"
    out_dir.mkdir(parents=True, exist_ok=True)

    summaries = []
    for session in sessions:
        for pf in session.files:
            df = load_table(pf.path)
            if df is None:
                continue

            filtered_df, epoch_names = extract_epochs(df, cfg.epoching)
            if filtered_df is None or len(filtered_df) == 0:
                print(f"  WARNING: no valid rows for {session.label}/subject_{pf.subject_id}, skipping.")
                continue

            out_name = cleaned_filename(session.levels, pf.subject_id)
            filtered_df.to_csv(out_dir / out_name, index=False)
            print(f"  Saved: {out_name} ({len(filtered_df)} rows)")

            summaries.append({
                **session.levels,
                "subject": pf.subject_id,
                "n_total_rows": len(df),
                "n_kept_rows": len(filtered_df),
                "n_epochs": len(epoch_names),
                "epoch_names": "|".join(epoch_names),
            })

    result = pd.DataFrame(summaries)
    summary_file = out_dir / "epoch_summary.csv"
    result.to_csv(summary_file, index=False)
    print(f"\nSaved: {summary_file}")
    return result


def _group_cleaned_files(cfg: ToolkitConfig) -> Dict[tuple, dict]:
    cleaned_dir = Path(cfg.output_dir) / "cleaned_epochs"
    groups: Dict[tuple, dict] = {}
    for f in sorted(cleaned_dir.glob(f"*{CLEANED_SUFFIX}")):
        parsed = parse_cleaned_filename(f.name, cfg.discovery.level_names)
        if parsed is None:
            print(f"  WARNING: unrecognized cleaned file name, skipping: {f.name}")
            continue
        levels, subject_id = parsed
        key = tuple(levels.values())
        group = groups.setdefault(key, {"levels": levels, "files": {}})
        group["files"][subject_id] = f
    return groups


def _build_intrabrain_graph(cfg: ToolkitConfig, levels: Dict[str, str], subject_id: str, df: pd.DataFrame, channels) -> Optional[dict]:
    label = f"S{subject_id}"
    edge_table, significant_edges = compute_intrabrain_connectivity(df, channels, label, cfg.thresholds)
    nodes = sorted(f"{label}_{ch}" for ch in channels)
    G = build_graph(significant_edges, {label: nodes})

    metrics = compute_intrabrain_graph_metrics(G, edge_table)
    node_metrics = compute_node_metrics(G, {n: label for n in nodes})

    out_dir = Path(cfg.output_dir) / "graphs" / "intra" / Path(*levels.values()) / f"subject_{subject_id}"
    out_dir.mkdir(parents=True, exist_ok=True)

    adj_matrix = pd.DataFrame(0.0, index=nodes, columns=nodes)
    for _, row in significant_edges.iterrows():
        adj_matrix.loc[row["source"], row["target"]] = row["weight"]
        adj_matrix.loc[row["target"], row["source"]] = row["weight"]
    adj_matrix.to_csv(out_dir / "adjacency_matrix.csv")
    edge_table.to_csv(out_dir / "all_tested_edges.csv", index=False)
    significant_edges[["source", "target", "weight", "raw_r", "p_value"]].to_csv(out_dir / "edge_table.csv", index=False)
    pd.DataFrame([metrics]).to_csv(out_dir / "graph_metrics.csv", index=False)
    node_metrics.to_csv(out_dir / "node_metrics.csv", index=False)

    viz_path = out_dir / "graph.png"
    visualize_intrabrain_graph(G, viz_path, title=f"Intra-brain connectivity — {'/'.join(levels.values())}/subject_{subject_id}")

    return {**levels, "subject": subject_id, "graph_type": "intra", **metrics}


def _build_interbrain_graph(cfg: ToolkitConfig, levels: Dict[str, str], s1: str, s2: str, df1: pd.DataFrame, df2: pd.DataFrame, channels1, channels2) -> Optional[dict]:
    label1, label2 = f"S{s1}", f"S{s2}"
    edge_table, significant_edges = compute_interbrain_connectivity(df1, df2, channels1, channels2, label1, label2, cfg.thresholds)

    group_a_nodes = sorted(f"{label1}_{ch}" for ch in channels1)
    group_b_nodes = sorted(f"{label2}_{ch}" for ch in channels2)
    G = build_graph(significant_edges, {label1: group_a_nodes, label2: group_b_nodes})

    metrics = compute_interbrain_graph_metrics(G, edge_table, group_a_nodes, group_b_nodes)
    node_participant = {n: label1 for n in group_a_nodes}
    node_participant.update({n: label2 for n in group_b_nodes})
    node_metrics = compute_node_metrics(G, node_participant)

    out_dir = Path(cfg.output_dir) / "graphs" / "inter" / Path(*levels.values()) / f"subject_{s1}_vs_subject_{s2}"
    out_dir.mkdir(parents=True, exist_ok=True)

    node_order = group_a_nodes + group_b_nodes
    adj_matrix = nx.to_pandas_adjacency(G, nodelist=node_order, weight="weight")
    adj_matrix.to_csv(out_dir / "adjacency_matrix.csv")
    edge_table.to_csv(out_dir / "all_tested_edges.csv", index=False)
    significant_edges[["source", "target", "weight", "raw_r", "p_value"]].to_csv(out_dir / "edge_table.csv", index=False)
    pd.DataFrame([metrics]).to_csv(out_dir / "graph_metrics.csv", index=False)
    node_metrics.to_csv(out_dir / "node_metrics.csv", index=False)

    viz_path = out_dir / "graph.png"
    visualize_bipartite_graph(
        G, group_a_nodes, group_b_nodes, viz_path,
        title=f"Inter-brain connectivity — {'/'.join(levels.values())}: subject_{s1} vs subject_{s2}",
    )

    return {**levels, "subject_a": s1, "subject_b": s2, "graph_type": "inter", **metrics}


def run_graphs(cfg: ToolkitConfig) -> Dict[str, pd.DataFrame]:
    """Build inter-brain (pairwise) and intra-brain graphs from the cleaned epoch files."""
    groups = _group_cleaned_files(cfg)
    if not groups:
        print(f"No cleaned files found under {Path(cfg.output_dir) / 'cleaned_epochs'}. Run 'extract' first.")
        return {"inter": pd.DataFrame(), "intra": pd.DataFrame()}

    inter_summaries = []
    intra_summaries = []

    for key, group in groups.items():
        levels = group["levels"]
        label = "/".join(levels.values())

        dfs, channels_map = {}, {}
        for subject_id, path in group["files"].items():
            df = load_table(path)
            if df is None:
                continue
            channels = select_channels(df, cfg.channels)
            if not channels:
                print(f"  WARNING: no channels found for {label}/subject_{subject_id}, skipping.")
                continue
            dfs[subject_id] = df
            channels_map[subject_id] = channels

        for subject_id, df in dfs.items():
            channels = channels_map[subject_id]
            if len(channels) < 2:
                continue
            summary = _build_intrabrain_graph(cfg, levels, subject_id, df, channels)
            if summary:
                intra_summaries.append(summary)

        subject_ids = sorted(dfs.keys())
        for s1, s2 in combinations(subject_ids, 2):
            summary = _build_interbrain_graph(cfg, levels, s1, s2, dfs[s1], dfs[s2], channels_map[s1], channels_map[s2])
            if summary:
                inter_summaries.append(summary)

    summary_dir = Path(cfg.output_dir) / "graphs"
    summary_dir.mkdir(parents=True, exist_ok=True)

    inter_df = pd.DataFrame(inter_summaries)
    intra_df = pd.DataFrame(intra_summaries)
    inter_df.to_csv(summary_dir / "inter_graph_summary.csv", index=False)
    intra_df.to_csv(summary_dir / "intra_graph_summary.csv", index=False)

    print(f"\nBuilt {len(inter_summaries)} inter-brain graph(s), {len(intra_summaries)} intra-brain graph(s).")
    print(f"Saved: {summary_dir / 'inter_graph_summary.csv'}")
    print(f"Saved: {summary_dir / 'intra_graph_summary.csv'}")

    return {"inter": inter_df, "intra": intra_df}


def run_all(cfg: ToolkitConfig) -> Dict[str, pd.DataFrame]:
    run_inspect(cfg)
    run_extract(cfg)
    return run_graphs(cfg)
