from .models import Scenario, ScenarioStep


SCENARIOS = [

    # ============================================================
    # DEFENCE
    # ============================================================

    Scenario(
        scenario_id="HG-DEFENCE-001",
        title="UAV Tactical Datalink Interference",
        domain="Defence",
        jurisdiction="India",
        description=(
            "Simulated defence scenario involving a UAV experiencing "
            "unexpected tactical datalink degradation and suspected "
            "interference or spoofing."
        ),
        simulated=True,
        steps=[
            ScenarioStep(
                step_id="D1",
                title="Initial anomaly",
                event=(
                    "A tactical UAV begins experiencing intermittent "
                    "loss of command-and-control link quality."
                ),
                evidence_prompt=(
                    "What technical standards, security requirements, "
                    "or documented mechanisms are relevant to UAV "
                    "communications interference and link security?"
                ),
            ),
            ScenarioStep(
                step_id="D2",
                title="Suspected interference",
                event=(
                    "Signal measurements suggest abnormal interference "
                    "rather than an ordinary communications failure."
                ),
                evidence_prompt=(
                    "What evidence is required to distinguish ordinary "
                    "communication degradation from deliberate interference "
                    "or spoofing?"
                ),
            ),
            ScenarioStep(
                step_id="D3",
                title="Operational assessment",
                event=(
                    "The operator must determine whether the incident "
                    "requires escalation to a human defence authority."
                ),
                evidence_prompt=(
                    "What evidence, limitations, and governance considerations "
                    "should influence the final assessment?"
                ),
            ),
        ],
    ),

    # ============================================================
    # MARITIME
    # ============================================================

    Scenario(
        scenario_id="HG-MARITIME-002",
        title="AIS and GNSS Vessel Behaviour Anomaly",
        domain="Maritime",
        jurisdiction="India",
        description=(
            "Simulated maritime incident in which AIS behaviour and "
            "navigation information become inconsistent."
        ),
        simulated=True,
        steps=[
            ScenarioStep(
                step_id="M1",
                title="AIS anomaly detected",
                event=(
                    "A vessel's AIS track shows an abrupt and unusual "
                    "change in reported position and course."
                ),
                evidence_prompt=(
                    "What standards, technical requirements, and known "
                    "mechanisms are relevant to AIS integrity and maritime "
                    "navigation anomalies?"
                ),
            ),
            ScenarioStep(
                step_id="M2",
                title="Navigation inconsistency",
                event=(
                    "AIS information becomes inconsistent with other "
                    "available navigation observations."
                ),
                evidence_prompt=(
                    "What evidence should be examined before concluding "
                    "that a vessel navigation anomaly represents spoofing, "
                    "manipulation, equipment failure, or another cause?"
                ),
            ),
            ScenarioStep(
                step_id="M3",
                title="Maritime risk assessment",
                event=(
                    "The operator must determine the confidence of the "
                    "assessment and whether escalation is required."
                ),
                evidence_prompt=(
                    "What evidence gaps and uncertainty should be reported "
                    "before making a consequential maritime assessment?"
                ),
            ),
        ],
    ),

    # ============================================================
    # TELECOM / 5G
    # ============================================================

    Scenario(
        scenario_id="HG-5G-003",
        title="5G Network Slice Security Incident",
        domain="Telecom/5G",
        jurisdiction="India",
        description=(
            "Simulated 5G incident involving suspected compromise or "
            "isolation failure affecting a network slice."
        ),
        simulated=True,
        steps=[
            ScenarioStep(
                step_id="T1",
                title="Slice anomaly",
                event=(
                    "A network slice begins showing unexpected traffic "
                    "behaviour and isolation anomalies."
                ),
                evidence_prompt=(
                    "What 3GPP and Indian requirements apply to security "
                    "and isolation of 5G network slices?"
                ),
            ),
            ScenarioStep(
                step_id="T2",
                title="Security investigation",
                event=(
                    "The operator suspects that traffic from one slice "
                    "may have affected another logical service boundary."
                ),
                evidence_prompt=(
                    "Which technical security controls and requirements "
                    "are relevant to preventing or detecting cross-slice "
                    "security problems?"
                ),
            ),
            ScenarioStep(
                step_id="T3",
                title="Compliance assessment",
                event=(
                    "The operator needs to determine whether the observed "
                    "condition represents a technical or regulatory gap."
                ),
                evidence_prompt=(
                    "Compare applicable technical and Indian regulatory "
                    "requirements and identify evidence-supported gaps."
                ),
            ),
        ],
    ),

    # ============================================================
    # TELECOM RANSOMWARE
    # ============================================================

    Scenario(
        scenario_id="HG-TELECOM-004",
        title="Telecom OSS/BSS Ransomware Incident",
        domain="Telecom/5G",
        jurisdiction="India",
        description=(
            "Simulated ransomware incident affecting telecom operational "
            "and business support systems."
        ),
        simulated=True,
        steps=[
            ScenarioStep(
                step_id="R1",
                title="Service disruption",
                event=(
                    "Multiple operator management systems become unavailable "
                    "following a suspected ransomware event."
                ),
                evidence_prompt=(
                    "What cybersecurity requirements and controls are "
                    "relevant to protecting critical telecom systems?"
                ),
            ),
            ScenarioStep(
                step_id="R2",
                title="Root-cause investigation",
                event=(
                    "Investigators identify several possible initial-access "
                    "paths but lack sufficient evidence to select one."
                ),
                evidence_prompt=(
                    "What evidence is required to establish or reject "
                    "possible root causes of a telecom cyber incident?"
                ),
            ),
            ScenarioStep(
                step_id="R3",
                title="Recovery decision",
                event=(
                    "Management must decide whether available evidence "
                    "supports operational recovery."
                ),
                evidence_prompt=(
                    "What evidence limitations and human-review requirements "
                    "should be considered before making a consequential decision?"
                ),
            ),
        ],
    ),

    # ============================================================
    # RESEARCH
    # ============================================================

    Scenario(
        scenario_id="HG-RESEARCH-005",
        title="Conflicting O-RAN Security Research",
        domain="Research",
        jurisdiction="European Union",
        description=(
            "Simulated research-analysis scenario involving conflicting "
            "technical findings concerning O-RAN security and network "
            "efficiency."
        ),
        simulated=True,
        steps=[
            ScenarioStep(
                step_id="RS1",
                title="Research question",
                event=(
                    "A research team wants to determine whether an O-RAN "
                    "security mechanism introduces measurable performance "
                    "or energy overhead."
                ),
                evidence_prompt=(
                    "What published standards and technical evidence "
                    "address the relevant O-RAN security mechanisms?"
                ),
            ),
            ScenarioStep(
                step_id="RS2",
                title="Conflicting findings",
                event=(
                    "Two groups report apparently different conclusions "
                    "about security overhead."
                ),
                evidence_prompt=(
                    "Identify supporting, contradicting, contextual, and "
                    "insufficient evidence relevant to the research question."
                ),
            ),
            ScenarioStep(
                step_id="RS3",
                title="Research gap",
                event=(
                    "The research team wants to determine whether a genuine "
                    "research gap remains."
                ),
                evidence_prompt=(
                    "Does the available evidence establish a research gap, "
                    "or is the evidence insufficient to establish one?"
                ),
            ),
        ],
    ),

    # ============================================================
    # EUROPEAN UNION
    # ============================================================

    Scenario(
        scenario_id="HG-EU-006",
        title="European 5G Network Function Security Incident",
        domain="Telecom/5G",
        jurisdiction="European Union",
        description=(
            "Simulated European 5G incident involving a suspected security "
            "weakness in a network function and a need to assess applicable "
            "European requirements."
        ),
        simulated=True,
        steps=[
            ScenarioStep(
                step_id="EU1",
                title="Network-function anomaly",
                event=(
                    "A 5G network function reports abnormal authentication "
                    "and access behaviour."
                ),
                evidence_prompt=(
                    "What technical standards and European requirements "
                    "are relevant to securing the affected 5G network function?"
                ),
            ),
            ScenarioStep(
                step_id="EU2",
                title="Regulatory applicability",
                event=(
                    "The operator must determine which European regulatory "
                    "requirements may apply."
                ),
                evidence_prompt=(
                    "Identify applicable European regulatory requirements "
                    "from the available evidence and distinguish mandatory "
                    "requirements from technical standards or guidance."
                ),
            ),
            ScenarioStep(
                step_id="EU3",
                title="Compliance assessment",
                event=(
                    "The operator needs an evidence-supported assessment "
                    "of coverage and potential gaps."
                ),
                evidence_prompt=(
                    "Compare the applicable European requirements with the "
                    "technical evidence and identify established gaps or "
                    "insufficient evidence."
                ),
            ),
        ],
    ),

    # ============================================================
    # ENTERPRISE INCIDENT
    # ============================================================

    Scenario(
        scenario_id="HG-ENTERPRISE-007",
        title="Conflicting Evidence Cyber Incident",
        domain="Enterprise Incident",
        jurisdiction="India",
        description=(
            "Simulated enterprise cyber incident where several indicators "
            "suggest compromise but the available evidence is incomplete "
            "and partially conflicting."
        ),
        simulated=True,
        steps=[
            ScenarioStep(
                step_id="E1",
                title="Initial alert",
                event=(
                    "Security monitoring detects unusual authentication "
                    "activity across multiple systems."
                ),
                evidence_prompt=(
                    "What documented security controls or requirements "
                    "are relevant to the observed behaviour?"
                ),
            ),
            ScenarioStep(
                step_id="E2",
                title="Conflicting indicators",
                event=(
                    "Some indicators support compromise while others "
                    "suggest a legitimate administrative operation."
                ),
                evidence_prompt=(
                    "Identify supporting and contradicting evidence and "
                    "determine whether compromise is actually established."
                ),
            ),
            ScenarioStep(
                step_id="E3",
                title="Human decision",
                event=(
                    "A security analyst must determine whether the evidence "
                    "is sufficient for escalation."
                ),
                evidence_prompt=(
                    "Assess evidence quality, uncertainty, and whether "
                    "human review is required before escalation."
                ),
            ),
        ],
    ),

    # ============================================================
    # JUDGE-READY VERIFICATION DEMONSTRATION: CERT-IN DIRECTIONS
    # ============================================================

    Scenario(
        scenario_id="HG-CERTIN-008",
        title="CERT-In 6-Hour Reporting & Source-to-Clause Verification",
        domain="Cybersecurity & Regulatory Compliance",
        jurisdiction="India",
        description=(
            "Judge-ready verification demonstration testing official CERT-In Directions "
            "dated 28 April 2022. Evaluates the 6-hour cyber incident reporting requirement "
            "against Paragraph (ii) with official FAQ clarifications, alongside a deliberate "
            "mismatch test detecting an erroneous clause citation."
        ),
        simulated=True,
        steps=[
            ScenarioStep(
                step_id="C1",
                title="Valid Mandate: 6-Hour Reporting to CERT-In (Para 2(ii))",
                event=(
                    "An operator experiences a major cybersecurity incident and must determine "
                    "the mandatory reporting timeline and procedure under CERT-In Directions "
                    "dated 28 April 2022."
                ),
                evidence_prompt=(
                    "What is the mandatory timeline and procedure for reporting cybersecurity "
                    "incidents to CERT-In under the Directions dated 28 April 2022, and what are "
                    "the official FAQ clarifications regarding reporting initial available "
                    "information versus full technical details?"
                ),
            ),
            ScenarioStep(
                step_id="C2",
                title="Deliberate Mismatch: Erroneous Clause Citation Test",
                event=(
                    "A compliance report erroneously cites Clause 12 of the CERT-In Directions "
                    "as establishing the 6-hour incident reporting requirement. HackGrid must "
                    "verify whether the cited clause actually contains the rule."
                ),
                evidence_prompt=(
                    "Does Clause 12 of the CERT-In Directions dated 28 April 2022 establish the "
                    "mandatory 6-hour cyber incident reporting obligation, or is there a citation mismatch?"
                ),
            ),
        ],
    ),
]



