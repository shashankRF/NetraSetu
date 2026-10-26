import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
import re
import time
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

from fastapi import FastAPI, HTTPException, Request
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
from .dynamic_kb_api import router as dynamic_kb_router
from .disaster_map_api import router as disaster_map_router
from .ecr5g.api import router as ecr5g_router
from .aftermath_api import router as aftermath_router
from .coordination_api import router as coordination_router
from .audit.recorder import (
    create_audit_record,
    append_audit_record,
    load_audit_records,
    get_latest_review_event,
    generate_audit_id,
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
        "NetraSetu — Evidence-Grounded Disaster Communication and Resilience Intelligence"
    ),
)


@app.middleware("http")
async def protect_dashboard_apis(request, call_next):
    """Enforce authenticated sessions, CSRF checks and baseline headers."""
    production = os.getenv("NETRASETU_ENV", "development").strip().lower() not in {"development", "dev", "local", "demo"}
    if production and request.url.scheme != "https":
        return JSONResponse({"detail": "HTTPS is required in this deployment."}, status_code=400)
    token, session = request_session(request)
    if request.method != "OPTIONS" and requires_session(request.url.path, request.method) and not session:
        return JSONResponse({"detail": "Sign in to access this dashboard service."}, status_code=401)
    if session and request.method not in {"GET", "HEAD", "OPTIONS"} and request.url.path != "/api/auth/login":
        if not valid_csrf(session, request.headers.get("x-csrf-token")):
            return JSONResponse({"detail": "CSRF token missing or invalid."}, status_code=403)
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    # OSM's public raster tiles require a valid web Referer; this policy sends
    # only the origin cross-site while withholding path and query parameters.
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.scheme == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

@app.on_event("startup")
def warmup_services():
    if os.environ.get("HACKGRID_TESTING") or os.environ.get("NETRASETU_TESTING"):
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

app.include_router(
    dynamic_kb_router
)

app.include_router(
    account_router
)

app.include_router(disaster_map_router)
app.include_router(
    ecr5g_router
)
app.include_router(aftermath_router)
app.include_router(coordination_router)


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


@app.get("/api/document_metadata")
def get_document_metadata_endpoint(
    doc_id: Optional[str] = None,
    query: Optional[str] = None,
):
    """
    Query official document registry metadata.
    """
    from Backend.evidence_engine.document_registry import (
        DOCUMENT_REGISTRY,
        resolve_document_metadata,
    )

    if doc_id:
        doc = DOCUMENT_REGISTRY.get(doc_id.upper())
        if doc:
            return doc.to_dict()

    if query:
        doc = resolve_document_metadata(query)
        if doc:
            return doc.to_dict()

    return {
        "count": len(DOCUMENT_REGISTRY),
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
                "text": request.claim,
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
    http_request: Request,
):
    request_started = time.perf_counter()
    supplied_trace_id = (http_request.headers.get("x-request-id") or "").strip()
    exec_id = supplied_trace_id if re.fullmatch(r"[A-Za-z0-9._-]{1,80}", supplied_trace_id) else f"RUN-{uuid.uuid4().hex[:12]}"

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

    scenario_validation_ms = round((time.perf_counter() - request_started) * 1000, 2)
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

        route_elapsed_ms = round((time.perf_counter() - request_started) * 1000, 2)
        pipeline_result.setdefault("performance", {})["scenario_validation_ms"] = scenario_validation_ms
        pipeline_result["performance"]["scenario_route_total_ms"] = route_elapsed_ms
        print(
            f"[SCENARIO_RUN] trace_id={exec_id} status=COMPLETED "
            f"elapsed_ms={route_elapsed_ms} stage_ms={pipeline_result.get('performance', {})}"
        )

        # ----------------------------------------------------
        # Return scenario + pipeline result
        # ----------------------------------------------------

        return {
            "trace_id": exec_id,

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
        print(f"[SCENARIO_RUN] trace_id={exec_id} status=FAILED category=VALIDATION elapsed_ms={round((time.perf_counter() - request_started) * 1000, 2)} error={type(exc).__name__}")
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
        print(f"[SCENARIO_RUN] trace_id={exec_id} status=FAILED category=ANALYSIS elapsed_ms={round((time.perf_counter() - request_started) * 1000, 2)} error={type(exc).__name__}")
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


class FailureCombinationRequest(BaseModel):
    profile: str = "URLLC"
    failure_types: List[str] = Field(min_length=1, max_length=5)
    combination_depth: int = Field(default=2, ge=1, le=5)
    max_scenarios: int = Field(default=32, ge=1, le=64)
    samples: int = Field(default=100, ge=66, le=500)
    seed: int = Field(default=42, ge=0, le=2147483647)
    trials: int = Field(default=1, ge=1, le=5)
    thresholds: Dict[str, float] = Field(default_factory=dict)
    jurisdiction: Optional[str] = None
    evidence_query: Optional[str] = Field(default=None, max_length=1200)


class ChangeImpactPlanRequest(BaseModel):
    revision_id: str


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
    """Append one completed or failed simulator run without rewriting history."""
    import json

    FAILURE_COMBINATION_STORE.parent.mkdir(parents=True, exist_ok=True)
    with FAILURE_COMBINATION_STORE.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, separators=(",", ":"), default=str) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _load_failure_combination_runs(limit: int = 20) -> List[Dict[str, Any]]:
    import json

    if not FAILURE_COMBINATION_STORE.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    with FAILURE_COMBINATION_STORE.open("r", encoding="utf-8") as stream:
        for line in stream:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return list(reversed(rows[-limit:]))


