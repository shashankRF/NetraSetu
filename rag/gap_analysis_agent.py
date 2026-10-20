from .gptoss_backend import generate_gptoss


def gap_analysis_agent(
    question,
    network_result,
    compliance_result,
    policy_result,
):

    print(
        "\n[GAP ANALYSIS AGENT] "
        "Comparing existing coverage..."
    )

    network_analysis = network_result

    compliance_analysis = compliance_result.get(
        "analysis",
        "No compliance analysis available.",
    )

    policy_analysis = policy_result.get(
        "analysis",
        "No policy analysis available.",
    )

    system_prompt = """
You are the Gap Analysis Agent in HackGrid.

Determine whether the available evidence
supports a policy or standards gap.

Do not invent regulations, policies,
standards or technical requirements.

Do not treat absence of a keyword as proof
of a gap.

First determine existing coverage.

Distinguish:

- Existing regulatory requirements
- Existing policy/standards coverage
- Technical inference
- Potential gap

A potential gap is NOT a definitive legal gap.

Choose exactly ONE:

NO GAP ESTABLISHED
PARTIALLY COVERED
POTENTIAL POLICY/STANDARDS GAP
INSUFFICIENT EVIDENCE
"""

    user_prompt = f"""
USER QUESTION:

{question}


NETWORK AGENT ANALYSIS:

{network_analysis}


COMPLIANCE AGENT ANALYSIS:

{compliance_analysis}


POLICY AGENT ANALYSIS:

{policy_analysis}


Return:

1. GAP STATUS
2. EXISTING COVERAGE
3. COVERED ASPECTS
4. REMAINING UNADDRESSED ASPECT
5. GAP JUSTIFICATION
6. TECHNICAL SIGNIFICANCE
7. EVIDENCE LIMITATIONS
"""

    analysis = generate_gptoss(
        system_prompt,
        user_prompt,
        reasoning_effort="low",
        max_tokens=1000,
    )

    return {
        "agent": "Gap Analysis Agent",
        "query": question,
        "analysis": analysis,
    }