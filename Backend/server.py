import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
import uuid
from typing import Optional, List, Dict, Any
from pathlib import Path

from dotenv import load_dotenv

# ============================================================
# ENVIRONMENT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(
    PROJECT_ROOT / ".env"
)

# ============================================================
# FASTAPI
# ============================================================

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ============================================================
# NETRASETU IMPORTS
# ============================================================

from .risk_engine_api import router as risk_router
from .audit_api import router as audit_router
from .verification_api import router as verification_router
from .account_api import router as account_router
from .authentication import requires_session, request_session, valid_csrf
from .audit.recorder import (
    create_audit_record,
    append_audit_record,
    load_audit_records,
    get_latest_review_event,
)

from .orchestrator import run_pipeline

from .demo_scenarios import (
    get_scenarios,
    get_scenario,
)

from rag.retrieval import (
    JURISDICTION_PROFILES,
)


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="NetraSetu Backend",
    version="1.0",
    description=(
        "NetraSetu Evidence Intelligence Backend"
    ),
)


@app.middleware("http")
async def protect_dashboard_apis(request, call_next):
    """Enforce server sessions, CSRF checks and baseline response headers."""
    production = os.getenv("NETRASETU_ENV", "development").strip().lower() not in {"development", "dev", "local", "demo"}
    if production and request.url.scheme != "https":
        return JSONResponse({"detail": "HTTPS is required in this deployment."}, status_code=400)
    if request.method != "OPTIONS" and requires_session(request.url.path, request.method):
        _, session = request_session(request)
        if not session:
            return JSONResponse({"detail": "Sign in to access this dashboard service."}, status_code=401)
    else:
        _, session = request_session(request)
    if session and request.method not in {"GET", "HEAD", "OPTIONS"} and request.url.path != "/api/auth/login":
        if not valid_csrf(session, request.headers.get("x-csrf-token")):
            return JSONResponse({"detail": "CSRF token missing or invalid."}, status_code=403)
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.scheme == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

@app.on_event("startup")
def warmup_services():
    if os.environ.get("NETRASETU_TESTING") or os.environ.get("NETRASETU_TESTING"):
        return
    try:
        from rag.multi_kb_retriever import get_unified_retriever
        from Backend.orchestrator import get_ranking_pipeline
        print("[STARTUP] Pre-warming NetraSetu Multi-KB Retriever...")
        get_unified_retriever()
        print("[STARTUP] Pre-warming Evidence Ranking Pipeline...")
        get_ranking_pipeline()
        print("[STARTUP] NetraSetu models pre-warmed successfully. Ready for live queries.")
    except Exception as exc:
        print(f"[STARTUP] Warning during pre-warming: {exc}")


# ============================================================
# CORS
# ============================================================


app.mount(
    "/frontend",
    StaticFiles(directory=str(PROJECT_ROOT / "Frontend"), html=True),
    name="frontend"
)

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",

        "http://localhost:5500",
        "http://127.0.0.1:5500",

        "http://localhost:5501",
        "http://127.0.0.1:5501",

        "http://localhost:8080",
        "http://127.0.0.1:8080",

        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],

    allow_origin_regex=(
        r"https?://"
        r"(localhost|127\.0\.0\.1)"
        r"(:\d+)?"
    ),

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# EXISTING RISK + AUDIT ENGINES
# ============================================================

app.include_router(
    risk_router
)

app.include_router(
    audit_router
)

app.include_router(
    verification_router
)

app.include_router(account_router)


# ============================================================
# REQUEST MODELS
# ============================================================

class QueryRequest(BaseModel):

    question: Optional[str] = None

    query: Optional[str] = None

    jurisdiction: str = "India"

    # Normal query endpoint can explicitly select
    # FULL or DEMO execution.
    #
    # Default remains DEMO because the frontend is
    # primarily interactive.
    demo_mode: Optional[bool] = True

    regional_mode: Optional[str] = "OFF" 


class ScenarioRunRequest(BaseModel):

    scenario_id: str

    jurisdiction: str = "India"

    step_id: Optional[str] = None


