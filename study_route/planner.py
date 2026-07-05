"""
Study Route - core planner logic.

Orchestrates the pipeline: build concept inventory → LLM analysis (optional) →
build prerequisite DAG → topological sort → assemble study steps.
"""

from __future__ import annotations

from .models import StudyStep, PrerequisiteEdge, StudyRoute
from .graph_utils import build_dag, topological_layers, detect_and_break_cycles, compute_degree_order
from .llm_analyzer import LLMAnalyzer


class StudyRoutePlanner:
    """Generate a study route from chapter study data."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        model: str = "qwen-plus",
    ):
        self._analyzer = LLMAnalyzer(
            api_key=api_key, base_url=base_url, model=model,
        )

    def plan(
        self,
        terms: list[dict] | None = None,
        relationships: list[dict] | None = None,
        graph: dict | None = None,
        summaries: list[dict] | None = None,
        mindmap: dict | None = None,
    ) -> StudyRoute:
        """Generate a study route.

        Args:
            terms: List of term dicts from knowledge-base.
            relationships: List of relationship dicts from knowledge-base.
            graph: Graph dict with 'nodes' and 'edges' from knowledge-graph.
            summaries: List of summary dicts from summary-generator.
            mindmap: Mindmap tree dict from mindmap-generator.

        Returns:
            A StudyRoute with linear steps and prerequisite DAG.
        """
        terms = terms or []
        relationships = relationships or []
        summaries = summaries or []

        if not terms:
            return StudyRoute(
                title="",
                total_steps=0,
                estimated_time="0 min",
                steps=[],
                prerequisites=[],
                layers=[],
            )

        # Step 1: Build concept inventory
        concepts = self._collect_concepts(terms, graph)

        # Step 2: Collect existing edges
        existing_edges = self._collect_edges(relationships, graph, concepts)

        # Step 3: Try LLM analysis
        llm_result = self._analyzer.analyze(
            terms, relationships, graph, summaries, mindmap,
        )

        if llm_result:
            prereqs = llm_result.get("prerequisites", [])
            llm_steps = llm_result.get("steps", [])
        else:
            prereqs = []
            llm_steps = []

        # Step 4: Merge prerequisites (existing edges + LLM inferred)
        all_edges = self._merge_edges(existing_edges, prereqs, concepts)

        # Step 5: Build DAG and compute layers
        concept_names = list(concepts.keys())
        dag = build_dag(concept_names, all_edges)
        dag = detect_and_break_cycles(dag)
        layers = topological_layers(dag)

        # Step 6: Build study steps
        if llm_steps:
            steps = self._build_llm_steps(llm_steps, concepts, summaries, prereqs)
        else:
            steps = self._build_algorithmic_steps(layers, concepts, summaries, mindmap, all_edges, dag)

        # Step 7: Build prerequisite edge objects
        prereq_objects = [
            PrerequisiteEdge(
                source=e["source"],
                target=e["target"],
                reason=e.get("reason", ""),
                strength=e.get("strength", 0.5),
            )
            for e in all_edges
        ]

        # Step 8: Compute title and total time
        title = ""
        if mindmap and mindmap.get("title"):
            title = mindmap["title"]
        elif terms and terms[0].get("term"):
            from .llm_analyzer import _is_cjk
            term_name = terms[0]["term"]
            title = f"{term_name} 学习路线" if _is_cjk(term_name) else f"{term_name} Study Route"

        total_minutes = sum(self._parse_time(s.estimated_time) for s in steps)
        estimated_time = f"{total_minutes} min"

        return StudyRoute(
            title=title,
            total_steps=len(steps),
            estimated_time=estimated_time,
            steps=steps,
            prerequisites=prereq_objects,
            layers=layers,
        )

    def _collect_concepts(self, terms: list[dict], graph: dict | None) -> dict[str, dict]:
        """Merge terms and graph nodes into a unified concept dict."""
        concepts: dict[str, dict] = {}

        for t in terms:
            name = t.get("term", "")
            if name:
                concepts[name] = {
                    "name": name,
                    "definition": t.get("definition", ""),
                    "category": t.get("category", ""),
                    "page": t.get("page", 0),
                }

        if graph:
            for n in graph.get("nodes", []):
                name = n.get("id", n.get("name", ""))
                if name and name not in concepts:
                    concepts[name] = {
                        "name": name,
                        "definition": n.get("definition", ""),
                        "category": n.get("category", n.get("group", "")),
                        "page": 0,
                    }

        return concepts

    def _collect_edges(
        self, relationships: list[dict], graph: dict | None,
        concepts: dict[str, dict] | None = None,
    ) -> list[dict]:
        """Collect edges from relationships and graph, filtering to known concepts."""
        edges: list[dict] = []
        concept_names = set(concepts.keys()) if concepts else None

        def _valid(src: str, tgt: str) -> bool:
            return bool(src and tgt) and (concept_names is None or (src in concept_names and tgt in concept_names))

        for r in relationships:
            src = r.get("source", "")
            tgt = r.get("target", "")
            if _valid(src, tgt):
                edges.append({
                    "source": src,
                    "target": tgt,
                    "reason": r.get("description", ""),
                    "strength": 0.8,
                })

        if graph:
            for e in graph.get("edges", []):
                src = e.get("source", "")
                tgt = e.get("target", "")
                if _valid(src, tgt):
                    edges.append({
                        "source": src,
                        "target": tgt,
                        "reason": f"{e.get('relation', 'related')}",
                        "strength": e.get("weight", 0.5),
                    })

        return edges

    def _merge_edges(
        self,
        existing: list[dict],
        llm_prereqs: list[dict],
        concepts: dict[str, dict],
    ) -> list[dict]:
        """Merge existing edges with LLM-inferred prerequisites."""
        seen: set[tuple[str, str]] = set()
        merged: list[dict] = []

        for e in existing:
            key = (e["source"], e["target"])
            if key not in seen and e["source"] in concepts and e["target"] in concepts:
                seen.add(key)
                merged.append(e)

        for e in llm_prereqs:
            key = (e.get("source", ""), e.get("target", ""))
            if key not in seen and key[0] in concepts and key[1] in concepts:
                seen.add(key)
                merged.append({
                    "source": key[0],
                    "target": key[1],
                    "reason": e.get("reason", ""),
                    "strength": e.get("strength", 0.5),
                })

        return merged

    def _build_llm_steps(
        self,
        llm_steps: list[dict],
        concepts: dict[str, dict],
        summaries: list[dict],
        prereqs: list[dict],
    ) -> list[StudyStep]:
        """Build StudyStep objects from LLM-generated steps."""
        result: list[StudyStep] = []
        summary_map = self._build_summary_map(summaries)

        for raw in llm_steps:
            step_concepts = [
                c for c in raw.get("concepts", []) if c in concepts
            ]
            if not step_concepts:
                continue

            # Find section and page range
            section = self._match_section(step_concepts, summary_map)
            pages = [concepts[c]["page"] for c in step_concepts if concepts[c].get("page")]
            page_range = (min(pages), max(pages)) if pages else (0, 0)

            # Find prerequisites for concepts in this step
            step_prereqs = list({
                e["source"]
                for e in prereqs
                if e["target"] in step_concepts and e["source"] not in step_concepts
            })

            # Find key points from summaries
            key_points = summary_map.get(section, {}).get("key_points", [])

            result.append(StudyStep(
                order=len(result) + 1,
                title=raw.get("title", f"Step {len(result) + 1}"),
                description=raw.get("description", ""),
                concepts=step_concepts,
                section=section,
                estimated_time=raw.get("estimated_time", "10 min"),
                prerequisites=step_prereqs,
                page_range=page_range,
                difficulty=raw.get("difficulty", "medium"),
                key_points=key_points[:5],
            ))

        return result

    def _build_algorithmic_steps(
        self,
        layers: list[list[str]],
        concepts: dict[str, dict],
        summaries: list[dict],
        mindmap: dict | None,
        edges: list[dict],
        dag=None,
    ) -> list[StudyStep]:
        """Build study steps from topological layers (algorithmic fallback)."""
        result: list[StudyStep] = []
        summary_map = self._build_summary_map(summaries)
        n_layers = len(layers)

        for i, layer in enumerate(layers, 1):
            if not layer:
                continue

            # Create one step per layer, sorted by degree (most connected first)
            step_concepts = [n for n in compute_degree_order(dag) if n in layer]
            pages = [concepts[c]["page"] for c in step_concepts if concepts.get(c, {}).get("page")]
            page_range = (min(pages), max(pages)) if pages else (0, 0)

            section = self._match_section(step_concepts, summary_map)
            key_points = summary_map.get(section, {}).get("key_points", [])

            # Estimate time: ~5 min per concept
            est_minutes = max(5, len(step_concepts) * 5)

            # Difficulty based on layer position (handle small layer counts)
            if n_layers <= 1:
                difficulty = "medium"
            elif n_layers == 2:
                difficulty = "easy" if i == 1 else "hard"
            else:
                if i <= n_layers / 3:
                    difficulty = "easy"
                elif i <= 2 * n_layers / 3:
                    difficulty = "medium"
                else:
                    difficulty = "hard"

            # Find prerequisites for concepts in this step
            step_prereqs = list({
                e["source"]
                for e in edges
                if e["target"] in step_concepts and e["source"] not in step_concepts
            })

            # Build step title (detect CJK)
            from .llm_analyzer import _is_cjk
            sample = " ".join(step_concepts[:3])
            if _is_cjk(sample):
                title = f"第{i}阶段：{'、'.join(step_concepts[:3])}"
                desc = f"学习 {len(step_concepts)} 个概念"
            else:
                title = f"Phase {i}: {', '.join(step_concepts[:3])}"
                desc = f"Learn {len(step_concepts)} concepts"

            result.append(StudyStep(
                order=len(result) + 1,
                title=title,
                description=desc,
                concepts=step_concepts,
                section=section,
                estimated_time=f"{est_minutes} min",
                prerequisites=step_prereqs,
                page_range=page_range,
                difficulty=difficulty,
                key_points=key_points[:5],
            ))

        return result

    def _build_summary_map(self, summaries: list[dict]) -> dict[str, dict]:
        """Build a section → summary lookup map."""
        return {s.get("section", ""): s for s in summaries if s.get("section")}

    def _match_section(self, concept_names: list[str], summary_map: dict[str, dict]) -> str:
        """Match concepts to the best section from summaries.

        Tries exact match first, then falls back to substring match
        where the concept covers at least 2 chars of the section title.
        """
        # Exact match
        for section in summary_map:
            for name in concept_names:
                if name == section:
                    return section

        # Substring match (require concept name >= 2 chars to avoid false positives)
        for section in summary_map:
            for name in concept_names:
                if len(name) >= 2 and name in section:
                    return section
        return ""

    @staticmethod
    def _parse_time(time_str: str) -> int:
        """Parse 'N min' string to integer minutes."""
        try:
            return int(time_str.replace("min", "").strip())
        except (ValueError, AttributeError):
            return 5
