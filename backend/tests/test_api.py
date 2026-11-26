"""
Comprehensive integration and unit tests for Residue Compass API.

Non-DB tests (run in all environments):
  - Auth & authorization contract
  - Security config validation
  - Demo seeder guards
  - Password hashing
  - Notification templates
  - Decision simulate bounds validation
  - Pagination bounds validation
  - make_schemas.py non-destructive behaviour

DB-dependent tests (skipped unless TEST_DATABASE_URL is set):
  - Village listing and scoping
  - Forecast shape
  - Decision shape and simulate
  - Match listing, ownership, and atomic state transitions
  - Burn events
  - Job trigger + polling
  - Notification failure logging
  - Health → 503 when DB down
  - Seed isolation (demo reset refuses in production mode)

Usage:
    # Without DB (CI smoke):
    cd backend && pytest tests/ -v

    # With DB:
    cd backend && TEST_DATABASE_URL=postgresql://rc:pass@localhost/residue_test pytest tests/ -v
"""
import json
import os
import pytest
from fastapi.testclient import TestClient

# ── Environment bootstrap ─────────────────────────────────────────────────
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("DATABASE_URL", "postgresql://rc:rc_pass@localhost:5432/residue")
os.environ.setdefault("SECRET_KEY", "test_secret_key_32_chars_long_xxx")

from app.main import app
from app.core.security import create_access_token

client = TestClient(app, raise_server_exceptions=False)

HAS_DB = bool(os.environ.get("TEST_DATABASE_URL"))
requires_db = pytest.mark.skipif(not HAS_DB, reason="TEST_DATABASE_URL not set")


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

@requires_db
def test_health():
    r = client.get("/api/v1/health")
    # 200 (DB up) or 503 (DB down) – both are correct contract responses
    assert r.status_code in (200, 503)
    body = r.json()
    assert "database" in body
    assert "demo_mode" in body
    if r.status_code == 200:
        assert body["status"] == "ok"
    else:
        assert body["status"] == "degraded"


def test_health_returns_503_when_db_down(monkeypatch):
    """Health must return 503 when the database is unreachable."""
    from app.core import db as db_module
    from sqlalchemy import create_engine

    # Point engine at a port that is guaranteed to refuse connections
    bad_engine = create_engine("postgresql://x:x@127.0.0.1:1/nonexistent",
                               connect_args={"connect_timeout": 1})
    monkeypatch.setattr(db_module, "engine", bad_engine)

    # Also patch the engine imported directly into main
    import app.main as main_module
    monkeypatch.setattr(main_module, "engine", bad_engine)

    r = client.get("/api/v1/health")
    assert r.status_code == 503
    assert r.json()["database"] == "down"
    assert r.json()["status"] == "degraded"


# ── Auth & authorization contract ─────────────────────────────────────────

def test_unauthenticated_returns_401():
    for method, path in [
        ("GET",  "/api/v1/villages"),
        ("POST", "/api/v1/auth/register"),
        ("POST", "/api/v1/demo/reset"),
    ]:
        r = client.request(method, path)
        assert r.status_code == 401, f"{method} {path} returned {r.status_code}"
        assert "error" in r.json()["detail"]


def test_wrong_role_returns_403():
    token = buyer_token()
    r = client.post("/api/v1/jobs/run",
                    json={"job": "daily_refresh"},
                    headers=auth(token))
    assert r.status_code == 403

    r_reset = client.post("/api/v1/demo/reset", headers=auth(token))
    assert r_reset.status_code == 403

    r_reg = client.post(
        "/api/v1/auth/register",
        json={"name": "Fake", "phone": "+919999999999", "password": "password123",
              "role": "farmer", "village_id": "PB-SNG-0142"},
        headers=auth(token),
    )
    assert r_reg.status_code == 403


