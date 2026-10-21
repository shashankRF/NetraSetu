from __future__ import annotations
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF

try:
    from .document_registry import (
        SourceDocumentMetadata,
        ClauseMetadata,
        DOCUMENT_REGISTRY,
        resolve_document_metadata,
        resolve_document_from_evidence,
    )
except ImportError:
    from Backend.evidence_engine.document_registry import (
        SourceDocumentMetadata,
        ClauseMetadata,
        DOCUMENT_REGISTRY,
        resolve_document_metadata,
        resolve_document_from_evidence,
    )

# Robust project root determination
CURRENT_FILE = Path(__file__).resolve()
if "evidence_engine" in str(CURRENT_FILE):
    PROJECT_ROOT = CURRENT_FILE.parent.parent.parent
else:
    PROJECT_ROOT = Path(r"C:\Users\Shashank Kotnala\OneDrive\Documents\NetraSetu")


class VerificationStatus:
    EXACT_MATCH_VERIFIED = "EXACT_MATCH_VERIFIED"
    MATCH_VERIFIED_WITH_OCR = "MATCH_VERIFIED_WITH_OCR"
    CLAUSE_LOCATION_VERIFIED_QUOTE_UNVERIFIED = "CLAUSE_LOCATION_VERIFIED_QUOTE_UNVERIFIED"
    QUOTE_NOT_VERIFIED = "QUOTE_NOT_VERIFIED"
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNSUPPORTED = "UNSUPPORTED"
    UNVERIFIED = "UNVERIFIED"


@dataclass
class StructuredEvidenceRecord:
    claim_id: str
    claim: str
    source_doc_id: str
    source_title: str
    issuing_authority: str
    document_identifier: str
    version: str
    publication_date: str
    effective_date: str
    jurisdiction: str
    legal_status: str  # BINDING_STATUTORY | BINDING_DIRECTION | NON_BINDING_TECHNICAL_STANDARD | INTERNATIONAL_RECOMMENDATION
    clause: str
    page: Optional[int]
    source_url: str
    local_viewer_url: str
    supporting_text: str
    surrounding_context: str
    relationship: str
    verification_status: str  # EXACT_MATCH_VERIFIED | CLAUSE_LOCATION_VERIFIED_QUOTE_UNVERIFIED | QUOTE_NOT_VERIFIED | SUPPORTED | ...
    verification_explanation: str
    contradictory_evidence: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    faq_clarification: Optional[str] = None
    # Enhanced Phase 2 traceability & highlighting fields:
    rule_number: Optional[str] = None
    rule_title: Optional[str] = None
    subrule_number: Optional[str] = None
    clause_number: Optional[str] = None
    subclause_letter: Optional[str] = None
    full_clause_hierarchy: Optional[str] = None
    printed_page_number: Optional[int] = None
    zero_based_pdf_page_index: int = 0
    viewer_page_number: int = 1
    exact_source_quote: str = ""
    ai_generated_summary: Optional[str] = None
    bounding_boxes: List[Dict[str, float]] = field(default_factory=list)
    source_line_numbers: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def normalize_clause_key(clause_str: str) -> str:
    if not clause_str:
        return ""
    c = str(clause_str).lower().strip()
    c = re.sub(r"[^a-z0-9]", "", c)
    return c


def extract_clause_and_page(
    claim_text: str,
    evidence_meta: Dict[str, Any],
) -> Tuple[str, Optional[int]]:
    clause = evidence_meta.get("clause") or ""
    page = evidence_meta.get("page")

    if not clause:
        c_match = re.search(
            r"(paragraph\s*\(?[a-z0-9ivx]+\)?|clause\s*[0-9]+(\.[0-9]+)*|section\s*[0-9]+(\([0-9a-z]+\))?|rule\s*[0-9]+(?:\([0-9a-z]+\))*)",
            claim_text,
            re.IGNORECASE,
        )
        if c_match:
            clause = c_match.group(0).strip()

    if not page:
        p_match = re.search(r"(?:page|p\.)\s*([0-9]+)", claim_text, re.IGNORECASE)
        if p_match:
            try:
                page = int(p_match.group(1))
            except Exception:
                page = None

    return clause or "General Provision", page


