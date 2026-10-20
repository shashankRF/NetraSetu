import os
import json
import faiss
import numpy as np

from sentence_transformers import SentenceTransformer
from groq import Groq


# ============================================================
# CONFIGURATION
# ============================================================

CHUNKS_FILE = "chunks_new.json"
EMBEDDINGS_FILE = "embeddings_new.npy"
FAISS_FILE = "faiss_new.index"

# BGE-M3 embedding model
MODEL_NAME = "BAAI/bge-m3"

# Groq model
GROQ_MODEL = "openai/gpt-oss-120b"


# ============================================================
# LOAD KNOWLEDGE BASE
# ============================================================

print("Loading chunks...")

with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print(f"Loaded {len(chunks)} chunks.")


# ============================================================
# LOAD FAISS
# ============================================================

print("Loading FAISS index...")

index = faiss.read_index(FAISS_FILE)

print(f"FAISS vectors: {index.ntotal}")


# ============================================================
# LOAD BGE-M3
# ============================================================

print("Loading BGE-M3...")

embedding_model = SentenceTransformer(
    MODEL_NAME,
    device="cpu"
)

print("BGE-M3 loaded.")


# ============================================================
# GROQ CLIENT
# ============================================================

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError(
        "GROQ_API_KEY not found. "
        "Set your Groq API key as an environment variable."
    )

client = Groq(api_key=api_key)

print("Groq connected.")
print(f"Model: {GROQ_MODEL}")


# ============================================================
# RAG RETRIEVAL
# ============================================================

def retrieve(query, k=8):

    query_embedding = embedding_model.encode(
        [query],
        normalize_embeddings=True
    )

    query_embedding = np.asarray(
        query_embedding,
        dtype="float32"
    )

    distances, indices = index.search(
        query_embedding,
        k
    )

    results = []

    for rank, (distance, idx) in enumerate(
        zip(distances[0], indices[0]),
        start=1
    ):

        if idx == -1:
            continue

        chunk = chunks[idx]

        results.append({
            "rank": rank,
            "distance": float(distance),
            "text": chunk["text"],
            "metadata": chunk["metadata"]
        })

    return results


# ============================================================
# FINAL GPT-OSS SYNTHESIS
# ============================================================