def test_farmer_cross_village_access_forbidden():
    token = farmer_token("PB-SNG-0142")
    assert client.get("/api/v1/villages/PB-TTN-0031", headers=auth(token)).status_code == 403
    assert client.get("/api/v1/matches?village_id=PB-TTN-0031", headers=auth(token)).status_code == 403
    assert client.get("/api/v1/burn-events?village_id=PB-TTN-0031", headers=auth(token)).status_code == 403
    assert client.post(
        "/api/v1/decisions/simulate?village_id=PB-TTN-0031",
        json={"distance_km": 10},
        headers=auth(token),
    ).status_code == 403


# ── Security config ───────────────────────────────────────────────────────

def test_security_config_fails_closed(monkeypatch):
    from app.core import config
    monkeypatch.setattr(config.settings, "SECRET_KEY", "change_me")
    with pytest.raises(RuntimeError):
        config.validate_security_config()

    monkeypatch.setattr(config.settings, "SECRET_KEY", "short")
    with pytest.raises(RuntimeError):
        config.validate_security_config()


# ── Demo seeder guards ────────────────────────────────────────────────────

def test_demo_seeder_refuses_when_demo_mode_false(monkeypatch):
    from app.core import config
    from scripts import load_seed, seed_demo
    monkeypatch.setattr(config.settings, "DEMO_MODE", False)
    with pytest.raises(RuntimeError):
        load_seed.main()
    with pytest.raises(RuntimeError):
        seed_demo.main()


def test_demo_endpoints_disabled_when_demo_mode_false(monkeypatch):
    from app.core import config
    monkeypatch.setattr(config.settings, "DEMO_MODE", False)
    r_run = client.post("/api/v1/demo/run?village_id=PB-SNG-0142")
    assert r_run.status_code == 403
    r_reset = client.post("/api/v1/demo/reset", headers=auth(officer_token()))
    assert r_reset.status_code == 403


# ── Password hashing ──────────────────────────────────────────────────────

def test_password_hash_and_verify():
    from app.core.security import hash_password, verify_password
    hashed = hash_password("strong_pass_123")
    assert hashed != "strong_pass_123"
    assert verify_password("strong_pass_123", hashed)
    assert not verify_password("wrong_pass", hashed)


# ── Error envelope format ─────────────────────────────────────────────────

@requires_db
def test_not_found_envelope():
    token = officer_token()
    r = client.get("/api/v1/villages/NONEXISTENT", headers=auth(token))
    assert r.status_code == 404
    body = r.json()
    assert "error" in body["detail"]
    assert "code" in body["detail"]["error"]


# ── Decision bounds validation (no DB needed) ─────────────────────────────

def test_decision_simulate_negative_distance_returns_422():
    """Negative distance must be rejected with 422, not cause a 500."""
    token = officer_token()
    r = client.post(
        "/api/v1/decisions/simulate?village_id=PB-SNG-0142",
        json={"distance_km": -5},
        headers=auth(token),
    )
    assert r.status_code == 422


def test_decision_simulate_excessive_baling_cost_returns_422():
    """Baling cost above 2000 must be rejected with 422."""
    token = officer_token()
    r = client.post(
        "/api/v1/decisions/simulate?village_id=PB-SNG-0142",
        json={"baling_cost_per_tonne": 99999},
        headers=auth(token),
    )
    assert r.status_code == 422


def test_decision_simulate_valid_assumptions_accepted():
    """
    Valid assumptions should not cause a 422.
    If DB is unavailable a 404 or 500 is expected (no village data), not a 422.
    """
    token = officer_token()
    r = client.post(
        "/api/v1/decisions/simulate?village_id=PB-SNG-0142",
        json={"distance_km": 10, "baling_cost_per_tonne": 400},
        headers=auth(token),
    )
    assert r.status_code in (200, 404, 500), (
        f"Expected 200/404/500 for valid assumptions, got {r.status_code}: {r.text}"
    )
    if r.status_code == 200:
        d = r.json()
        # With distance_km=10 and default transport=12: break-even = 400 + 12*10 = 520
        assert d["break_even_price_per_tonne_inr"] == pytest.approx(520, abs=1)


