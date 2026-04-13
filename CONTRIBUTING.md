# Contributing

This repository is a CSC-343 **team AI system** project. Use these practices so graders (and teammates) can follow your work.

## Roadmap and phased work

Larger improvements follow **[docs/project_improvement_plan.md](docs/project_improvement_plan.md)** (RL narrative, Module 6 hardening, pipeline tooling, reporting, CI fixtures, typing, docs, and fleet summary JSON). **Module 5** is documented there as **future work**; it is **not scheduled** for the current repo. Work is done **one phase at a time** with review/approval before starting the next phase.

**Full stack locally:** from the repo root, `make pipeline` runs Modules 1–4 and 6 with bundled demo data and refreshes `outputs/report.html` (see README and the `Makefile`).

## Commits

- Write **meaningful commit messages** (imperative mood, one line summary; optional body for context).
- Prefer **small, focused commits** (one logical change per commit when practical).
- Avoid “empty” or bulk commits that only touch whitespace unless that is the actual task.

## Branches and pull requests

- Use a **feature branch** for each module, fix, or report update (e.g. `module-4-production-schedule`).
- Open a **pull request** for merges to `main`; include a short description of what changed and why.
- Resolve **merge conflicts** on the branch before requesting review.

## Issues (optional but helpful)

- Use **GitHub Issues** (or team checklist) for checkpoint tasks: rubric reports, integration tests, demo prep.

## Code review

- Run tests before merging: **`make test`** (or **`pytest unit_tests integration_tests`**). **`make test`** prefers **`.venv/bin/python`** when that file exists—create the venv once with `python3 -m venv .venv` and `.venv/bin/pip install -r requirements.txt` so Homebrew/system Python does not need pytest installed globally.
- After changing **`src/equipment_monitoring/`**, run **`make typecheck`** (or **`mypy`**) so the full-package mypy configuration in **`pyproject.toml`** stays green.
- Keep **Module boundaries** clear: new behavior should live in the right `moduleN` package with matching tests under `unit_tests/moduleN/` or `integration_tests/moduleN/`.
- **CI:** pushes and PRs to **`main`** / **`master`** run **`.github/workflows/ci.yml`** (`pytest` + `mypy`). Keep that workflow green before merge.
- **Module 6 / Checkpoint 6**: use a dedicated branch (e.g. `module-6-rl`); PR should mention `run_module6`, `mdp.json` changes, and link or attach **`checkpoint_6_elegance_report.md`** / **`checkpoint_6_module_report.md`** when submitting the checkpoint. Reviewer confirms green CI before merge.

## Participation

- Both teammates should have **substantive commits** (design, implementation, tests, or documentation), not only one person driving the branch history.