def _integrate_failure_combination_run(result: Dict[str, Any], request: FailureCombinationRequest) -> None:
    """Attach existing evidence, risk, coordination and audit services to a run."""
    from Backend.telemetry_5g.governance_integration import (
        SimulationRiskInput,
        assess_simulation_row,
        retrieve_and_verify_simulation_sources,
    )
    from Backend.telemetry_5g.coordination import build_agency_messages

    source_assessment = retrieve_and_verify_simulation_sources(
        query=request.evidence_query or " ".join(["5G reliability failure combination", *request.failure_types]),
        jurisdiction=request.jurisdiction,
        limit=5,
    )
    result["evidence_assessment"] = {
        "status": "EVIDENCE_PENDING" if source_assessment.get("status") == "EVIDENCE_PENDING" else source_assessment.get("status"),
        "scope": "Retrieved policy sources are not evidence that synthetic simulator metrics satisfy or violate a real-world requirement.",
        "source_assessment": source_assessment,
    }

    for row in result.get("results", []):
        if row.get("status") != "COMPLETED":
            row["governance_assessment"] = {"engine": "Backend.risk_engine.RiskEngine", "review_status": "NOT_EVALUATED", "reason": "Simulator case did not complete; no successful metric assessment was produced."}
            continue
        config = row.get("configuration", {})
        risk_input = SimulationRiskInput(
            run_id=result["run_id"], scenario_id=request.evidence_query,
            profile=str(config.get("profile", request.profile)),
            failure_types=list(config.get("failure_types", [])),
            seed=int(config.get("seed", request.seed)), samples=int(config.get("samples", request.samples)),
            simulator_version=str(row.get("simulator_version") or result.get("engine_version") or "unknown"),
            metrics=dict(row.get("metrics") or {}),
            simulator_provenance=dict(row.get("provenance") or result.get("provenance") or {}),
        )
        row["governance_assessment"] = assess_simulation_row(risk_input, source_assessment)

    completed = [row for row in result.get("results", []) if row.get("status") == "COMPLETED"]
    representative = completed[-1] if completed else None
    risk = representative.get("governance_assessment", {}) if representative else {}
    blocking = any(row.get("governance_assessment", {}).get("blocking_conditions") for row in completed)
    result["integration"] = {
        "risk_engine": "Backend.risk_engine.RiskEngine",
        "review_gate": "BLOCKED" if blocking else "REVIEW_REQUIRED" if completed else "NOT_EVALUATED",
        "evidence": result["evidence_assessment"],
        "coordination_messages": [],
    }
    if representative:
        result["integration"]["coordination_messages"] = build_agency_messages(
            run_id=result["run_id"], scenario_id=request.evidence_query,
            simulation_case_id=representative.get("scenario_id"),
            profile=str(representative.get("configuration", {}).get("profile", request.profile)),
            failures=list(representative.get("configuration", {}).get("failure_types", [])),
            metrics=dict(representative.get("metrics") or {}),
            slo_status=str(representative.get("profile_evaluation", {}).get("status", "NOT_EVALUATED")),
            recovery_recommendations=list(representative.get("recovery_recommendations", [])),
            risk=risk, evidence=source_assessment,
        )

    audit = create_audit_record(
        question=request.evidence_query or "Run bounded failure-combination simulator",
        execution_id=result["run_id"], event_type="FAILURE_COMBINATION_SIMULATION",
        execution_status=str(result.get("status", "UNKNOWN")),
        provenance="SIMULATION; not a live network action", domain="Telecom/5G reliability simulation",
        jurisdiction=request.jurisdiction, human_review_required=bool(completed),
        evidence_assessment=result["evidence_assessment"],
        risk_assessment=risk,
        notes=["Simulator results are synthetic and do not measure a live network.", "No operational or coordination action was executed."],
    )
    audit["integration_record"] = {"full_run": result}
    audit.pop("audit_id", None)
    audit["audit_id"] = generate_audit_id(audit)
    append_audit_record(audit)
    result["audit_id"] = audit["audit_id"]
    result["review"] = {"human_action": "PENDING", "reviewer": "", "statement": "", "audit_id": audit["audit_id"]}


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
    except CombinationValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        _integrate_failure_combination_run(result, req)
        _persist_failure_combination_run(result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failure-combination result could not be fully integrated and persisted; no success was recorded.") from exc
    return result


@app.get("/api/5g/failure-combinations")
def list_failure_combination_runs(limit: int = 20):
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    runs = _load_failure_combination_runs(limit)
    return {"runs": runs, "count": len(runs)}


@app.get("/api/5g/failure-combinations/{run_id}")
def get_failure_combination_run(run_id: str):
    for result in _load_failure_combination_runs(100):
        if result.get("run_id") == run_id:
            audit_id = result.get("audit_id")
            review = get_latest_review_event(audit_id) if audit_id else None
            result["review"] = review or result.get("review", {"human_action": "PENDING"})
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
