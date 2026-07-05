"""
Study Route - data models.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StudyStep:
    """A single step in the study route."""

    order: int
    title: str
    description: str
    concepts: list[str]
    section: str = ""
    estimated_time: str = "5 min"
    prerequisites: list[str] = field(default_factory=list)
    page_range: tuple[int, int] = (0, 0)
    difficulty: str = "medium"
    key_points: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "order": self.order,
            "title": self.title,
            "description": self.description,
            "concepts": self.concepts,
            "section": self.section,
            "estimated_time": self.estimated_time,
            "prerequisites": self.prerequisites,
            "page_range": list(self.page_range),
            "difficulty": self.difficulty,
            "key_points": self.key_points,
        }


@dataclass
class PrerequisiteEdge:
    """A prerequisite relationship between two concepts."""

    source: str
    target: str
    reason: str
    strength: float = 0.5

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "reason": self.reason,
            "strength": self.strength,
        }


@dataclass
class StudyRoute:
    """A complete study route with linear path and prerequisite DAG."""

    title: str
    total_steps: int
    estimated_time: str
    steps: list[StudyStep] = field(default_factory=list)
    prerequisites: list[PrerequisiteEdge] = field(default_factory=list)
    layers: list[list[str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "total_steps": self.total_steps,
            "estimated_time": self.estimated_time,
            "steps": [s.to_dict() for s in self.steps],
            "prerequisites": [p.to_dict() for p in self.prerequisites],
            "layers": self.layers,
        }