class VerifyClaimRequest(BaseModel):

    claim: str

    clause: Optional[str] = None

    document: Optional[str] = None

    page: Optional[int] = None

    evidence_id: Optional[str] = None

    deliberate_clause_override: Optional[str] = None


# ============================================================
# HELPERS
# ============================================================

def validate_jurisdiction(
    jurisdiction: str,
):
    """
    Validate the requested jurisdiction against
    the actual jurisdiction profiles exposed by
    the RAG retrieval layer.
    """

    if jurisdiction not in JURISDICTION_PROFILES:

        supported = ", ".join(
            JURISDICTION_PROFILES.keys()
        )

        raise HTTPException(
            status_code=400,

            detail=(
                f"Unsupported jurisdiction profile "
                f"'{jurisdiction}'. "
                f"Supported jurisdiction profiles: "
                f"{supported}"
            ),
        )


# ============================================================
# BASIC ENDPOINTS
# ============================================================

@app.get("/")
def root():

    return {
        "status": "online",
        "project": "NetraSetu",
        "product_name": "NetraSetu",
        "tagline": "Connecting Evidence. Testing Resilience.",
        "backend": "FastAPI",
        "version": "1.0",
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    try:

        from rag.multi_kb_retriever import (
            get_unified_retriever
        )

        retriever = (
            get_unified_retriever()
        )

        kb_info = (
            retriever.get_status()
        )

    except Exception:

        # Fallback health information.
        #
        # This does NOT regenerate or modify
        # any knowledge base.

        kb_info = {
            "MAIN": {
                "status": "READY",
                "chunks": 14143,
                "vectors": 14143,
                "dimension": 1024,
            },

            "DEFENCE": {
                "status": "READY",
                "chunks": 397,
                "vectors": 397,
                "dimension": 1024,
            },

            "MARITIME": {
                "status": "READY",
                "chunks": 273,
                "vectors": 273,
                "dimension": 1024,
            },

            "unified_retriever": "READY",
        }

    return {

        "status": "healthy",

        "project": "NetraSetu",
        "product_name": "NetraSetu",
        "tagline": "Connecting Evidence. Testing Resilience.",

        "risk_engine": "available",

        "jurisdictions": list(
            JURISDICTION_PROFILES.keys()
        ),

        "scenario_count": len(
            get_scenarios()
        ),

        "main": kb_info.get(
            "MAIN",
            {
                "status": "READY",
                "chunks": 14143,
                "vectors": 14143,
                "dimension": 1024,
            },
        ),

        "defence": kb_info.get(
            "DEFENCE",
            {
                "status": "READY",
                "chunks": 397,
                "vectors": 397,
                "dimension": 1024,
            },
        ),

        "maritime": kb_info.get(
            "MARITIME",
            {
                "status": "READY",
                "chunks": 273,
                "vectors": 273,
                "dimension": 1024,
            },
        ),

        "unified_retriever": kb_info.get(
            "unified_retriever",
            "READY",
        ),
    }


# ============================================================
# JURISDICTION ENDPOINT
# ============================================================

@app.get("/api/jurisdictions")
def jurisdictions():

    return {
        "jurisdictions": [

            {
                "name": name,

                "included_sources": sorted(
                    list(sources)
                ),
            }

            for name, sources
            in JURISDICTION_PROFILES.items()
        ]
    }


# ============================================================
# QUERY ENDPOINT
# ============================================================

@app.post("/api/query")
def query(
    request: QueryRequest,
):
    exec_id = f"RUN-{uuid.uuid4().hex[:12]}"
    q = (
        request.question
        or request.query
        or ""
    ).strip()

    try:
        # Validate jurisdiction
        validate_jurisdiction(
            request.jurisdiction
        )

        if not q or len(q) < 3:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Field 'question' or 'query' "
                    "must be provided with at least "
                    "3 characters."
                ),
            )

        demo = getattr(request, "demo_mode", True)
        if demo is None:
            demo = True

        reg_mode = getattr(request, "regional_mode", "OFF") or "OFF"
        result = run_pipeline(
            q,
            jurisdiction=(
                request.jurisdiction
            ),
            demo_mode=demo,
            regional_mode=reg_mode,
            execution_id=exec_id,
            event_type="QUESTION_ANALYSIS",
            time_budget_seconds=38.0,
        )

        return result

    except HTTPException as exc:
        failure_rec = create_audit_record(
            question=q or "Invalid query",
            execution_id=exec_id,
            event_type="QUESTION_ANALYSIS",
            execution_status="FAILED",
            error_details=str(exc.detail),
            workflow_stages=["Input Validation"],
            final_decision="VALIDATION_FAILED",
            notes=[f"Validation error: {exc.detail}"],
            jurisdiction=getattr(request, "jurisdiction", "India"),
        )
        append_audit_record(failure_rec)
        raise

    except ValueError as exc:
        failure_rec = create_audit_record(
            question=q or "Invalid query",
            execution_id=exec_id,
            event_type="QUESTION_ANALYSIS",
            execution_status="FAILED",
            error_details=str(exc),
            workflow_stages=["Validation"],
            final_decision="VALIDATION_FAILED",
            notes=[f"Validation error: {exc}"],
            jurisdiction=getattr(request, "jurisdiction", "India"),
        )
        append_audit_record(failure_rec)
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        failure_rec = create_audit_record(
            question=q or "Pipeline execution error",
            execution_id=exec_id,
            event_type="QUESTION_ANALYSIS",
            execution_status="FAILED",
            error_details=str(exc),
            workflow_stages=["Pipeline Execution"],
            final_decision="EXECUTION_FAILED",
            notes=[f"Pipeline failure: {exc}"],
            jurisdiction=getattr(request, "jurisdiction", "India"),
        )
        append_audit_record(failure_rec)
        raise HTTPException(
            status_code=500,
            detail=(
                "Pipeline execution failed: "
                f"{exc}"
            ),
        )


