"""Tests for study_route.graph_utils."""

from __future__ import annotations

import networkx as nx
import pytest

from study_route.graph_utils import (
    build_dag,
    topological_layers,
    detect_and_break_cycles,
    compute_degree_order,
)


# ── 1. build_dag ─────────────────────────────────────────────────────────────

def test_build_dag_from_edges():
    concepts = ["A", "B", "C", "D"]
    edges = [
        {"source": "A", "target": "B"},
        {"source": "A", "target": "C"},
        {"source": "B", "target": "D"},
    ]
    dag = build_dag(concepts, edges)
    assert set(dag.nodes()) == {"A", "B", "C", "D"}
    assert dag.has_edge("A", "B")
    assert dag.has_edge("B", "D")
    assert not dag.has_edge("D", "A")


def test_build_dag_isolated_nodes():
    concepts = ["A", "B", "C"]
    edges = [{"source": "A", "target": "B"}]
    dag = build_dag(concepts, edges)
    assert "C" in dag.nodes()
    assert dag.degree("C") == 0


def test_build_dag_empty():
    dag = build_dag([], [])
    assert len(dag.nodes()) == 0


# ── 2. topological_layers ────────────────────────────────────────────────────

def test_topological_layers_linear():
    edges = [("A", "B"), ("B", "C")]
    concepts = ["A", "B", "C"]
    dag = build_dag(concepts, [{"source": s, "target": t} for s, t in edges])
    layers = topological_layers(dag)
    assert layers == [["A"], ["B"], ["C"]]


def test_topological_layers_parallel():
    edges = [("A", "C"), ("B", "C")]
    concepts = ["A", "B", "C"]
    dag = build_dag(concepts, [{"source": s, "target": t} for s, t in edges])
    layers = topological_layers(dag)
    assert len(layers) == 2
    assert set(layers[0]) == {"A", "B"}
    assert layers[1] == ["C"]


def test_topological_layers_no_edges():
    concepts = ["X", "Y", "Z"]
    dag = build_dag(concepts, [])
    layers = topological_layers(dag)
    assert len(layers) == 1
    assert set(layers[0]) == {"X", "Y", "Z"}


# ── 3. detect_and_break_cycles ───────────────────────────────────────────────

def test_detect_and_break_cycles_no_cycle():
    edges = [("A", "B"), ("B", "C")]
    concepts = ["A", "B", "C"]
    dag = build_dag(concepts, [{"source": s, "target": t} for s, t in edges])
    result = detect_and_break_cycles(dag)
    assert result.has_edge("A", "B")
    assert result.has_edge("B", "C")
    # Original graph unchanged
    assert dag.has_edge("A", "B")


def test_detect_and_break_cycles_removes_edge():
    concepts = ["A", "B", "C"]
    dag = build_dag(concepts, [
        {"source": "A", "target": "B"},
        {"source": "B", "target": "C"},
        {"source": "C", "target": "A"},
    ])
    result = detect_and_break_cycles(dag)
    assert nx.is_directed_acyclic_graph(result)
    # Original graph still has cycle
    assert dag.has_edge("C", "A")
    assert not nx.is_directed_acyclic_graph(dag)


# ── 4. compute_degree_order ──────────────────────────────────────────────────

def test_compute_degree_order():
    concepts = ["A", "B", "C"]
    edges = [{"source": "A", "target": "B"}, {"source": "A", "target": "C"}]
    dag = build_dag(concepts, edges)
    order = compute_degree_order(dag)
    # A has highest degree (2), should come first
    assert order[0] == "A"
    assert set(order[1:]) == {"B", "C"}
