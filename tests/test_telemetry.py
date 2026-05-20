"""Tests for centralized telemetry persistence, queries, and dashboard APIs."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from telemetry.event_store import configure_db_path, init_event_store
from telemetry.events import EventSeverity, EventSource, EventType, emit_event, emit_inference_event
from telemetry.queries import query_events, export_events
from telemetry.aggregator import get_dashboard_summary, get_recent_activity, get_security_event_summary
from app import app


@pytest.fixture()
def telemetry_db(tmp_path):
    db_path = tmp_path / "security_events.db"
    configure_db_path(db_path)
    init_event_store(db_path)
    yield db_path
    configure_db_path(Path(__file__).parent.parent / "training_state" / "security_events.db")


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture()
def logged_in_client(client):
    with client.session_transaction() as sess:
        sess["user"] = "person1"
    return client


def _emit_sample(owner: str = "person1", **overrides):
    payload = {
        "severity": EventSeverity.INFO,
        "event_type": EventType.INFERENCE_COMPLETED,
        "source": EventSource.INFERENCE,
        "title": "Inference completed",
        "description": "Test inference event",
        "metadata": {"model_name": "EfficientNet-B0", "prediction": "cat"},
        "owner": owner,
    }
    payload.update(overrides)
    return emit_event(**payload)


class TestEventPersistence:
    def test_emit_event_persists_record(self, telemetry_db):
        event_id = _emit_sample()
        assert event_id is not None
        result = query_events(page_size=10)
        assert result["pagination"]["total"] == 1
        assert result["events"][0]["title"] == "Inference completed"

    def test_query_filters_by_severity(self, telemetry_db):
        _emit_sample(severity=EventSeverity.INFO)
        _emit_sample(severity=EventSeverity.HIGH, event_type=EventType.INFERENCE_HIGH_RISK, title="High risk")
        high_only = query_events(severity="HIGH")
        assert high_only["pagination"]["total"] == 1
        assert high_only["events"][0]["severity"] == "HIGH"

    def test_query_filters_by_category(self, telemetry_db):
        _emit_sample()
        emit_event(
            severity=EventSeverity.WARNING,
            event_type=EventType.DRIFT_HIGH_WARNING,
            source=EventSource.DRIFT,
            title="Drift warning",
            description="Drift warning",
            metadata={"drift_score": 0.8},
            owner="person1",
        )
        drift = query_events(category="drift")
        assert drift["pagination"]["total"] == 1
        assert drift["events"][0]["event_type"].startswith("drift.")

    def test_pagination(self, telemetry_db):
        for idx in range(5):
            _emit_sample(title=f"Event {idx}", metadata={"model_name": f"m{idx}"})
        page1 = query_events(page=1, page_size=2)
        page2 = query_events(page=2, page_size=2)
        assert page1["pagination"]["total"] == 5
        assert len(page1["events"]) == 2
        assert len(page2["events"]) == 2
        assert page1["events"][0]["id"] != page2["events"][0]["id"]

    def test_search(self, telemetry_db):
        _emit_sample(title="ResNet18 training completed", metadata={"model_name": "ResNet18"})
        found = query_events(search="ResNet18")
        assert found["pagination"]["total"] == 1

    def test_export_json(self, telemetry_db):
        _emit_sample()
        content, content_type, filename = export_events(format="json", owner="person1")
        assert "application/json" in content_type
        assert filename.endswith(".json")
        assert "Inference completed" in content

    def test_export_csv(self, telemetry_db):
        _emit_sample()
        content, content_type, filename = export_events(format="csv", owner="person1")
        assert "text/csv" in content_type
        assert filename.endswith(".csv")
        assert "Inference completed" in content


class TestAggregation:
    def test_dashboard_summary_metrics(self, telemetry_db):
        _emit_sample()
        emit_event(
            severity=EventSeverity.HIGH,
            event_type=EventType.INFERENCE_HIGH_RISK,
            source=EventSource.INFERENCE,
            title="High risk inference",
            description="High risk",
            metadata={"owner": "person1"},
            owner="person1",
        )
        summary = get_dashboard_summary(owner="person1")
        assert summary["metrics"]["total_inferences"] >= 1
        assert summary["metrics"]["high_risk_events"] >= 1

    def test_recent_activity(self, telemetry_db):
        _emit_sample()
        activity = get_recent_activity(limit=5, owner="person1")
        assert len(activity) == 1

    def test_security_summary(self, telemetry_db):
        emit_event(
            severity=EventSeverity.HIGH,
            event_type=EventType.ADVERSARIAL_SUSPICION,
            source=EventSource.ADVERSARIAL,
            title="Adversarial suspicion",
            description="Detected",
            metadata={"owner": "person1"},
            owner="person1",
        )
        events = get_security_event_summary(owner="person1")
        assert len(events) == 1


class TestInferenceEventEmission:
    def test_emit_inference_event_blocked(self, telemetry_db):
        emit_inference_event(
            {
                "status": "blocked",
                "risk_level": "HIGH",
                "decision_reason": "Rate limited",
                "prediction": None,
            },
            username="person1",
        )
        result = query_events(event_type=EventType.INFERENCE_BLOCKED, owner="person1")
        assert result["pagination"]["total"] == 1


class TestDashboardApis:
    def test_dashboard_summary_requires_login(self, client):
        response = client.get("/api/dashboard/summary")
        assert response.status_code == 401

    def test_dashboard_summary_ok(self, logged_in_client, telemetry_db):
        _emit_sample()
        response = logged_in_client.get("/api/dashboard/summary")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        assert "metrics" in payload["summary"]

    def test_security_events_api(self, logged_in_client, telemetry_db):
        _emit_sample()
        response = logged_in_client.get("/api/security/events?page=1&page_size=10")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        assert payload["pagination"]["total"] >= 1

    def test_security_events_filter(self, logged_in_client, telemetry_db):
        _emit_sample(severity=EventSeverity.HIGH, event_type=EventType.INFERENCE_HIGH_RISK)
        response = logged_in_client.get("/api/security/events?severity=HIGH")
        payload = response.get_json()
        assert all(event["severity"] == "HIGH" for event in payload["events"])

    def test_dashboard_activity_api(self, logged_in_client, telemetry_db):
        _emit_sample()
        response = logged_in_client.get("/api/dashboard/activity?limit=5")
        assert response.status_code == 200
        payload = response.get_json()
        assert len(payload["activity"]) >= 1

    def test_security_export_api(self, logged_in_client, telemetry_db):
        _emit_sample()
        response = logged_in_client.get("/api/security/events/export?format=json")
        assert response.status_code == 200
        assert "Inference completed" in response.get_data(as_text=True)
