# backend/orchestrator.py

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict

from .network_agent import network_agent
from .compliance_agent import compliance_agent
from .policy_agent import policy_agent
from .gap_analysis_agent import gap_analysis_agent

# GPT-OSS backend
from .gptoss_backend import generate_gptoss

# EXISTING Risk & Governance engine
from Backend.risk_integration import assess_rag_result


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger(__name__)

if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )


# ============================================================
# FINAL SYNTHESIS PROMPT
# ============================================================

FINAL_SYNTHESIS_PROMPT = """
You are the final decision-intelligence synthesizer for HackGrid.

HackGrid is an evidence-first AI system. You MUST distinguish:

1. Verified facts directly supported by retrieved evidence.
2. Evidence-supported inferences.
3. AI analytical interpretation.
4. Unknown / unresolved issues.

Do NOT convert an evidence gap into a negative fact.

Do NOT invent:
- standards requirements
- incidents
- regulations
- technical facts
- causes
- timelines
- recommendations presented as mandatory requirements

The specialist agents have already analyzed the query.

Your task is to synthesize their outputs into one rigorous final assessment.

QUESTION:
{question}

NETWORK ANALYSIS:
{network}

COMPLIANCE ANALYSIS:
{compliance}

POLICY ANALYSIS:
{policy}

GAP ANALYSIS:
{gap}

FINAL RESPONSE REQUIREMENTS:

A. EXECUTIVE ASSESSMENT
Give a concise answer to the original question.

B. KEY FINDINGS
List the most important findings.

C. SUPPORTING EVIDENCE
Explain which findings are directly supported by evidence.

D. CONTRADICTING OR CONFLICTING EVIDENCE
Explicitly mention evidence that weakens, conflicts with, or limits a conclusion.
If none is available, say so.

E. EVIDENCE GAPS
Identify what cannot currently be established from the available evidence.

F. ANALYTICAL ASSESSMENT
Clearly separate inference/analysis from verified facts.

G. RECOMMENDATION
Give practical next steps, but do not present an AI recommendation as a legal,
regulatory, or mandatory requirement unless the evidence explicitly establishes it.

H. CONFIDENCE
Give:
- Evidence confidence
- Analytical confidence

Do NOT confuse AI confidence with decision authority.

Keep the answer precise, evidence-grounded, and suitable for professional review.
"""


# ============================================================
# SAFE AGENT EXECUTION
# ============================================================

def _run_agent(
    agent_name: str,
    agent_function,
    question: str
) -> Dict[str, Any]:
    """
    Runs one specialist agent safely.

    A failure in one specialist agent should NOT crash the
    complete HackGrid pipeline.
    """

    start_time = time.perf_counter()

    try:
        logger.info(
            "[AGENT START] %s",
            agent_name
        )

        result = agent_function(question)

        elapsed = time.perf_counter() - start_time

        logger.info(
            "[AGENT COMPLETE] %s | %.2fs",
            agent_name,
            elapsed
        )

        return {
            "agent": agent_name,
            "status": "success",
            "elapsed_seconds": round(elapsed, 2),
            "result": result
        }

    except Exception as exc:

        elapsed = time.perf_counter() - start_time

        logger.exception(
            "[AGENT FAILED] %s | %.2fs",
            agent_name,
            elapsed
        )

        return {
            "agent": agent_name,
            "status": "error",
            "elapsed_seconds": round(elapsed, 2),
            "error": str(exc),
            "result": None
        }


# ============================================================
# PARALLEL SPECIALIST AGENTS
# ============================================================

def run_specialist_agents(question: str) -> Dict[str, Any]:
    """
    Run Network, Compliance and Policy agents concurrently.

    These agents are independent of one another, so running
    them in parallel significantly reduces end-to-end latency.
    """

    results = {
        "network": None,
        "compliance": None,
        "policy": None
    }

    agents = {
        "network": network_agent,
        "compliance": compliance_agent,
        "policy": policy_agent
    }

    start_time = time.perf_counter()

    logger.info(
        "[SPECIALISTS] Starting 3 parallel specialist agents"
    )

    with ThreadPoolExecutor(max_workers=3) as executor:

        future_map = {
            executor.submit(
                _run_agent,
                name,
                function,
                question
            ): name
            for name, function in agents.items()
        }

        for future in as_completed(future_map):

            agent_name = future_map[future]

            try:
                result = future.result()

                results[agent_name] = result

            except Exception as exc:

                logger.exception(
                    "[SPECIALISTS] Unexpected failure in %s",
                    agent_name
                )

                results[agent_name] = {
                    "agent": agent_name,
                    "status": "error",
                    "error": str(exc),
                    "result": None
                }

    elapsed = time.perf_counter() - start_time

    logger.info(
        "[SPECIALISTS COMPLETE] %.2fs",
        elapsed
    )

    return results


# ============================================================
# GAP ANALYSIS
# ============================================================

