#!/usr/bin/env python3
"""
Study Route - standalone demo script.

Generates a study route from the default chapter PDF or user-specified input.

Usage:
    python main.py                              # Extract from default PDF
    python main.py --pdf path/to/chapter.pdf    # Extract from custom PDF
    python main.py --knowledge-json path.json   # Use existing knowledge JSON
    python main.py --format text                # Human-readable output
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DEFAULT_PDF = Path(__file__).parent.parent / "data" / "chapter04.pdf"
DEFAULT_OUTPUT = Path(__file__).parent / "output"


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Study Route - generate learning paths from chapter data",
    )
    parser.add_argument(
        "--knowledge-json",
        type=Path,
        help="Path to knowledge.json (skips PDF extraction)",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=DEFAULT_PDF,
        help=f"PDF file for extraction (default: {DEFAULT_PDF})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output directory (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--model",
        default="qwen-plus",
        help="LLM model name (default: qwen-plus)",
    )

    args = parser.parse_args()

    # Step 1: Get knowledge data
    if args.knowledge_json:
        if not args.knowledge_json.exists():
            print(f"Error: {args.knowledge_json} not found.", file=sys.stderr)
            sys.exit(1)
        with open(args.knowledge_json, encoding="utf-8") as f:
            kb_data = json.load(f)
    else:
        if not args.pdf.exists():
            print(f"Error: {args.pdf} not found.", file=sys.stderr)
            sys.exit(1)
        kb_data = _extract_from_pdf(args.pdf)

    print("=" * 70)
    print("Study Route Demo")
    print("=" * 70)

    # Step 2: Generate study route
    from study_route import StudyRoutePlanner

    planner = StudyRoutePlanner(model=args.model)
    route = planner.plan(
        terms=kb_data.get("terms", []),
        relationships=kb_data.get("relationships", []),
        summaries=kb_data.get("summaries", []),
    )

    print(f"\nRoute: {route.title}")
    print(f"Steps: {route.total_steps}")
    print(f"Estimated time: {route.estimated_time}")
    print(f"Prerequisites: {len(route.prerequisites)}")
    print(f"Layers: {len(route.layers)}")

    print(f"\n{'─' * 70}")
    print("STUDY STEPS")
    print(f"{'─' * 70}")
    for step in route.steps:
        print(f"  Step {step.order}: {step.title}")
        print(f"    Concepts: {', '.join(step.concepts)}")
        print(f"    Time: {step.estimated_time} | Difficulty: {step.difficulty}")
        if step.key_points:
            for kp in step.key_points[:3]:
                print(f"    • {kp}")
        print()

    if route.prerequisites:
        print(f"{'─' * 70}")
        print("PREREQUISITES")
        print(f"{'─' * 70}")
        for p in route.prerequisites:
            print(f"  {p.source} → {p.target} ({p.reason})")
        print()

    # Step 3: Save output
    args.output.mkdir(parents=True, exist_ok=True)

    if args.format == "json":
        output_file = args.output / "route.json"
        output_file.write_text(
            json.dumps(route.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    else:
        from study_route.cli import _format_text
        output_file = args.output / "route.txt"
        output_file.write_text(_format_text(route), encoding="utf-8")

    print(f"Saved to: {output_file}")


def _extract_from_pdf(pdf_path: Path) -> dict:
    """Extract knowledge from PDF using knowledge-base package."""
    print(f"Extracting knowledge from: {pdf_path}", file=sys.stderr)
    try:
        from knowledge_base import KnowledgeExtractor
    except ImportError:
        print("Error: knowledge-base not installed.", file=sys.stderr)
        print("Run: pip install -e packages/knowledge-base/", file=sys.stderr)
        sys.exit(1)

    extractor = KnowledgeExtractor(max_terms=30, max_flashcards=50)
    kb = extractor.extract_from_pdf(pdf_path)
    return kb.to_dict()


if __name__ == "__main__":
    main()
