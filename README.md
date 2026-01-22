# Industrial Equipment Monitoring & Predictive Maintenance System

## Overview

This system monitors industrial equipment (motors, pumps, bearings) using sensor data (temperature, vibration, pressure) to detect anomalies and predict failures before breakdowns occur. It starts with simple rule-based checks and then adds more sophisticated layers: searching for complex failure patterns, reasoning about root causes, optimizing maintenance schedules, learning to classify problems automatically, and adapting responses over time based on outcomes.

Equipment monitoring uses core AI techniques: propositional logic defines normal operating conditions, search algorithms find multi-step degradation patterns, first-order logic connects symptoms to causes, optimization balances maintenance costs against downtime risks, supervised learning discovers failure patterns, and reinforcement learning adapts maintenance strategies. The system uses publicly available datasets (NASA CMAPSS, Kaggle PHM datasets) that simulate real industrial scenarios, which makes it practical to build without needing actual factory equipment or domain experience.

## Team

- [Team member names to be added]

## Proposal

# Industrial Equipment Monitoring & Predictive Maintenance System - Final Proposal

## System Overview

This system monitors industrial equipment (motors, pumps, bearings) using sensor data (temperature, vibration, pressure) to detect anomalies and predict failures before breakdowns occur. It starts with simple rule-based checks and then adds more sophisticated layers: searching for complex failure patterns, reasoning about root causes, optimizing maintenance schedules, learning to classify problems automatically, and adapting responses over time based on outcomes.

Equipment monitoring uses core AI techniques: propositional logic defines normal operating conditions, search algorithms find multi-step degradation patterns, first-order logic connects symptoms to causes, optimization balances maintenance costs against downtime risks, supervised learning discovers failure patterns, and reinforcement learning adapts maintenance strategies. The system uses publicly available datasets (NASA CMAPSS, Kaggle PHM datasets) that simulate real industrial scenarios, which makes it practical to build without needing actual factory equipment or domain experience.

## Modules

### Module 1: Basic Rule-Based Monitoring

**Topics:** Propositional Logic (Knowledge Bases, Inference Methods)

**Input:** 
- Configuration file (JSON format): `{"temperature": {"min": 20, "max": 80}, "vibration": {"max": 5.0}, "pressure": {"min": 10, "max": 50}}`
- Sensor readings CSV: columns `timestamp, temperature, vibration, pressure` with numeric values
- Equipment specifications (JSON): normal operating condition ranges per equipment type

**Output:** 
- Per-reading classification: `{"timestamp": "...", "status": "normal" or "anomaly", "violated_rules": ["temperature_high"], "confidence": 0.85}`
- Alert messages (text format): formatted list of all detected issues with timestamps

**Integration:** This is the foundation module that provides baseline detection. It generates the initial dataset of flagged anomalies. Later modules catch problems these rules miss and reduce false alarms.

**Prerequisites:** Propositional Logic (Week 1.5)

---

### Module 2: Failure Pattern Discovery

**Topics:** Uninformed Search (BFS, DFS), Informed Search (A*, Heuristics)

**Input:** 
- Historical sensor data from Module 1 marked with known failure events
- Graph structure representing equipment states and transitions between them
- Search parameters defining how far back to look and pattern length requirements

**Output:** 
- Discovered sequences of sensor changes that precede failures, with frequency and timing statistics
- Visualizations showing how equipment degrades over time
- Ranked list of warning signs sorted by how often they predict actual failures

**Integration:** Finds subtle patterns that threshold checks miss (e.g., three-day sequence of vibration increases predicts bearing failure). This helps Module 3's reasoning and provides labeled training data for Module 5.

**Prerequisites:** Module 1; Search algorithms (Week 3)

---

### Module 3: Equipment Diagnosis System

**Topics:** First-Order Logic (Quantifiers, Unification, Inference)

**Input:** 
- Knowledge base encoding relationships between symptoms and causes (e.g., high temperature combined with low pressure indicates cooling system failure; bearing wear causes vibration increases)
- Current equipment state and sensor readings from Modules 1-2
- Detected anomalies with timestamps

**Output:** 
- Inferred diagnosis of likely failures with confidence scores
- Explanation chains showing logical reasoning steps
- Priority ranking when multiple problems are possible
- Recommended inspection points for verification

**Integration:** Takes raw anomaly detections and adds reasoning to them. Instead of just saying "temperature high," it figures out why and what might fail next. This reduces false alarms by distinguishing when multiple issues indicate one root cause versus separate problems.

**Prerequisites:** Modules 1-2; First-Order Logic (Week 6)

---

### Module 4: Maintenance Schedule Optimizer

**Topics:** Advanced Search (Hill Climbing, Simulated Annealing), Game Theory (Minimax, Nash Equilibrium)

