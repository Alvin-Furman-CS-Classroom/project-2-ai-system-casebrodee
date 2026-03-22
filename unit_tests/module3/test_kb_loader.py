"""Unit tests for Module 3 knowledge-base loading (`kb_loader` module)."""

import json
from pathlib import Path

import pytest

from equipment_monitoring.module3.kb_loader import KnowledgeBaseError, load_kb, rules_by_id


def test_load_kb_valid(tmp_path: Path) -> None:
    """Load a minimal valid KB JSON."""
    path = tmp_path / "kb.json"
    path.write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "id": "r_test",
                        "priority": 50,
                        "antecedents": [["p", "?x"]],
                        "consequent": ["q", "?x"],
                        "inspection": "Check thing",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    rules = load_kb(path)
    assert len(rules) == 1
    assert rules[0].id == "r_test"
    assert rules[0].priority == 50
    assert rules[0].inspection == "Check thing"
    idx = rules_by_id(rules)
    assert idx["r_test"].consequent == ("q", "?x")


def test_load_kb_missing_rules_key(tmp_path: Path) -> None:
    path = tmp_path / "kb.json"
    path.write_text('{"not_rules": []}', encoding="utf-8")
    with pytest.raises(KnowledgeBaseError, match="rules"):
        load_kb(path)


def test_load_kb_rules_not_array(tmp_path: Path) -> None:
    path = tmp_path / "kb.json"
    path.write_text('{"rules": "bad"}', encoding="utf-8")
    with pytest.raises(KnowledgeBaseError, match="array"):
        load_kb(path)


def test_load_kb_rule_missing_id(tmp_path: Path) -> None:
    path = tmp_path / "kb.json"
    path.write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "priority": 1,
                        "antecedents": [["a", "x"]],
                        "consequent": ["b", "x"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(KnowledgeBaseError, match="id"):
        load_kb(path)


def test_load_kb_rule_empty_antecedents(tmp_path: Path) -> None:
    path = tmp_path / "kb.json"
    path.write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "id": "bad",
                        "antecedents": [],
                        "consequent": ["b", "x"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(KnowledgeBaseError, match="antecedents"):
        load_kb(path)


def test_load_kb_default_priority_and_inspection(tmp_path: Path) -> None:
    path = tmp_path / "kb.json"
    path.write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "id": "minimal",
                        "antecedents": [["a", "K"]],
                        "consequent": ["b", "K"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    rules = load_kb(path)
    assert rules[0].priority == 0
    assert rules[0].inspection == ""