def run_gap_analysis(
    question: str,
    specialist_results: Dict[str, Any]
) -> Dict[str, Any]:

    """
    Gap analysis runs after Network, Compliance and Policy
    because it needs their outputs.
    """

    start_time = time.perf_counter()

    network_result = specialist_results.get("network")

    compliance_result = specialist_results.get("compliance")

    policy_result = specialist_results.get("policy")

    # Extract actual agent outputs
    network_output = (
        network_result.get("result")
        if isinstance(network_result, dict)
        else network_result
    )

    compliance_output = (
        compliance_result.get("result")
        if isinstance(compliance_result, dict)
        else compliance_result
    )

    policy_output = (
        policy_result.get("result")
        if isinstance(policy_result, dict)
        else policy_result
    )

    logger.info("[GAP] Starting gap analysis")

    try:

        result = gap_analysis_agent(
            question=question,
            network_analysis=network_output,
            compliance_analysis=compliance_output,
            policy_analysis=policy_output
        )

        elapsed = time.perf_counter() - start_time

        logger.info(
            "[GAP COMPLETE] %.2fs",
            elapsed
        )

        return {
            "agent": "gap_analysis",
            "status": "success",
            "elapsed_seconds": round(elapsed, 2),
            "result": result
        }

    except TypeError:
        """
        Compatibility fallback.

        If your gap_analysis_agent currently expects positional
        arguments rather than named arguments.
        """

        try:

            result = gap_analysis_agent(
                question,
                network_output,
                compliance_output,
                policy_output
            )

            elapsed = time.perf_counter() - start_time

            logger.info(
                "[GAP COMPLETE - FALLBACK] %.2fs",
                elapsed
            )

            return {
                "agent": "gap_analysis",
                "status": "success",
                "elapsed_seconds": round(elapsed, 2),
                "result": result
            }

        except Exception as exc:

            elapsed = time.perf_counter() - start_time

            logger.exception(
                "[GAP FAILED] %.2fs",
                elapsed
            )

            return {
                "agent": "gap_analysis",
                "status": "error",
                "elapsed_seconds": round(elapsed, 2),
                "error": str(exc),
                "result": None
            }

    except Exception as exc:

        elapsed = time.perf_counter() - start_time

        logger.exception(
            "[GAP FAILED] %.2fs",
            elapsed
        )

        return {
            "agent": "gap_analysis",
            "status": "error",
            "elapsed_seconds": round(elapsed, 2),
            "error": str(exc),
            "result": None
        }


# ============================================================
# FINAL GPT-OSS SYNTHESIS
# ============================================================

def run_final_synthesis(
    question: str,
    specialist_results: Dict[str, Any],
    gap_result: Dict[str, Any]
) -> Dict[str, Any]:

    start_time = time.perf_counter()

    logger.info(
        "[SYNTHESIS] Starting GPT-OSS final synthesis"
    )

    def extract(result):

        if isinstance(result, dict):

            if "result" in result:
                return result["result"]

            if "analysis" in result:
                return result["analysis"]

        return result

    network = extract(
        specialist_results.get("network")
    )

    compliance = extract(
        specialist_results.get("compliance")
    )

    policy = extract(
        specialist_results.get("policy")
    )

    gap = extract(
        gap_result
    )

    prompt = FINAL_SYNTHESIS_PROMPT.format(
        question=question,
        network=network,
        compliance=compliance,
        policy=policy,
        gap=gap
    )

    try:

        final_answer = generate_gptoss(
            prompt=prompt,
            reasoning_effort="medium",
            temperature=0.15,
            max_tokens=2500
        )

        elapsed = time.perf_counter() - start_time

        logger.info(
            "[SYNTHESIS COMPLETE] %.2fs",
            elapsed
        )

        return {
            "status": "success",
            "elapsed_seconds": round(elapsed, 2),
            "answer": final_answer
        }

    except Exception as exc:

        elapsed = time.perf_counter() - start_time

        logger.exception(
            "[SYNTHESIS FAILED] %.2fs",
            elapsed
        )

        return {
            "status": "error",
            "elapsed_seconds": round(elapsed, 2),
            "error": str(exc),
            "answer": None
        }


# ============================================================
# RISK & GOVERNANCE
# ============================================================

def run_governance(
    question: str,
    final_answer: str,
    evidence: Dict[str, Any]
) -> Dict[str, Any]:

    start_time = time.perf_counter()

    logger.info(
        "[GOVERNANCE] Running existing Risk & Governance engine"
    )

    try:

        governance = assess_rag_result(
            question=question,
            final_answer=final_answer,
            evidence=evidence
        )

        elapsed = time.perf_counter() - start_time

        logger.info(
            "[GOVERNANCE COMPLETE] %.2fs",
            elapsed
        )

        return {
            "status": "success",
            "elapsed_seconds": round(elapsed, 2),
            "result": governance
        }

    except TypeError:

        """
        Compatibility fallback for an existing
        assess_rag_result implementation using a different
        argument signature.
        """

        try:

            governance = assess_rag_result(
                final_answer
            )

            elapsed = time.perf_counter() - start_time

            logger.info(
                "[GOVERNANCE COMPLETE - FALLBACK] %.2fs",
                elapsed
            )

            return {
                "status": "success",
                "elapsed_seconds": round(elapsed, 2),
                "result": governance
            }

        except Exception as exc:

            elapsed = time.perf_counter() - start_time

            logger.exception(
                "[GOVERNANCE FAILED] %.2fs",
                elapsed
            )

            return {
                "status": "error",
                "elapsed_seconds": round(elapsed, 2),
                "error": str(exc),
                "result": None
            }

    except Exception as exc:

        elapsed = time.perf_counter() - start_time

        logger.exception(
            "[GOVERNANCE FAILED] %.2fs",
            elapsed
        )

        return {
            "status": "error",
            "elapsed_seconds": round(elapsed, 2),
            "error": str(exc),
            "result": None
        }