# ── Notifications pagination bounds ──────────────────────────────────────

def test_notifications_limit_zero_returns_422():
    """limit=0 should be rejected (ge=1)."""
    r = client.get("/api/v1/notifications?limit=0", headers=auth(officer_token()))
    assert r.status_code == 422


def test_notifications_limit_above_max_returns_422():
    """limit=201 should be rejected (le=200)."""
    r = client.get("/api/v1/notifications?limit=201", headers=auth(officer_token()))
    assert r.status_code == 422


def test_notifications_negative_offset_returns_422():
    """offset=-1 should be rejected (ge=0)."""
    r = client.get("/api/v1/notifications?offset=-1", headers=auth(officer_token()))
    assert r.status_code == 422


def test_notifications_valid_pagination_accepted():
    """Valid pagination params should not cause a 422."""
    r = client.get("/api/v1/notifications?limit=100&offset=0",
                   headers=auth(officer_token()))
    assert r.status_code in (200, 500), (
        f"Expected 200 or 500 (no DB), got {r.status_code}: {r.text}"
    )


# ── make_schemas.py non-destructive ──────────────────────────────────────

def test_make_schemas_skips_existing_files(tmp_path, monkeypatch):
    """make_schemas.py must not overwrite an existing schema file by default."""
    import scripts.make_schemas as ms_module

    # Redirect SCHEMAS dir to tmp
    monkeypatch.setattr(ms_module, "SCHEMAS", tmp_path)

    # Pre-create one file with sentinel content
    sentinel = "# HAND_MAINTAINED_SENTINEL\n"
    (tmp_path / "common.py").write_text(sentinel, encoding="utf-8")

    ms_module.main(force=False)

    # Sentinel must still be intact
    content = (tmp_path / "common.py").read_text(encoding="utf-8")
    assert "HAND_MAINTAINED_SENTINEL" in content, (
        "make_schemas.py overwrote an existing file without --force"
    )


def test_make_schemas_force_overwrites(tmp_path, monkeypatch):
    """With --force, make_schemas.py should overwrite existing files."""
    import scripts.make_schemas as ms_module
    monkeypatch.setattr(ms_module, "SCHEMAS", tmp_path)

    (tmp_path / "common.py").write_text("# OLD\n", encoding="utf-8")
    ms_module.main(force=True)
    content = (tmp_path / "common.py").read_text(encoding="utf-8")
    assert "# OLD\n" not in content


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
    assert "2026-10-24" in msg


def test_template_fallback_bad_language():
    from app.notifier.templates import render_message
    msg = render_message("zh", "match_confirmed",
                         buyer_name="X", pickup_date="2026-10-24", price=1000)
    assert "X" in msg


def test_unknown_template():
    from app.notifier.templates import render_message
    msg = render_message("en", "nonexistent_template")
    assert "unknown template" in msg


# ── Notification idempotency (unit, no DB) ────────────────────────────────

def test_notification_idempotency_skips_duplicate(monkeypatch):
    """
    If _already_sent returns True, send_notification_for_match must skip
    without calling _log_to_db a second time.
    """
    from app.notifier import sender

    # Fake a row coming back from the DB
    class FakeRow(dict):
        """Dict subclass that also supports attribute access."""
        pass

    # Patch the main query to return one fake row
    fake_row = FakeRow({
        "match_id": "M1", "village_id": "V1", "pickup_date": "2026-10-24",
        "price_per_tonne_inr": 1500, "tonnes": 10,
        "buyer_name": "Buyer", "user_id": 2, "phone": "+91999",
        "language": "en",
    })

    class FakeMappings:
        def all(self): return [fake_row]

    class FakeResult:
        def mappings(self): return FakeMappings()

    class FakeConn:
        def execute(self, *a, **kw): return FakeResult()
        def __enter__(self): return self
        def __exit__(self, *a): pass

    class FakeEngine:
        def connect(self): return FakeConn()
        def begin(self):   return FakeConn()

    log_calls = []
    monkeypatch.setattr(sender, "engine", FakeEngine())
    monkeypatch.setattr(sender, "_log_to_db", lambda **kw: log_calls.append(kw))
    # _already_sent should return True for any call
    monkeypatch.setattr(sender, "_already_sent", lambda *a, **kw: True)

    result = sender.send_notification_for_match("M1")
    assert result == 0, "Expected 0 sends when already_sent=True"
    assert log_calls == [], "_log_to_db must not be called for duplicate"


