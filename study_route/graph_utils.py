"""
Graph utilities for study route computation.

Provides topological sorting, layer computation, and cycle detection
using networkx directed acyclic graphs.
"""

from __future__ import annotations

import networkx as nx


def build_dag(
    concepts: list[str],
    edges: list[dict],
) -> nx.DiGraph:
    """Build a directed graph from concepts and prerequisite edges.

    Args:
        concepts: List of concept names (nodes).
        edges: List of dicts with 'source' and 'target' keys.

    Returns:
        A networkx DiGraph with all concepts as nodes and edges as directed edges.
    """
    dag = nx.DiGraph()
    dag.add_nodes_from(concepts)
    for e in edges:
        src = e.get("source", "")
        tgt = e.get("target", "")
        if src and tgt and src in concepts and tgt in concepts:
            dag.add_edge(src, tgt)
    return dag


def topological_layers(dag: nx.DiGraph) -> list[list[str]]:
    """Compute topological layers using Kahn's algorithm.

    Concepts in the same layer have no dependency on each other
    and can be studied in parallel.

    Returns:
        List of layers, where each layer is a sorted list of concept names.
    """
    if len(dag.nodes()) == 0:
        return []

    # Kahn's algorithm: repeatedly remove nodes with in_degree 0
    remaining = dag.copy()
    layers: list[list[str]] = []

    while remaining.nodes():
        # Find all nodes with no incoming edges
        roots = sorted(n for n in remaining.nodes() if remaining.in_degree(n) == 0)
        if not roots:
            # Should not happen in a DAG; break to avoid infinite loop
            break
        layers.append(roots)
        remaining.remove_nodes_from(roots)

    return layers


def detect_and_break_cycles(dag: nx.DiGraph) -> nx.DiGraph:
    """Detect and break cycles by removing edges.

    Works on a copy of the input graph. Returns a new acyclic DiGraph.

    Returns:
        A new DiGraph with all cycles broken.
    """
    result = dag.copy()
    removed: list[tuple[str, str]] = []

    while not nx.is_directed_acyclic_graph(result):
        try:
            cycle = nx.find_cycle(result)
            # Remove the last edge in the cycle
            src, tgt = cycle[-1][0], cycle[-1][1]
            result.remove_edge(src, tgt)
            removed.append((src, tgt))
        except nx.NetworkXNoCycle:
            break

    return result


def compute_degree_order(dag: nx.DiGraph) -> list[str]:
    """Sort concepts by degree (most connected first).

    Used as a tiebreaker within topological layers.

    Returns:
        List of concept names sorted by descending degree.
    """
    return sorted(dag.nodes(), key=lambda n: dag.degree(n), reverse=True)
