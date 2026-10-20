from .gptoss_backend import (
    retrieve,
    format_evidence,
    generate_gptoss,
)


def compliance_agent(question):

    print(
        "\n[COMPLIANCE AGENT] "
        "Retrieving regulatory evidence..."
    )

    retrieved_chunks = retrieve(
        question,
        k=5,
    )

    context = format_evidence(
        retrieved_chunks
    )

    print(
        f"[COMPLIANCE AGENT] Retrieved "
        f"{len(retrieved_chunks)} sources."
    )

    system_prompt = """
You are the Compliance Agent in HackGrid.

Analyze the user's issue ONLY against the
retrieved regulatory and standards evidence.

Do not invent regulations.

Do not perform policy-gap analysis.

Every regulatory requirement must be supported
by the retrieved evidence.

Cite document and page when available.

If evidence is insufficient, explicitly state:

"The retrieved evidence is insufficient to
establish this requirement."
"""

    user_prompt = f"""
USER QUESTION:

{question}


RETRIEVED REGULATORY EVIDENCE:

{context}


Identify:

1. Applicable regulatory framework
2. Regulatory requirements
3. Required compliance actions
4. Reporting/government-cooperation obligations
5. Evidence limitations
"""

    analysis = generate_gptoss(
        system_prompt,
        user_prompt,
        reasoning_effort="low",
        max_tokens=1100,
    )

    return {
        "agent": "Compliance Agent",
        "query": question,
        "retrieved_evidence": retrieved_chunks,
        "analysis": analysis,
    }