# ── DB-dependent tests ────────────────────────────────────────────────────

@requires_db
def test_list_villages_officer():
    r = client.get("/api/v1/villages", headers=auth(officer_token()))
    assert r.status_code == 200
    villages = r.json()
    assert isinstance(villages, list)
    if villages:
        v = villages[0]
        assert "village_id" in v
        assert "centroid" in v
        assert v["centroid"]["type"] == "Point"


@requires_db
def test_farmer_scoped_to_own_village():
    token = farmer_token("PB-SNG-0142")
    r = client.get("/api/v1/villages", headers=auth(token))
    assert r.status_code == 200
    for v in r.json():
        assert v["village_id"] == "PB-SNG-0142"


@requires_db
def test_forecast_shape():
    token = officer_token()
    r = client.get("/api/v1/villages/PB-SNG-0142/forecast", headers=auth(token))
    assert r.status_code == 200
    f = r.json()
    assert "harvest" in f
    assert "expected_date" in f["harvest"]
    assert "straw" in f
    assert "expected_tonnes" in f["straw"]
    assert f["confidence"]["tag"] in ("LOW", "MEDIUM", "HIGH")


@requires_db
def test_decision_shape():
    token = officer_token()
    r = client.get("/api/v1/villages/PB-SNG-0142/decision", headers=auth(token))
    assert r.status_code == 200
    d = r.json()
    assert d["best_option"] in ("keep", "sell", "feed")
    assert "break_even_price_per_tonne_inr" in d
    assert "per_tonne_inr" in d
    assert "sell" in d["per_tonne_inr"]


@requires_db
def test_decision_simulate_with_db():
    token = officer_token()
    r = client.post(
        "/api/v1/decisions/simulate?village_id=PB-SNG-0142",
        json={"distance_km": 10, "baling_cost_per_tonne": 400},
        headers=auth(token),
    )
    assert r.status_code == 200
    d = r.json()
    # With distance_km=10 and default transport=12: break-even = 400 + 12*10 = 520
    assert d["break_even_price_per_tonne_inr"] == pytest.approx(520, abs=1)


@requires_db
def test_list_matches_shape():
    token = officer_token()
    r = client.get("/api/v1/matches", headers=auth(token))
    assert r.status_code == 200
    matches = r.json()
    assert isinstance(matches, list)
    if matches:
        m = matches[0]
        assert "match_id" in m
        assert "buyer" in m
        assert m["status"] in ("PROPOSED", "CONFIRMED", "COMPLETED", "CANCELLED")


@requires_db
def test_buyer_sees_only_own_matches():
    token = buyer_token("B-012")
    r = client.get("/api/v1/matches", headers=auth(token))
    assert r.status_code == 200
    for m in r.json():
        assert m["buyer"]["id"] == "B-012"


@requires_db
def test_match_confirm_wrong_owner_returns_403():
    """A farmer for village A cannot confirm a match belonging to village B."""
    # Get a proposed match for PB-SNG-0142
    token_officer = officer_token()
    all_matches = client.get("/api/v1/matches?status=PROPOSED",
                             headers=auth(token_officer)).json()
    if not all_matches:
        pytest.skip("No PROPOSED matches in test DB")

    # Find a match for a different village
    target = None
    for m in all_matches:
        if m["village_id"] != "PB-SNG-0142":
            target = m
            break
    if target is None:
        pytest.skip("All PROPOSED matches belong to PB-SNG-0142")

    farmer = farmer_token("PB-SNG-0142")
    r = client.post(f"/api/v1/matches/{target['match_id']}/confirm",
                    headers=auth(farmer))
    assert r.status_code == 403


