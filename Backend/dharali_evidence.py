"""Source-backed Dharali (Uttarkashi) incident evidence search.

The searchable corpus is extracted from the two official PDFs shipped in
knowledge_base/Dharali Incident 2025. No incident metrics or facility states
are synthesized here.
"""
from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "knowledge_base" / "Dharali Incident 2025"

SOURCES = {
    "GSI-DHARALI-2025": {
        "path": SOURCE_DIR / "GSI_Preliminary_Note_Dharali_2025-08-05.pdf",
        "title": "Preliminary Note on the devastating flash flood in Kheer Gad, Dharali, Uttarkashi district, Uttarakhand",
        "authority": "Geological Survey of India (GSI)",
        "issued": "2025-08-05 (incident date; report date not explicit in extracted title page)",
        "url": "https://bhusanket.gsi.gov.in/Public_Portal_News_pdf/GSI%20Preliminary%20note_Dharali_Flash%20Flood%20of%205th%20August%202025.pdf",
    },
    "NRSC-NDEM-DHARALI-2025": {
        "path": SOURCE_DIR / "NRSC_NDEM_Dharali_Damage_Assessment_2025-08-06.pdf",
        "title": "Damage Assessment in Dharali, Uttarkashi on 05 August 2025",
        "authority": "National Remote Sensing Centre (NRSC), ISRO / National Database for Emergency Management (NDEM)",
        "issued": "2025-08-06 (map date; observed 06/08/2025)",
        "url": "https://ndem.nrsc.gov.in/documents/Disaster_Document/2025/UK/uklandslide50dsc06082025/uklandslide50dsc06082025_vap1.pdf",
    },
}

TARGETS = [
    {
        "target_id": "DHARALI-SETTLEMENT",
        "name": "Dharali settlement / built-up area",
        "target_type": "SETTLEMENT_ASSESSMENT_AREA",
        "status": "SOURCE_REPORTED_DAMAGE",
        "source_refs": ["GSI-DHARALI-2025", "NRSC-NDEM-DHARALI-2025"],
        "note": "GSI reports severe impact, property damage and loss of life; NRSC maps the affected area. No current building-by-building condition or population count was retrieved.",
    },
    {
        "target_id": "KHEER-GAD-RUNOUT",
        "name": "Kheer Gad channel and debris runout / deposition zone",
        "target_type": "CHANNEL_AND_HAZARD_CHECKPOINT",
        "status": "SOURCE_MAPPED_IMPACT",
        "source_refs": ["GSI-DHARALI-2025", "NRSC-NDEM-DHARALI-2025"],
        "note": "GSI describes the steep-gradient channel and high runout context; NRSC maps a debris deposition zone. Current channel geometry and stabilization status were not retrieved.",
    },
    {
        "target_id": "BHAGIRATHI-CONFLUENCE",
        "name": "Bhagirathi River at the Kheer Gad confluence",
        "target_type": "RIVER_AND_BLOCKAGE_CHECKPOINT",
        "status": "SOURCE_REPORTED_PARTIAL_BLOCKAGE",
        "source_refs": ["NRSC-NDEM-DHARALI-2025"],
        "note": "NRSC reports partial river blockage on its rapid map. Later flow, obstruction clearance, water level and downstream condition were not retrieved.",
    },
    {
        "target_id": "DHARALI-MUKHBA-ACCESS",
        "name": "Dharali–Mukhba Bridge / Gangotri Highway access checkpoint",
        "target_type": "TRANSPORT_ACCESS_CHECKPOINT",
        "status": "NAMED_ON_SOURCE_MAP_CONDITION_NOT_RETRIEVED",
        "source_refs": ["NRSC-NDEM-DHARALI-2025"],
        "note": "The NRSC map labels the bridge and Gangotri Highway; it does not establish current structural condition or passability. Verify with current road/bridge authorities.",
    },
]


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold())


@lru_cache(maxsize=1)
def source_passages() -> tuple[dict[str, Any], ...]:
    passages: list[dict[str, Any]] = []
    for source_id, info in SOURCES.items():
        if not info["path"].is_file():
            continue
        with pymupdf.open(info["path"]) as pdf:
            for page_idx, page in enumerate(pdf):
                text = page.get_text("text") or ""
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                # Keep page-level context intact: GSI's figures and notes often
                # separate facts that belong together across short paragraphs.
                if not lines:
                    continue
                passages.append({
                    "source_id": source_id,
                    "title": info["title"],
                    "authority": info["authority"],
                    "issued": info["issued"],
                    "url": info["url"],
                    "path": str(info["path"]),
                    "page": page_idx + 1,
                    "text": "\n".join(lines),
                    "tokens": _tokens(" ".join(lines)),
                })
    return tuple(passages)


def _bm25(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    docs = list(source_passages())
    terms = list(dict.fromkeys(_tokens(query)))
    if not docs or not terms:
        return []
    avgdl = sum(len(row["tokens"]) for row in docs) / max(1, len(docs))
    scores = [0.0] * len(docs)
    for term in terms:
        df = sum(1 for row in docs if term in row["tokens"])
        if not df:
            continue
        idf = math.log(1 + (len(docs) - df + 0.5) / (df + 0.5))
        for idx, row in enumerate(docs):
            tf = row["tokens"].count(term)
            if tf:
                length = len(row["tokens"])
                scores[idx] += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * length / max(1, avgdl)))
    ranked = sorted(zip(scores, docs), key=lambda item: item[0], reverse=True)
    query_terms = set(terms)
    selected = []
    for score, row in ranked[:top_k]:
        if score <= 0:
            continue
        lines = [line.strip() for line in row["text"].splitlines() if line.strip()]
        matches = [i for i, line in enumerate(lines) if query_terms.intersection(_tokens(line))]
        if matches:
            center = matches[0]
            start = max(0, center - 2)
            end = min(len(lines), max(center + 4, start + 8))
            excerpt = "\n".join(lines[start:end])
        else:
            start, end, excerpt = 0, len(lines), row["text"]
        selected.append(dict(row, retrieval_score=round(score, 4), excerpt=excerpt,
                             extracted_line_range=[start + 1, end]))
    return selected


def search_incident_evidence(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    return _bm25(query, top_k=top_k)


def source_catalog() -> list[dict[str, Any]]:
    return [{"source_id": source_id, "title": info["title"], "authority": info["authority"],
             "publication_or_map_date": info["issued"], "official_url": info["url"],
             "document_filename": info["path"].name, "available": info["path"].is_file()}
            for source_id, info in SOURCES.items()]