class LegalClauseParser:
    """
    Layout and regex parser for Indian gazettes, statutory rules, directions, and acts.
    """
    @staticmethod
    def extract_printed_page(page_text: str, fallback_page: int) -> int:
        lines = [l.strip() for l in page_text.splitlines() if l.strip()]
        candidates = lines[:4] + lines[-4:]
        for c in candidates:
            m = re.fullmatch(r"(\d{1,4})", c)
            if m:
                try:
                    val = int(m.group(1))
                    if 1 <= val <= 2000:
                        return val
                except Exception:
                    pass
        return fallback_page

    @staticmethod
    def parse_clause_hierarchy(
        doc: fitz.Document,
        page_index: int,
        target_quote: str = "",
    ) -> Dict[str, Any]:
        """
        Parses rules, sub-rules, and clauses from the page text, accounting for
        cross-page rule boundaries (e.g. Rule 6 starting on page 7 and continuing to page 8).
        """
        page = doc[page_index]
        page_text = page.get_text()

        # Rule header regex: e.g. "6. Chief Telecommunication Security Officer."
        rule_pattern = re.compile(r"(?:^|\n)\s*(\d+)\.\s+([A-Z][^\n\.\(]+?)(?:\.|\n|\r)")
        rules_on_page = []
        for m in rule_pattern.finditer(page_text):
            rules_on_page.append({
                "start": m.start(),
                "number": f"Rule {m.group(1)}",
                "raw_num": m.group(1),
                "title": m.group(2).strip(),
                "content_start": m.end(),
                "page_index": page_index,
            })

        # Section pattern: e.g. "Section 70B"
        sec_pattern = re.compile(r"(?:^|\n)\s*(?:Section|Sec\.)\s*(\d+[A-Z]?)\.?\s*([^\n\.\(]*)", re.IGNORECASE)
        for m in sec_pattern.finditer(page_text):
            rules_on_page.append({
                "start": m.start(),
                "number": f"Section {m.group(1)}",
                "raw_num": m.group(1),
                "title": m.group(2).strip(),
                "content_start": m.end(),
                "page_index": page_index,
            })

        # Gazette directions often label an operative provision as a
        # paragraph (for example, "(ii) MANDATORY ...:") rather than a rule.
        paragraph_pattern = re.compile(
            r"(?:^|\n)\s*\(([ivxlcdm]+)\)\s+([A-Z][^\n:]{2,120}):",
            re.IGNORECASE,
        )
        for m in paragraph_pattern.finditer(page_text):
            rules_on_page.append({
                "start": m.start(),
                "number": f"Paragraph ({m.group(1).lower()})",
                "raw_num": m.group(1).lower(),
                "title": m.group(2).strip().title(),
                "content_start": m.end(),
                "page_index": page_index,
                "provision_type": "paragraph",
            })

        rules_on_page.sort(key=lambda r: r["start"])

        # Determine quote position
        quote_pos = -1
        if target_quote:
            q_needle = target_quote.strip()[:35].lower()
            quote_pos = page_text.lower().find(q_needle)

        active_rule = None
        if quote_pos != -1:
            preceding = [r for r in rules_on_page if r["start"] <= quote_pos]
            if preceding:
                active_rule = preceding[-1]
            elif page_index > 0:
                # Quote appears BEFORE any rule header on this page
                # Look at previous page to find the running rule!
                prev_text = doc[page_index - 1].get_text()
                prev_rules = []
                for m in rule_pattern.finditer(prev_text):
                    prev_rules.append({
                        "start": m.start(),
                        "content_start": m.end(),
                        "number": f"Rule {m.group(1)}",
                        "raw_num": m.group(1),
                        "title": m.group(2).strip(),
                        "page_index": page_index - 1,
                    })
                if prev_rules:
                    active_rule = prev_rules[-1]
        elif rules_on_page:
            active_rule = rules_on_page[0]
        elif page_index > 0:
            prev_text = doc[page_index - 1].get_text()
            prev_rules = []
            for m in rule_pattern.finditer(prev_text):
                prev_rules.append({
                    "start": m.start(),
                    "content_start": m.end(),
                    "number": f"Rule {m.group(1)}",
                    "raw_num": m.group(1),
                    "title": m.group(2).strip(),
                    "page_index": page_index - 1,
                })
            if prev_rules:
                active_rule = prev_rules[-1]

        # Derive nested provision markers from source text preceding the
        # located quote, never from the generated claim.
        subrule = None
        subclause = None
        if quote_pos >= 0:
            if active_rule and active_rule.get("page_index") == page_index:
                hierarchy_text = page_text[active_rule.get("content_start", active_rule.get("start", 0)):quote_pos]
            elif active_rule and active_rule.get("page_index") == page_index - 1:
                prev_text = doc[page_index - 1].get_text()
                hierarchy_text = prev_text[active_rule.get("content_start", active_rule.get("start", 0)):] + "\n" + page_text[:quote_pos]
            else:
                hierarchy_text = page_text[:quote_pos]
            for line in hierarchy_text.splitlines():
                marker = re.match(r"^\s*[^\w]*\((\d+)\)\s*", line)
                if marker:
                    subrule = marker.group(1)
                    subclause = None
                    nested_marker = re.match(r"^\s*[^\w]*\(([a-z])\)\s*", line[marker.end():], re.IGNORECASE)
                    if nested_marker:
                        subclause = f"({nested_marker.group(1).lower()})"
                    continue
                marker = re.match(r"^\s*[^\w]*\(([a-z])\)\s*", line, re.IGNORECASE)
                if marker:
                    subclause = f"({marker.group(1).lower()})"
            # Some gazette layouts extract the marker and its provision text
            # onto separate PDF lines; the verbatim source quote may therefore
            # begin with the marker even though it is not before quote_pos.
            leading_marker = re.match(r"^\s*\((\d+|[a-z])\)\s*", target_quote, re.IGNORECASE)
            if leading_marker:
                value = leading_marker.group(1)
                if value.isdigit():
                    subrule = value
                    subclause = None
                else:
                    subclause = f"({value.lower()})"

        rule_num = active_rule["number"] if active_rule else None
        rule_title = active_rule["title"] if active_rule else None

        parts = []
        if rule_num:
            parts.append(rule_num)
        if subrule:
            parts.append(f"({subrule})")
        if subclause:
            parts.append(f"{subclause}")

        full_hier = "".join(parts) if parts else "General Provision"
        if rule_title and parts:
            full_hier = f"{full_hier} - {rule_title}"

        clause_num = None
        if active_rule:
            raw_n = active_rule.get("raw_num", "")
            if subrule:
                clause_num = f"{raw_n}({subrule})"
            else:
                clause_num = str(raw_n)

        return {
            "rule_number": rule_num,
            "rule_title": rule_title,
            "subrule_number": subrule,
            "clause_number": clause_num,
            "subclause_letter": subclause,
            "full_clause_hierarchy": full_hier,
            "provision_type": active_rule.get("provision_type") if active_rule else None,
        }