def generate_answer(
    question,
    network_output,
    compliance_output,
    policy_output,
    gap_output
):

    prompt = f"""
You are the Final Synthesis AI of a multi-agent
5G telecommunications regulatory, policy, and
architectural analysis system.

Your task is to combine the outputs of four specialist
agents into ONE coherent, accurate, evidence-grounded
answer to the user's question.

The four specialist agents are:

1. NETWORK AGENT
   Analyzes the technical 5G architecture,
   network functions, slicing, AI/ML components,
   dependencies, and technical security implications.

2. COMPLIANCE AGENT
   Identifies applicable Indian regulations,
   obligations, security requirements, reporting,
   monitoring, logging, risk assessment, and
   government-cooperation requirements.

3. POLICY AGENT
   Analyzes existing policies, standards,
   strategies, frameworks, and broader coverage.

4. GAP ANALYSIS AGENT
   Determines whether the available evidence
   establishes:

   - NOT APPLICABLE
   - NO GAP ESTABLISHED
   - PARTIALLY COVERED
   - POTENTIAL POLICY/STANDARDS GAP
   - INSUFFICIENT EVIDENCE


========================================================
USER QUESTION
========================================================

{question}


========================================================
NETWORK AGENT OUTPUT
========================================================

{network_output}


========================================================
COMPLIANCE AGENT OUTPUT
========================================================

{compliance_output}


========================================================
POLICY AGENT OUTPUT
========================================================

{policy_output}


========================================================
GAP ANALYSIS AGENT OUTPUT
========================================================

{gap_output}


========================================================
CORE SYNTHESIS RULES
========================================================

1. ANSWER THE USER'S ACTUAL QUESTION

Start with the direct answer.

Do not simply summarize the four agents separately.

Combine their findings into one logical explanation.


2. CONNECT TECHNICAL ARCHITECTURE WITH REGULATION

The final answer must consider both:

A. What is happening technically?

B. What existing regulatory/policy/standards
   framework applies?

Where relevant, consider:

- RAN
- gNodeB
- 5G Core
- AMF
- SMF
- UPF
- PCF
- network slicing
- slice management
- orchestration
- AI/ML decision-making
- policy enforcement
- interfaces
- dependencies
- monitoring
- logging
- security controls
- remote access
- CTI infrastructure

Only mention components relevant to the user's scenario.


3. CTI MUST BE CONDITIONAL

Do NOT automatically assume that every 5G
network is Critical Telecommunication Infrastructure.

If the scenario involves CTI and the evidence
supports applicability, explain the relevant
CTI requirements.

If CTI applicability is not established,
clearly state:

"Applicability of the CTI-specific requirements
is not established by the available evidence."

Do not use CTI merely because it is present
in the knowledge base.


4. REGULATORY REQUIREMENTS

Only describe something as a regulatory requirement
when supported by the Compliance Agent's evidence.

Use the document name and page when available.

DO NOT invent:

- laws
- rules
- policies
- standards
- deadlines
- obligations
- government directions


5. TECHNICAL RECOMMENDATIONS

Technical recommendations may be proposed based
on the technical analysis.

However, clearly label them as:

"Technical recommendation"

or

"Architectural recommendation"

Do NOT present a technical recommendation
as a legal or regulatory requirement.


6. POLICY AND STANDARDS COVERAGE

Use the Policy Agent's findings to identify:

- direct coverage
- broader coverage
- partial coverage
- related framework coverage

Do not invent additional frameworks.


========================================================
GAP ANALYSIS LOGIC
========================================================
JURISDICTIONAL CONFLICT ANALYSIS

When comparing an international technical standard with an
Indian law, regulation, policy, or national standard:

1. First establish whether the Indian instrument is applicable
   to the scenario.

2. Determine whether the Indian provision is binding,
   advisory, conditional, or voluntary based on explicit evidence.

3. Determine whether the international provision is binding,
   recommended, optional, or informational based on explicit
   evidence.

4. Do not assume that a national requirement conflicts with an
   international standard merely because it is stricter.

5. A conflict may be classified only when the retrieved evidence
   establishes that compliance with the two applicable
   requirements is incompatible or requires mutually inconsistent
   actions.

6. If the Indian framework provides a stricter requirement but
   the international requirement can still be satisfied,
   classify the relationship based on the actual evidence rather
   than automatically calling it a conflict or policy gap.

7. Never state "the operator must comply" unless the retrieved
   evidence establishes applicability and mandatory status.

8. If applicability or legal status cannot be established,
   use INSUFFICIENT EVIDENCE and explain exactly what is missing.

9. Distinguish:
   - national mandatory requirement
   - national advisory guidance
   - international technical standard
   - international recommendation
   - technical compatibility
   - regulatory applicability
   - actual conflict
   - potential policy/standards gap.

7. NEVER FORCE A POLICY GAP

A missing keyword, missing document, or absence
from retrieved evidence does NOT automatically
prove a policy or standards gap.


8. DISTINGUISH TECHNICAL WEAKNESS FROM POLICY GAP

A technical weakness is NOT automatically a
policy or standards gap.

For example:

Technical observation:

An AI-based network-slicing controller may require
stronger validation, monitoring, or human oversight.

This becomes a potential policy/standards gap ONLY
if the available evidence indicates that the specific
requirement is not adequately addressed by existing
frameworks.


9. COVERAGE-FIRST ANALYSIS

Before determining a gap, compare:

Technical requirement
+
Existing regulatory coverage
+
Existing policy coverage
+
Existing standards coverage
+
CTI coverage where applicable
+
Related telecom/cybersecurity frameworks


10. GAP STATUS

Choose EXACTLY ONE:

NOT APPLICABLE

NO GAP ESTABLISHED

PARTIALLY COVERED

POTENTIAL POLICY/STANDARDS GAP

INSUFFICIENT EVIDENCE


========================================================
WHEN GAP STATUS = NOT APPLICABLE
========================================================

If the user's question is purely:

- informational
- definitional
- technical
- architectural

and does not require policy or standards-gap analysis,
do not manufacture a gap.

State:

"Policy/standards gap analysis is not applicable
to this question."

Then answer the actual question.


========================================================
WHEN GAP STATUS = NO GAP ESTABLISHED
========================================================

Do NOT simply say:

"No gap exists."

You MUST demonstrate why no gap is established.

Identify the existing rules, regulations, policies,
or standards that already cover the issue.

For EACH relevant framework, provide:

1. Framework / Rule / Standard name
2. Specific requirement or coverage
3. How it relates to the technical architecture
4. Source document and page, when available

Present the information concisely in this format:

Framework | What it covers | Technical relevance | Source/Page

Only include frameworks supported by the available
evidence.

Then explain why the identified existing framework(s)
provide sufficient coverage for the relevant issue.

Do NOT automatically use the phrase:

"No additional policy or standards gap exists."

unless the evidence actually supports that conclusion.

Do NOT recommend creating or modifying a policy
when existing coverage is adequate.

Technical improvements may still be suggested,
but they MUST be labelled as technical/engineering
recommendations rather than policy gaps.


========================================================
WHEN GAP STATUS = PARTIALLY COVERED
========================================================

Clearly identify:

1. What existing frameworks already cover.
2. What aspect is only partially addressed.
3. Whether the remaining issue is:
   - technical
   - regulatory
   - policy-related
   - standards-related
4. Why the remaining aspect matters.

Do NOT automatically call partial coverage
a definitive policy gap.


========================================================
WHEN GAP STATUS = POTENTIAL POLICY/STANDARDS GAP
========================================================

Only use this classification when the combined
technical + regulatory + policy evidence supports it.

Clearly explain:

1. Existing frameworks that already cover the issue.
2. The specific remaining aspect.
3. Why that aspect matters technically.
4. Why existing frameworks do not adequately address
   that specific aspect.
5. Why the evidence supports treating it as a
   POTENTIAL policy/standards gap.

Use the phrase:

"Potential policy/standards gap"

rather than claiming a definitive legal gap.

Do NOT invent a missing regulation or standard.


========================================================
WHEN GAP STATUS = INSUFFICIENT EVIDENCE
========================================================

Clearly state that the available evidence is
insufficient.

Explain what can be established and what cannot.

Do not fill missing information using assumptions.


========================================================
EVIDENCE PRIORITY
========================================================

When specialist outputs conflict:

1. Prefer explicit retrieved regulatory evidence.
2. Prefer specific source/page references.
3. Use technical agent output for architectural context.
4. Use Policy Agent output for framework coverage.
5. Use Gap Agent output for gap classification.
6. If uncertainty remains, state it explicitly.


========================================================
HUMAN-IN-THE-LOOP
========================================================

For consequential compliance or architectural actions,
make clear that final implementation or compliance
decisions require appropriate human review and approval.


========================================================
FINAL ANSWER STYLE
========================================================

Do NOT expose internal reasoning.

Do NOT reproduce the full outputs of the agents.

Do NOT mention that you are "combining agent outputs."

Write as ONE professional expert response.

Target approximately 250-400 words.

Be precise rather than verbose.


========================================================
FINAL RESPONSE FORMAT
========================================================

### Assessment

Give the direct answer to the user's question
in 1-3 concise paragraphs.


### Technical Architecture Impact

Explain the relevant technical architecture and connect
it to the regulatory requirements.

Only describe something as a regulatory requirement if
the cited source explicitly supports it.

If a technical control is inferred from a regulation,
clearly label it as:

"Technical/architectural implication"


### Applicable Regulatory Requirements

List the most relevant regulatory requirements.

For each important requirement provide:

- Requirement
- Document
- Page


### Actions

Separate clearly:

**Regulatory obligations**

and

**Technical / architectural recommendations**


### Policy & Standards Coverage

Explain which existing frameworks address the issue.

If coverage exists, identify the relevant
rules/policies/standards and what they cover.


### Gap Status

Before determining the gap status, distinguish:

A. Explicit regulatory requirements
B. Existing policy/standards coverage
C. Technical/architectural implications
D. Technical recommendations
E. Potential policy/standards gaps

A technical weakness alone must NOT be classified
as a policy or standards gap.

Choose exactly ONE:

NOT APPLICABLE
NO GAP ESTABLISHED
PARTIALLY COVERED
POTENTIAL POLICY/STANDARDS GAP
INSUFFICIENT EVIDENCE

Then justify the classification.

If NO GAP ESTABLISHED, explicitly identify
the existing framework(s) that cover the issue
and explain their technical relevance.


### Sources

List the most relevant documents and page numbers.
"""


    # ========================================================
    # GPT-OSS CALL
    # ========================================================

    try:

        response = client.chat.completions.create(
            model=GROQ_MODEL,

            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an evidence-grounded "
                        "telecommunications regulatory "
                        "and technical analysis assistant."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            reasoning_effort="medium",

            temperature=0.2,

            max_tokens=4000
        )

        return response.choices[0].message.content


    except Exception as e:

        return (
            "GPT-OSS synthesis failed.\n\n"
            f"Error: {str(e)}"
        )


