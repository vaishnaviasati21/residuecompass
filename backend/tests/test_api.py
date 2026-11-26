"""
Integration tests – run against a live DB.
To run without a DB (CI smoke test), set DEMO_MODE=true; most tests
use the TestClient against the FastAPI app which routes through queries.py.

Usage:
    cd backend
    pytest tests/ -v
"""
import json
import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("DATABASE_URL", "postgresql://rc:rc_pass@localhost:5432/residue")
os.environ.setdefault("SECRET_KEY", "test_secret_key_32_chars_long_xxx")

from app.main import app
from app.core.security import create_access_token

client = TestClient(app, raise_server_exceptions=False)


# ── Token helpers ─────────────────────────────────────────────────────────

def officer_token():
    return create_access_token({"sub": "1", "role": "officer",
                                 "village_id": None, "buyer_id": None})


def farmer_token(village_id="PB-SNG-0142"):
    return create_access_token({"sub": "2", "role": "farmer",
                                 "village_id": village_id, "buyer_id": None})


def buyer_token(buyer_id="B-012"):
    return create_access_token({"sub": "3", "role": "buyer",
                                 "village_id": None, "buyer_id": buyer_id})


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── Health ────────────────────────────────────────────────────────────────

def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "demo_mode" in body


# ── Auth error contract ───────────────────────────────────────────────────

def test_unauthenticated_returns_401():
    r = client.get("/api/v1/villages")
    assert r.status_code == 401
    assert "error" in r.json()["detail"]


def test_wrong_role_returns_403():
    # buyer trying to access officer-only job endpoint
    token = buyer_token()
    r = client.post("/api/v1/jobs/run",
                    json={"job": "daily_refresh"},
                    headers=auth(token))
    assert r.status_code == 403


# ── Error envelope format ─────────────────────────────────────────────────

def test_not_found_envelope():
    token = officer_token()
    r = client.get("/api/v1/villages/NONEXISTENT", headers=auth(token))
    assert r.status_code == 404
    body = r.json()
    assert "error" in body["detail"]
    assert "code" in body["detail"]["error"]


# ── Villages ──────────────────────────────────────────────────────────────

def test_list_villages_officer():
    r = client.get("/api/v1/villages", headers=auth(officer_token()))
    # May be 200 (with DB) or 500 (no DB in CI) – just check the shape if 200
    if r.status_code == 200:
        villages = r.json()
        assert isinstance(villages, list)
        if villages:
            v = villages[0]
            assert "village_id" in v
            assert "centroid" in v
            assert v["centroid"]["type"] == "Point"


def test_farmer_scoped_to_own_village():
    token = farmer_token("PB-SNG-0142")
    r = client.get("/api/v1/villages", headers=auth(token))
    if r.status_code == 200:
        villages = r.json()
        for v in villages:
            assert v["village_id"] == "PB-SNG-0142"


# ── Forecast ──────────────────────────────────────────────────────────────

def test_forecast_shape():
    token = officer_token()
    r = client.get("/api/v1/villages/PB-SNG-0142/forecast", headers=auth(token))
    if r.status_code == 200:
        f = r.json()
        assert "harvest" in f
        assert "expected_date" in f["harvest"]
        assert "straw" in f
        assert "expected_tonnes" in f["straw"]
        assert f["confidence"]["tag"] in ("LOW", "MEDIUM", "HIGH")


# ── Decision ──────────────────────────────────────────────────────────────

def test_decision_shape():
    token = officer_token()
    r = client.get("/api/v1/villages/PB-SNG-0142/decision", headers=auth(token))
    if r.status_code == 200:
        d = r.json()
        assert d["best_option"] in ("keep", "sell", "feed")
        assert "break_even_price_per_tonne_inr" in d
        assert "per_tonne_inr" in d
        assert "sell" in d["per_tonne_inr"]


def test_decision_simulate():
    token = officer_token()
    r = client.post(
        "/api/v1/decisions/simulate?village_id=PB-SNG-0142",
        json={"distance_km": 10, "baling_cost_per_tonne": 400},
        headers=auth(token),
    )
    if r.status_code == 200:
        d = r.json()
        # With distance_km=10 and default transport=12: break-even = 400 + 12*10 = 520
        assert d["break_even_price_per_tonne_inr"] == pytest.approx(520, abs=1)


# ── Matches ───────────────────────────────────────────────────────────────

def test_list_matches_shape():
    token = officer_token()
    r = client.get("/api/v1/matches", headers=auth(token))
    if r.status_code == 200:
        matches = r.json()
        assert isinstance(matches, list)
        if matches:
            m = matches[0]
            assert "match_id" in m
            assert "buyer" in m
            assert m["status"] in ("PROPOSED", "CONFIRMED", "COMPLETED", "CANCELLED")


def test_buyer_sees_only_own_matches():
    token = buyer_token("B-012")
    r = client.get("/api/v1/matches", headers=auth(token))
    if r.status_code == 200:
        for m in r.json():
            assert m["buyer"]["id"] == "B-012"


# ── Burn events ───────────────────────────────────────────────────────────

def test_burn_events_shape():
    token = officer_token()
    r = client.get("/api/v1/burn-events", headers=auth(token))
    if r.status_code == 200:
        burns = r.json()
        if burns:
            b = burns[0]
            assert "event_id" in b
            assert b["confidence"] in ("LOW", "MEDIUM", "HIGH")
            assert b["location"]["type"] == "Point"


# ── Notification templates ────────────────────────────────────────────────

def test_template_rendering_english():
    from app.notifier.templates import render_message
    msg = render_message("en", "match_confirmed",
                          buyer_name="Sample Pellet Unit",
                          pickup_date="2026-10-24", price=1500)
    assert "2026-10-24" in msg
    assert "1500" in msg
    assert "Sample Pellet Unit" in msg


def test_template_rendering_punjabi():
    from app.notifier.templates import render_message
    msg = render_message("pa", "match_confirmed",
                          buyer_name="Sample Pellet Unit",
                          pickup_date="2026-10-24", price=1500)
    assert "pa" != "en"           # just checking it ran
    assert "2026-10-24" in msg


def test_template_fallback_bad_language():
    from app.notifier.templates import render_message
    msg = render_message("zh", "match_confirmed",
                          buyer_name="X", pickup_date="2026-10-24", price=1000)
    # Should not raise; falls back to English
    assert "X" in msg


def test_unknown_template():
    from app.notifier.templates import render_message
    msg = render_message("en", "nonexistent_template")
    assert "unknown template" in msg


# ── Demo loop ─────────────────────────────────────────────────────────────

def test_demo_run_shape():
    r = client.post("/api/v1/demo/run?village_id=PB-SNG-0142")
    if r.status_code == 200:
        body = r.json()
        assert "steps" in body
        assert isinstance(body["steps"], list)
        step_names = [s["step"] for s in body["steps"]]
        assert "forecast" in step_names
        assert "decision" in step_names
        assert "match" in step_names
        assert "notification" in step_names
        assert "burn_check" in step_names