# ============================================================
# MAIN ORCHESTRATOR
# ============================================================

def orchestrate(question: str) -> Dict[str, Any]:
    """
    Complete HackGrid decision-intelligence pipeline.

    Pipeline:

        USER QUERY
             |
             v
        SPECIALIST AGENTS
        /       |       \
    Network Compliance Policy
        \       |       /
             |
             v
        GAP ANALYSIS
             |
             v
        GPT-OSS 120B
        FINAL SYNTHESIS
             |
             v
        RISK & GOVERNANCE
             |
             v
        FINAL RESPONSE
    """

    pipeline_start = time.perf_counter()

    logger.info("=" * 70)
    logger.info("[HACKGRID] Pipeline started")
    logger.info("[QUERY] %s", question)
    logger.info("=" * 70)

    # --------------------------------------------------------
    # Validate query
    # --------------------------------------------------------

    if not question or not question.strip():

        return {
            "status": "error",
            "error": "Question cannot be empty."
        }

    question = question.strip()

    # --------------------------------------------------------
    # STEP 1
    # Network + Compliance + Policy
    # PARALLEL
    # --------------------------------------------------------

    specialist_results = run_specialist_agents(
        question
    )

    # --------------------------------------------------------
    # STEP 2
    # Gap Analysis
    # --------------------------------------------------------

    gap_result = run_gap_analysis(
        question,
        specialist_results
    )

    # --------------------------------------------------------
    # STEP 3
    # Final GPT-OSS Synthesis
    # --------------------------------------------------------

    synthesis = run_final_synthesis(
        question,
        specialist_results,
        gap_result
    )

    final_answer = synthesis.get(
        "answer"
    )

    # --------------------------------------------------------
    # Build evidence package for governance
    # --------------------------------------------------------

    evidence_package = {
        "network": specialist_results.get(
            "network"
        ),
        "compliance": specialist_results.get(
            "compliance"
        ),
        "policy": specialist_results.get(
            "policy"
        ),
        "gap_analysis": gap_result
    }

    # --------------------------------------------------------
    # STEP 4
    # Existing Risk & Governance
    # --------------------------------------------------------

    if final_answer:

        governance = run_governance(
            question=question,
            final_answer=final_answer,
            evidence=evidence_package
        )

    else:

        governance = {
            "status": "skipped",
            "reason": "Final synthesis failed."
        }

    # --------------------------------------------------------
    # Timing
    # --------------------------------------------------------

    total_elapsed = time.perf_counter() - pipeline_start

    logger.info("=" * 70)
    logger.info(
        "[HACKGRID] Pipeline completed in %.2fs",
        total_elapsed
    )
    logger.info("=" * 70)

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    return {
        "status": "success" if final_answer else "partial",

        "question": question,

        "analysis": {

            "network": specialist_results.get(
                "network"
            ),

            "compliance": specialist_results.get(
                "compliance"
            ),

            "policy": specialist_results.get(
                "policy"
            ),

            "gap_analysis": gap_result
        },

        "final_answer": final_answer,

        "governance": governance,

        "performance": {

            "total_seconds": round(
                total_elapsed,
                2
            ),

            "parallel_specialists": True,

            "agents": {

                "network": specialist_results.get(
                    "network",
                    {}
                ).get(
                    "elapsed_seconds"
                ),

                "compliance": specialist_results.get(
                    "compliance",
                    {}
                ).get(
                    "elapsed_seconds"
                ),

                "policy": specialist_results.get(
                    "policy",
                    {}
                ).get(
                    "elapsed_seconds"
                ),

                "gap_analysis": gap_result.get(
                    "elapsed_seconds"
                ),

                "final_synthesis": synthesis.get(
                    "elapsed_seconds"
                ),

                "governance": governance.get(
                    "elapsed_seconds"
                )
            }
        }
    }


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def run_orchestrator(question: str) -> Dict[str, Any]:
    """
    Alias for projects that already call run_orchestrator().
    """
    return orchestrate(question)


def run_pipeline(question: str) -> Dict[str, Any]:
    """
    Alias for projects that already call run_pipeline().
    """
    return orchestrate(question)


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    test_question = (
        "Assess the security implications of 5G network slicing "
        "and identify relevant compliance gaps."
    )

    result = orchestrate(
        test_question
    )

    print("\n")
    print("=" * 70)
    print("FINAL HACKGRID RESULT")
    print("=" * 70)

    print(
        result.get(
            "final_answer"
        )
    )

    print("\n")
    print("=" * 70)
    print("PERFORMANCE")
    print("=" * 70)

    print(
        result.get(
            "performance"
        )
    )