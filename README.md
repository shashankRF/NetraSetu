# NetraSetu

**Evidence-grounded disaster and telecom decision support**

NetraSetu is a research and demonstration platform for analyzing incident evidence, exploring communication failures, and preparing decisions for authorized human review. It combines a FastAPI backend with a browser dashboard and a document knowledge base.

> Evidence supports the analysis. The Risk & Governance Engine sets review gates. Authorized people make consequential decisions.

## Current capabilities

| Area | What is implemented | Boundary |
|---|---|---|
| Evidence analysis | BGE-M3/FAISS retrieval, reranking, supporting and counter-evidence, gap and absence analysis, citation verification | Search results are limited to the ingested corpus; an unavailable citation is reported as not retrieved |
| Document registry | Source metadata, local PDF viewing, and links to the cited page | Document names and metadata do not replace checking the original source |
| Risk & governance | Deterministic risk assessment, human-review gates, and recorded approve/modify/reject decisions | Recommendations do not authorize production or field actions |
| Failure Combination Lab | Bounded, reproducible multi-failure simulation, persisted results, policy thresholds, and scenario p95 metrics | Software simulation only; no live 5G measurements or network changes |
| Latency & reliability | Separates browser/backend processing time from simulator p95 network latency | Historical runs without detailed distributions show only the p95 value actually stored |
| ECR-5G | Controlled QoS/failure simulation and governance review | Not a 3GPP conformance test or production controller |
| Inter-Agency Coordination | Saved local conversation and run-linked message proposals | Messages are not delivered to external agencies |
| Uttarakhand Disaster Map | MapLibre district map with separately switchable, source-dated reports | Only the dated layers listed below are integrated; no unsupported area is labeled safe |
| Dharali aftermath review | BM25 search across two official incident PDFs, page-linked citations, four incident assessment checkpoints, and governance parameter/audit recording | Dated document evidence, not live observations or a verified rehabilitation plan |
| Change-impact workbench | Prototype for comparing document revisions and planning affected-evidence review | Continuous authoritative change ingestion is not implemented |

## Uttarakhand data and source limits

The checked-in map window is **25 July–25 October 2026**. Its current layers use an Uttarakhand PWD SRMD report snapshot dated **11 September 2026** (86 dated road-closure records in the selected period), a USDMA heavy-rain warning dated **26 September 2026**, and two GSI portal-reported landslide summaries dated **19 August** and **1 September 2026**. Road shading counts reported road closures; it is not a flood or landslide footprint. The warning is an alert, not proof of an incident. GSI entries have district/route context but no event geometry.

Flood extents, forest-fire records, and lower-risk areas are not currently integrated as dated public datasets. They remain unavailable or unclassified. See the source and freshness captions in the map and `Backend/disaster_map_api.py` for the checked-in source metadata.

### Dharali source pack

The aftermath workbench refers to the **5 August 2025 Kheer Gad flash flood and debris flow at Dharali, Uttarkashi**. It searches these source PDFs, included under `knowledge_base/Dharali Incident 2025/`:

- Geological Survey of India, *Preliminary Note on the devastating flash flood in Kheer Gad, Dharali, Uttarkashi district, Uttarakhand*.
- NRSC/ISRO NDEM, *Damage Assessment in Dharali, Uttarkashi on 05 August 2025*, Map 2025/LS/UK/01. The map compares a 13 June 2024 pre-event image with a 6 August 2025 post-event image.

The search window defaults to **1–30 August 2025**; this is not daily data coverage. Search uses BM25 ranking over text extracted from PDF pages with PyMuPDF. Citations identify source, page, and extracted line range and link to the local PDF page. Four displayed targets are mapped assessment checkpoints: Dharali settlement, Kheer Gad runout, the Bhagirathi confluence, and the Dharali–Mukhba bridge/Gangotri Highway access. They are not four confirmed damaged facilities. Current facility condition, absolute elevation/DEM, later river state, and rehabilitation progress remain **Not retrieved** unless supported by added evidence.

