from __future__ import annotations
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

@dataclass
class ClauseMetadata:
    clause_id: str
    clause_title: str
    page: int
    text: str
    surrounding_context: str = ''
    faq_clarification: Optional[str] = None

@dataclass
class SourceDocumentMetadata:
    doc_id: str
    title: str
    issuing_authority: str
    document_identifier: str
    version: str
    publication_date: str
    effective_date: str
    jurisdiction: str
    document_type: str
    legal_status: str  # BINDING_STATUTORY | BINDING_DIRECTION | NON_BINDING_TECHNICAL_STANDARD | INTERNATIONAL_RECOMMENDATION
    official_url: str
    local_path: str = ''
    faq_url: Optional[str] = None
    clauses: Dict[str, ClauseMetadata] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def find_local_document_path(source_file_or_name: str) -> str:
    """
    Safely find the real relative path of a source document PDF on disk.
    Searches knowledge_base, Documents main, and all subfolders.
    """
    if not source_file_or_name:
        return ""
    clean = str(source_file_or_name).replace("\\", "/").lstrip("/")
    
    # 1. Direct path check
    p1 = PROJECT_ROOT / clean
    if p1.is_file():
        return clean
        
    # 2. Under knowledge_base
    p2 = PROJECT_ROOT / "knowledge_base" / clean
    if p2.is_file():
        return f"knowledge_base/{clean}"
        
    # 3. Under knowledge_base / Documents main
    p3 = PROJECT_ROOT / "knowledge_base" / "Documents main" / clean
    if p3.is_file():
        return f"knowledge_base/Documents main/{clean}"
        
    # 4. Search by filename across knowledge_base
    fname = Path(clean).name
    matches = list((PROJECT_ROOT / "knowledge_base").rglob(fname))
    if matches and matches[0].is_file():
        return str(matches[0].relative_to(PROJECT_ROOT)).replace("\\", "/")
        
    return clean