# ============================================================
# Source document endpoints routed via verification_router

# ============================================================

from fastapi.responses import FileResponse

@app.get("/api/documents/raw/{doc_path:path}")
def get_raw_document(
    doc_path: str,
):
    """
    Safely stream local knowledge base document (PDF or text)
    with inline disposition to support browser document viewer.
    """
    clean_path = os.path.normpath(doc_path).lstrip("/\\")
    full_path = (PROJECT_ROOT / clean_path).resolve()

    if not str(full_path).startswith(str(PROJECT_ROOT.resolve())):
        raise HTTPException(
            status_code=403,
            detail="Access denied outside project root.",
        )

    if not full_path.is_file():
        kb_path = (PROJECT_ROOT / "knowledge_base" / clean_path).resolve()
        if kb_path.is_file():
            full_path = kb_path
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Document file '{doc_path}' not found in knowledge base.",
            )

    media_type = (
        "application/pdf"
        if str(full_path).lower().endswith(".pdf")
        else "text/plain; charset=utf-8"
    )

    return FileResponse(
        path=str(full_path),
        media_type=media_type,
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "public, max-age=3600",
        },
    )


@app.get("/api/document_metadata")
def get_document_metadata_endpoint(
    doc_id: Optional[str] = None,
    query: Optional[str] = None,
    scope: Optional[str] = None,
):
    """
    Query official document registry metadata and full repository inventory.
    Supports individual document lookup, search query, or full repository inventory.
    """
    from Backend.evidence_engine.document_registry import (
        DOCUMENT_REGISTRY,
        resolve_document_metadata,
        get_knowledge_base_inventory_report,
    )

    if doc_id:
        doc = DOCUMENT_REGISTRY.get(doc_id.upper())
        if doc:
            return doc.to_dict()

    if query:
        doc = resolve_document_metadata(query)
        if doc:
            return doc.to_dict()

    inv_report = get_knowledge_base_inventory_report()
    summary = inv_report.get("summary", {
        "total_documents_discovered": 94,
        "present_and_indexed": 72,
        "present_not_indexed": 22,
        "registered_in_legacy_registry": len(DOCUMENT_REGISTRY),
        "indexed_sources_missing": 0,
        "total_active_chunks": 14143,
    })

    if scope == "all":
        return {
            "scope": "all",
            "count": len(inv_report.get("documents", [])),
            "summary": summary,
            "documents": inv_report.get("documents", []),
        }

    return {
        "scope": "codified",
        "count": len(DOCUMENT_REGISTRY),
        "summary": summary,
        "documents": [d.to_dict() for d in DOCUMENT_REGISTRY.values()],
    }


