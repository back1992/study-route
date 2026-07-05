"""Tests for study_route.planner."""

from __future__ import annotations

import pytest

from study_route import StudyRoutePlanner, StudyRoute


# ── Fixtures ─────────────────────────────────────────────────────────────────

SAMPLE_TERMS = [
    {"term": "编码", "definition": "把信息转换成可供传输的信号", "page": 1, "category": ""},
    {"term": "装车过程", "definition": "把信息加载到符号上面", "page": 2, "category": ""},
    {"term": "类似与相近", "definition": "人们感知事物时趋向于把相似的东西视为一类", "page": 5, "category": "concept"},
    {"term": "完形趋向", "definition": "人们对事物的感知总是趋向于整齐划一", "page": 6, "category": "concept"},
    {"term": "残缺闭合", "definition": "与完形趋向有共同之处", "page": 7, "category": "concept"},
    {"term": "共同命运", "definition": "人们倾向于把类似的东西当成一个共同体", "page": 8, "category": "concept"},
]

SAMPLE_GRAPH = {
    "nodes": [
        {"id": "编码", "category": "", "definition": "把信息转换成可供传输的信号"},
        {"id": "装车过程", "category": "", "definition": "把信息加载到符号上面"},
        {"id": "类似与相近", "category": "concept", "definition": "感知相似东西为一类"},
        {"id": "完形趋向", "category": "concept", "definition": "感知趋向整齐划一"},
        {"id": "残缺闭合", "category": "concept", "definition": "与完形趋向相通"},
        {"id": "共同命运", "category": "concept", "definition": "把类似东西当共同体"},
    ],
    "edges": [
        {"source": "残缺闭合", "target": "完形趋向", "relation": "related_to", "weight": 1.0},
        {"source": "共同命运", "target": "类似与相近", "relation": "related_to", "weight": 1.0},
    ],
}

SAMPLE_SUMMARIES = [
    {"section": "第一节 编码与译码", "summary": "编码是把信息转换成信号...", "key_points": ["编码定义"], "page": 1},
    {"section": "第二节 心理机制", "summary": "左右认知的心理机制...", "key_points": ["感知机制"], "page": 5},
]

SAMPLE_MINDMAP = {
    "title": "第四章 符号互动",
    "level": 0,
    "children": [
        {"title": "第一节 编码与译码", "level": 1, "children": []},
        {"title": "第二节 心理机制", "level": 1, "children": []},
    ],
}


@pytest.fixture
def planner() -> StudyRoutePlanner:
    """Planner with no API key — forces algorithmic fallback."""
    return StudyRoutePlanner(api_key="")


# ── 1. Algorithmic fallback (no LLM) ─────────────────────────────────────────

def test_plan_returns_study_route(planner: StudyRoutePlanner):
    route = planner.plan(terms=SAMPLE_TERMS, graph=SAMPLE_GRAPH)
    assert isinstance(route, StudyRoute)


def test_plan_has_steps(planner: StudyRoutePlanner):
    route = planner.plan(terms=SAMPLE_TERMS, graph=SAMPLE_GRAPH)
    assert route.total_steps >= 1
    assert len(route.steps) >= 1


def test_plan_steps_have_concepts(planner: StudyRoutePlanner):
    route = planner.plan(terms=SAMPLE_TERMS, graph=SAMPLE_GRAPH)
    all_concepts = set()
    for step in route.steps:
        assert len(step.concepts) > 0
        all_concepts.update(step.concepts)
    # All terms should appear in at least one step
    term_names = {t["term"] for t in SAMPLE_TERMS}
    assert all_concepts == term_names


def test_plan_has_layers(planner: StudyRoutePlanner):
    route = planner.plan(terms=SAMPLE_TERMS, graph=SAMPLE_GRAPH)
    assert len(route.layers) >= 1
    # All concepts should appear in layers
    layer_concepts = set()
    for layer in route.layers:
        layer_concepts.update(layer)
    assert layer_concepts == {t["term"] for t in SAMPLE_TERMS}


def test_plan_step_order_is_sequential(planner: StudyRoutePlanner):
    route = planner.plan(terms=SAMPLE_TERMS, graph=SAMPLE_GRAPH)
    for i, step in enumerate(route.steps, 1):
        assert step.order == i


def test_plan_with_summaries_and_mindmap(planner: StudyRoutePlanner):
    route = planner.plan(
        terms=SAMPLE_TERMS,
        graph=SAMPLE_GRAPH,
        summaries=SAMPLE_SUMMARIES,
        mindmap=SAMPLE_MINDMAP,
    )
    assert isinstance(route, StudyRoute)
    assert route.total_steps >= 1


# ── 2. Edge cases ────────────────────────────────────────────────────────────

def test_plan_empty_terms(planner: StudyRoutePlanner):
    route = planner.plan(terms=[])
    assert isinstance(route, StudyRoute)
    assert route.total_steps == 0
    assert route.steps == []


def test_plan_single_term(planner: StudyRoutePlanner):
    route = planner.plan(terms=[{"term": "A", "definition": "test", "page": 1}])
    assert route.total_steps == 1
    assert route.steps[0].concepts == ["A"]


def test_plan_no_graph(planner: StudyRoutePlanner):
    route = planner.plan(terms=SAMPLE_TERMS)
    assert isinstance(route, StudyRoute)
    assert route.total_steps >= 1


def test_plan_terms_only(planner: StudyRoutePlanner):
    route = planner.plan(terms=SAMPLE_TERMS[:2])
    assert route.total_steps >= 1
    for step in route.steps:
        assert step.difficulty in ("easy", "medium", "hard")
