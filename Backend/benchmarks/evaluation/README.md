# HackGrid Benchmark Evaluation

## Purpose

This evaluation framework measures the reliability of the HackGrid
evidence-aware decision pipeline.

## Evaluation Dimensions

1. Pipeline reliability
2. Evidence classification
3. Evidence status
4. Evidence strength
5. Claim-to-evidence grounding
6. Unsupported claims
7. Invalid evidence references
8. Absence handling
9. Gap analysis
10. Risk escalation
11. Human-review decisions
12. Audit completeness

## Core Principle

The language model is not treated as the source of truth.

Evidence retrieved from the knowledge base is the primary factual basis.

The evaluation therefore distinguishes:

- retrieval
- classification
- evidence sufficiency
- grounding
- governance
- final synthesis

## Safety Principle

Failure to retrieve evidence must not be interpreted as proof
that a regulation, requirement, or policy does not exist.

## Benchmark Artifacts

- benchmark_results.json
- benchmark_metrics.json
- grounding_validation.json
- gold_evaluation.json
- research_scorecard.json

## Models

Embedding model:

BAAI/bge-m3

Generative model:

openai/gpt-oss-120b

## Retrieval

FAISS

Validated knowledge base:

14,143 chunks

Embedding dimension:

1,024

## Evaluation Version

research-scorecard-v1