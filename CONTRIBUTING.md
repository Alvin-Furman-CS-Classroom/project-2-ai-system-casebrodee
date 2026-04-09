# Contributing

This repository is a CSC-343 **team AI system** project. Use these practices so graders (and teammates) can follow your work.

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

- Run **`pytest unit_tests integration_tests`** before merging.
- Keep **Module boundaries** clear: new behavior should live in the right `moduleN` package with matching tests under `unit_tests/moduleN/` or `integration_tests/moduleN/`.
- **Module 6 / Checkpoint 6**: use a dedicated branch (e.g. `module-6-rl`); PR should mention `run_module6`, `mdp.json` changes, and link or attach **`checkpoint_6_elegance_report.md`** / **`checkpoint_6_module_report.md`** when submitting the checkpoint. Reviewer confirms green CI (full pytest) before merge.

## Participation

- Both teammates should have **substantive commits** (design, implementation, tests, or documentation), not only one person driving the branch history.
