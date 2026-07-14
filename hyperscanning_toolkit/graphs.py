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

from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd


def build_graph(edge_table: pd.DataFrame, node_groups: Dict[str, List[str]]) -> nx.Graph:
    """Build a weighted undirected graph.

    `node_groups` maps a participant label -> list of node names to add upfront
    (even nodes with no surviving significant edges), so adjacency matrices have
    stable dimensions. Only edges with weight > 0 (significant) are added.
    """
    G = nx.Graph()
    for label, nodes in node_groups.items():
        G.add_nodes_from(nodes, participant=label)

    for _, row in edge_table.iterrows():
        if row["weight"] > 0:
            G.add_edge(
                row["source"], row["target"],
                weight=row["weight"], raw_r=row["raw_r"], p_value=row["p_value"],
            )
    return G


def compute_node_metrics(G: nx.Graph, node_participant: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """Comprehensive node-level metrics. `node_participant` optionally maps node -> participant label."""
    if G.number_of_nodes() == 0:
        return pd.DataFrame()

    degree = dict(G.degree())
    strength = dict(G.degree(weight="weight"))
    degree_centrality = nx.degree_centrality(G)

    try:
        betweenness = nx.betweenness_centrality(G, weight="weight")
    except Exception:
        betweenness = {n: np.nan for n in G.nodes()}
    try:
        closeness = nx.closeness_centrality(G, distance="weight")
    except Exception:
        closeness = {n: np.nan for n in G.nodes()}
    try:
        eigenvector = nx.eigenvector_centrality(G, weight="weight", max_iter=1000)
    except Exception:
        eigenvector = {n: np.nan for n in G.nodes()}
    try:
        clustering = nx.clustering(G, weight="weight")
    except Exception:
        clustering = {n: np.nan for n in G.nodes()}

    rows = []
    for node in G.nodes():
        row = {
            "node": node,
            "node_strength": strength.get(node, 0),
            "degree": degree.get(node, 0),
            "weighted_degree": strength.get(node, 0),
            "degree_centrality": degree_centrality.get(node, 0),
            "betweenness_centrality": betweenness.get(node, np.nan),
            "closeness_centrality": closeness.get(node, np.nan),
            "eigenvector_centrality": eigenvector.get(node, np.nan),
            "local_clustering_coefficient": clustering.get(node, np.nan),
        }
        if node_participant is not None:
            row["participant"] = node_participant.get(node)
        rows.append(row)

    return pd.DataFrame(rows)


def _common_graph_metrics(G: nx.Graph, edge_table: pd.DataFrame) -> dict:
    positive_weights = edge_table[edge_table["weight"] > 0]["weight"].values
    strength_values = list(dict(G.degree(weight="weight")).values())
    degree_values = list(dict(G.degree()).values())

    metrics = {
        "number_of_nodes": G.number_of_nodes(),
        "number_of_edges": G.number_of_edges(),
        "density": nx.density(G) if G.number_of_nodes() > 1 else 0.0,
        "mean_positive_edge_weight": float(np.mean(positive_weights)) if len(positive_weights) else 0.0,
        "max_edge_weight": float(np.max(positive_weights)) if len(positive_weights) else 0.0,
        "min_positive_edge_weight": float(np.min(positive_weights)) if len(positive_weights) else 0.0,
        "average_node_strength": float(np.mean(strength_values)) if strength_values else 0.0,
        "average_degree": float(np.mean(degree_values)) if degree_values else 0.0,
    }

    try:
        metrics["average_clustering_coefficient"] = nx.average_clustering(G, weight="weight")
    except Exception:
        metrics["average_clustering_coefficient"] = np.nan
    try:
        metrics["global_efficiency"] = nx.global_efficiency(G) if G.number_of_nodes() > 1 else 0.0
    except Exception:
        metrics["global_efficiency"] = np.nan
    try:
        num_components = nx.number_connected_components(G)
        metrics["number_connected_components"] = num_components
        metrics["largest_connected_component_size"] = (
            len(max(nx.connected_components(G), key=len)) if num_components > 0 else 0
        )
    except Exception:
        metrics["number_connected_components"] = np.nan
        metrics["largest_connected_component_size"] = np.nan
    try:
        metrics["transitivity"] = nx.transitivity(G)
    except Exception:
        metrics["transitivity"] = np.nan
    try:
        metrics["assortativity_coefficient"] = nx.degree_assortativity_coefficient(G)
    except Exception:
        metrics["assortativity_coefficient"] = np.nan

    return metrics


def compute_modularity(G: nx.Graph) -> float:
    if G.number_of_edges() == 0 or G.number_of_nodes() < 2:
        return np.nan
    try:
        communities = list(nx.algorithms.community.greedy_modularity_communities(G, weight="weight"))
        return float(nx.algorithms.community.modularity(G, communities, weight="weight"))
    except Exception:
        return np.nan


def compute_interbrain_graph_metrics(
    G: nx.Graph, edge_table: pd.DataFrame, group_a_nodes: List[str], group_b_nodes: List[str]
) -> dict:
    """Graph-level metrics for a bipartite inter-brain/inter-participant graph."""
    metrics = _common_graph_metrics(G, edge_table)

    n_a, n_b = len(group_a_nodes), len(group_b_nodes)
    metrics["n_group_a_nodes"] = n_a
    metrics["n_group_b_nodes"] = n_b

    max_bipartite_edges = n_a * n_b
    metrics["bipartite_density"] = (
        G.number_of_edges() / max_bipartite_edges if max_bipartite_edges > 0 else 0.0
    )
    metrics["group_a_nodes_connected"] = sum(1 for n in group_a_nodes if G.degree(n) > 0)
    metrics["group_b_nodes_connected"] = sum(1 for n in group_b_nodes if G.degree(n) > 0)

    return metrics


def compute_intrabrain_graph_metrics(G: nx.Graph, edge_table: pd.DataFrame) -> dict:
    """Graph-level metrics for a single-participant intra-brain graph."""
    metrics = _common_graph_metrics(G, edge_table)
    metrics["modularity"] = compute_modularity(G)
    return metrics


def visualize_bipartite_graph(
    G: nx.Graph,
    group_a_nodes: List[str],
    group_b_nodes: List[str],
    output_path: Path,
    title: str = "Inter-brain connectivity graph",
) -> None:
    if G.number_of_nodes() == 0:
        print("    WARNING: Graph has no nodes, skipping visualization.")
        return

    fig, ax = plt.subplots(figsize=(14, 10))

    n_a, n_b = len(group_a_nodes), len(group_b_nodes)
    pos = {}
    for i, node in enumerate(sorted(group_a_nodes)):
        pos[node] = (0, i - n_a / 2)
    for i, node in enumerate(sorted(group_b_nodes)):
        pos[node] = (2, i - n_b / 2)

    nx.draw_networkx_nodes(G, pos, nodelist=group_a_nodes, node_color="lightblue", node_size=300, label="Group A", ax=ax)
    nx.draw_networkx_nodes(G, pos, nodelist=group_b_nodes, node_color="lightcoral", node_size=300, label="Group B", ax=ax)

    sig_edges = [(u, v) for u, v in G.edges() if G[u][v]["weight"] > 0]
    if sig_edges:
        weights = [G[u][v]["weight"] for u, v in sig_edges]
        max_w = max(weights) if weights else 1
        nx.draw_networkx_edges(G, pos, edgelist=sig_edges, width=[3 * (w / max_w) for w in weights], alpha=0.5, ax=ax)

    active_nodes = {n for n in G.nodes() if G.degree(n) > 0}
    nx.draw_networkx_labels(G, pos, labels={n: n for n in active_nodes}, font_size=6, font_weight="bold", ax=ax)

    n_sig = len(sig_edges)
    max_possible = n_a * n_b
    subtitle = f"Significant edges: {n_sig} / {max_possible} possible  (bipartite density = {n_sig / max_possible:.3f})" if max_possible > 0 else ""
    ax.set_title(f"{title}\n{subtitle}", fontsize=12, fontweight="bold")
    ax.legend(loc="upper center", fontsize=12)
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"    Saved graph visualization: {output_path.name}")


def visualize_intrabrain_graph(
    G: nx.Graph,
    output_path: Path,
    title: str = "Intra-brain connectivity graph",
) -> None:
    if G.number_of_nodes() == 0:
        print("    WARNING: Graph has no nodes, skipping visualization.")
        return

    fig, ax = plt.subplots(figsize=(10, 10))
    pos = nx.spring_layout(G, weight="weight", seed=0)

    nx.draw_networkx_nodes(G, pos, node_color="lightgreen", node_size=300, ax=ax)

    sig_edges = [(u, v) for u, v in G.edges() if G[u][v]["weight"] > 0]
    if sig_edges:
        weights = [G[u][v]["weight"] for u, v in sig_edges]
        max_w = max(weights) if weights else 1
        nx.draw_networkx_edges(G, pos, edgelist=sig_edges, width=[3 * (w / max_w) for w in weights], alpha=0.5, ax=ax)

    active_nodes = {n for n in G.nodes() if G.degree(n) > 0}
    nx.draw_networkx_labels(G, pos, labels={n: n for n in active_nodes}, font_size=6, font_weight="bold", ax=ax)

    ax.set_title(f"{title}\nSignificant edges: {len(sig_edges)}", fontsize=12, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"    Saved graph visualization: {output_path.name}")