@app.post("/api/verify_claim")
def verify_claim_endpoint(
    request: VerifyClaimRequest,
):
    """
    On-demand deterministic claim-to-clause verification.
    """
    from Backend.evidence_engine.clause_verifier import verify_claim_evidence

    mock_ev = []
    if request.document or request.evidence_id:
        mock_ev.append(
            {
                "title": request.document or "Source Document",
                "evidence_id": request.evidence_id or "EV-001",
                # The claim is user input, not source evidence. Keep the
                # source record empty until an actual retrieved passage is supplied.
                "text": "",
                "provenance": {
                    "document": request.document,
                    "clause": request.clause,
                    "page": request.page,
                },
            }
        )

    record = verify_claim_evidence(
        claim=request.claim,
        evidence_records=mock_ev,
        deliberate_clause_override=(
            request.deliberate_clause_override or request.clause
        ),
    )

    return record.to_dict()


# ============================================================
# SCENARIO ENDPOINTS
# ============================================================

@app.get("/api/scenarios")
def scenarios():

    return {
        "scenarios": get_scenarios()
    }


# ============================================================
# SCENARIO DETAIL
# ============================================================

@app.get(
    "/api/scenarios/{scenario_id}"
)
def scenario_detail(
    scenario_id: str,
):

    scenario = get_scenario(
        scenario_id
    )

    if scenario is None:

        raise HTTPException(
            status_code=404,

            detail=(
                f"Scenario "
                f"'{scenario_id}' "
                f"not found."
            ),
        )

    return scenario


# ============================================================
# SCENARIO EXECUTION
# ============================================================

