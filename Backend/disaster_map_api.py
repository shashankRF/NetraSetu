"""Source-dated Uttarakhand map data with explicit geographic precision."""
from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/disaster-map", tags=["uttarakhand-disaster-map"])
_DATA_DIR = Path(__file__).resolve().parent / "disaster_map_data"
_BOUNDARY_DIR = Path(__file__).resolve().parent / "disaster_map_boundaries"
_BOUNDARY_GEOJSON = _BOUNDARY_DIR / "uttarakhand-admin.geojson"
_PWD_DATA = _DATA_DIR / "pwd_road_closures_2026-09-11.json"
WINDOW_START = date(2026, 7, 25)
WINDOW_END = date(2026, 10, 25)

SOURCES: tuple[dict[str, str], ...] = (
    {"name": "Uttarakhand PWD · SRMD report (11 Sep 2026)", "url": "https://pwd.uk.gov.in/srmd-reports-1/", "integration_status": "Integrated dated report snapshot · district/road table, not live", "freshness": "Report snapshot 2026-09-11; events date-filtered through 2026-10-25"},
    {"name": "USDMA · heavy-rain red-alert notice", "url": "https://usdma.uk.gov.in/26-september-2026-usdma-disaster-management-system-on-full-alert-amid-heavy-rainfall-warning/", "integration_status": "Integrated as a dated warning, not an observed flood", "freshness": "Alert date 2026-09-26 · page published 2026-09-28"},
    {"name": "Geological Survey of India · Bhooskhalan portal", "url": "https://bhusanket.gsi.gov.in/", "integration_status": "Integrated dated portal news summaries · no event geometry", "freshness": "Reported events 2026-08-19 and 2026-09-01; portal entries 2026-08-20 and 2026-09-02"},
    {"name": "Bhuvan disaster portal", "url": "https://bhuvan-app1.nrsc.gov.in/disaster/disaster.php", "integration_status": "Official viewer only; no current Uttarakhand event layer integrated", "freshness": "No current Uttarakhand event timestamp verified"},
    {"name": "NRSC National Database for Emergency Management", "url": "https://ndem.nrsc.gov.in/", "integration_status": "Not integrated; access may require authorisation", "freshness": "No public Uttarakhand feed timestamp verified"},
    {"name": "Forest Survey of India forest-fire alerts", "url": "https://fsiforestfire.gov.in/", "integration_status": "Official viewer only; no documented public historical feed integrated", "freshness": "No Uttarakhand dated alert records integrated"},
    {"name": "Uttarakhand Forest GIS", "url": "https://www.ukforestgis.in/web/indexs", "integration_status": "Official viewer only; no documented dated feed integrated", "freshness": "No feed timestamp available"},
    {"name": "USDMA disaster risk assessment", "url": "https://usdma.uk.gov.in/document-category/disaster-risk-assessment/", "integration_status": "Official reports; no machine-readable event geometry integrated", "freshness": "Document dates are source-published; no feed timestamp"},
)

_LANDSLIDES: tuple[dict[str, Any], ...] = (
    {"id": "gsi-pithoragarh-2026-08-19", "event_date": "2026-08-19", "reported_date": "2026-08-20", "district": "Pithoragarh", "location": "Kulagad suspension bridge, Dharchula–Gunji route", "type": "Landslide reported by GSI portal", "status": "Portal-reported event; location is route/district context", "details": "GSI portal summary says heavy rainfall triggered a landslide, damaging the suspension bridge and halting traffic to the Vyas and Darma valleys. The source summary provides no coordinates or affected-area polygon.", "source": "Geological Survey of India · Bhooskhalan portal", "source_url": "https://bhusanket.gsi.gov.in/", "location_precision": "Named route/bridge and district; no coordinates or event perimeter published in the source summary."},
    {"id": "gsi-dehradun-2026-09-01", "event_date": "2026-09-01", "reported_date": "2026-09-02", "district": "Dehradun", "location": "Dehradun–Mussoorie highway", "type": "Landslide reported by GSI portal", "status": "Portal news summary; location is highway/district context", "details": "GSI portal news summary reports landslides blocking the Dehradun–Mussoorie highway. It does not provide a geocoded segment or affected-area polygon.", "source": "Geological Survey of India · Bhooskhalan portal", "source_url": "https://bhusanket.gsi.gov.in/", "location_precision": "Named highway and district; no coordinates or event perimeter published in the source summary."},
)

_RAINFALL_ALERT = {
    "id": "usdma-red-rain-alert-2026-09-26",
    "alert_date": "2026-09-26",
    "published_date": "2026-09-28",
    "districts": ["Bageshwar", "Pithoragarh", "Champawat", "Nainital", "Udham Singh Nagar"],
    "type": "IMD red alert for heavy to extremely heavy rainfall",
    "status": "Historical warning; not an observed flood or current alert",
    "source": "USDMA",
    "source_url": "https://usdma.uk.gov.in/26-september-2026-usdma-disaster-management-system-on-full-alert-amid-heavy-rainfall-warning/",
    "location_precision": "Districts named by USDMA; no rainfall footprint or flood extent published in this notice.",
}


def _read_json(path: Path, message: str) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(503, message) from exc


