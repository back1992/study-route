"""Tests for study_route.models."""

from __future__ import annotations

from study_route.models import StudyStep, PrerequisiteEdge, StudyRoute


# ── 1. StudyStep serialization ───────────────────────────────────────────────

def test_study_step_to_dict():
    step = StudyStep(
        order=1,
        title="基础概念",
        description="先理解编码和装车的基本含义",
        concepts=["编码", "装车过程"],
        section="第一节",
        estimated_time="10 min",
        prerequisites=[],
        page_range=(1, 5),
        difficulty="easy",
        key_points=["编码是信息转换", "装车是加载到符号上"],
    )
    d = step.to_dict()
    assert d["order"] == 1
    assert d["title"] == "基础概念"
    assert d["concepts"] == ["编码", "装车过程"]
    assert d["page_range"] == [1, 5]
    assert d["difficulty"] == "easy"
    assert len(d["key_points"]) == 2


def test_study_step_defaults():
    step = StudyStep(order=1, title="Test", description="", concepts=[])
    d = step.to_dict()
    assert d["prerequisites"] == []
    assert d["page_range"] == [0, 0]
    assert d["difficulty"] == "medium"
    assert d["key_points"] == []
    assert d["estimated_time"] == "5 min"


# ── 2. PrerequisiteEdge serialization ────────────────────────────────────────

def test_prerequisite_edge_to_dict():
    edge = PrerequisiteEdge(
        source="编码",
        target="装车过程",
        reason="装车需要理解编码的概念",
        strength=0.8,
    )
    d = edge.to_dict()
    assert d == {
        "source": "编码",
        "target": "装车过程",
        "reason": "装车需要理解编码的概念",
        "strength": 0.8,
    }


def test_prerequisite_edge_defaults():
    edge = PrerequisiteEdge(source="A", target="B", reason="")
    assert edge.strength == 0.5


# ── 3. StudyRoute serialization ──────────────────────────────────────────────

def test_study_route_to_dict():
    step = StudyStep(order=1, title="Step 1", description="", concepts=["A"])
    edge = PrerequisiteEdge(source="A", target="B", reason="prereq")
    route = StudyRoute(
        title="第四章学习路线",
        total_steps=1,
        estimated_time="10 min",
        steps=[step],
        prerequisites=[edge],
        layers=[["A"], ["B"]],
    )
    d = route.to_dict()
    assert d["title"] == "第四章学习路线"
    assert d["total_steps"] == 1
    assert len(d["steps"]) == 1
    assert d["steps"][0]["order"] == 1
    assert len(d["prerequisites"]) == 1
    assert d["layers"] == [["A"], ["B"]]


def test_study_route_empty():
    route = StudyRoute(
        title="Empty",
        total_steps=0,
        estimated_time="0 min",
        steps=[],
        prerequisites=[],
        layers=[],
    )
    d = route.to_dict()
    assert d["steps"] == []
    assert d["prerequisites"] == []
    assert d["layers"] == []