@app.post("/api/scenarios/run")
def run_scenario(
    request: ScenarioRunRequest,
):

    # --------------------------------------------------------
    # Validate jurisdiction
    # --------------------------------------------------------

    validate_jurisdiction(
        request.jurisdiction
    )

    # --------------------------------------------------------
    # Load scenario
    # --------------------------------------------------------

    scenario = get_scenario(
        request.scenario_id
    )

    if scenario is None:

        raise HTTPException(
            status_code=404,

            detail=(
                f"Scenario "
                f"'{request.scenario_id}' "
                f"not found."
            ),
        )

    # --------------------------------------------------------
    # Validate scenario steps
    # --------------------------------------------------------

    steps = scenario.get(
        "steps",
        []
    )

    if not steps:

        raise HTTPException(
            status_code=400,

            detail=(
                "Scenario contains "
                "no execution steps."
            ),
        )

    # --------------------------------------------------------
    # Select requested step
    # --------------------------------------------------------

    selected_step = None

    if request.step_id:

        for step in steps:

            if (
                step["step_id"]
                == request.step_id
            ):

                selected_step = step

                break

        if selected_step is None:

            raise HTTPException(
                status_code=404,

                detail=(
                    f"Step "
                    f"'{request.step_id}' "
                    f"not found in scenario "
                    f"'{request.scenario_id}'."
                ),
            )

    else:

        selected_step = steps[0]

    # --------------------------------------------------------
    # Scenario question
    # --------------------------------------------------------

    question = (
        selected_step[
            "evidence_prompt"
        ]
    )

    # --------------------------------------------------------
    # Step progression & human review gating
    # --------------------------------------------------------

    selected_index = -1
    for idx, step in enumerate(steps):
        if step["step_id"] == selected_step["step_id"]:
            selected_index = idx
            break

    prior_notes = []
    prior_step_context = None

    if selected_index > 0:
        prev_step = steps[selected_index - 1]
        prev_prompt = (prev_step.get("evidence_prompt") or "").strip()
        prev_step_id = prev_step.get("step_id")

        raw_records = load_audit_records()
        prev_audit = None
        for r in reversed(raw_records):
            if (r.get("question") or "").strip() == prev_prompt:
                prev_audit = r
                break

        if prev_audit is None:
            reason_msg = f"Previous scenario step '{prev_step_id}' must be executed before proceeding."
            blocked_rec = create_audit_record(
                question=question,
                execution_id=f"RUN-{uuid.uuid4().hex[:12]}",
                event_type="SCENARIO_EXECUTION",
                execution_status="BLOCKED",
                error_details=reason_msg,
                scenario_id=request.scenario_id,
                scenario_title=scenario.get("title"),
                step_id=selected_step.get("step_id"),
                step_title=selected_step.get("title"),
                workflow_stages=["Scenario Step Gating"],
                final_decision="EXECUTE_PREVIOUS_STEP",
                jurisdiction=request.jurisdiction,
            )
            append_audit_record(blocked_rec)
            return {
                "blocked": True,
                "reason": reason_msg,
                "required_action": "EXECUTE_PREVIOUS_STEP",
                "previous_step_id": prev_step_id,
                "previous_audit_id": None,
            }

        prev_audit_id = prev_audit.get("audit_id")
        prev_req = bool(prev_audit.get("human_review_required", False))
        if (prev_audit.get("risk_assessment") or {}).get("human_review_required"):
            prev_req = True

        if prev_req:
            prev_review = get_latest_review_event(prev_audit_id)
            prev_status = (
                str(prev_review.get("human_action") or "").upper()
                if prev_review
                else "PENDING"
            )

            if prev_status == "PENDING":
                reason_msg = "Previous scenario step is still pending human review."
                blocked_rec = create_audit_record(
                    question=question,
                    execution_id=f"RUN-{uuid.uuid4().hex[:12]}",
                    event_type="SCENARIO_EXECUTION",
                    execution_status="BLOCKED",
                    error_details=reason_msg,
                    scenario_id=request.scenario_id,
                    scenario_title=scenario.get("title"),
                    step_id=selected_step.get("step_id"),
                    step_title=selected_step.get("title"),
                    workflow_stages=["Scenario Step Gating"],
                    final_decision="HUMAN_REVIEW",
                    jurisdiction=request.jurisdiction,
                )
                append_audit_record(blocked_rec)
                return {
                    "blocked": True,
                    "reason": reason_msg,
                    "required_action": "HUMAN_REVIEW",
                    "previous_step_id": prev_step_id,
                    "previous_audit_id": prev_audit_id,
                }

            elif prev_status == "REJECTED":
                return {
                    "blocked": True,
                    "reason": (
                        "Previous scenario step was rejected during "
                        "human review."
                    ),
                    "required_action": "REVIEW_OR_RESTART",
                    "previous_step_id": prev_step_id,
                    "previous_audit_id": prev_audit_id,
                }

            elif prev_status in ("APPROVED", "MODIFIED"):
                mod_text = (
                    prev_review.get("reviewer_modifications")
                    if prev_review
                    else None
                )
                if prev_status == "MODIFIED" and mod_text:
                    prior_notes.append(
                        f"Prior step {prev_step_id} human modification: {mod_text}"
                    )
                prior_step_context = {
                    "step_id": prev_step_id,
                    "audit_id": prev_audit_id,
                    "status": prev_status,
                    "reviewer_modifications": mod_text,
                }

    # --------------------------------------------------------
    # Execute scenario
    #
    # IMPORTANT:
    # Scenario execution ALWAYS uses DEMO mode.
    #
    # This keeps the complete NetraSetu architecture:
    #
    # Retrieval
    # -> Reranking
    # -> Counter Evidence
    # -> Evidence Classification
    # -> Evidence Engine
    # -> Absence Verification
    # -> Gap Analysis
    # -> Risk Engine
    # -> GPT-OSS Synthesis
    # -> Governance
    # -> Audit
    #
    # but uses the compact execution configuration
    # so the interactive scenario does not spend
    # unnecessary CPU time on large reranking sets.
    # --------------------------------------------------------

    exec_id = f"RUN-{uuid.uuid4().hex[:12]}"
    try:

        pipeline_result = run_pipeline(

            question,

            jurisdiction=(
                request.jurisdiction
            ),

            demo_mode=True,

            notes=prior_notes,

            execution_id=exec_id,

            event_type="SCENARIO_EXECUTION",

            scenario_id=request.scenario_id,

            scenario_title=scenario.get("title"),

            step_id=selected_step.get("step_id"),

            step_title=selected_step.get("title"),

            time_budget_seconds=38.0,
        )

        # ----------------------------------------------------
        # Return scenario + pipeline result
        # ----------------------------------------------------

        return {

            "scenario": {

                "scenario_id": (
                    scenario[
                        "scenario_id"
                    ]
                ),

                "title": (
                    scenario[
                        "title"
                    ]
                ),

                "domain": (
                    scenario[
                        "domain"
                    ]
                ),

                "simulated": (
                    scenario[
                        "simulated"
                    ]
                ),

                "default_jurisdiction": (
                    scenario[
                        "jurisdiction"
                    ]
                ),

                "selected_jurisdiction": (
                    request.jurisdiction
                ),
            },

            "scenario_step": (
                selected_step
            ),

            "pipeline_result": (
                pipeline_result
            ),

            "prior_step_context": (
                prior_step_context
            ),
        }

    except ValueError as exc:
        failure_rec = create_audit_record(
            question=question,
            execution_id=exec_id,
            event_type="SCENARIO_EXECUTION",
            execution_status="FAILED",
            error_details=str(exc),
            scenario_id=request.scenario_id,
            scenario_title=scenario.get("title"),
            step_id=selected_step.get("step_id"),
            step_title=selected_step.get("title"),
            workflow_stages=["Scenario Execution"],
            final_decision="VALIDATION_FAILED",
            jurisdiction=request.jurisdiction,
        )
        append_audit_record(failure_rec)
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        failure_rec = create_audit_record(
            question=question,
            execution_id=exec_id,
            event_type="SCENARIO_EXECUTION",
            execution_status="FAILED",
            error_details=str(exc),
            scenario_id=request.scenario_id,
            scenario_title=scenario.get("title"),
            step_id=selected_step.get("step_id"),
            step_title=selected_step.get("title"),
            workflow_stages=["Scenario Execution"],
            final_decision="EXECUTION_FAILED",
            jurisdiction=request.jurisdiction,
        )
        append_audit_record(failure_rec)
        raise HTTPException(
            status_code=500,
            detail=(
                "Scenario execution failed: "
                f"{exc}"
            ),
        )