**Input:** 
- Current equipment health assessments from Module 3 with failure probabilities
- Available maintenance actions with costs, time requirements, and effectiveness
- Production schedule showing when downtime is acceptable
- Cost parameters including failure costs, downtime costs, and maintenance budget

**Output:** 
- Optimized maintenance schedule balancing prevention versus cost, with expected savings calculations
- Trade-off analysis showing risk versus expense for different scheduling strategies
- Contingency plans for different failure scenarios

**Integration:** Turns Module 3 diagnostics into actionable maintenance decisions. Uses optimization search (hill climbing, simulated annealing) to explore the space of possible maintenance schedules. Game theory models the competitive dynamics between two actors: the decision-maker trying to minimize costs while maintaining safety, and the degradation process (nature as an adversarial player) that threatens equipment at unpredictable times. Minimax evaluates worst-case scenarios while Nash equilibrium concepts help find stable strategies that balance risk tolerance against budget constraints.

**Prerequisites:** Modules 1-3; Advanced Search (Week 7.5), Game Theory (Week 9)

---

### Module 5: Automated Failure Classifier

**Topics:** Supervised Learning (Logistic Regression, Evaluation Metrics, Neural Networks)

**Input:** 
- Labeled dataset of sensor readings marked as normal or one of several failure types
- Feature engineering pipeline extracting relevant patterns from time windows
- Training parameters and cross-validation settings

**Output:** 
- Trained model with accuracy, precision, and recall scores for each failure type
- Confusion matrix showing which failures get mistaken for others
- Real-time predictions with confidence percentages for incoming sensor data
- Performance comparison against Module 1's rule-based approach

**Integration:** Replaces the rigid rules from Module 1 with learned patterns that adapt to different equipment. Can detect novel failure modes that weren't anticipated when writing the original rules. Feeds its predictions to Module 6 for adaptive learning.

**Prerequisites:** Modules 1-4; Supervised Learning (foundational concepts by Week 11, advanced techniques Week 12+)

---

### Module 6: Adaptive Monitoring System

**Topics:** Reinforcement Learning (MDP, Q-Learning, Policy Functions)

**Input:** 
- Environment state including equipment metrics, recent maintenance actions, and current detection thresholds
- Reward function that penalizes missed failures heavily, penalizes false alarms moderately, and accounts for maintenance costs
- Historical feedback data showing which alerts led to finding real problems versus false alarms

**Output:** 
- Learned policy for adjusting detection thresholds and alert priorities based on experience
- Adaptation history showing performance improvements over time (reduction in false alarms and missed detections)
- Performance metrics and visualization data demonstrating system learning

**Integration:** Completes the feedback loop by learning from experience. When alerts find nothing wrong, the system reduces sensitivity in similar situations. When failures occur without warning, it learns to detect earlier warning signs. This makes the system self-improving rather than static.

**Prerequisites:** Modules 1-5; Reinforcement Learning (Week 12+)

---

## Feasibility Study

_A timeline showing that each module's prerequisites align with the course schedule. Verify that you are not planning to implement content before it is taught._

| Module | Required Topic(s) | Topic Covered By | Checkpoint Due |
| ------ | ----------------- | ---------------- | -------------- |
| 1      | Propositional Logic | Week 1.5 | Checkpoint 1 (Week 3) |
| 2      | Search Algorithms | Week 3 | Checkpoint 2 (Week 5) |
| 3      | First-Order Logic | Week 6 | Checkpoint 3 (Week 7) |
| 4      | Advanced Search, Game Theory | Weeks 7.5, 9 | Checkpoint 4 (Week 9) |
| 5      | Supervised Learning (foundational) | Week 11 (foundational concepts), Week 12+ (advanced) | Checkpoint 5 (Week 11) |
| 6      | Reinforcement Learning | Week 12+ | Checkpoint 6 (Week 13) |

**Note on Module 4 timing:** Module 4 will start with Advanced Search algorithms (Week 7.5), which gives me time to make good progress before Game Theory content is covered in Week 9. Game Theory concepts will be added as I learn them, with the checkpoint submission including the optimization search components and initial game theory framework.

**Note on Module 5 timing:** Module 5 will start with foundational supervised learning concepts (classification basics, evaluation metrics) that are typically introduced by Week 11, which lets me start implementation at Checkpoint 5. Advanced techniques (neural networks, deep learning) from Week 12+ can be added as enhancements if I have time.

## Coverage Rationale

This system covers six modules using seven core AI topics: Propositional Logic, Search, First-Order Logic, Advanced Search, Game Theory, Supervised Learning, and Reinforcement Learning. These topics fit naturally with the progression from simple to sophisticated monitoring systems, similar to how industrial monitoring has evolved in practice.