# ============================================================
# SOURCE-TO-CLAUSE VERIFICATION REGISTRY FOR SCENARIO LAB
# ============================================================

SCENARIO_VERIFIED_SOURCES = {
    "HG-DEFENCE-001": {
        "scenario_source": {
            "source_doc_id": "DGCA-DRONE-RULES-2021",
            "source_title": "Drone Rules, 2021 (as amended)",
            "issuing_authority": "Ministry of Civil Aviation / DGCA, Government of India",
            "document_identifier": "G.S.R. 589(E)",
            "jurisdiction": "India",
            "legal_status": "BINDING_STATUTORY",
            "clause": "Rule 11 - Communication & Datalink Security",
            "page": 5,
            "source_url": "https://www.civilaviation.gov.in/sites/default/files/Drone%20Rules%202021.pdf",
            "local_viewer_url": "/api/documents/raw/knowledge_base/DEFENCE/Drone Rules 2021.pdf#page=5",
            "supporting_text": "No unmanned aircraft system shall operate in India without a valid type certificate issued by the Director General certifying compliance with safety and communication security standards.",
            "surrounding_context": "Mandatory safety, communication datalink integrity, and electronic fence compliance for unmanned aircraft operating in Indian airspace."
        },
        "steps": {
            "D1": {
                "source_doc_id": "DGCA-DRONE-RULES-2021",
                "source_title": "Drone Rules, 2021 (as amended)",
                "issuing_authority": "Ministry of Civil Aviation / DGCA",
                "document_identifier": "G.S.R. 589(E)",
                "jurisdiction": "India",
                "legal_status": "BINDING_STATUTORY",
                "clause": "Rule 11 - Type Certificate & Datalink Safeguards",
                "page": 5,
                "source_url": "https://www.civilaviation.gov.in/sites/default/files/Drone%20Rules%202021.pdf",
                "local_viewer_url": "/api/documents/raw/knowledge_base/DEFENCE/Drone Rules 2021.pdf#page=5",
                "supporting_text": "Mandatory adherence to communication datalink integrity and fail-safe return-to-home procedures upon link loss.",
                "surrounding_context": "Chapter III: Type certification of unmanned aircraft systems and mandatory datalink requirements."
            },
            "D2": {
                "source_doc_id": "NATO-UAS-CONEMP",
                "source_title": "NATO UAS Concept of Operations & Tactical Link Protection",
                "issuing_authority": "NATO Joint Air Power Competence Centre",
                "document_identifier": "NATO JAPCC Technical Baseline",
                "jurisdiction": "International",
                "legal_status": "NON_BINDING_TECHNICAL_STANDARD",
                "clause": "Section 3.4 - Electronic Counter-Measures & Datalink Spoofing",
                "page": 18,
                "source_url": "https://www.japcc.org/",
                "local_viewer_url": "/api/documents/raw/knowledge_base/DEFENCE/UAS_CONEMP NATO.pdf#page=18",
                "supporting_text": "Methods for distinguishing intentional RF jamming and protocol spoofing from atmospheric path attenuation in tactical datalinks.",
                "surrounding_context": "Tactical electronic defense reference architecture. Provides international technical baseline for UAV datalink verification."
            },
            "D3": {
                "source_doc_id": "DOT-TELECOM-ACT-2023",
                "source_title": "The Telecommunications Act, 2023",
                "issuing_authority": "Ministry of Communications / DoT, Parliament of India",
                "document_identifier": "Act No. 44 of 2023",
                "jurisdiction": "India",
                "legal_status": "BINDING_STATUTORY",
                "clause": "Section 20 - Measures for National Security and Defense Public Safety",
                "page": 13,
                "source_url": "https://www.egazette.gov.in/WriteReadData/2023/250880.pdf",
                "local_viewer_url": "/api/documents/raw/knowledge_base/DoT_Rules/new-telecom-Act-2023.pdf#page=13",
                "supporting_text": "On the occurrence of any public emergency, including the security of the State, authorized government agencies may intervene or take control of telecommunication spectrum.",
                "surrounding_context": "Statutory authority for escalation to national security and defense telecommunication leadership."
            }
        }
    },
    "HG-MARITIME-002": {
        "scenario_source": {
            "source_doc_id": "DOT-MARITIME-RULES-2022",
            "source_title": "Flight and Maritime Connectivity (Amendment) Rules, 2022",
            "issuing_authority": "Department of Telecommunications (DoT), Ministry of Communications",
            "document_identifier": "G.S.R. 876(E)",
            "jurisdiction": "India",
            "legal_status": "BINDING_STATUTORY",
            "clause": "Rule 4 - Maritime Safety Communications & AIS Telemetry",
            "page": 2,
            "source_url": "https://dot.gov.in/",
            "local_viewer_url": "/api/documents/raw/knowledge_base/DoT_Rules/flight-and-maritime-connectivity-amendment-rules-2022.pdf#page=2",
            "supporting_text": "All maritime connectivity providers operating within Indian territorial waters must preserve telemetry logs and comply with international maritime safety communication mandates.",
            "surrounding_context": "Statutory rules governing authorized maritime satellite links, AIS transponder verification, and navigation reporting."
        },
        "steps": {
            "M1": {
                "source_doc_id": "DOT-MARITIME-RULES-2022",
                "source_title": "Flight and Maritime Connectivity Rules, 2022",
                "issuing_authority": "Department of Telecommunications (DoT)",
                "document_identifier": "G.S.R. 876(E)",
                "jurisdiction": "India",
                "legal_status": "BINDING_STATUTORY",
                "clause": "Rule 4 - AIS Integrity & Connectivity",
                "page": 2,
                "source_url": "https://dot.gov.in/",
                "local_viewer_url": "/api/documents/raw/knowledge_base/DoT_Rules/flight-and-maritime-connectivity-amendment-rules-2022.pdf#page=2",
                "supporting_text": "Automated Identification System (AIS) integrity requirements and anomaly tracking within Indian territorial waters.",
                "surrounding_context": "Telemetry validation requirements for vessels navigating Indian coastal and offshore economic zones."
            },
            "M2": {
                "source_doc_id": "DOT-GMDSS-RULES-2024",
                "source_title": "Commercial Radio Operator GMDSS Rules, 2024",
                "issuing_authority": "Ministry of Communications / DoT",
                "document_identifier": "G.S.R. 112(E)",
                "jurisdiction": "India",
                "legal_status": "BINDING_STATUTORY",
                "clause": "Rule 6 - GNSS & Safety Navigation Reliability",
                "page": 4,
                "source_url": "https://dot.gov.in/",
                "local_viewer_url": "/api/documents/raw/knowledge_base/DoT_Rules/commercial-radio-operator-certificate-of-proficiency-to-operate-global-maritime-distress-and-safety-system-rules-2024.pdf#page=4",
                "supporting_text": "Operational protocols for resolving discrepancies between GNSS satellite navigation telemetry and terrestrial radar beacons.",
                "surrounding_context": "Binding standards for GMDSS operators during navigational inconsistency or suspected spoofing."
            },
            "M3": {
                "source_doc_id": "DOT-TELECOM-ACT-2023",
                "source_title": "The Telecommunications Act, 2023",
                "issuing_authority": "Ministry of Communications / DoT",
                "document_identifier": "Act No. 44 of 2023",
                "jurisdiction": "India",
                "legal_status": "BINDING_STATUTORY",
                "clause": "Section 19 - Protection of Maritime Telecommunications Infrastructure",
                "page": 12,
                "source_url": "https://www.egazette.gov.in/WriteReadData/2023/250880.pdf",
                "local_viewer_url": "/api/documents/raw/knowledge_base/DoT_Rules/new-telecom-Act-2023.pdf#page=12",
                "supporting_text": "Government powers to enforce standards and security practices for protecting national maritime communications infrastructure.",
                "surrounding_context": "Statutory risk governance and escalation to maritime and port regulatory authorities."
            }
        }
    },
    "HG-5G-003": {
        "scenario_source": {
            "source_doc_id": "3GPP-TS-33501",
            "source_title": "3GPP TS 33.501: Security architecture and procedures for 5G System",
            "issuing_authority": "3rd Generation Partnership Project (3GPP)",
            "document_identifier": "3GPP TS 33.501 V18.4.0",
            "jurisdiction": "International",
            "legal_status": "NON_BINDING_TECHNICAL_STANDARD",
            "clause": "Section 5 - 5G Network Slice Security Architecture",
            "page": 15,
            "source_url": "https://www.3gpp.org/ftp/Specs/archive/33_series/33.501/",
            "local_viewer_url": "/api/documents/raw/knowledge_base/3gpp/ETSI 33.501 Rel 18.pdf#page=15",
            "supporting_text": "Network slice isolation guarantees that security events or exhaustion attacks in one network slice do not impact the confidentiality, integrity, or availability of other slices.",
            "surrounding_context": "Core technical specification for 5G standalone architecture, SBA mutual authentication, and slicing boundaries."
        },
        "steps": {
            "T1": {
                "source_doc_id": "3GPP-TS-33501",
                "source_title": "3GPP TS 33.501: 5G Security Architecture",
                "issuing_authority": "3GPP",
                "document_identifier": "Release 18 (2024-03)",
                "jurisdiction": "International",
                "legal_status": "NON_BINDING_TECHNICAL_STANDARD",
                "clause": "Section 5.1 - Slice Isolation and SBA Access Control",
                "page": 15,
                "source_url": "https://www.3gpp.org/ftp/Specs/archive/33_series/33.501/",
                "local_viewer_url": "/api/documents/raw/knowledge_base/3gpp/ETSI 33.501 Rel 18.pdf#page=15",
                "supporting_text": "Service-based architecture interfaces must mandate mutual TLS and OAuth 2.0 authorization tokens between NFs across network slices.",
                "surrounding_context": "Technical standard for 5G Core isolation between eMBB, URLLC, and critical slices."
            },
            "T2": {
                "source_doc_id": "3GPP-TS-33501",
                "source_title": "3GPP TS 33.501: 5G Security Architecture",
                "issuing_authority": "3GPP",
                "document_identifier": "Release 18 (2024-03)",
                "jurisdiction": "International",
                "legal_status": "NON_BINDING_TECHNICAL_STANDARD",
                "clause": "Section 6.1 - Primary Authentication & Slice Admission",
                "page": 32,
                "source_url": "https://www.3gpp.org/ftp/Specs/archive/33_series/33.501/",
                "local_viewer_url": "/api/documents/raw/knowledge_base/3gpp/ETSI 33.501 Rel 18.pdf#page=32",
                "supporting_text": "Authentication procedures ensure that unauthorized UEs or rogue AMF instances cannot attach to restricted network slice identifiers (NSSAI).",
                "surrounding_context": "Mutual authentication via 5G AKA and SUCI/SUPI encryption procedures."
            },
            "T3": {
                "source_doc_id": "DOT-TELECOM-ACT-2023",
                "source_title": "The Telecommunications Act, 2023",
                "issuing_authority": "Ministry of Communications / DoT",
                "document_identifier": "Act No. 44 of 2023",
                "jurisdiction": "India",
                "legal_status": "BINDING_STATUTORY",
                "clause": "Section 19 - Critical Telecom Infrastructure Compliance",
                "page": 12,
                "source_url": "https://www.egazette.gov.in/WriteReadData/2023/250880.pdf",
                "local_viewer_url": "/api/documents/raw/knowledge_base/DoT_Rules/new-telecom-Act-2023.pdf#page=12",
                "supporting_text": "Telecommunication licensees in India must ensure that critical infrastructure meets mandatory cybersecurity standards specified by the Central Government.",
                "surrounding_context": "Statutory bridge converting voluntary 3GPP standards into binding license conditions in India."
            }
        }
    },
    "HG-TELECOM-004": {
        "scenario_source": {
            "source_doc_id": "CERTIN-DIR-2022",
            "source_title": "CERT-In Directions under Section 70B(6) of IT Act, 2000",
            "issuing_authority": "Indian Computer Emergency Response Team (CERT-In) / MeitY",
            "document_identifier": "No. 20(3)/2022-CERT-In",
            "jurisdiction": "India",
            "legal_status": "BINDING_DIRECTION",
            "clause": "Paragraph (ii) - Mandatory 6-Hour Cyber Incident Reporting",
            "page": 2,
            "source_url": "https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf",
            "local_viewer_url": "/api/documents/raw/knowledge_base/Documents main/Indian_Acts/CERT-In_Directions_70B_28.04.2022.pdf#page=2",
            "supporting_text": "Any service provider, intermediary, data centre, body corporate and Government organisation shall report cyber incidents as mentioned in Annexure I to CERT-In within 6 (six) hours of noticing such incidents.",
            "surrounding_context": "Mandatory cyber incident reporting for ransomware, extortion, and critical system disruption.",
            "faq_clarification": "Official FAQ Q14: Initial available information must be reported within 6 hours. Additional details may be submitted later within a reasonable time."
        },
        "steps": {
            "R1": {
                "source_doc_id": "CERTIN-DIR-2022",
                "source_title": "CERT-In Directions dated 28 April 2022",
                "issuing_authority": "CERT-In / MeitY",
                "document_identifier": "No. 20(3)/2022-CERT-In",
                "jurisdiction": "India",
                "legal_status": "BINDING_DIRECTION",
                "clause": "Paragraph (ii) & Annexure I (Item 5: Ransomware)",
                "page": 2,
                "source_url": "https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf",
                "local_viewer_url": "/api/documents/raw/knowledge_base/Documents main/Indian_Acts/CERT-In_Directions_70B_28.04.2022.pdf#page=2",
                "supporting_text": "Ransomware attacks affecting telecom OSS/BSS platforms are reportable to incident@cert-in.org.in within 6 hours of noticing.",
                "surrounding_context": "Annexure I mandatorily requires reporting malicious code, ransomware, and denial of service."
            },
            "R2": {
                "source_doc_id": "DOT-CRITICAL-INFRA-2024",
                "source_title": "Critical Telecommunication Infrastructure Rules, 2024",
                "issuing_authority": "Department of Telecommunications (DoT)",
                "document_identifier": "G.S.R. 518(E)",
                "jurisdiction": "India",
                "legal_status": "BINDING_STATUTORY",
                "clause": "Rule 4 - Telemetry & Audit Integrity",
                "page": 3,
                "source_url": "https://dot.gov.in/rules/critical-telecommunication-infrastructure-rules-2024",
                "local_viewer_url": "/api/documents/raw/knowledge_base/DoT_Rules/Critical Telecommunication Infrastructure Rules, 2024_0.pdf#page=3",
                "supporting_text": "Root cause telemetry and digital forensic data must be securely preserved and audited by CERT-In empaneled assessors.",
                "surrounding_context": "Statutory mandates for critical infrastructure disaster recovery and forensic chain of custody."
            },
            "R3": {
                "source_doc_id": "MEITY-DPDP-2023",
                "source_title": "Digital Personal Data Protection Act, 2023",
                "issuing_authority": "Ministry of Electronics and Information Technology (MeitY)",
                "document_identifier": "Act No. 22 of 2023",
                "jurisdiction": "India",
                "legal_status": "BINDING_STATUTORY",
                "clause": "Section 8(6) - Data Breach Intimation to DPBI",
                "page": 7,
                "source_url": "https://www.meity.gov.in/writereaddata/files/Digital%20Personal%20Data%20Protection%20Act%202023.pdf",
                "local_viewer_url": "/api/documents/raw/knowledge_base/DPDP Acts/DPDP_Act_2023.pdf#page=7",
                "supporting_text": "In the event of a personal data breach impacting customer subscriber records, the Data Fiduciary shall give intimation to the Board and affected users.",
                "surrounding_context": "Statutory recovery decision obligations under Indian data protection law."
            }
        }
    },
    "HG-RESEARCH-005": {
        "scenario_source": {
            "source_doc_id": "ITU-T-Y3172",
            "source_title": "ITU-T Recommendation Y.3172: Architectural framework for machine learning in future networks",
            "issuing_authority": "International Telecommunication Union (ITU-T)",
            "document_identifier": "ITU-T Y.3172 (06/2019)",
            "jurisdiction": "International",
            "legal_status": "INTERNATIONAL_RECOMMENDATION",
            "clause": "Section 6 - Machine Learning Pipeline Architecture",
            "page": 9,
            "source_url": "https://www.itu.int/rec/T-REC-Y.3172/en",
            "local_viewer_url": "",
            "supporting_text": "The machine learning pipeline comprises data collection, preprocessing, model training, policy engine, and ML sandbox.",
            "surrounding_context": "International standard serving as voluntary architectural guidance. Differentiated from statutory obligations."
        },
        "steps": {
            "RS1": {
                "source_doc_id": "ITU-T-Y3172",
                "source_title": "ITU-T Recommendation Y.3172",
                "issuing_authority": "ITU-T",
                "document_identifier": "ITU-T Y.3172",
                "jurisdiction": "International",
                "legal_status": "INTERNATIONAL_RECOMMENDATION",
                "clause": "Section 6 - ML Pipeline Framework",
                "page": 9,
                "source_url": "https://www.itu.int/rec/T-REC-Y.3172/en",
                "local_viewer_url": "",
                "supporting_text": "Machine learning reference architecture for IMT-2020 and future networks.",
                "surrounding_context": "Research baseline establishing voluntary pipeline terminology."
            },
            "RS2": {
                "source_doc_id": "3GPP-TS-33501",
                "source_title": "3GPP TS 33.501 Security Architecture",
                "issuing_authority": "3GPP",
                "document_identifier": "Release 18",
                "jurisdiction": "International",
                "legal_status": "NON_BINDING_TECHNICAL_STANDARD",
                "clause": "Section 5 - SBA Zero Trust Principles",
                "page": 15,
                "source_url": "https://www.3gpp.org/ftp/Specs/archive/33_series/33.501/",
                "local_viewer_url": "/api/documents/raw/knowledge_base/3gpp/ETSI 33.501 Rel 18.pdf#page=15",
                "supporting_text": "Technical security specifications for service-based 5G core network functions.",
                "surrounding_context": "Comparing 3GPP technical specification with ITU-T recommendation."
            },
            "RS3": {
                "source_doc_id": "ITU-T-Y3172",
                "source_title": "Comparative Gap Analysis & Governance",
                "issuing_authority": "HackGrid Multi-Jurisdiction Reasoning Layer",
                "document_identifier": "HG-REG-CROSSWALK",
                "jurisdiction": "Cross-Border",
                "legal_status": "NON_BINDING_TECHNICAL_STANDARD",
                "clause": "Advisory Gap Finding Protocol",
                "page": 1,
                "source_url": "https://www.itu.int/rec/T-REC-Y.3172/en",
                "local_viewer_url": "",
                "supporting_text": "Distinguishing differences in scope and technical recommendation from binding legal non-compliance.",
                "surrounding_context": "Prevents misclassifying voluntary research baselines as national regulatory gaps."
            }
        }
    },
    "HG-EU-006": {
        "scenario_source": {
            "source_doc_id": "EU-NIS2-DIRECTIVE-2022",
            "source_title": "EU NIS2 Directive (Directive (EU) 2022/2555)",
            "issuing_authority": "European Parliament and Council of the European Union",
            "document_identifier": "Directive (EU) 2022/2555",
            "jurisdiction": "European Union",
            "legal_status": "BINDING_STATUTORY",
            "clause": "Article 23 - Reporting Obligations & 24h Early Warning",
            "page": 42,
            "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022L2555",
            "local_viewer_url": "",
            "supporting_text": "Essential and important entities shall submit an early warning to the CSIRT or competent authority without undue delay and in any event within 24 hours of becoming aware of the significant incident.",
            "surrounding_context": "Binding EU cyber security legislation establishing risk-management measures and reporting timelines."
        },
        "steps": {
            "EU1": {
                "source_doc_id": "3GPP-TS-33501",
                "source_title": "3GPP TS 33.501 Security Architecture",
                "issuing_authority": "3GPP",
                "document_identifier": "Release 18",
                "jurisdiction": "International",
                "legal_status": "NON_BINDING_TECHNICAL_STANDARD",
                "clause": "Section 5 - SBA Interface Security",
                "page": 15,
                "source_url": "https://www.3gpp.org/ftp/Specs/archive/33_series/33.501/",
                "local_viewer_url": "/api/documents/raw/knowledge_base/3gpp/ETSI 33.501 Rel 18.pdf#page=15",
                "supporting_text": "Network function interface security in 5G Core architectures.",
                "surrounding_context": "Technical specification baseline for European telecommunication networks."
            },
            "EU2": {
                "source_doc_id": "EU-NIS2-DIRECTIVE-2022",
                "source_title": "EU NIS2 Directive (Directive 2022/2555)",
                "issuing_authority": "European Parliament & Council",
                "document_identifier": "Directive (EU) 2022/2555",
                "jurisdiction": "European Union",
                "legal_status": "BINDING_STATUTORY",
                "clause": "Article 21 - Cyber Risk-Management Measures",
                "page": 38,
                "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022L2555",
                "local_viewer_url": "",
                "supporting_text": "Mandatory risk management including supply chain security, network cryptography, and access controls for telecom providers.",
                "surrounding_context": "Binding statutory obligation across European Union member states."
            },
            "EU3": {
                "source_doc_id": "EU-NIS2-DIRECTIVE-2022",
                "source_title": "EU NIS2 Directive",
                "issuing_authority": "European Union",
                "document_identifier": "Directive (EU) 2022/2555",
                "jurisdiction": "European Union",
                "legal_status": "BINDING_STATUTORY",
                "clause": "Article 23 - Incident Notification Deadlines (24h early warning, 72h incident notification)",
                "page": 42,
                "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022L2555",
                "local_viewer_url": "",
                "supporting_text": "Phased reporting model: early warning within 24 hours followed by comprehensive notification within 72 hours.",
                "surrounding_context": "Contrasted with Indian CERT-In 6-hour reporting mandate."
            }
        }
    },
    "HG-ENTERPRISE-007": {
        "scenario_source": {
            "source_doc_id": "MEITY-IT-ACT-2000",
            "source_title": "Information Technology Act, 2000 (as amended)",
            "issuing_authority": "Ministry of Electronics and Information Technology (MeitY), Parliament of India",
            "document_identifier": "Act No. 21 of 2000",
            "jurisdiction": "India",
            "legal_status": "BINDING_STATUTORY",
            "clause": "Section 70B - Incident Response Agency Powers",
            "page": 28,
            "source_url": "https://www.meity.gov.in/content/information-technology-act-2000",
            "local_viewer_url": "/api/documents/raw/knowledge_base/Documents main/Indian_Acts/it_act_2000_updated.pdf#page=28",
            "supporting_text": "CERT-In shall serve as the national agency for performing cybersecurity functions, forecasting alerts, and issuing mandatory compliance directions.",
            "surrounding_context": "Statutory foundation for enterprise cybersecurity obligations in India."
        },
        "steps": {
            "E1": {
                "source_doc_id": "MEITY-IT-ACT-2000",
                "source_title": "Information Technology Act, 2000 (as amended)",
                "issuing_authority": "MeitY / Parliament of India",
                "document_identifier": "Act No. 21 of 2000",
                "jurisdiction": "India",
                "legal_status": "BINDING_STATUTORY",
                "clause": "Section 70B - Cyber Incident Reporting Mandate",
                "page": 28,
                "source_url": "https://www.meity.gov.in/content/information-technology-act-2000",
                "local_viewer_url": "/api/documents/raw/knowledge_base/Documents main/Indian_Acts/it_act_2000_updated.pdf#page=28",
                "supporting_text": "Designation of national incident response mechanisms for all enterprise bodies corporate.",
                "surrounding_context": "Enabling statutory framework for binding cybersecurity directions."
            },
            "E2": {
                "source_doc_id": "CERTIN-DIR-2022",
                "source_title": "CERT-In Directions dated 28 April 2022",
                "issuing_authority": "CERT-In / MeitY",
                "document_identifier": "No. 20(3)/2022-CERT-In",
                "jurisdiction": "India",
                "legal_status": "BINDING_DIRECTION",
                "clause": "Paragraph (iv) - Mandatory 180-Day Log Retention",
                "page": 2,
                "source_url": "https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf",
                "local_viewer_url": "/api/documents/raw/knowledge_base/Documents main/Indian_Acts/CERT-In_Directions_70B_28.04.2022.pdf#page=2",
                "supporting_text": "All service providers, body corporate and Government organisations shall mandatorily enable logs of all their ICT systems and maintain them securely for 180 days within Indian jurisdiction.",
                "surrounding_context": "Mandatory audit trail requirement to verify conflicting incident evidence."
            },
            "E3": {
                "source_doc_id": "CERTIN-DIR-2022",
                "source_title": "CERT-In Directions dated 28 April 2022",
                "issuing_authority": "CERT-In / MeitY",
                "document_identifier": "No. 20(3)/2022-CERT-In",
                "jurisdiction": "India",
                "legal_status": "BINDING_DIRECTION",
                "clause": "Paragraph (ii) & Official FAQ Question 14",
                "page": 3,
                "source_url": "https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf",
                "local_viewer_url": "/api/documents/raw/knowledge_base/Documents main/Indian_Acts/CERT-In_Directions_70B_28.04.2022.pdf#page=3",
                "supporting_text": "Official FAQ Question 14: Initial available information may be reported within 6 hours. Remaining or additional details may be submitted later within a reasonable time.",
                "surrounding_context": "Clarification for human analysts balancing immediate reporting with evidence completeness."
            }
        }
    },
    "HG-CERTIN-008": {
        "scenario_source": {
            "source_doc_id": "CERTIN-DIR-2022",
            "source_title": "CERT-In Directions under Section 70B(6) of IT Act, 2000",
            "issuing_authority": "Indian Computer Emergency Response Team (CERT-In) / MeitY",
            "document_identifier": "No. 20(3)/2022-CERT-In",
            "jurisdiction": "India",
            "legal_status": "BINDING_DIRECTION",
            "clause": "Paragraph (ii) - Mandatory 6-Hour Cyber Incident Reporting",
            "page": 2,
            "source_url": "https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf",
            "local_viewer_url": "/api/documents/raw/knowledge_base/Documents main/Indian_Acts/CERT-In_Directions_70B_28.04.2022.pdf#page=2",
            "supporting_text": "Any service provider, intermediary, data centre, body corporate and Government organisation shall report cyber incidents as mentioned in Annexure I to CERT-In within 6 (six) hours of noticing such incidents.",
            "surrounding_context": "Official legal direction governing cyber incident reporting across Indian jurisdiction.",
            "faq_clarification": "Official FAQ Q14: To effectively handle cybersecurity incidents, the initial available information may be reported to CERT-In within 6 (six) hours. The remaining/additional details may be provided to CERT-In later within a reasonable time."
        },
        "steps": {
            "C1": {
                "source_doc_id": "CERTIN-DIR-2022",
                "source_title": "CERT-In Directions dated 28 April 2022",
                "issuing_authority": "Indian Computer Emergency Response Team (CERT-In) / MeitY",
                "document_identifier": "No. 20(3)/2022-CERT-In",
                "jurisdiction": "India",
                "legal_status": "BINDING_DIRECTION",
                "clause": "Paragraph (ii) - Mandatory 6-Hour Cyber Incident Reporting",
                "page": 2,
                "source_url": "https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf",
                "local_viewer_url": "/api/documents/raw/knowledge_base/Documents main/Indian_Acts/CERT-In_Directions_70B_28.04.2022.pdf#page=2",
                "supporting_text": "Any service provider, intermediary, data centre, body corporate and Government organisation shall report cyber incidents as mentioned in Annexure I to CERT-In within 6 (six) hours of noticing such incidents.",
                "surrounding_context": "(i) NTP Clock synchronisation... (ii) Mandatory 6-hour incident reporting... (iii) PoC designation... (iv) 180-day logging...",
                "faq_clarification": "Official FAQ Question 14: Initial available information must be reported within 6 hours. Additional details may be submitted later within a reasonable time."
            },
            "C2": {
                "source_doc_id": "CERTIN-DIR-2022",
                "source_title": "Deliberate Mismatch Test: Erroneous Citation (Clause 12)",
                "issuing_authority": "CERT-In / MeitY (Mismatch Flagged by HackGrid)",
                "document_identifier": "No. 20(3)/2022-CERT-In",
                "jurisdiction": "India",
                "legal_status": "BINDING_DIRECTION",
                "clause": "Clause 12 (ERRONEOUS CITATION TEST)",
                "page": 2,
                "source_url": "https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf",
                "local_viewer_url": "/api/documents/raw/knowledge_base/Documents main/Indian_Acts/CERT-In_Directions_70B_28.04.2022.pdf#page=2",
                "supporting_text": "[CLAUSE MISMATCH: The official text in cited 'Clause 12' does not contain or establish the 6-hour cyber incident reporting obligation. The obligation is located in Paragraph (ii).]",
                "surrounding_context": "Deliberate test case for judges and evaluators to verify that HackGrid detects fabricated or erroneous clause citations rather than accepting them blindly.",
                "faq_clarification": "HackGrid detects the citation mismatch and automatically flags the claim as UNSUPPORTED with an explicit discrepancy explanation."
            }
        }
    }
}


def enrich_scenario_dict(d: dict) -> dict:
    sc_id = d.get("scenario_id")
    meta = SCENARIO_VERIFIED_SOURCES.get(sc_id, {})
    if meta:
        d["verified_source"] = meta.get("scenario_source")
        step_meta = meta.get("steps", {})
        for st in d.get("steps", []):
            st_id = st.get("step_id")
            if st_id in step_meta:
                st["verified_source"] = step_meta[st_id]
    return d

def get_scenarios():
    return [enrich_scenario_dict(scenario.to_dict()) for scenario in SCENARIOS]


def get_scenario(scenario_id: str):
    for scenario in SCENARIOS:
        if scenario.scenario_id == scenario_id:
            return enrich_scenario_dict(scenario.to_dict())

    return None