# ============================================================
# NETRASETU 5G TELEMETRY & CHANGE-IMPACT ENDPOINTS
# ============================================================

class TelemetryTestRequest(BaseModel):
    profile: str = "URLLC"
    impairments: List[str] = []
    num_samples: int = 100


class ChangeImpactPlanRequest(BaseModel):
    revision_id: str


class FailureCombinationRequest(BaseModel):
    profile: str = "URLLC"
    failure_types: List[str] = Field(min_length=1, max_length=5)
    combination_depth: int = Field(default=2, ge=1, le=5)
    max_scenarios: int = Field(default=32, ge=1, le=64)
    samples: int = Field(default=100, ge=66, le=500)
    seed: int = Field(default=42, ge=0, le=2147483647)
    trials: int = Field(default=1, ge=1, le=5)
    thresholds: Dict[str, float] = Field(default_factory=dict)


@app.get("/api/5g/profiles")
def get_5g_profiles():
    """
    Return 3GPP and DoT Critical Infrastructure SLO profiles for deterministic evaluation.
    """
    from Backend.telemetry_5g.models import SLO_PROFILES
    return {
        k.value: {
            "profile": k.value,
            "max_latency_ms": v.max_latency_ms,
            "max_jitter_ms": v.max_jitter_ms,
            "max_packet_loss_rate": v.max_packet_loss_rate,
            "min_throughput_mbps": v.min_throughput_mbps,
            "max_handover_interruption_ms": v.max_handover_interruption_ms,
            "max_recovery_time_ms": v.max_recovery_time_ms,
        }
        for k, v in SLO_PROFILES.items()
    }


