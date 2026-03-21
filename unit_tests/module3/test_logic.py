"""Unit tests for Module 3 unification and forward chaining."""

import pytest

from equipment_monitoring.module3.logic import (
    Rule,
    atom_from_list,
    forward_chain,
    match_atom,
    substitute_atom,
    unify_atoms,
)


def test_unify_atoms_two_vars() -> None:
    a1 = atom_from_list(["p", "?x", "?y"])
    a2 = atom_from_list(["p", "M1", "?z"])
    th = unify_atoms(a1, a2, {})
    assert th is not None
    assert th["?x"] == "M1"
    assert th["?y"] == "?z"


def test_unify_atoms_clash() -> None:
    a1 = atom_from_list(["p", "?x", "a"])
    a2 = atom_from_list(["p", "M1", "b"])
    assert unify_atoms(a1, a2, {}) is None


def test_substitute_atom() -> None:
    a = atom_from_list(["suggests", "?e", "hypo"])
    g = substitute_atom(a, {"?e": "pump_1"})
    assert g == ("suggests", "pump_1", "hypo")


def test_match_atom() -> None:
    pat = atom_from_list(["violated", "?e", "vibration_high"])
    fact = ("violated", "M1", "vibration_high")
    th = match_atom(pat, fact, {})
    assert th == {"?e": "M1"}


def test_forward_chain_simple() -> None:
    rules = [
        Rule(
            id="r1",
            priority=10,
            antecedents=(atom_from_list(["a", "?x"]),),
            consequent=atom_from_list(["b", "?x"]),
            inspection="",
        )
    ]
    facts = {("a", "K1")}
    closed, prov = forward_chain(facts, rules)
    assert ("b", "K1") in closed
    assert prov[("b", "K1")][0] == "r1"


def test_forward_chain_shared_variable() -> None:
    rules = [
        Rule(
            id="chain",
            priority=5,
            antecedents=(
                atom_from_list(["p", "?e", "v1"]),
                atom_from_list(["q", "?e", "v2"]),
            ),
            consequent=atom_from_list(["suggests", "?e", "both"]),
            inspection="inspect",
        )
    ]
    facts = {("p", "E1", "v1"), ("q", "E1", "v2")}
    closed, _ = forward_chain(facts, rules)
    assert ("suggests", "E1", "both") in closed
