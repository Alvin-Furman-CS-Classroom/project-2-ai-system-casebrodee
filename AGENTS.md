## Project Context

- System title: Industrial Equipment Monitoring & Predictive Maintenance System
- Theme: Rule-based and AI-driven monitoring of industrial equipment using sensor data.
- Proposal link or summary: See `PROPOSAL.md` (Industrial Equipment Monitoring & Predictive Maintenance System - Final Proposal).

**Module plan:**

| Module | Topic(s) | Inputs | Outputs | Depends On | Checkpoint |
| ------ | -------- | ------ | ------- | ---------- | ---------- |
| 1 | Propositional Logic | Configuration file (JSON), Sensor readings CSV, Equipment specifications (JSON) | Per-reading classification (JSON), Alert messages (text) | None | Checkpoint 1 (Week 3) |
| 2 | Uninformed Search (BFS, DFS), Informed Search (A*, Heuristics) | Historical sensor data with failure events, Graph structure, Search parameters | Discovered failure sequences, Visualizations, Ranked warning signs | Module 1 | Checkpoint 2 (Week 5) |
| 3 | First-Order Logic (Quantifiers, Unification, Inference) | Knowledge base, Equipment state and sensor readings, Detected anomalies | Inferred diagnosis with confidence, Explanation chains, Priority ranking, Inspection recommendations | Modules 1-2 | Checkpoint 3 (Week 7) |
| 4 | Advanced Search (Hill Climbing, Simulated Annealing), Game Theory (Minimax, Nash Equilibrium) | Equipment health assessments, Maintenance actions, Production schedule, Cost parameters | Optimized maintenance schedule, Trade-off analysis, Contingency plans | Modules 1-3 | Checkpoint 4 (Week 9) |
| 5 | Supervised Learning (Logistic Regression, Evaluation Metrics, Neural Networks) | Labeled dataset, Feature engineering pipeline, Training parameters | Trained model with metrics, Confusion matrix, Real-time predictions, Performance comparison | Modules 1-4 | Checkpoint 5 (Week 11) |
| 6 | Reinforcement Learning (MDP, Q-Learning, Policy Functions) | Environment state, Reward function, Historical feedback data | Learned policy, Adaptation history, Performance metrics | Modules 1-5 | Checkpoint 6 (Week 13) |

## Constraints

- 5-6 modules total, each tied to course topics.
- Each module must have clear inputs/outputs and tests.
- Align module timing with the course schedule.

## How the Agent Should Help

- Draft plans for each module before coding.
- Suggest clean architecture and module boundaries.
- Identify missing tests and edge cases.
- Review work against the rubric using the code-review skill.

## Agent Workflow

1. Ask for the current module spec from `README.md`.
2. Produce a plan (use "Plan" mode if available).
3. Wait for approval before writing or editing code.
4. After implementation, run the code-review skill and list gaps.

## Key References

- Project Instructions: https://csc-343.path.app/projects/project-2-ai-system/ai-system.project.md
- Code elegance rubric: https://csc-343.path.app/rubrics/code-elegance.rubric.md
- Course schedule: https://csc-343.path.app/resources/course.schedule.md
- Rubric: https://csc-343.path.app/projects/project-2-ai-system/ai-system.rubric.md
