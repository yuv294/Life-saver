"""Parsing/validation of Gemini's classification output (no network, no API key)."""

import json

from services.gemini_service import VALID_SKILL_TAGS, parse_classification


def raw(**overrides):
    data = {
        "skill_tags": ["analytical", "creative"], "primary_skill": "analytical",
        "complexity": "high", "eisenhower_quadrant": 1, "importance": "high", "urgency": "low",
    }
    data.update(overrides)
    return json.dumps(data)


def test_plain_json():
    out = parse_classification(raw())
    assert out["skill_tags"] == ["analytical", "creative"]
    assert out["primary_skill"] == "analytical"
    assert out["complexity"] == "high"
    assert out["_source"] == "gemini"


def test_json_wrapped_in_a_json_code_fence():
    out = parse_classification("```json\n" + raw() + "\n```")
    assert out["skill_tags"] == ["analytical", "creative"]


def test_json_wrapped_in_a_bare_code_fence_with_trailing_whitespace():
    out = parse_classification("```\n" + raw() + "\n```  \n")
    assert out["complexity"] == "high"


def test_unknown_tags_are_dropped_and_duplicates_removed():
    out = parse_classification(raw(skill_tags=["Analytical", "magic", "analytical", 7]))
    assert out["skill_tags"] == ["analytical"]


def test_no_valid_tags_falls_back_to_administrative():
    out = parse_classification(raw(skill_tags=["nonsense"], primary_skill="nonsense"))
    assert out["skill_tags"] == ["administrative"]
    assert out["primary_skill"] == "administrative"


def test_invalid_levels_and_quadrant_are_coerced():
    out = parse_classification(raw(complexity="extreme", importance=None, urgency="HIGH", eisenhower_quadrant=9))
    assert out["complexity"] == "medium"
    assert out["importance"] == "medium"
    assert out["urgency"] == "high"
    assert out["eisenhower_quadrant"] == 2


def test_primary_skill_must_be_valid():
    out = parse_classification(raw(primary_skill="wizardry"))
    assert out["primary_skill"] in VALID_SKILL_TAGS


def test_non_json_raises_so_the_caller_can_use_heuristics():
    for bad in ("Sorry, I can't help with that.", "", "[1, 2, 3]"):
        try:
            parse_classification(bad)
        except json.JSONDecodeError:
            continue
        raise AssertionError(f"expected JSONDecodeError for {bad!r}")
