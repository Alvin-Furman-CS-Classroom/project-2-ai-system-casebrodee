"""
Unification and forward chaining for Module 3.

Variables are strings whose first character is ``?`` (e.g. ``?e``). All other
strings are constants. Atoms are tuples ``(predicate, arg1, arg2, ...)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

Atom = Tuple[str, ...]


def is_var(s: str) -> bool:
    return isinstance(s, str) and len(s) > 0 and s[0] == "?"


def atom_from_list(parts: Sequence[str]) -> Atom:
    if not parts:
        raise ValueError("atom must have a predicate")
    return tuple(parts)


def substitute_atom(atom: Atom, theta: Mapping[str, str]) -> Atom:
    """Apply substitution to variables in atom arguments (not predicate name)."""
    pred = atom[0]
    args = []
    for a in atom[1:]:
        if is_var(a):
            if a not in theta:
                args.append(a)
            else:
                args.append(theta[a])
        else:
            args.append(a)
    return (pred, *args)


def is_ground_atom(atom: Atom) -> bool:
    return not any(is_var(a) for a in atom[1:])


def apply_theta_symbol(x: str, theta: Mapping[str, str]) -> str:
    if is_var(x) and x in theta:
        return theta[x]
    return x


def unify_terms(x: str, y: str, theta: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """
    Unify two terms (constants or variables) under substitution theta.
    Returns extended theta or None if unification fails.
    """
    if theta is None:
        return None
    x = apply_theta_symbol(x, theta)
    y = apply_theta_symbol(y, theta)
    if x == y:
        return theta
    if is_var(x):
        return _unify_var(x, y, theta)
    if is_var(y):
        return _unify_var(y, x, theta)
    return None


def _occurs_check(var: str, term: str, theta: Mapping[str, str]) -> bool:
    t = apply_theta_symbol(term, theta)
    return var == t


def _unify_var(var: str, x: str, theta: Dict[str, str]) -> Optional[Dict[str, str]]:
    if var in theta:
        return unify_terms(theta[var], x, theta)
    if x in theta:
        return unify_terms(var, theta[x], theta)
    if _occurs_check(var, x, theta):
        return None
    out = dict(theta)
    out[var] = x
    return out


def unify_atoms(a1: Atom, a2: Atom, theta: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """Unify two atoms (may contain variables on both sides)."""
    if theta is None:
        return None
    if len(a1) != len(a2) or a1[0] != a2[0]:
        return None
    for t1, t2 in zip(a1[1:], a2[1:]):
        theta = unify_terms(t1, t2, theta)
        if theta is None:
            return None
    return theta


def match_atom(pattern: Atom, fact: Atom, theta: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """
    Match a (possibly non-ground) pattern atom against a ground fact.
    Fact must be fully ground. Extends theta or returns None.
    """
    if theta is None:
        return None
    if pattern[0] != fact[0] or len(pattern) != len(fact):
        return None
    out = dict(theta)
    for p, f in zip(pattern[1:], fact[1:]):
        if is_var(p):
            if p in out:
                if out[p] != f:
                    return None
            else:
                out[p] = f
        elif p != f:
            return None
    return out


@dataclass(frozen=True)
class Rule:
    id: str
    priority: int
    antecedents: Tuple[Atom, ...]
    consequent: Atom
    inspection: str


def _derive_from_rule(rule: Rule, facts: Set[Atom]) -> List[Tuple[Atom, Tuple[Atom, ...]]]:
    """
    For one rule, find all ground consequents provable from facts.
    Returns list of (consequent, antecedent_tuple_grounded) for explanation.
    """
    results: List[Tuple[Atom, Tuple[Atom, ...]]] = []
    ant = rule.antecedents

    def dfs(i: int, theta: Dict[str, str]) -> None:
        if i >= len(ant):
            conc = substitute_atom(rule.consequent, theta)
            if not is_ground_atom(conc):
                return
            parents = tuple(substitute_atom(a, theta) for a in ant)
            results.append((conc, parents))
            return
        pat = ant[i]
        g = substitute_atom(pat, theta)
        if is_ground_atom(g):
            if g in facts:
                dfs(i + 1, theta)
            return
        for fact in facts:
            th2 = match_atom(pat, fact, theta)
            if th2 is not None:
                dfs(i + 1, th2)

    dfs(0, {})
    return results


def forward_chain(
    facts: Set[Atom],
    rules: Sequence[Rule],
    max_iterations: int = 500,
) -> Tuple[Set[Atom], Dict[Atom, Tuple[str, Tuple[Atom, ...]]]]:
    """
    Forward chaining to fixpoint. Rules are tried in descending priority order.

    Returns:
        - Closed set of facts
        - Provenance: derived fact -> (rule_id, ground antecedent tuple)
    """
    closed: Set[Atom] = set(facts)
    provenance: Dict[Atom, Tuple[str, Tuple[Atom, ...]]] = {}
    ordered = sorted(rules, key=lambda r: r.priority, reverse=True)

    for _ in range(max_iterations):
        added = False
        for rule in ordered:
            for conc, parents in _derive_from_rule(rule, closed):
                if conc not in closed:
                    closed.add(conc)
                    provenance[conc] = (rule.id, parents)
                    added = True
        if not added:
            break
    else:
        raise RuntimeError("forward_chain exceeded max_iterations; check rules for a loop")

    return closed, provenance


def collect_suggests(facts: Iterable[Atom]) -> List[Atom]:
    """Return ground atoms with predicate ``suggests``."""
    return sorted(f for f in facts if f[0] == "suggests" and is_ground_atom(f))