We start with basic logic rules because that's how real equipment monitoring began. Search algorithms find complex patterns humans might miss. First-order logic reasons about relationships and causes, not just individual sensor readings. Optimization and game theory balance competing concerns (cost vs. safety, maintenance vs. downtime). Supervised learning automates pattern recognition at scale. Reinforcement learning enables continuous improvement from experience.

The system doesn't include NLP and CNNs. While these could analyze maintenance logs or visualize sensor data as images, they would add complexity without really strengthening the core monitoring pipeline. The topics I chose create a cohesive story focused on detection, diagnosis, and decision-making under uncertainty—which is what industrial monitoring is really about. Each module naturally leads to the next by showing limitations that the subsequent technique addresses.

## Module Plan

| Module | Topic(s) | Inputs | Outputs | Depends On | Checkpoint |
| ------ | -------- | ------ | ------- | ---------- | ---------- |
| 1 | Propositional Logic | Configuration file (JSON), Sensor readings CSV, Equipment specifications (JSON) | Per-reading classification (JSON), Alert messages (text) | None | Checkpoint 1 (Week 3) |
| 2 | Uninformed Search (BFS, DFS), Informed Search (A*, Heuristics) | Historical sensor data with failure events, Graph structure, Search parameters | Discovered failure sequences, Visualizations, Ranked warning signs | Module 1 | Checkpoint 2 (Week 5) |
| 3 | First-Order Logic (Quantifiers, Unification, Inference) | Knowledge base, Equipment state and sensor readings, Detected anomalies | Inferred diagnosis with confidence, Explanation chains, Priority ranking, Inspection recommendations | Modules 1-2 | Checkpoint 3 (Week 7) |
| 4 | Advanced Search (Hill Climbing, Simulated Annealing), Game Theory (Minimax, Nash Equilibrium) | Equipment health assessments, Maintenance actions, Production schedule, Cost parameters | Optimized maintenance schedule, Trade-off analysis, Contingency plans | Modules 1-3 | Checkpoint 4 (Week 9) |
| 5 | Supervised Learning (Logistic Regression, Evaluation Metrics, Neural Networks) | Labeled dataset, Feature engineering pipeline, Training parameters | Trained model with metrics, Confusion matrix, Real-time predictions, Performance comparison | Modules 1-4 | Checkpoint 5 (Week 11) |
| 6 | Reinforcement Learning (MDP, Q-Learning, Policy Functions) | Environment state, Reward function, Historical feedback data | Learned policy, Adaptation history, Performance metrics | Modules 1-5 | Checkpoint 6 (Week 13) |

## Repository Layout

```
your-repo/
├── src/                              # main system source code
├── unit_tests/                       # unit tests (parallel structure to src/)
├── integration_tests/                # integration tests (new folder for each module)
├── .claude/skills/code-review/SKILL.md  # rubric-based agent review
├── AGENTS.md                         # instructions for your LLM agent
└── README.md                         # system overview and checkpoints
```

## Setup

List dependencies, setup steps, and any environment variables required to run the system.

## Running

Provide commands or scripts for running modules and demos.

## Testing

**Unit Tests** (`unit_tests/`): Mirror the structure of `src/`. Each module should have corresponding unit tests.

**Integration Tests** (`integration_tests/`): Create a new subfolder for each module beyond the first, demonstrating how modules work together.

Provide commands to run tests and describe any test data needed.

## Checkpoint Log

| Checkpoint | Date | Modules Included | Status | Evidence |
| ---------- | ---- | ---------------- | ------ | -------- |
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |
| 6 |  |  |  |  |

## Required Workflow (Agent-Guided)

Before each module:

1. Write a short module spec in this README (inputs, outputs, dependencies, tests).
2. Ask the agent to propose a plan in "Plan" mode.
3. Review and edit the plan. You must understand and approve the approach.
4. Implement the module in `src/`.
5. Unit test the module, placing tests in `unit_tests/` (parallel structure to `src/`).
6. For modules beyond the first, add integration tests in `integration_tests/` (new subfolder per module).
7. Run a rubric review using the code-review skill at `.claude/skills/code-review/SKILL.md`.

Keep `AGENTS.md` updated with your module plan, constraints, and links to APIs/data sources.

## References

- NASA CMAPSS (Commercial Modular Aero-Propulsion System Simulation) dataset
- Kaggle PHM (Prognostics and Health Management) datasets
- Project Instructions: https://csc-343.path.app/projects/project-2-ai-system/ai-system.project.md
- Code elegance rubric: https://csc-343.path.app/rubrics/code-elegance.rubric.md
- Course schedule: https://csc-343.path.app/resources/course.schedule.md
- Rubric: https://csc-343.path.app/projects/project-2-ai-system/ai-system.rubric.md