class PDFSourceMatcher:
    """
    High-precision verbatim source matching engine using PyMuPDF.
    """
    @staticmethod
    def normalize_text(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip().lower()

    @staticmethod
    def _matching_source_lines(page: fitz.Page, rects: List[fitz.Rect]) -> List[Tuple[int, str]]:
        """Return page-local visual line numbers and exact text intersecting the match."""
        lines = []
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                box = fitz.Rect(line.get("bbox", spans[0].get("bbox", (0, 0, 0, 0))))
                lines.append((box.y0, box.x0, box, "".join(s.get("text", "") for s in spans).strip()))
        lines.sort(key=lambda item: (round(item[0], 1), item[1]))
        return [(index, line_text) for index, (_, _, box, line_text) in enumerate(lines, start=1)
                if line_text and any(box.intersects(rect) for rect in rects)]

    @staticmethod
    def _source_lines(page: fitz.Page, rects: List[fitz.Rect]) -> List[int]:
        return [number for number, _ in PDFSourceMatcher._matching_source_lines(page, rects)]

    @staticmethod
    def match_quote_in_pdf(
        pdf_path: Path,
        candidate_quote: str,
        preferred_page: Optional[int] = None, # 1-based
    ) -> Dict[str, Any]:
        if not pdf_path.exists():
            return {
                "matched": False,
                "match_type": VerificationStatus.QUOTE_NOT_VERIFIED,
                "zero_based_pdf_page_index": 0,
                "viewer_page_number": preferred_page or 1,
                "printed_page_number": preferred_page or 1,
                "exact_source_quote": "",
                "bounding_boxes": [],
                "clause_hierarchy": {
                    "rule_number": None,
                    "rule_title": None,
                    "subrule_number": None,
                    "clause_number": None,
                    "subclause_letter": None,
                    "full_clause_hierarchy": "File Not Found",
                },
                "page_text": "",
            }

        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        q_clean = candidate_quote.strip()
        words = q_clean.split()
        norm_query = PDFSourceMatcher.normalize_text(q_clean)
        clean_query = re.sub(r"[^\w\s]", "", norm_query)

        # Ordering of pages to inspect
        page_indices = []
        if preferred_page and 1 <= preferred_page <= total_pages:
            page_indices.append(preferred_page - 1)
        for i in range(total_pages):
            if i not in page_indices:
                page_indices.append(i)

        # 1. Exact match attempt
        for idx in page_indices:
            page = doc[idx]
            rects = page.search_for(q_clean)
            if not rects and len(words) >= 4:
                sub_q = " ".join(words[:6])
                rects = page.search_for(sub_q)

            if rects:
                page_text = page.get_text()
                matched_lines = PDFSourceMatcher._matching_source_lines(page, rects)
                exact_quote = " ".join(text for _, text in matched_lines)

                pw = page.rect.width
                ph = page.rect.height
                boxes = [
                    {
                        "x0": round(r.x0, 2), "y0": round(r.y0, 2),
                        "x1": round(r.x1, 2), "y1": round(r.y1, 2),
                        "left_pct": round((r.x0 / pw) * 100, 2),
                        "top_pct": round((r.y0 / ph) * 100, 2),
                        "width_pct": round((r.width / pw) * 100, 2),
                        "height_pct": round((r.height / ph) * 100, 2),
                    }
                    for r in rects
                ]

                printed_page = LegalClauseParser.extract_printed_page(page_text, idx + 1)
                clause_hier = LegalClauseParser.parse_clause_hierarchy(doc, idx, exact_quote)

                return {
                    "matched": True,
                    "match_type": VerificationStatus.EXACT_MATCH_VERIFIED,
                    "zero_based_pdf_page_index": idx,
                    "viewer_page_number": idx + 1,
                    "printed_page_number": printed_page,
                    "exact_source_quote": exact_quote,
                    "bounding_boxes": boxes,
                    "source_line_numbers": [number for number, _ in matched_lines],
                    "clause_hierarchy": clause_hier,
                    "page_text": page_text,
                }

        # Some PDFs clip long lines in MuPDF's text layer while another
        # parser can still read the embedded text. This fallback verifies
        # only whitespace-normalized verbatim matches; it cannot provide
        # geometry, so no bounding boxes or source lines are invented.
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(pdf_path))
            for idx in page_indices:
                page_text = reader.pages[idx].extract_text() or ""
                norm_page = PDFSourceMatcher.normalize_text(page_text)
                if norm_query and norm_query in norm_page:
                    local_doc = fitz.open(str(pdf_path))
                    hierarchy = LegalClauseParser.parse_clause_hierarchy(local_doc, idx, "")
                    local_doc.close()
                    return {
                        "matched": True,
                        "match_type": VerificationStatus.EXACT_MATCH_VERIFIED,
                        "zero_based_pdf_page_index": idx,
                        "viewer_page_number": idx + 1,
                        "printed_page_number": idx + 1,
                        "exact_source_quote": " ".join(q_clean.split()),
                        "bounding_boxes": [],
                        "source_line_numbers": [],
                        "clause_hierarchy": hierarchy,
                        "page_text": page_text,
                    }
        except Exception:
            # Parser failures remain an unverified citation, never a fallback
            # to generated claim text.
            pass

        # No fuzzy paraphrase fallback: similarity cannot establish a
        # verbatim citation or legal provision number.
        return {
            "matched": False,
            "match_type": VerificationStatus.QUOTE_NOT_VERIFIED,
            "zero_based_pdf_page_index": (preferred_page - 1) if preferred_page else 0,
            "viewer_page_number": preferred_page or 1,
            "printed_page_number": preferred_page or 1,
            "exact_source_quote": "",
            "bounding_boxes": [],
            "clause_hierarchy": {
                "rule_number": None,
                "rule_title": None,
                "subrule_number": None,
                "clause_number": None,
                "subclause_letter": None,
                "full_clause_hierarchy": "Unverified Location",
            },
            "page_text": "",
        }


