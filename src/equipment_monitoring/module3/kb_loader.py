"""Load knowledge-base JSON into Rule objects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .logic import Rule, atom_from_list


class KnowledgeBaseError(ValueError):
    pass


def load_kb(path: str | Path) -> List[Rule]:
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or "rules" not in data:
        raise KnowledgeBaseError("KB JSON must be an object with a 'rules' array")
    rules_raw = data["rules"]
    if not isinstance(rules_raw, list):
        raise KnowledgeBaseError("'rules' must be an array")

    rules: List[Rule] = []
    for i, r in enumerate(rules_raw):
        if not isinstance(r, dict):
            raise KnowledgeBaseError(f"rules[{i}] must be an object")
        rid = r.get("id")
        if not rid or not isinstance(rid, str):
            raise KnowledgeBaseError(f"rules[{i}] needs string 'id'")
        priority = int(r.get("priority", 0))
        ant_raw = r.get("antecedents")
        cons_raw = r.get("consequent")
        if not isinstance(ant_raw, list) or not ant_raw:
            raise KnowledgeBaseError(f"rules[{i}] needs non-empty 'antecedents' list")
        if not isinstance(cons_raw, list) or not cons_raw:
            raise KnowledgeBaseError(f"rules[{i}] needs 'consequent' list")
        try:
            antecedents = tuple(atom_from_list([str(x) for x in a]) for a in ant_raw)
            consequent = atom_from_list([str(x) for x in cons_raw])
        except (TypeError, ValueError) as e:
            raise KnowledgeBaseError(f"rules[{i}] invalid atom: {e}") from e
        inspection = str(r.get("inspection", ""))
        rules.append(
            Rule(
                id=rid,
                priority=priority,
                antecedents=antecedents,
                consequent=consequent,
                inspection=inspection,
            )
        )
    return rules


def rules_by_id(rules: List[Rule]) -> Dict[str, Rule]:
    return {r.id: r for r in rules}
