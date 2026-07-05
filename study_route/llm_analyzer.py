"""
Study Route - LLM-based prerequisite analysis.

Uses an OpenAI-compatible LLM to analyze concept definitions and infer
prerequisite relationships, study step groupings, and difficulty estimates.
"""

from __future__ import annotations

import json
import logging
import os
import re

_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
_DEFAULT_TIMEOUT = 60  # seconds

logger = logging.getLogger(__name__)


def _is_cjk(text: str) -> bool:
    """Check if text is predominantly CJK."""
    cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    latin = sum(1 for c in text if c.isascii() and c.isalpha())
    return cjk > latin


def _parse_llm_response(raw: str) -> dict | None:
    """Parse LLM JSON response, stripping code fences.

    Returns parsed dict or None on failure.
    """
    if not raw or not raw.strip():
        return None

    text = raw.strip()

    # Strip markdown code fences using regex
    text = re.sub(r"^```(?:json|JSON)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None

    if not isinstance(data, dict):
        return None

    return data


class LLMAnalyzer:
    """Use LLM to analyze concepts and infer prerequisite relationships."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        model: str = "qwen-plus",
        max_tokens: int = 4096,
    ):
        self._api_key = api_key or os.getenv("LLM_API_KEY", "")
        self._base_url = base_url or os.getenv("LLM_BASE_URL", _DEFAULT_BASE_URL)
        self._model = model or os.getenv("LLM_MODEL", "qwen-plus")
        self._max_tokens = max_tokens
        self._client = None

    @property
    def client(self):
        """Lazy-initialized OpenAI client."""
        if self._client is None and self._api_key:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self._api_key, base_url=self._base_url, timeout=_DEFAULT_TIMEOUT,
            )
        return self._client

    def analyze(
        self,
        terms: list[dict],
        relationships: list[dict] | None = None,
        graph: dict | None = None,
        summaries: list[dict] | None = None,
        mindmap: dict | None = None,
    ) -> dict | None:
        """Analyze concepts and return prerequisites + study steps.

        Returns:
            Dict with 'prerequisites' and 'steps' keys, or None on failure.
        """
        if not self._api_key:
            return None

        prompt = self._build_prompt(terms, relationships, graph, summaries, mindmap)
        is_cjk = _is_cjk(" ".join(t.get("term", "") for t in terms[:5]))

        system_msg = (
            "你是教育专家，擅长分析知识点之间的前置关系和学习顺序。\n"
            "请根据提供的概念定义和关系，推断学习前置条件，并将概念分组为学习步骤。\n"
            "输出JSON格式，包含 prerequisites 和 steps 两个字段。"
            if is_cjk
            else "You are an education expert. Analyze concept definitions to infer "
            "prerequisite relationships and group concepts into study steps.\n"
            "Output JSON with 'prerequisites' and 'steps' fields."
        )

        try:
            response = self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self._max_tokens,
                temperature=0.3,
            )
            if not response.choices or not response.choices[0].message.content:
                logger.warning("LLM returned empty response")
                return None
            raw = response.choices[0].message.content.strip()
            return _parse_llm_response(raw)
        except Exception as exc:
            logger.warning("LLM analysis failed: %s", exc)
            return None

    def _build_prompt(
        self,
        terms: list[dict],
        relationships: list[dict] | None,
        graph: dict | None,
        summaries: list[dict] | None,
        mindmap: dict | None,
    ) -> str:
        """Build the LLM prompt with all available context."""
        is_cjk = _is_cjk(" ".join(t.get("term", "") for t in terms[:5]))

        parts: list[str] = []

        # Concepts and definitions
        if is_cjk:
            parts.append("## 概念列表\n")
        else:
            parts.append("## Concepts\n")

        for t in terms:
            name = t.get("term", "")
            defn = t.get("definition", "")
            page = t.get("page", 0)
            parts.append(f"- **{name}** (p.{page}): {defn[:200]}")

        # Existing relationships
        rels = relationships or []
        if rels:
            parts.append(f"\n## {'已知关系' if is_cjk else 'Known Relationships'}\n")
            for r in rels[:20]:
                parts.append(
                    f"- {r.get('source', '')} → {r.get('relation_type', '')} → {r.get('target', '')}"
                )

        # Graph edges (structural connections from knowledge graph)
        if graph and graph.get("edges"):
            graph_edges = graph["edges"]
            # Deduplicate: only show edges not already covered by relationships
            rel_pairs = {
                (r.get("source", ""), r.get("target", ""))
                for r in rels
            }
            extra_edges = [
                e for e in graph_edges
                if (e.get("source", ""), e.get("target", "")) not in rel_pairs
            ]
            if extra_edges:
                parts.append(f"\n## {'图关系' if is_cjk else 'Graph Edges'}\n")
                for e in extra_edges[:20]:
                    parts.append(
                        f"- {e.get('source', '')} → {e.get('relation', '')} → {e.get('target', '')}"
                    )

        # Section structure from mindmap
        if mindmap and mindmap.get("children"):
            parts.append(f"\n## {'章节结构' if is_cjk else 'Section Structure'}\n")
            for child in mindmap.get("children", [])[:10]:
                parts.append(f"- {child.get('title', '')}")

        # Summaries
        if summaries:
            parts.append(f"\n## {'章节摘要' if is_cjk else 'Section Summaries'}\n")
            for s in summaries[:10]:
                section = s.get("section", "")
                summary = s.get("summary", "")[:150]
                parts.append(f"- **{section}**: {summary}")

        # Output format
        if is_cjk:
            parts.append(
                "\n## 输出要求\n"
                "请输出JSON格式，包含以下字段：\n"
                "1. `prerequisites`: 前置关系列表，每项包含 `source`(前置概念), `target`(后续概念), `reason`(原因), `strength`(强度0.0-1.0)\n"
                "2. `steps`: 学习步骤列表，每项包含 `title`(标题), `description`(描述), `concepts`(包含的概念名列表), `difficulty`(easy/medium/hard), `estimated_time`(预估时间)\n"
                "请将相关概念分组到同一步骤中，并按照学习顺序排列。"
            )
        else:
            parts.append(
                "\n## Output Requirements\n"
                "Output JSON with:\n"
                "1. `prerequisites`: list of {source, target, reason, strength(0.0-1.0)}\n"
                "2. `steps`: list of {title, description, concepts[], difficulty(easy/medium/hard), estimated_time}\n"
                "Group related concepts into steps, ordered by learning sequence."
            )

        return "\n".join(parts)