# ============================================================
# STANDALONE RAG TEST
# ============================================================

if __name__ == "__main__":

    print("\n" + "=" * 80)
    print("HACKGRID GPT-OSS RAG SYSTEM READY")
    print("=" * 80)

    print("\nKnowledge Base:")
    print(f"  Chunks: {len(chunks)}")
    print(f"  FAISS vectors: {index.ntotal}")
    print(f"  Embeddings: BGE-M3")
    print(f"  LLM: {GROQ_MODEL}")

    print("\nThis module performs:")
    print("  BGE-M3 retrieval")
    print("  FAISS evidence retrieval")
    print("  GPT-OSS final synthesis")

    print("\nType 'exit' to quit.")

    while True:

        question = input(
            "\nEnter your question: "
        )

        if question.lower().strip() == "exit":
            break

        print("\n" + "=" * 80)
        print("RETRIEVING RELEVANT EVIDENCE...")
        print("=" * 80)

        results = retrieve(
            question,
            k=8
        )

        if not results:

            print("\nNo evidence found.")
            continue


        # ----------------------------------------------------
        # DISPLAY RETRIEVED EVIDENCE
        # ----------------------------------------------------

        print("\n" + "=" * 80)
        print("RETRIEVED SOURCES")
        print("=" * 80)

        for r in results:

            metadata = r["metadata"]

            print(
                f"\nRank {r['rank']}"
            )

            print(
                f"Document: "
                f"{metadata.get('document')}"
            )

            print(
                f"Page: "
                f"{metadata.get('page')}"
            )

            print(
                f"Distance: "
                f"{r['distance']:.4f}"
            )

            print(
                f"Source: "
                f"{metadata.get('source_file')}"
            )

            print(
                "\nEvidence:"
            )

            print(
                r["text"][:1000]
            )

            print("-" * 80)


        # ----------------------------------------------------
        # SIMPLE STANDALONE SYNTHESIS TEST
        # ----------------------------------------------------
        #
        # This standalone mode does not have separate
        # Network / Compliance / Policy / Gap agent outputs.
        #
        # Therefore, the retrieved evidence is passed into
        # GPT-OSS as the evidence context.
        # ----------------------------------------------------

        evidence_text = ""

        for r in results:

            metadata = r["metadata"]

            evidence_text += f"""

--- Evidence {r['rank']} ---

Document:
{metadata.get('document')}

Page:
{metadata.get('page')}

Source:
{metadata.get('source_file')}

Evidence:
{r['text']}

"""


        standalone_prompt = f"""
You are HackGrid, an evidence-grounded AI system
for 5G/6G telecommunications, regulation,
policy and standards analysis.

Answer the user's question using ONLY the retrieved
evidence provided below.

USER QUESTION:
{question}

RETRIEVED EVIDENCE:
{evidence_text}

Rules:

1. Answer the question directly.

2. Do not invent laws, regulations, policies,
   standards, clauses, deadlines or obligations.

3. If the evidence is insufficient, explicitly say so.

4. Do not treat absence from the retrieved evidence
   as proof that a regulation or policy does not exist.

5. Clearly distinguish:
   - verified evidence
   - technical interpretation
   - technical recommendation
   - potential policy/standards gap

6. For every important regulatory or standards claim,
   provide the document and page when available.

7. If discussing a policy/standards gap, use:
   "Potential policy/standards gap"

   rather than claiming a definitive legal gap.

8. Keep the answer professional and concise.

Use this format:

### Assessment

Direct answer.

### Technical Impact

Relevant technical explanation.

### Applicable Requirements

Relevant requirements with document/page.

### Policy & Standards Coverage

Existing coverage supported by the evidence.

### Gap Status

Choose exactly one:

NOT APPLICABLE
NO GAP ESTABLISHED
PARTIALLY COVERED
POTENTIAL POLICY/STANDARDS GAP
INSUFFICIENT EVIDENCE

Explain why.

### Sources

Relevant source documents and pages.
"""


        print("\n" + "=" * 80)
        print("GENERATING GPT-OSS ANSWER...")
        print("=" * 80)

        try:

            response = client.chat.completions.create(
                model=GROQ_MODEL,

                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are HackGrid, an evidence-grounded "
                            "5G/6G regulatory and technical analysis "
                            "assistant."
                        )
                    },
                    {
                        "role": "user",
                        "content": standalone_prompt
                    }
                ],

                reasoning_effort="medium",

                temperature=0.2,

                max_tokens=4000
            )

            answer = response.choices[0].message.content

            print("\n" + "=" * 80)
            print("GPT-OSS ANSWER")
            print("=" * 80)

            print("\n")
            print(answer)

            print("\n" + "=" * 80)


        except Exception as e:

            print("\nGPT-OSS ERROR:")
            print(str(e))

            print(
                "\nRetrieved evidence is still available above."
            )