DOCUMENT_REGISTRY: Dict[str, SourceDocumentMetadata] = {
    'CERTIN-DIR-2022': SourceDocumentMetadata(
        doc_id='CERTIN-DIR-2022',
        title='Directions under sub-section (6) of section 70B of the Information Technology Act, 2000 relating to information security practices, procedure, prevention, response and reporting of cyber incidents for Safe and Trusted Internet',
        issuing_authority='Indian Computer Emergency Response Team (CERT-In), Ministry of Electronics and Information Technology (MeitY), Government of India',
        document_identifier='No. 20(3)/2022-CERT-In',
        version='Directions 2022 (with FAQs dated 18.05.2022)',
        publication_date='2022-04-28',
        effective_date='2022-06-27',
        jurisdiction='India',
        document_type='Government Direction (Statutory)',
        legal_status='BINDING_DIRECTION',
        official_url='https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf',
        faq_url='https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_FAQs_18.05.2022.pdf',
        local_path='knowledge_base/Documents main/Indian_Acts/CERT-In_Directions_70B_28.04.2022.pdf',
        clauses={
            'para_2_ii': ClauseMetadata(
                clause_id='para_2_ii',
                clause_title='Paragraph (ii) - Mandatory 6-Hour Cyber Incident Reporting',
                page=2,
                text='Any service provider, intermediary, data centre, body corporate and Government organisation shall report cyber incidents as mentioned in Annexure I to CERT-In within 6 (six) hours of noticing such incidents or being brought to notice about such incidents. The cyber incidents can be reported to CERT-In via email (incident@cert-in.org.in), Phone (1800-11-4949) and Fax (1800-11-6969).',
                surrounding_context='(i) NTP Clock synchronisation to NPL/NIC...\n(ii) Mandatory cyber incident reporting within 6 hours to CERT-In...\n(iii) Designation of Point of Contact (PoC) to interface with CERT-In...\n(iv) Mandatory logging enabled and securely maintained for rolling 180 days within Indian jurisdiction.',
                faq_clarification='Official FAQ Clarification (FAQ Q14, 18 May 2022): To effectively handle cybersecurity incidents, the initial available information may be reported to CERT-In within 6 (six) hours of noticing the incident or being brought to notice about such incident. The remaining/additional details may be provided to CERT-In later within a reasonable time so that CERT-In can assist and take timely action.'
            ),
            'para_2_i': ClauseMetadata(
                clause_id='para_2_i',
                clause_title='Paragraph (i) - Mandatory NTP Time Synchronisation',
                page=2,
                text='All service providers, intermediaries, data centres, body corporate and Government organisations shall connect to the Network Time Protocol (NTP) Server of National Physical Laboratory (NPL) or National Informatics Centre (NIC) or NTP servers traceable to these for synchronisation of all their ICT systems clocks.',
                surrounding_context='Directions issued for compliance by all service providers, intermediaries, data centres, body corporate and Government organisations.'
            ),
            'para_2_iv': ClauseMetadata(
                clause_id='para_2_iv',
                clause_title='Paragraph (iv) - Mandatory 180-Day Log Retention',
                page=2,
                text='All service providers, intermediaries, data centres, body corporate and Government organisations shall mandatorily enable logs of all their ICT systems and maintain them securely for a rolling period of 180 days within the Indian jurisdiction.',
                surrounding_context='(iii) Designation of Point of Contact... (iv) Enable logs and maintain securely for 180 days... (v) VPS/Cloud/VPN customer KYC maintenance for 5 years.'
            ),
            'annexure_i': ClauseMetadata(
                clause_id='annexure_i',
                clause_title='Annexure I - Cyber Incidents Mandatorily Reportable',
                page=3,
                text='Types of cyber incidents mandatorily to be reported to CERT-In include: Targeted scanning/probing of critical networks/systems; Compromise of critical systems/information; Unauthorised access of IT systems/data; Defacement of website; Malicious code attacks; DoS and DDoS attacks; Attacks on Critical Information Infrastructure (CII); Data Breach and Data Leak incidents.',
                surrounding_context='Annexure I lists categories of cybersecurity incidents that must be reported to CERT-In within the mandatory 6-hour window.'
            ),
        }
    ),
    'DOT-TELECOM-ACT-2023': SourceDocumentMetadata(
        doc_id='DOT-TELECOM-ACT-2023',
        title='The Telecommunications Act, 2023',
        issuing_authority='Ministry of Communications, Department of Telecommunications (DoT), Parliament of India',
        document_identifier='Act No. 44 of 2023',
        version='Gazette of India, Extraordinary, Part II, Section 1',
        publication_date='2023-12-24',
        effective_date='2024-06-26',
        jurisdiction='India',
        document_type='Statute / Act of Parliament',
        legal_status='BINDING_STATUTORY',
        official_url='https://www.egazette.gov.in/WriteReadData/2023/250880.pdf',
        local_path='knowledge_base/Documents main/DoT_Rules/new-telecom-Act-2023.pdf',
        clauses={
            'sec_19': ClauseMetadata(
                clause_id='sec_19',
                clause_title='Section 19 - Protection of Telecommunication Networks and Critical Telecommunication Infrastructure',
                page=12,
                text='The Central Government may, for reasons to be recorded in writing, by notification, notify critical telecommunication infrastructure and provide standards, security practices and procedures for protection of such critical infrastructure.',
                surrounding_context='Chapter VI: Cybersecurity and Network Integrity. Sections 19-22 govern protection of networks, security standards, and national security directives.'
            ),
            'sec_20': ClauseMetadata(
                clause_id='sec_20',
                clause_title='Section 20 - Measures for National Security and Public Safety',
                page=13,
                text='On the occurrence of any public emergency, including the security of the State, the Central Government or a State Government may take temporary possession of any telecommunication service or telecommunication network.',
                surrounding_context='Emergency powers, interception safeguards, and network suspension authorities.'
            )
        }
    ),
    'DOT-CRITICAL-INFRA-2024': SourceDocumentMetadata(
        doc_id='DOT-CRITICAL-INFRA-2024',
        title='Critical Telecommunication Infrastructure Rules, 2024',
        issuing_authority='Department of Telecommunications (DoT), Ministry of Communications',
        document_identifier='G.S.R. 518(E)',
        version='Notification dated 2024',
        publication_date='2024-07-01',
        effective_date='2024-07-01',
        jurisdiction='India',
        document_type='Subordinate Legislation / Statutory Rules',
        legal_status='BINDING_STATUTORY',
        official_url='https://dot.gov.in/rules/critical-telecommunication-infrastructure-rules-2024',
        local_path='knowledge_base/Documents main/DoT_Rules/Critical Telecommunication Infrastructure Rules, 2024_0.pdf',
        clauses={
            'rule_4': ClauseMetadata(
                clause_id='rule_4',
                clause_title='Rule 4 - Security Audit and Vulnerability Assessment',
                page=3,
                text='Every telecommunication entity managing Critical Telecommunication Infrastructure shall undergo periodic cybersecurity audits by CERT-In empaneled auditors and implement mandatory security telemetry.',
                surrounding_context='Obligations on designated telecommunication service providers for safeguarding critical national infrastructure.'
            )
        }
    ),
    'MEITY-DPDP-2023': SourceDocumentMetadata(
        doc_id='MEITY-DPDP-2023',
        title='Digital Personal Data Protection Act, 2023',
        issuing_authority='Ministry of Electronics and Information Technology (MeitY), Parliament of India',
        document_identifier='Act No. 22 of 2023',
        version='Gazette of India, Extraordinary, Part II, Section 1',
        publication_date='2023-08-11',
        effective_date='2023-08-11',
        jurisdiction='India',
        document_type='Statute / Act of Parliament',
        legal_status='BINDING_STATUTORY',
        official_url='https://www.meity.gov.in/writereaddata/files/Digital%20Personal%20Data%20Protection%20Act%202023.pdf',
        local_path='knowledge_base/Documents main/DPDP Acts/DPDP Act_2023.pdf',
        clauses={
            'sec_8_6': ClauseMetadata(
                clause_id='sec_8_6',
                clause_title='Section 8(6) - Personal Data Breach Notification',
                page=7,
                text='In the event of a personal data breach, the Data Fiduciary shall give the Data Protection Board of India and each affected Data Principal intimation of such breach in such form and manner as may be prescribed.',
                surrounding_context='Obligations of Data Fiduciary to protect personal data by taking reasonable security safeguards to prevent personal data breach.'
            )
        }
    ),
    'MEITY-IT-ACT-2000': SourceDocumentMetadata(
        doc_id='MEITY-IT-ACT-2000',
        title='Information Technology Act, 2000 (as amended)',
        issuing_authority='Ministry of Electronics and Information Technology (MeitY), Parliament of India',
        document_identifier='Act No. 21 of 2000',
        version='Amended 2008 / 2022',
        publication_date='2000-06-09',
        effective_date='2000-10-17',
        jurisdiction='India',
        document_type='Statute / Act of Parliament',
        legal_status='BINDING_STATUTORY',
        official_url='https://www.meity.gov.in/content/information-technology-act-2000',
        local_path='knowledge_base/Documents main/Indian_Acts/it_act_2000_updated.pdf',
        clauses={
            'sec_70b': ClauseMetadata(
                clause_id='sec_70b',
                clause_title='Section 70B - CERT-In incident response mandate',
                page=28,
                text='CERT-In shall serve as the national agency for performing cybersecurity functions, including collection, analysis and dissemination of information on cyber incidents, and issuing directions under subsection (6).',
                surrounding_context='Sub-section (6) provides that any entity failing to comply with directions shall be liable to punishment.'
            )
        }
    ),
    'MEITY-IT-ACT-RULES-2000': SourceDocumentMetadata(
        doc_id='MEITY-IT-ACT-RULES-2000',
        title='Information Technology (Certifying Authorities) Rules, 2000 & Statutory Notifications',
        issuing_authority='Ministry of Information Technology (MeitY), Government of India',
        document_identifier='G.S.R. 788(E) / G.S.R. 789(E)',
        version='Rules 2000 (G.S.R. 788(E))',
        publication_date='2000-10-17',
        effective_date='2000-10-17',
        jurisdiction='India',
        document_type='Subordinate Legislation / Statutory Rules',
        legal_status='BINDING_STATUTORY',
        official_url='https://www.meity.gov.in/content/information-technology-act-2000',
        local_path='knowledge_base/Documents main/Indian_Acts/IT-Act-Rules_2000_0.pdf',
        clauses={
            'notif_gsr_788': ClauseMetadata(
                clause_id='notif_gsr_788',
                clause_title='Notification G.S.R. 788(E) - Commencement of IT Act 2000',
                page=1,
                text='In exercise of the powers conferred by sub-section (3) of section 1 of the Information Technology Act, 2000 (21 of 2000), the Central Government hereby appoints 17th Day of October 2000 as the date on which the provisions of the said Act comes into force.',
                surrounding_context='[To be published in the Gazette of India, Extraordinary, Part II, Section 3, Sub-section (i)] Government of India Ministry of Information Technology New Delhi, the 17th October, 2000 NOTIFICATION G.S.R 788 (E) [ No. 1(20)/97-IID(NII)/F6] (P.M.Singh) Joint Secretary'
            ),
            'notif_gsr_789': ClauseMetadata(
                clause_id='notif_gsr_789',
                clause_title='Notification G.S.R. 789(E) - Information Technology (Certifying Authorities) Rules 2000',
                page=1,
                text='In exercise of the powers conferred by section 87 of the Information Technology Act, 2000 (21 of 2000), the Central Government hereby makes the following rules regulating the application and other procedures for Certifying Authorities...',
                surrounding_context='Central Government rules regulating electronic signatures, public key certificates, and Certifying Authorities under Section 87.'
            ),
            'rule_2': ClauseMetadata(
                clause_id='rule_2',
                clause_title='Rule 2 - Definitions',
                page=2,
                text='In these Rules, unless the context otherwise requires, (a) "Act" means the Information Technology Act, 2000 (21 of 2000); (b) "applicant" means Certifying Authority applicant; (c) "auditor" means any accredited computer security professional...',
                surrounding_context='Statutory definitions for Certifying Authorities, private keys, and repository security.'
            )
        }
    ),
    'DOT-MTCTE-2023': SourceDocumentMetadata(
        doc_id='DOT-MTCTE-2023',
        title='Mandatory Testing and Certification of Telecom Equipment (MTCTE) Regulations',
        issuing_authority='Telecommunication Engineering Centre (TEC), Department of Telecommunications (DoT)',
        document_identifier='TEC MTCTE Procedure',
        version='Gazette Notification 2017 as updated 2023/2024',
        publication_date='2017-09-05',
        effective_date='2019-10-01',
        jurisdiction='India',
        document_type='Technical Regulation',
        legal_status='BINDING_STATUTORY',
        official_url='https://mtcte.tec.gov.in/',
        local_path='knowledge_base/Documents main/MTCTE Regulations/Testing and Certification MTCTE.pdf',
        clauses={
            'proc_sec_4': ClauseMetadata(
                clause_id='proc_sec_4',
                clause_title='Section 4 - Mandatory Security and Conformance Testing',
                page=8,
                text='Telecom equipment must be tested by designated Conformance Assessment Bodies (CABs) for EMI/EMC, Technical Requirements (ERs), and Telecom Security Requirements (ITSARs) before sale or deployment in India.',
                surrounding_context='Mandatory certification under Indian Telegraph Rules prior to network deployment.'
            )
        }
    ),
    'ITU-T-Y3172': SourceDocumentMetadata(
        doc_id='ITU-T-Y3172',
        title='ITU-T Recommendation Y.3172: Architectural framework for machine learning in future networks including IMT-2020',
        issuing_authority='International Telecommunication Union - Telecommunication Standardization Sector (ITU-T)',
        document_identifier='ITU-T Y.3172 (06/2019)',
        version='Edition 1.0 (2019)',
        publication_date='2019-06-13',
        effective_date='2019-06-13',
        jurisdiction='International',
        document_type='International Standard / Recommendation',
        legal_status='INTERNATIONAL_RECOMMENDATION',
        official_url='https://www.itu.int/rec/T-REC-Y.3172/en',
        clauses={
            'sec_6': ClauseMetadata(
                clause_id='sec_6',
                clause_title='Section 6 - Machine Learning Pipeline Architecture',
                page=9,
                text='The machine learning pipeline in future networks comprises data collection (src), preprocessing (prep), model training and execution (model), policy engine, and ML sandbox.',
                surrounding_context='ITU-T Recommendations serve as voluntary international technical reference architectures unless specifically adopted by national legislation.'
            )
        }
    ),
    '3GPP-TS-33501': SourceDocumentMetadata(
        doc_id='3GPP-TS-33501',
        title='3GPP TS 33.501: Security architecture and procedures for 5G System',
        issuing_authority='3rd Generation Partnership Project (3GPP)',
        document_identifier='3GPP TS 33.501 V18.4.0',
        version='Release 18 (2024-03)',
        publication_date='2024-03-22',
        effective_date='2024-03-22',
        jurisdiction='International',
        document_type='Technical Specification',
        legal_status='NON_BINDING_TECHNICAL_STANDARD',
        official_url='https://www.3gpp.org/ftp/Specs/archive/33_series/33.501/',
        local_path='knowledge_base/Documents main/3gpp/ETSI 33.501 Rel 18.pdf',
        clauses={
            'sec_5': ClauseMetadata(
                clause_id='sec_5',
                clause_title='Section 5 - 5G Security Principles and Architecture',
                page=15,
                text='Network access security provides users with secure access to 5G services, protecting against radio interface attacks. Network domain security protects signaling and user plane data across SBA interfaces.',
                surrounding_context='Technical specifications defined by 3GPP. Adopted in India through TSDSI national transposed standards and DoT license conditions.'
            ),
            'sec_6_1': ClauseMetadata(
                clause_id='sec_6_1',
                clause_title='Section 6.1 - Primary Authentication and Key Agreement (5G AKA)',
                page=32,
                text='Mutual authentication between the UE and the network is performed via 5G AKA or EAP-AKA protocol using the Subscription Permanent Identifier (SUPI) protected by the SUCI mechanism.',
                surrounding_context='Subscriber privacy and authentication procedures for 5G standalone networks.'
            )
        }
    ),
    'DGCA-DRONE-RULES-2021': SourceDocumentMetadata(
        doc_id='DGCA-DRONE-RULES-2021',
        title='Drone Rules, 2021 (as amended)',
        issuing_authority='Ministry of Civil Aviation / Directorate General of Civil Aviation (DGCA), Government of India',
        document_identifier='G.S.R. 589(E)',
        version='Gazette Notification 2021 as amended 2022/2023',
        publication_date='2021-08-25',
        effective_date='2021-08-25',
        jurisdiction='India',
        document_type='Statutory Rules',
        legal_status='BINDING_STATUTORY',
        official_url='https://www.civilaviation.gov.in/sites/default/files/Drone%20Rules%202021.pdf',
        local_path='knowledge_base/DEFENCE/Drone Rules 2021.pdf',
        clauses={
            'rule_11': ClauseMetadata(
                clause_id='rule_11',
                clause_title='Rule 11 - Type Certificate and Mandatory Equipment',
                page=5,
                text='No unmanned aircraft system shall operate in India without a valid type certificate issued by the Director General certifying compliance with safety and communication security standards.',
                surrounding_context='Mandatory safety, communication datalink, and geofencing requirements for UAV operations.'
            )
        }
    )
}

