"""Tests for study_route.llm_analyzer."""

from __future__ import annotations

import json

from study_route.llm_analyzer import LLMAnalyzer, _parse_llm_response


# -- 1. Response parsing ------------------------------------------------------

VALID_LLM_RESPONSE = json.dumps({
    "prerequisites": [
        {"source": "编码", "target": "装车过程", "reason": "理解编码才能装车", "strength": 0.9},
        {"source": "类似与相近", "target": "共同命运", "reason": "共同命运是类似与相近的延伸", "strength": 0.7},
    ],
    "steps": [
        {
            "title": "基础概念",
            "description": "理解编码和装车的基本含义",
            "concepts": ["编码", "装车过程"],
            "difficulty": "easy",
            "estimated_time": "10 min",
        },
        {
            "title": "感知机制",
            "description": "学习人类感知事物的心理机制",
            "concepts": ["类似与相近", "完形趋向", "残缺闭合", "共同命运"],
            "difficulty": "medium",
            "estimated_time": "20 min",
        },
    ],
}, ensure_ascii=False)


def test_parse_valid_response():
    result = _parse_llm_response(VALID_LLM_RESPONSE)
    assert result is not None
    assert len(result["prerequisites"]) == 2
    assert len(result["steps"]) == 2
    assert result["prerequisites"][0]["source"] == "编码"
    assert result["steps"][0]["concepts"] == ["编码", "装车过程"]


def test_parse_response_with_code_fences():
    raw = f"```json\n{VALID_LLM_RESPONSE}\n```"
    result = _parse_llm_response(raw)
    assert result is not None
    assert len(result["steps"]) == 2


def test_parse_response_with_markdown_fence():
    raw = f"```\n{VALID_LLM_RESPONSE}\n```"
    result = _parse_llm_response(raw)
    assert result is not None


def test_parse_invalid_json():
    result = _parse_llm_response("this is not json")
    assert result is None


def test_parse_empty_string():
    result = _parse_llm_response("")
    assert result is None


def test_parse_missing_keys():
    raw = json.dumps({"prerequisites": []})
    result = _parse_llm_response(raw)
    # Should still return if at least one key exists
    assert result is not None
    assert result["prerequisites"] == []


# -- 2. CJK detection ---------------------------------------------------------

def test_is_cjk_chinese():
    from study_route.llm_analyzer import _is_cjk
    assert _is_cjk("编码与传播学") is True


def test_is_cjk_english():
    from study_route.llm_analyzer import _is_cjk
    assert _is_cjk("encoding and decoding") is False


# -- 3. Analyzer construction (no API call) ------------------------------------

def test_analyzer_init_defaults():
    analyzer = LLMAnalyzer(api_key="test-key")
    assert analyzer._model == "qwen-plus"


def test_analyzer_init_custom():
    analyzer = LLMAnalyzer(api_key="test", model="gpt-4o", base_url="http://custom")
    assert analyzer._model == "gpt-4o"
    assert analyzer._base_url == "http://custom"
