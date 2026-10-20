from .gptoss_backend import (
    retrieve,
    format_evidence,
    generate_gptoss,
)


def policy_agent(question):

    print(
        "\n[POLICY AGENT] "
        "Analyzing policy/framework coverage..."
    )

    retrieved_chunks = retrieve(
        question,
        k=6,
    )

    context = format_evidence(
        retrieved_chunks
    )

    print(
        f"[POLICY AGENT] Retrieved "
        f"{len(retrieved_chunks)} sources."
    )

    system_prompt = """
You are the Policy Analysis Agent in HackGrid.

Analyze policy, strategy, framework and
standardization coverage.

Use ONLY the retrieved evidence.

Do not invent policies, standards,
regulations or government initiatives.

Do not make a final policy-gap determination.

Do not assume absence of a keyword means
a policy gap.

Distinguish:

A. Direct coverage
B. Broad/partial coverage
C. Related framework coverage
D. Insufficient evidence
"""

    user_prompt = f"""
USER QUESTION:

{question}


RETRIEVED POLICY AND STANDARDS EVIDENCE:

{context}


Return:

1. Policy/framework landscape
2. Direct policy coverage
3. Broader/partial coverage
4. Related framework coverage
5. Policy/standards implications
6. Evidence limitations
"""

    analysis = generate_gptoss(
        system_prompt,
        user_prompt,
        reasoning_effort="low",
        max_tokens=1100,
    )

    return {
        "agent": "Policy Agent",
        "query": question,
        "retrieved_evidence": retrieved_chunks,
        "analysis": analysis,
    }