def resolve_document_metadata(
    identifier_or_text: str,
    jurisdiction_hint: Optional[str] = None
) -> Optional[SourceDocumentMetadata]:
    if not identifier_or_text:
        return None
    
    text = str(identifier_or_text).lower()
    
    upper_id = identifier_or_text.strip().upper()
    if upper_id in DOCUMENT_REGISTRY:
        return DOCUMENT_REGISTRY[upper_id]
        
    if any(k in text for k in ['cert-in', 'certin', '70b', '6 hour', 'six hour', 'cyber incidents as mentioned in annexure i']) and not ('itu' in text or '3gpp' in text):
        return DOCUMENT_REGISTRY['CERTIN-DIR-2022']
        
    if any(k in text for k in ['telecom act 2023', 'telecommunications act', 'dot_rules/new-telecom', 'act no. 44 of 2023']):
        return DOCUMENT_REGISTRY['DOT-TELECOM-ACT-2023']
        
    if any(k in text for k in ['critical telecommunication', 'gsr 518', 'critical telecom infrastructure']):
        return DOCUMENT_REGISTRY['DOT-CRITICAL-INFRA-2024']
        
    if any(k in text for k in ['dpdp', 'digital personal data', 'act no. 22 of 2023', 'data protection act']):
        return DOCUMENT_REGISTRY['MEITY-DPDP-2023']
        
    if any(k in text for k in ['it-act-rules', 'rules_2000', 'rules 2000', 'it-act-rules_2000_0', 'certifying authorities rules']):
        return DOCUMENT_REGISTRY['MEITY-IT-ACT-RULES-2000']
        
    if any(k in text for k in ['it act', 'it-act', 'information technology act 2000']):
        return DOCUMENT_REGISTRY['MEITY-IT-ACT-2000']
        
    if any(k in text for k in ['mtcte', 'testing and certification mtcte', 'mandatory testing']):
        return DOCUMENT_REGISTRY['DOT-MTCTE-2023']
        
    if any(k in text for k in ['y.3172', 'y3172', 'itu-t', 'itu recommendation']):
        return DOCUMENT_REGISTRY['ITU-T-Y3172']
        
    if any(k in text for k in ['33.501', '33501', '3gpp', 'etsi 33.501', 'etsi rel 18']):
        return DOCUMENT_REGISTRY['3GPP-TS-33501']
        
    if any(k in text for k in ['drone rules', 'uav', 'defence/drone']):
        return DOCUMENT_REGISTRY['DGCA-DRONE-RULES-2021']
        
    return None