def _boundaries() -> dict[str, Any]:
    collection = _read_json(_BOUNDARY_GEOJSON, "Bundled Uttarakhand boundary data is missing or invalid.")
    metadata = _read_json(_BOUNDARY_DIR / "metadata.json", "Boundary metadata is missing or invalid.")
    if collection.get("type") != "FeatureCollection" or not isinstance(collection.get("features"), list):
        raise HTTPException(503, "Bundled Uttarakhand boundaries are not a GeoJSON FeatureCollection.")
    features = collection["features"]
    if not any(item.get("properties", {}).get("layer") == "state" for item in features) or not any(item.get("properties", {}).get("layer") == "district" for item in features):
        raise HTTPException(503, "Bundled boundaries must include the state and district features.")
    return {"geojson": collection, "metadata": metadata}


def _district_name(name: str) -> str:
    normalized = " ".join(name.casefold().replace(".", "").split())
    aliases = {
        "haridwar": "Hardwar", "hardwar": "Hardwar", "nanital": "Nainital",
        "nainital": "Nainital", "pauri": "Garhwal", "pauri garhwal": "Garhwal",
        "tehri": "Tehri Garhwal", "tehri garhwal": "Tehri Garhwal",
        "u s nagar": "Udham Singh Nagar", "us nagar": "Udham Singh Nagar",
    }
    return aliases.get(normalized, " ".join(word.capitalize() for word in name.split()))


def _report_data() -> dict[str, Any]:
    report = _read_json(_PWD_DATA, "Bundled PWD report snapshot is missing or invalid.")
    start = date.fromisoformat(report["window_start"])
    end = date.fromisoformat(report["window_end"])
    rows = [row for row in report["records"] if start <= date.fromisoformat(row["date_closed"]) <= end]
    report["records"] = rows
    report["record_count"] = len(rows)
    counts = Counter(_district_name(row["district_as_reported"]) for row in rows if row.get("district_as_reported"))
    report["by_district"] = dict(sorted(counts.items()))
    return report


@router.get("/health")
def disaster_map_health() -> dict[str, Any]:
    _boundaries()
    report = _report_data()
    return {"ok": True, "service": "uttarakhand-disaster-map", "dated_pwd_records": report["record_count"], "reported_landslides": len(_LANDSLIDES), "demo_data": False}


@router.get("/data")
def disaster_map_data() -> dict[str, Any]:
    boundary_data = _boundaries()
    report = _report_data()
    road_counts = report["by_district"]
    alert_districts = {_district_name(name) for name in _RAINFALL_ALERT["districts"]}
    landslide_districts = {_district_name(item["district"]) for item in _LANDSLIDES}
    features = []
    for feature in boundary_data["geojson"]["features"]:
        item = json.loads(json.dumps(feature))
        props = item.setdefault("properties", {})
        if props.get("layer") == "district":
            name = _district_name(str(props.get("shapeName") or props.get("district") or props.get("name") or ""))
            props.update({
                "district_name": name,
                "pwd_closed_road_count": road_counts.get(name, 0),
                "rainfall_alert": name in alert_districts,
                "gsi_landslide_report_count": sum(1 for record in _LANDSLIDES if _district_name(record["district"]) == name),
                "road_data_date": report["report_snapshot_date"],
                "road_data_source": "Uttarakhand PWD SRMD report; road closures of all causes",
                "area_interpretation": "District shading encodes count of dated road-closure rows, not disaster-affected area.",
            })
        features.append(item)
    report["by_district"] = dict(sorted(road_counts.items()))
    return {
        "boundaries": {"type": "FeatureCollection", "features": features},
        "boundary_metadata": boundary_data["metadata"],
        "coordinate_reference_system": "EPSG:4326",
        "window": {"start": WINDOW_START.isoformat(), "end": WINDOW_END.isoformat(), "reviewed_date": "2026-10-25"},
        "road_closures": report,
        "landslide_reports": list(_LANDSLIDES),
        "rainfall_alerts": [_RAINFALL_ALERT],
        "unsupported_layers": {
            "flood": "No publicly retrievable Uttarakhand flood extent or event geometry was verified for this window. This is not evidence that no flooding occurred.",
            "forest_fire": "No documented public, dated Uttarakhand fire-incident feed was integrated for this window.",
            "lower_risk": "Unclassified: no supporting district-level risk/status dataset integrated.",
        },
        "sources": list(SOURCES),
        "layer_status": {"pwd_road_closures": "DATED_REPORT_SNAPSHOT", "rainfall_alerts": "HISTORICAL_WARNING_NOT_INCIDENT", "landslides": "PORTAL_REPORTED_DISTRICT_CONTEXT_NO_GEOMETRY", "flood": "NO_PUBLIC_GEOMETRY_VERIFIED", "forest_fire": "NO_DATED_PUBLIC_FEED_INTEGRATED", "lower_risk": "UNCLASSIFIED_NO_SUPPORTING_DATA"},
        "data_freshness": {"reviewed_date": "2026-10-25", "pwd_snapshot_date": report["report_snapshot_date"], "pwd_snapshot_note": "Latest integrated PWD report snapshot is 2026-09-11; it is not live data."},
    }