def resolve_pdf_physical_path(doc_meta: SourceDocumentMetadata) -> Optional[Path]:
    if not doc_meta or not doc_meta.local_path:
        return None

    cand_paths = [
        PROJECT_ROOT / doc_meta.local_path,
        PROJECT_ROOT / "knowledge_base" / doc_meta.local_path,
        PROJECT_ROOT / "knowledge_base" / "Documents main" / doc_meta.local_path,
    ]
    if doc_meta.local_path.startswith("knowledge_base/"):
        sub = doc_meta.local_path[len("knowledge_base/"):]
        cand_paths.append(PROJECT_ROOT / "knowledge_base" / "Documents main" / sub)

    for p in cand_paths:
        if p.exists() and p.is_file():
            return p.resolve()

    fname = Path(doc_meta.local_path).name
    matches = list((PROJECT_ROOT / "knowledge_base").rglob(fname))
    if matches and matches[0].is_file():
        return matches[0].resolve()

    return None


def verify_claim_evidence(
    claim: str,
    evidence_records: List[Dict[str, Any]],
    claim_id: str = "CLM-001",
    deliberate_clause_override: Optional[str] = None,
) -> StructuredEvidenceRecord:
    c_lower = claim.lower()

    # 1. Determine primary document and cited clause
    best_ev = evidence_records[0] if evidence_records else {}
    doc_meta = resolve_document_from_evidence(best_ev) if best_ev else None

    if not doc_meta:
        doc_meta = resolve_document_metadata(claim)

    if not doc_meta:
        return StructuredEvidenceRecord(
            claim_id=claim_id,
            claim=claim,
            source_doc_id="UNKNOWN-DOC",
            source_title="Unindexed / Inaccessible Source Document",
            issuing_authority="Unverified Authority",
            document_identifier="None",
            version="Unknown",
            publication_date="",
            effective_date="",
            jurisdiction="Unknown",
            legal_status="UNKNOWN",
            clause="Unknown Clause",
            page=None,
            source_url="",
            local_viewer_url="",
            supporting_text="",
            surrounding_context="",
            relationship="UNESTABLISHED",
            verification_status=VerificationStatus.UNVERIFIED,
            verification_explanation=(
                "Evidence not retrieved from an accessible source document; the claim cannot be verified. Citation details are unavailable."
            ),
            confidence=0.0,
            full_clause_hierarchy="Unverified",
            exact_source_quote="",
            ai_generated_summary=claim,
        )

    # 2. Extract cited clause and page hint
    ev_meta = best_ev.get("provenance") or best_ev.get("metadata") or {}
    has_retrieved_passage = bool(str(best_ev.get("text") or best_ev.get("evidence_text") or "").strip())
    cited_clause, cited_page = extract_clause_and_page(claim, ev_meta)
    if deliberate_clause_override:
        cited_clause = deliberate_clause_override

    pdf_path = resolve_pdf_physical_path(doc_meta)

    # Source-specific citation validation is handled uniformly below from the
    # retrieved passage and the physical PDF text. No provision number or
    # corrective citation is synthesized from a claim alone.

    # 5. Check Legal vs Technical Status distinction
    is_statutory_assertion = any(
        w in c_lower
        for w in [
            "statutory",
            "mandatory under indian law",
            "legally required in india",
            "statutory obligation",
            "indian legal mandate",
        ]
    )

    if (
        doc_meta.legal_status in ["INTERNATIONAL_RECOMMENDATION", "NON_BINDING_TECHNICAL_STANDARD"]
        and is_statutory_assertion
    ):
        return StructuredEvidenceRecord(
            claim_id=claim_id,
            claim=claim,
            source_doc_id=doc_meta.doc_id,
            source_title=doc_meta.title,
            issuing_authority=doc_meta.issuing_authority,
            document_identifier=doc_meta.document_identifier,
            version=doc_meta.version,
            publication_date=doc_meta.publication_date,
            effective_date=doc_meta.effective_date,
            jurisdiction=doc_meta.jurisdiction,
            legal_status=doc_meta.legal_status,
            clause=cited_clause,
            page=cited_page or 1,
            source_url=doc_meta.official_url,
            local_viewer_url=f"/api/documents/raw/{doc_meta.local_path}#page=1" if doc_meta.local_path else "",
            supporting_text=best_ev.get("text", "")[:300],
            surrounding_context="Technical standard or international recommendation issued by " + doc_meta.issuing_authority,
            relationship="NON_BINDING_STANDARD_MISCLASSIFIED_AS_STATUTORY",
            verification_status=VerificationStatus.PARTIALLY_SUPPORTED,
            verification_explanation=(
                f"LEGAL STATUS DISTINCTION: {doc_meta.title} is an international {doc_meta.document_type} "
                f"({doc_meta.legal_status}). It establishes a technical baseline but is NOT an Indian statutory "
                "obligation unless specifically enacted by an Indian statutory instrument or license amendment."
            ),
            confidence=0.45,
            full_clause_hierarchy=cited_clause,
            exact_source_quote="",
            ai_generated_summary=claim,
        )

    # 6. Physical PDF verbatim search for general claims
    if pdf_path:
        retrieved_passage = str(best_ev.get("text") or best_ev.get("evidence_text") or "").strip()
        match_res = PDFSourceMatcher.match_quote_in_pdf(
            pdf_path, retrieved_passage, preferred_page=cited_page
        ) if retrieved_passage else {
            "matched": False,
            "match_type": VerificationStatus.QUOTE_NOT_VERIFIED,
            "zero_based_pdf_page_index": 0,
            "viewer_page_number": 1,
            "printed_page_number": None,
            "exact_source_quote": "",
            "bounding_boxes": [],
            "source_line_numbers": [],
            "clause_hierarchy": {
                "rule_number": None, "rule_title": None,
                "subrule_number": None, "clause_number": None,
                "subclause_letter": None,
                "full_clause_hierarchy": "Evidence not retrieved",
            },
            "page_text": "",
        }
        hier = match_res["clause_hierarchy"]
        v_page = match_res["viewer_page_number"]
        p_page = match_res["printed_page_number"]
        boxes = match_res["bounding_boxes"]
        status = match_res["match_type"]

        # A caller-supplied provision must agree with the provision structure
        # parsed from the source page. A page-level quote alone cannot validate
        # a different rule or clause number.
        if (status == VerificationStatus.EXACT_MATCH_VERIFIED
                and deliberate_clause_override
                and normalize_clause_key(deliberate_clause_override)
                not in normalize_clause_key(hier.get("full_clause_hierarchy", ""))):
            actual_clause = hier.get("full_clause_hierarchy") or "Unverified provision"
            return StructuredEvidenceRecord(
                claim_id=claim_id, claim=claim, source_doc_id=doc_meta.doc_id,
                source_title=doc_meta.title, issuing_authority=doc_meta.issuing_authority,
                document_identifier=doc_meta.document_identifier, version=doc_meta.version,
                publication_date=doc_meta.publication_date, effective_date=doc_meta.effective_date,
                jurisdiction=doc_meta.jurisdiction, legal_status=doc_meta.legal_status,
                clause=actual_clause, page=v_page, source_url=doc_meta.official_url,
                local_viewer_url=f"/api/documents/raw/{doc_meta.local_path}#page={v_page}",
                supporting_text=match_res["exact_source_quote"],
                surrounding_context=match_res["page_text"][:500],
                relationship="INCORRECT_CLAUSE_ATTRIBUTION",
                verification_status=VerificationStatus.UNSUPPORTED,
                verification_explanation=(
                    f"CITATION MISMATCH DETECTED: the supplied citation '{deliberate_clause_override}' "
                    f"does not match the provision identified in the source: {actual_clause}."
                ),
                confidence=0.0, full_clause_hierarchy=actual_clause,
                printed_page_number=p_page, zero_based_pdf_page_index=match_res["zero_based_pdf_page_index"],
                viewer_page_number=v_page, exact_source_quote=match_res["exact_source_quote"],
                bounding_boxes=boxes, source_line_numbers=match_res.get("source_line_numbers", []),
            )

        # Citation verification is not claim entailment. Where the retrieved
        # passage is verbatim but the material claim terms are absent, report
        # the claim as unsupported while preserving the verified citation.
        claim_terms = {t for t in re.findall(r"[a-z0-9]+", c_lower)
                       if len(t) >= 5 and t not in {"under", "within", "there", "their", "shall", "must", "would", "could", "should", "these", "those", "such", "from", "that", "this", "with", "have", "been", "being", "paragraph", "section", "clause", "entities", "deployment", "mandatory"}}
        evidence_text_norm = PDFSourceMatcher.normalize_text(retrieved_passage)
        matched_claim_terms = sum(term in evidence_text_norm for term in claim_terms)
        if (status == VerificationStatus.EXACT_MATCH_VERIFIED and claim_terms
                and matched_claim_terms / len(claim_terms) < 0.25):
            return StructuredEvidenceRecord(
                claim_id=claim_id, claim=claim, source_doc_id=doc_meta.doc_id,
                source_title=doc_meta.title, issuing_authority=doc_meta.issuing_authority,
                document_identifier=doc_meta.document_identifier, version=doc_meta.version,
                publication_date=doc_meta.publication_date, effective_date=doc_meta.effective_date,
                jurisdiction=doc_meta.jurisdiction, legal_status=doc_meta.legal_status,
                clause=hier.get("full_clause_hierarchy", "Evidence not retrieved"), page=v_page,
                source_url=doc_meta.official_url,
                local_viewer_url=f"/api/documents/raw/{doc_meta.local_path}#page={v_page}",
                supporting_text=match_res["exact_source_quote"],
                surrounding_context=match_res["page_text"][:500],
                relationship="UNSUPPORTED_CLAIM_BY_RETRIEVED_PASSAGE",
                verification_status=VerificationStatus.UNSUPPORTED,
                verification_explanation="The retrieved source passage does not contain sufficient factual evidence for the material terms in the claim.",
                confidence=0.0, full_clause_hierarchy=hier.get("full_clause_hierarchy"),
                printed_page_number=p_page, zero_based_pdf_page_index=match_res["zero_based_pdf_page_index"],
                viewer_page_number=v_page, exact_source_quote=match_res["exact_source_quote"],
                bounding_boxes=boxes, source_line_numbers=match_res.get("source_line_numbers", []),
            )

        if status == VerificationStatus.EXACT_MATCH_VERIFIED:
            expl = (
                f"VERIFIED EXACT MATCH: Verbatim sentence located in {doc_meta.title} on Page {v_page} "
                f"(Printed Page {p_page}). Operative clause: {hier['full_clause_hierarchy']}."
            )
            conf = 0.98
        else:
            status = VerificationStatus.QUOTE_NOT_VERIFIED
            expl = (
                "Evidence not retrieved. No source passage, citation, or clause number is asserted."
                if not retrieved_passage else
                f"Retrieved evidence could not be matched to the source PDF for {doc_meta.title}. "
                "No citation or clause number is asserted."
            )
            conf = 0.15

        return StructuredEvidenceRecord(
            claim_id=claim_id,
            claim=claim,
            source_doc_id=doc_meta.doc_id,
            source_title=doc_meta.title,
            issuing_authority=doc_meta.issuing_authority,
            document_identifier=doc_meta.document_identifier,
            version=doc_meta.version,
            publication_date=doc_meta.publication_date,
            effective_date=doc_meta.effective_date,
            jurisdiction=doc_meta.jurisdiction,
            legal_status=doc_meta.legal_status,
            clause=hier["full_clause_hierarchy"] if status != VerificationStatus.QUOTE_NOT_VERIFIED else "Evidence not retrieved",
            page=v_page if status != VerificationStatus.QUOTE_NOT_VERIFIED else None,
            source_url=doc_meta.official_url,
            local_viewer_url=f"/api/documents/raw/{doc_meta.local_path}#page={v_page}" if status != VerificationStatus.QUOTE_NOT_VERIFIED else "",
            supporting_text=match_res["exact_source_quote"] if status != VerificationStatus.QUOTE_NOT_VERIFIED else "",
            surrounding_context=match_res["page_text"][:500] if match_res["page_text"] and status != VerificationStatus.QUOTE_NOT_VERIFIED else "",
            relationship="EVIDENCE_GROUNDED" if status != VerificationStatus.QUOTE_NOT_VERIFIED else "UNESTABLISHED",
            verification_status=status,
            verification_explanation=expl,
            confidence=conf,
            rule_number=hier.get("rule_number"),
            rule_title=hier.get("rule_title"),
            subrule_number=hier.get("subrule_number"),
            clause_number=hier.get("clause_number"),
            subclause_letter=hier.get("subclause_letter"),
            full_clause_hierarchy=hier.get("full_clause_hierarchy") if status != VerificationStatus.QUOTE_NOT_VERIFIED else "Evidence not retrieved",
            printed_page_number=p_page if status != VerificationStatus.QUOTE_NOT_VERIFIED else None,
            zero_based_pdf_page_index=match_res["zero_based_pdf_page_index"],
            viewer_page_number=v_page,
            exact_source_quote=match_res["exact_source_quote"],
            ai_generated_summary=claim,
            bounding_boxes=boxes,
            source_line_numbers=match_res.get("source_line_numbers", []),
        )

    # 7. Fallback when physical PDF is not available
    ev_text = str(best_ev.get("text") or best_ev.get("evidence_text") or "") if best_ev else ""
    return StructuredEvidenceRecord(
        claim_id=claim_id,
        claim=claim,
        source_doc_id=doc_meta.doc_id,
        source_title=doc_meta.title,
        issuing_authority=doc_meta.issuing_authority,
        document_identifier=doc_meta.document_identifier,
        version=doc_meta.version,
        publication_date=doc_meta.publication_date,
        effective_date=doc_meta.effective_date,
        jurisdiction=doc_meta.jurisdiction,
        legal_status=doc_meta.legal_status,
        clause="Evidence not retrieved",
        page=None,
        source_url=doc_meta.official_url,
        local_viewer_url="",
        supporting_text="",
        surrounding_context="",
        relationship="UNESTABLISHED",
        verification_status=VerificationStatus.QUOTE_NOT_VERIFIED if ev_text else VerificationStatus.UNVERIFIED,
        verification_explanation=(
            "Retrieved text could not be verified against an accessible source PDF. No citation is asserted."
            if ev_text else "Evidence not retrieved from an accessible source document. Citation details are unavailable."
        ),
        confidence=0.0,
        full_clause_hierarchy="Evidence not retrieved",
        exact_source_quote="",
        ai_generated_summary=claim,
    )
