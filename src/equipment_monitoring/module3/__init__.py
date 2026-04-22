"""
Module 3: First-order style diagnosis via unification and forward chaining.

- Loads an editable JSON knowledge base (Horn-style rules).
- Builds ground facts from Module 1 classifications and Module 2 sequences / warning signs.
- Runs forward chaining with unification; produces ranked diagnoses and explanation chains.
"""

from .runner import infer_batch, run_module3

__all__ = ["infer_batch", "run_module3"]
