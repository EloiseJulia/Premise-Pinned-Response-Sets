# Premise-Pinned Response Sets

This repository contains the execution materials for a short, reproducible pilot on premise-pinned response sets (PPRS). The study asks whether judge-rating uncertainty hidden by stable sampling can be exposed by fixing the unstated rubric premises a judge identifies for itself.

## Start Here

- [Proposal and implementation specification](开题报告-Premise-Pinned-Response-Sets-实施规格.md) is the binding research baseline.
- [Research roadmap](docs/plans/research-roadmap.md) defines the work packages, dependencies, and acceptance gates.
- [AI-native research workflow](ai-native-workflow/AI-Native-Workflow.md) defines how agents plan, execute, audit, and hand off work.

## Study Contract

The primary comparison is between forced-choice sampling, self-reported response sets, and premise-pinned response sets. The locked datasets are ChaosNLI SNLI, ChaosNLI MNLI, and SummEval-Relevance. The study must preserve raw provider responses and explicit parse failures, use idempotent caching, freeze a preregistration before the full run, and regenerate every reported figure from raw Parquet data.

Generated provider outputs, caches, local credentials, and large artifacts remain outside Git. This repository stores code, locked configuration, documentation, run manifests, and hashes needed to reproduce the analysis.

## Status

The repository currently contains the proposal baseline, research governance, and the implementation roadmap. The next gated action is Phase 1: inspect the upstream indeterminacy repository to record its SummEval discretization exactly, then create the executable project skeleton and dependency lock.