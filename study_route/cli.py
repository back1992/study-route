"""
Study Route CLI.

Usage:
    study-route --knowledge-json ../knowledge-base/output/knowledge.json
    study-route --pdf chapter.pdf --extract
    study-route --format text
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="study-route",
        description="Generate a study route from chapter knowledge data",
    )
    parser.add_argument(
        "--knowledge-json",
        type=Path,
        help="Path to knowledge.json from knowledge-base",
    )
    parser.add_argument(
        "--extract",
        action="store_true",
        help="Extract knowledge from PDF first",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        help="PDF file for extraction",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--model",
        default="qwen-plus",
        help="LLM model name (default: qwen-plus)",
    )

    args = parser.parse_args(argv)

    # Get knowledge data
    kb_data = None

    if args.extract:
        if not args.pdf:
            print("Error: --pdf required with --extract", file=sys.stderr)
            return 1
        kb_data = _extract_from_pdf(args.pdf)
    elif args.knowledge_json:
        if not args.knowledge_json.exists():
            print(f"Error: file not found: {args.knowledge_json}", file=sys.stderr)
            return 1
        with open(args.knowledge_json, encoding="utf-8") as f:
            kb_data = json.load(f)
    else:
        print("Error: provide --knowledge-json or --extract --pdf", file=sys.stderr)
        return 1

    # Build route
    from .planner import StudyRoutePlanner

    planner = StudyRoutePlanner(model=args.model)
    route = planner.plan(
        terms=kb_data.get("terms", []),
        relationships=kb_data.get("relationships", []),
        summaries=kb_data.get("summaries", []),
    )

    # Format output
    if args.format == "json":
        output = json.dumps(route.to_dict(), indent=2, ensure_ascii=False)
    else:
        output = _format_text(route)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
        print(f"Route saved to: {args.output}", file=sys.stderr)
    else:
        print(output)

    print(
        f"\nRoute: {route.total_steps} steps, {route.estimated_time}, "
        f"{len(route.prerequisites)} prerequisites",
        file=sys.stderr,
    )
    return 0


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


def _format_text(route) -> str:
    """Format study route as human-readable text."""
    lines: list[str] = []
    lines.append(f"# {route.title}")
    lines.append(f"Total: {route.total_steps} steps | {route.estimated_time}\n")

    for step in route.steps:
        lines.append(f"## Step {step.order}: {step.title}")
        lines.append(f"  Time: {step.estimated_time} | Difficulty: {step.difficulty}")
        if step.section:
            lines.append(f"  Section: {step.section}")
        pr = step.page_range
        if pr and (pr[0] != 0 or pr[1] != 0):
            lines.append(f"  Pages: {pr[0]}-{pr[1]}")
        lines.append(f"  Concepts: {', '.join(step.concepts)}")
        if step.description:
            lines.append(f"  {step.description}")
        if step.key_points:
            lines.append("  Key Points:")
            for kp in step.key_points:
                lines.append(f"    • {kp}")
        lines.append("")

    if route.prerequisites:
        lines.append("## Prerequisites")
        for p in route.prerequisites:
            lines.append(f"  {p.source} → {p.target}: {p.reason}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