@requires_db
def test_match_confirm_wrong_status_returns_409():
    """Cannot confirm a match that is already CONFIRMED or CANCELLED."""
    token = officer_token()
    confirmed = client.get("/api/v1/matches?status=CONFIRMED",
                           headers=auth(token)).json()
    if not confirmed:
        pytest.skip("No CONFIRMED matches in test DB")
    r = client.post(f"/api/v1/matches/{confirmed[0]['match_id']}/confirm",
                    headers=auth(token))
    assert r.status_code == 409
    assert r.json()["detail"]["error"]["code"] == "WRONG_STATUS"


@requires_db
def test_burn_events_shape():
    token = officer_token()
    r = client.get("/api/v1/burn-events", headers=auth(token))
    assert r.status_code == 200
    burns = r.json()
    if burns:
        b = burns[0]
        assert "event_id" in b
        assert b["confidence"] in ("LOW", "MEDIUM", "HIGH")
        assert b["location"]["type"] == "Point"


@requires_db
def test_job_trigger_and_poll():
    """POST /jobs/run returns a run_id; GET /jobs/{run_id} returns a status."""
    token = officer_token()
    r = client.post("/api/v1/jobs/run",
                    json={"job": "daily_refresh"},
                    headers=auth(token))
    assert r.status_code == 202
    body = r.json()
    assert "run_id" in body
    assert body["job"] == "daily_refresh"
    assert body["status"] in ("queued", "running", "done", "failed")

    run_id = body["run_id"]
    r2 = client.get(f"/api/v1/jobs/{run_id}", headers=auth(token))
    assert r2.status_code == 200
    assert r2.json()["run_id"] == run_id


@requires_db
def test_job_unknown_name_returns_error():
    """An unknown job name must return an error, not a 500."""
    token = officer_token()
    r = client.post("/api/v1/jobs/run",
                    json={"job": "nonexistent_job"},
                    headers=auth(token))
    # Should be 400 (bad request) or 422, not 200 or 500
    assert r.status_code in (400, 422)


@requires_db
def test_notification_failure_logged(monkeypatch):
    """
    When Twilio fails, the notification must still be persisted with status='failed'.
    """
    from app.notifier import sender
    from app.core.config import settings

    # Switch to Twilio channel
    monkeypatch.setattr(settings, "NOTIFIER_CHANNEL", "twilio_sms")
    # Make _send_twilio always fail
    monkeypatch.setattr(sender, "_send_twilio", lambda *a, **kw: None)

    # Need a real match_id from the DB; use the first PROPOSED one
    token = officer_token()
    matches = client.get("/api/v1/matches?status=PROPOSED",
                         headers=auth(token)).json()
    if not matches:
        pytest.skip("No PROPOSED matches in test DB")

    mid = matches[0]["match_id"]
    # Reset idempotency for this match (delete existing notifs) – best-effort
    try:
        from app.core.db import engine
        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM notifications WHERE match_id = :mid"),
                         {"mid": mid})
    except Exception:
        pass

    sender.send_notification_for_match(mid)

    # Check that a 'failed' row was persisted
    from app.core.db import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT status FROM notifications WHERE match_id=:mid ORDER BY sent_at DESC LIMIT 1"),
            {"mid": mid},
        ).first()
    assert row is not None, "No notification row was written"
    assert row[0] == "failed", f"Expected status='failed', got '{row[0]}'"


@requires_db
def test_demo_run_shape():
    r = client.post("/api/v1/demo/run?village_id=PB-SNG-0142")
    assert r.status_code == 200
    body = r.json()
    assert "steps" in body
    assert isinstance(body["steps"], list)
    step_names = [s["step"] for s in body["steps"]]
    assert "forecast" in step_names
    assert "decision" in step_names
    assert "match" in step_names
    assert "notification" in step_names
    assert "burn_check" in step_names
