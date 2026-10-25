from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

from Backend.disaster_map_api import router
from Backend.authentication import requires_session

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_map_data_has_date_filtered_official_report_records_and_contextual_boundaries():
    response = client.get("/api/disaster-map/data")
    assert response.status_code == 200
    data = response.json()
    assert data["boundaries"]["type"] == "FeatureCollection"
    assert data["coordinate_reference_system"] == "EPSG:4326"
    assert data["boundary_metadata"]["district_feature_count"] == 13
    assert data["window"] == {"start": "2026-07-25", "end": "2026-10-25", "reviewed_date": "2026-10-25"}

    report = data["road_closures"]
    assert report["record_count"] == 86
    assert len(report["records"]) == report["record_count"]
    assert sum(report["by_district"].values()) == report["record_count"]
    assert report["report_snapshot_date"] == "2026-09-11"
    assert report["source_url"].endswith("20260911159033709.pdf")
    for record in report["records"]:
        assert date.fromisoformat("2026-07-25") <= date.fromisoformat(record["date_closed"]) <= date.fromisoformat("2026-10-25")
        assert record["status_at_snapshot"].lower() == "closed"
        assert record["district_as_reported"]
        assert record["source_page"] in range(5, 10)

    districts = [feature["properties"] for feature in data["boundaries"]["features"] if feature["properties"].get("layer") == "district"]
    assert len(districts) == 13
    assert any(item["district_name"] == "Pithoragarh" and item["pwd_closed_road_count"] == 14 and item["rainfall_alert"] and item["gsi_landslide_report_count"] == 1 for item in districts)
    assert all("not disaster-affected area" in item["area_interpretation"] for item in districts)

    assert [item["event_date"] for item in data["landslide_reports"]] == ["2026-08-19", "2026-09-01"]
    alert = data["rainfall_alerts"][0]
    assert alert["alert_date"] == "2026-09-26"
    assert alert["published_date"] == "2026-09-28"
    assert "not an observed flood" in alert["status"]
    assert "No publicly retrievable" in data["unsupported_layers"]["flood"]
    assert data["layer_status"]["lower_risk"] == "UNCLASSIFIED_NO_SUPPORTING_DATA"
    assert all(source["url"].startswith("https://") for source in data["sources"])
    assert all("demo" not in source["integration_status"].lower() for source in data["sources"])


def test_map_health_and_authenticated_route_policy():
    response = client.get("/api/disaster-map/health")
    assert response.status_code == 200
    assert response.json()["dated_pwd_records"] == 86
    assert response.json()["reported_landslides"] == 2
    assert response.json()["demo_data"] is False
    assert requires_session("/api/disaster-map/data", "GET") is True


def test_map_route_is_registered_and_session_protected_in_application():
    from Backend.server import app as netrasetu_app

    app_client = TestClient(netrasetu_app)
    denied = app_client.get("/api/disaster-map/data")
    assert denied.status_code == 401
    login = app_client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login.status_code == 200
    response = app_client.get("/api/disaster-map/data")
    assert response.status_code == 200
    assert response.json()["coordinate_reference_system"] == "EPSG:4326"
    assert len(response.json()["road_closures"]["records"]) == 86
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