## Architecture

```text
Browser dashboard
  ├─ Evidence query → retrieval → reranking → evidence/counter-evidence checks
  │                  → gap/absence analysis → risk/governance → citations + audit
  ├─ Failure Combination Lab → deterministic simulator → stored run + p95 metrics
  │                              → governance review gate
  └─ Dharali aftermath search → PyMuPDF page extraction + BM25 → cited findings
                                 → Risk & Governance Engine → audit record

FastAPI routes and static dashboard: Backend/server.py
Knowledge base: rag/ and knowledge_base/
Interactive UI: Frontend/index.html
Focused backend tests: Backend/tests/
```

Core components include Python, FastAPI, Pydantic, BGE-M3, FAISS, BGE reranking, PyMuPDF, and the existing NetraSetu Risk & Governance Engine. LLM synthesis uses the configured Groq provider when enabled. The failure simulator is deterministic and does not use an LLM in its decision loop.

## Run locally

Requirements: Python 3.11 or newer. From the repository root on Windows:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt  # only needed to run the test suite
Copy-Item .env.example .env
```

Set `GROQ_API_KEY` in the local `.env` file to enable provider-backed synthesis. Keep secrets out of Git. The deterministic simulator, map, and source-PDF search do not require a Groq key.

Start the local development dashboard:

```powershell
.\RUN_NETRASETU_DEV.bat
```

The script starts FastAPI on `127.0.0.1:8000`, serves `Frontend/` on `127.0.0.1:5500`, and opens the browser. The backend also serves the frontend at `/frontend/`; when using that same-origin route, the UI derives the API host and port from the page URL. Do not use a remote machine's `localhost` address from another computer's browser.

Production deployments must set `NETRASETU_ENV=production`, configure an administrator username and Argon2id password hash, serve over HTTPS, and follow [SECURITY.md](SECURITY.md) and [Backend/SECURITY_DEPLOYMENT.md](Backend/SECURITY_DEPLOYMENT.md). The built-in development login fallback is for local demonstrations only.

## API and run history

The FastAPI schema is available at `/openapi.json` while the server is running. Key routes include:

- `GET /api/health`
- `GET /api/disaster-map/data`
- `GET /api/aftermath/incident-sources/dharali-2025`
- `POST /api/aftermath/incident-analysis`
- `GET /api/5g/failure-combinations/catalog`
- `POST /api/5g/failure-combinations`
- `GET /api/5g/failure-combinations?limit=20`
- `GET /api/5g/failure-combinations/{run_id}`
- `GET /api/coordination/messages`

Protected dashboard API requests require a server session; state-changing requests also require the session CSRF token. Failure-combination runs are appended to `Backend/audit/records/failure_combination_runs.jsonl` (ignored by Git), and governance records are stored in the audit ledger. The p95 chart reads persisted run results; it does not synthesize missing values.

## Tests

Run backend and browser-side checks from the repository root:

```powershell
python -m pytest Backend/tests -q
node --test Frontend/tests/disaster_map.test.js Frontend/tests/ecr5g.test.js Frontend/tests/gap_analysis.test.js Frontend/tests/latency_chart.test.js
```

Some integration tests initialize retrieval/model components and may take longer than unit tests. Provider-backed smoke tests, where configured, may require network access and a valid local API key.

## Limitations and responsible use

- This is a prototype for research and decision support, not a certified emergency-management or telecom control system.
- Map observations are source-dated snapshots; missing layers do not imply that no incident occurred.
- Terrain or satellite detections are not verified damage assessments unless a cited authority confirms them.
- Simulator values are not measurements from deployed networks.
- A recommendation is not an agency assignment, legal determination, or authorization to act.
- Check cited primary documents and obtain current field evidence before operational decisions.

## License

See [LICENSE](LICENSE) for the project license.