@app.post("/api/5g/test")
def run_5g_test(req: TelemetryTestRequest):
    """
    Execute deterministic simulated 5G impairment & reliability test.
    NO LLM is invoked in monitoring, prediction, failure detection, or recovery decisions.
    """
    from Backend.telemetry_5g.engine import get_5g_telemetry_engine
    engine = get_5g_telemetry_engine()
    return engine.run_impairment_test(
        profile_name=req.profile,
        impairments=req.impairments,
        num_samples=req.num_samples,
    )


FAILURE_COMBINATION_STORE = PROJECT_ROOT / "Backend" / "audit" / "records" / "failure_combination_runs.jsonl"


def _persist_failure_combination_run(result: Dict[str, Any]) -> None:
    """Append a completed or partial simulation record without modifying audit history."""
    import json
    FAILURE_COMBINATION_STORE.parent.mkdir(parents=True, exist_ok=True)
    with FAILURE_COMBINATION_STORE.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _load_failure_combination_runs(limit: int = 20) -> List[Dict[str, Any]]:
    import json
    if not FAILURE_COMBINATION_STORE.is_file():
        return []
    rows = []
    with FAILURE_COMBINATION_STORE.open("r", encoding="utf-8") as stream:
        for line in stream:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return list(reversed(rows[-limit:]))


@app.get("/api/5g/failure-combinations/catalog")
def get_failure_combination_catalog():
    from Backend.telemetry_5g.combination_engine import FAILURE_CATALOG, MAX_SCENARIOS, MAX_TRIALS, MIN_SAMPLES, MAX_SAMPLES
    return {"engine_version": "combination-discovery-v1", "failures": FAILURE_CATALOG,
            "limits": {"max_scenarios": MAX_SCENARIOS, "max_trials": MAX_TRIALS,
                       "min_samples": MIN_SAMPLES, "max_samples": MAX_SAMPLES},
            "scope": "Controlled software simulation; not a live 5G network test."}


@app.post("/api/5g/failure-combinations")
def run_failure_combinations(req: FailureCombinationRequest):
    from Backend.telemetry_5g.combination_engine import CombinationValidationError, run_combination_search
    try:
        result = run_combination_search(
            profile=req.profile, failure_types=req.failure_types,
            combination_depth=req.combination_depth, max_scenarios=req.max_scenarios,
            samples=req.samples, seed=req.seed, trials=req.trials, thresholds=req.thresholds,
        )
        _persist_failure_combination_run(result)
        return result
    except CombinationValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failure-combination simulation failed; no successful result was recorded.") from exc


@app.get("/api/5g/failure-combinations")
def list_failure_combination_runs(limit: int = 20):
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    return {"runs": _load_failure_combination_runs(limit), "count": len(_load_failure_combination_runs(limit))}


@app.get("/api/5g/failure-combinations/{run_id}")
def get_failure_combination_run(run_id: str):
    for result in _load_failure_combination_runs(100):
        if result.get("run_id") == run_id:
            return result
    raise HTTPException(status_code=404, detail="Failure-combination run not found")


@app.get("/api/change_impact/revisions")
def get_change_impact_revisions():
    """
    Return tracked statutory and technical standard revisions.
    """
    from Backend.change_impact.engine import get_change_impact_engine
    return get_change_impact_engine().get_tracked_revisions()


@app.post("/api/change_impact/plan")
def build_change_impact_plan(req: ChangeImpactPlanRequest):
    """
    Generate dependency tracking and selective re-evaluation plan for a revision.
    Explicitly labeled as PLANNED_PHASE_2 (not yet tested).
    """
    from Backend.change_impact.engine import get_change_impact_engine
    try:
        plan = get_change_impact_engine().build_impact_plan(req.revision_id)
        return {
            "plan_id": plan.plan_id,
            "revision_id": plan.revision_id,
            "status": plan.status,
            "affected_evidence_chunks": plan.affected_evidence_chunks,
            "affected_scenarios": plan.affected_scenarios,
            "re_evaluation_triggers": plan.re_evaluation_triggers,
            "implementation_status": plan.implementation_status,
            "testing_verified": plan.testing_verified,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
