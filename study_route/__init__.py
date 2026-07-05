"""
Study Route - generate personalized learning paths from chapter data.

Analyzes concepts, definitions, and knowledge graph structure to produce
a recommended study sequence with prerequisite dependencies.

Usage:
    from study_route import StudyRoutePlanner

    planner = StudyRoutePlanner()
    route = planner.plan(terms=terms, graph=graph)
"""

from .models import StudyStep, PrerequisiteEdge, StudyRoute
from .planner import StudyRoutePlanner

__all__ = [
    "StudyStep",
    "PrerequisiteEdge",
    "StudyRoute",
    "StudyRoutePlanner",
]

__version__ = "1.0.0"