def resolve_document_from_evidence(evidence_record: Dict[str, Any]) -> SourceDocumentMetadata:
    meta = evidence_record.get('metadata') or evidence_record.get('provenance') or {}
    candidates = [
        evidence_record.get('title', ''),
        meta.get('document', ''),
        meta.get('source_file', ''),
        meta.get('publisher', ''),
        evidence_record.get('evidence_id', ''),
        str(evidence_record.get('text', ''))[:200]
    ]
    for c in candidates:
        if c:
            resolved = resolve_document_metadata(c)
            if resolved:
                return resolved

    title_str = meta.get('document') or meta.get('source_file') or evidence_record.get('title') or 'Indexed Knowledge Document'
    jur = meta.get('jurisdiction') or 'India'
    sf = meta.get('source_file') or ''
    resolved_disk_path = find_local_document_path(sf) if sf else ''
    
    return SourceDocumentMetadata(
        doc_id=f'GEN-{abs(hash(title_str)) % 100000:05d}',
        title=title_str,
        issuing_authority=meta.get('publisher') or ('Authorized Regulatory Body' if jur == 'India' else 'Standards Organization'),
        document_identifier=meta.get('version') or 'Indexed Source Document',
        version=meta.get('version') or 'Indexed Release',
        publication_date=meta.get('publication_date') or 'Documented',
        effective_date=meta.get('effective_date') or 'Applicable',
        jurisdiction=jur,
        document_type=meta.get('document_type') or 'Technical Document',
        legal_status='BINDING_STATUTORY' if jur == 'India' and any(k in title_str.lower() for k in ['act', 'rule', 'direction']) else 'NON_BINDING_TECHNICAL_STANDARD',
        official_url='' if not sf.endswith('.pdf') else 'https://dot.gov.in/',
        local_path=resolved_disk_path
    )
