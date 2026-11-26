"""
Comprehensive integration and unit tests for Residue Compass API.

Test DB safety:
  - When TEST_DATABASE_URL is set, DATABASE_URL is overridden BEFORE importing
    any app module so tests never accidentally connect to the default local DB.
  - A guard refuses to run DB tests if the target database name does not
    contain 'test' (preventing accidental writes to dev/prod databases).
"""
import concurrent.futures
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

# ── Environment bootstrap (MUST happen before importing app.*) ────────────
TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "").strip()
if TEST_DB_URL:
    db_name = urlparse(TEST_DB_URL).path.lstrip("/").lower()
    if "test" not in db_name:
        raise RuntimeError(
            f"Refusing to run DB tests against non-test database '{db_name}'. "
            "TEST_DATABASE_URL database name must contain 'test'."
        )
    os.environ["DATABASE_URL"] = TEST_DB_URL
else:
    os.environ.setdefault(
        "DATABASE_URL", "postgresql://rc:rc_pass@127.0.0.1:5432/residue_test"
    )

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("SECRET_KEY", "test_secret_key_32_chars_long_xxx")
os.environ.setdefault("CORS_ORIGINS", "https://test.residuecompass.local")

from app.main import app  # noqa: E402
from app.core.security import create_access_token  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)

HAS_DB = bool(TEST_DB_URL)
requires_db = pytest.mark.skipif(not HAS_DB, reason="TEST_DATABASE_URL not set")


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_test_db():
    """Apply Alembic migrations and demo seed once per test session when DB is active."""
    if not HAS_DB:
        yield
        return
    from scripts.init_db import main as init_db_main
    from scripts.seed_demo import main as seed_demo_main
    init_db_main()
    seed_demo_main()
    yield


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
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert "demo_mode" in body


def test_health_returns_503_when_db_down(monkeypatch):
    """Health must return 503 when the database is unreachable."""
    from sqlalchemy import create_engine
    import app.main as main_module

    bad_engine = create_engine(
        "postgresql+psycopg://x:x@127.0.0.1:1/nonexistent",
        connect_args={"connect_timeout": 1},
    )
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
        ("POST", "/api/v1/demo/run"),
        ("POST", "/api/v1/demo/reset"),
    ]:
        r = client.request(method, path)
        assert r.status_code == 401, f"{method} {path} returned {r.status_code}"
        assert "error" in r.json()["detail"]


def test_wrong_role_returns_403():
    token = buyer_token()
    assert client.post(
        "/api/v1/jobs/run", json={"job": "daily_refresh"}, headers=auth(token)
    ).status_code == 403
    assert client.post("/api/v1/demo/run", headers=auth(token)).status_code == 403
    assert client.post("/api/v1/demo/reset", headers=auth(token)).status_code == 403
    assert client.post(
        "/api/v1/auth/register",
        json={"name": "Fake", "phone": "+919999999999", "password": "password123",
              "role": "farmer", "village_id": "PB-SNG-0142"},
        headers=auth(token),
    ).status_code == 403


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


# ── Security & CORS config ────────────────────────────────────────────────

def test_security_config_fails_closed(monkeypatch):
    from app.core import config
    monkeypatch.setattr(config.settings, "SECRET_KEY", "change_me")
    with pytest.raises(RuntimeError):
        config.validate_security_config()

    monkeypatch.setattr(config.settings, "SECRET_KEY", "short")
    with pytest.raises(RuntimeError):
        config.validate_security_config()


def test_cors_enforced_outside_demo_mode(monkeypatch):
    from app.core import config
    monkeypatch.setattr(config.settings, "SECRET_KEY", "a" * 32)
    monkeypatch.setattr(config.settings, "DEMO_MODE", False)

    monkeypatch.setattr(config.settings, "CORS_ORIGINS", "*")
    with pytest.raises(RuntimeError):
        config.validate_security_config()

    monkeypatch.setattr(config.settings, "CORS_ORIGINS", "")
    with pytest.raises(RuntimeError):
        config.validate_security_config()

    monkeypatch.setattr(config.settings, "CORS_ORIGINS", "https://app.residuecompass.in")
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
    r_run = client.post(
        "/api/v1/demo/run?village_id=PB-SNG-0142", headers=auth(officer_token())
    )
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


# ── Decision bounds validation (no DB needed) ─────────────────────────────

def test_decision_simulate_negative_distance_returns_422():
    r = client.post(
        "/api/v1/decisions/simulate?village_id=PB-SNG-0142",
        json={"distance_km": -5},
        headers=auth(officer_token()),
    )
    assert r.status_code == 422


def test_decision_simulate_excessive_baling_cost_returns_422():
    r = client.post(
        "/api/v1/decisions/simulate?village_id=PB-SNG-0142",
        json={"baling_cost_per_tonne": 99999},
        headers=auth(officer_token()),
    )
    assert r.status_code == 422


# ── Notifications pagination bounds ──────────────────────────────────────

def test_notifications_limit_zero_returns_422():
    assert client.get("/api/v1/notifications?limit=0", headers=auth(officer_token())).status_code == 422


def test_notifications_limit_above_max_returns_422():
    assert client.get("/api/v1/notifications?limit=201", headers=auth(officer_token())).status_code == 422


def test_notifications_negative_offset_returns_422():
    assert client.get("/api/v1/notifications?offset=-1", headers=auth(officer_token())).status_code == 422


# ── make_schemas.py non-destructive ──────────────────────────────────────

def test_make_schemas_skips_existing_files(tmp_path, monkeypatch):
    import scripts.make_schemas as ms_module
    monkeypatch.setattr(ms_module, "SCHEMAS", tmp_path)
    sentinel = "# HAND_MAINTAINED_SENTINEL\n"
    (tmp_path / "common.py").write_text(sentinel, encoding="utf-8")
    ms_module.main(force=False)
    assert "HAND_MAINTAINED_SENTINEL" in (tmp_path / "common.py").read_text(encoding="utf-8")


def test_make_schemas_force_overwrites(tmp_path, monkeypatch):
    import scripts.make_schemas as ms_module
    monkeypatch.setattr(ms_module, "SCHEMAS", tmp_path)
    (tmp_path / "common.py").write_text("# OLD\n", encoding="utf-8")
    ms_module.main(force=True)
    assert "# OLD\n" not in (tmp_path / "common.py").read_text(encoding="utf-8")


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


# ── Jobs schema & unknown run_id ──────────────────────────────────────────

def test_job_unknown_id_returns_404():
    r = client.get("/api/v1/jobs/does-not-exist-uuid", headers=auth(officer_token()))
    assert r.status_code == 404


def test_job_celery_states_schema_valid():
    from types import SimpleNamespace
    from app.api.v1.jobs import _celery_state_to_schema
    from app.schemas.job import JobStatusResponse

    for celery_state, expected in [
        ("PENDING", "queued"),
        ("STARTED", "running"),
        ("RETRY",   "running"),
        ("SUCCESS", "done"),
        ("FAILURE", "failed"),
        ("REVOKED", "cancelled"),
    ]:
        meta = {"job": "daily_refresh", "started_at": "2026-10-12T06:00:00+00:00", "finished_at": None}
        res = SimpleNamespace(id="task-123", state=celery_state, result={"ok": True} if celery_state == "SUCCESS" else "err")
        mapped = _celery_state_to_schema(res, meta)
        validated = JobStatusResponse(**mapped)
        assert validated.status == expected
        assert validated.job == "daily_refresh"
        assert validated.started_at is not None


# ── DB-dependent tests ────────────────────────────────────────────────────

@requires_db
def test_not_found_envelope():
    r = client.get("/api/v1/villages/NONEXISTENT", headers=auth(officer_token()))
    assert r.status_code == 404
    body = r.json()
    assert "error" in body["detail"]
    assert "code" in body["detail"]["error"]


@requires_db
def test_audit_log_writes_to_at_column():
    """Verify log_action persists a real row into audit_log using the `at` column."""
    from sqlalchemy import text
    from app.core.db import engine
    from app.services.audit import log_action

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM audit_log WHERE action = 'test_audit_event'"))

    log_action(
        user_id=None,
        action="test_audit_event",
        entity="test",
        entity_id="T-1",
        details={"source": "pytest"},
    )

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT action, entity, entity_id, at FROM audit_log WHERE action = 'test_audit_event' LIMIT 1")
        ).mappings().first()

    assert row is not None, "audit_log row was not written"
    assert row["entity"] == "test"
    assert row["entity_id"] == "T-1"
    assert row["at"] is not None


@requires_db
def test_seed_demo_works_on_fresh_database():
    """
    Truncate all tables (including reference tables districts/villages/buyers/users)
    and verify seed_demo.main() succeeds on a completely empty database.
    """
    from sqlalchemy import text
    from app.core.db import engine
    from scripts.seed_demo import main as seed_demo_main

    with engine.begin() as conn:
        conn.execute(text(
            "TRUNCATE notifications, audit_log, matches, burn_events, decisions, forecasts, "
            "users, trucks, machines, buyers, villages, districts RESTART IDENTITY CASCADE"
        ))

    seed_demo_main()

    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM villages")).scalar() >= 3
        assert conn.execute(text("SELECT COUNT(*) FROM buyers")).scalar() >= 2
        assert conn.execute(text("SELECT COUNT(*) FROM users")).scalar() >= 3
        assert conn.execute(text("SELECT COUNT(*) FROM forecasts")).scalar() >= 3
        assert conn.execute(text("SELECT COUNT(*) FROM matches")).scalar() >= 1


@requires_db
def test_alembic_upgrade_from_existing_db():
    """Verify init_db.main() is idempotent and leaves alembic_version at head."""
    from sqlalchemy import text
    from app.core.db import engine
    from scripts.init_db import main as init_db_main

    init_db_main()
    with engine.connect() as conn:
        ver = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert ver == "0004_notification_idempotency"


@requires_db
def test_list_villages_officer():
    r = client.get("/api/v1/villages", headers=auth(officer_token()))
    assert r.status_code == 200
    villages = r.json()
    assert isinstance(villages, list) and len(villages) > 0
    v = villages[0]
    assert "village_id" in v
    assert v["centroid"]["type"] == "Point"


@requires_db
def test_farmer_scoped_to_own_village():
    r = client.get("/api/v1/villages", headers=auth(farmer_token("PB-SNG-0142")))
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["village_id"] == "PB-SNG-0142"


@requires_db
def test_forecast_shape():
    r = client.get("/api/v1/villages/PB-SNG-0142/forecast", headers=auth(officer_token()))
    assert r.status_code == 200
    f = r.json()
    assert "harvest" in f and "expected_date" in f["harvest"]
    assert "straw" in f and "expected_tonnes" in f["straw"]
    assert f["confidence"]["tag"] in ("LOW", "MEDIUM", "HIGH")


@requires_db
def test_decision_shape():
    r = client.get("/api/v1/villages/PB-SNG-0142/decision", headers=auth(officer_token()))
    assert r.status_code == 200
    d = r.json()
    assert d["best_option"] in ("keep", "sell", "feed")
    assert "break_even_price_per_tonne_inr" in d
    assert "sell" in d["per_tonne_inr"]


@requires_db
def test_decision_simulate_recalculates_best_option_and_diesel():
    token = officer_token()
    # Low costs -> sell should be very profitable
    r_low = client.post(
        "/api/v1/decisions/simulate?village_id=PB-SNG-0142",
        json={"distance_km": 10, "baling_cost_per_tonne": 400},
        headers=auth(token),
    )
    assert r_low.status_code == 200
    d_low = r_low.json()
    assert d_low["break_even_price_per_tonne_inr"] == pytest.approx(520, abs=1)
    assert d_low["price_range_inr"]["low"] <= d_low["price_range_inr"]["high"]

    # Very high baling cost + diesel spike -> sell net drops, best_option flips away from sell
    r_high = client.post(
        "/api/v1/decisions/simulate?village_id=PB-SNG-0142",
        json={"distance_km": 150, "baling_cost_per_tonne": 1800, "diesel_price_per_litre": 180},
        headers=auth(token),
    )
    assert r_high.status_code == 200
    d_high = r_high.json()
    assert d_high["assumptions"]["transport_cost_per_tonne_per_km"] > 12
    assert d_high["best_option"] != "sell"


@requires_db
def test_list_matches_shape():
    r = client.get("/api/v1/matches", headers=auth(officer_token()))
    assert r.status_code == 200
    matches = r.json()
    assert isinstance(matches, list) and len(matches) > 0
    assert matches[0]["status"] in ("PROPOSED", "CONFIRMED", "COMPLETED", "CANCELLED")


@requires_db
def test_buyer_sees_only_own_matches():
    r = client.get("/api/v1/matches", headers=auth(buyer_token("B-012")))
    assert r.status_code == 200
    for m in r.json():
        assert m["buyer"]["id"] == "B-012"


@requires_db
def test_match_confirm_wrong_owner_and_atomic_race():
    token_officer = officer_token()
    all_matches = client.get("/api/v1/matches?status=PROPOSED", headers=auth(token_officer)).json()
    if not all_matches:
        pytest.skip("No PROPOSED matches in test DB")

    # Wrong owner check
    other = next((m for m in all_matches if m["village_id"] != "PB-SNG-0142"), None)
    if other:
        assert client.post(
            f"/api/v1/matches/{other['match_id']}/confirm",
            headers=auth(farmer_token("PB-SNG-0142")),
        ).status_code == 403

    # Atomic race: confirm same PROPOSED match twice concurrently -> one 200, one 409
    target_id = all_matches[0]["match_id"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(client.post, f"/api/v1/matches/{target_id}/confirm", headers=auth(token_officer))
        f2 = pool.submit(client.post, f"/api/v1/matches/{target_id}/confirm", headers=auth(token_officer))
        codes = sorted([f1.result().status_code, f2.result().status_code])
    assert codes == [200, 409]


@requires_db
def test_burn_events_shape():
    r = client.get("/api/v1/burn-events", headers=auth(officer_token()))
    assert r.status_code == 200
    burns = r.json()
    if burns:
        assert burns[0]["confidence"] in ("LOW", "MEDIUM", "HIGH")
        assert burns[0]["location"]["type"] == "Point"


@requires_db
def test_job_trigger_and_poll():
    token = officer_token()
    r = client.post("/api/v1/jobs/run", json={"job": "daily_refresh"}, headers=auth(token))
    assert r.status_code == 202
    body = r.json()
    assert body["job"] == "daily_refresh"
    assert body["status"] in ("queued", "running", "done", "failed", "cancelled")

    r2 = client.get(f"/api/v1/jobs/{body['run_id']}", headers=auth(token))
    assert r2.status_code == 200
    assert r2.json()["run_id"] == body["run_id"]


@requires_db
def test_notification_concurrency_safe_claim():
    """Concurrent calls to send_notification_for_match must only create 1 sent row."""
    from sqlalchemy import text
    from app.core.db import engine
    from app.notifier.sender import send_notification_for_match

    matches = client.get("/api/v1/matches", headers=auth(officer_token())).json()
    mid = next(m["match_id"] for m in matches if m["village_id"] == "PB-SNG-0142")

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM notifications WHERE match_id = :mid"), {"mid": mid})

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: send_notification_for_match(mid, channel_override="log"), range(4)))

    assert sum(results) == 1
    with engine.connect() as conn:
        sent_count = conn.execute(
            text("SELECT COUNT(*) FROM notifications WHERE match_id = :mid AND status = 'sent'"),
            {"mid": mid},
        ).scalar()
    assert sent_count == 1


@requires_db
def test_notification_missing_recipient_marked_failed():
    """If a village has no farmer user, notification must be logged as 'failed', never 'sent'."""
    from sqlalchemy import text
    from app.core.db import engine
    from app.notifier.sender import send_notification_for_match

    matches = client.get("/api/v1/matches", headers=auth(officer_token())).json()
    # PB-SNG-0187 or PB-TTN-0031 has no demo farmer user
    no_farmer = next((m for m in matches if m["village_id"] != "PB-SNG-0142"), None)
    if not no_farmer:
        pytest.skip("No match for village without farmer user")

    mid = no_farmer["match_id"]
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM notifications WHERE match_id = :mid"), {"mid": mid})

    sent = send_notification_for_match(mid, channel_override="log")
    assert sent == 0

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT status FROM notifications WHERE match_id = :mid ORDER BY sent_at DESC LIMIT 1"),
            {"mid": mid},
        ).first()
    assert row is not None and row[0] == "failed"


@requires_db
def test_notification_failure_logged(monkeypatch):
    from sqlalchemy import text
    from app.core.config import settings
    from app.core.db import engine
    from app.notifier import sender

    monkeypatch.setattr(settings, "NOTIFIER_CHANNEL", "twilio_sms")
    monkeypatch.setattr(sender, "_send_twilio", lambda *a, **kw: None)

    matches = client.get("/api/v1/matches", headers=auth(officer_token())).json()
    mid = next(m["match_id"] for m in matches if m["village_id"] == "PB-SNG-0142")

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM notifications WHERE match_id = :mid"), {"mid": mid})

    sent = sender.send_notification_for_match(mid)
    assert sent == 0

    with engine.connect() as conn:
        status = conn.execute(
            text("SELECT status FROM notifications WHERE match_id = :mid ORDER BY sent_at DESC LIMIT 1"),
            {"mid": mid},
        ).scalar()
    assert status == "failed"


@requires_db
def test_demo_run_surfaces_notification_failure_and_uses_proposed_template(monkeypatch):
    """Ensure demo/run uses match_proposed for PROPOSED match and surfaces errors."""
    from app.api.v1 import demo as demo_module
    from scripts.seed_demo import main as seed_demo_main

    seed_demo_main()

    # Force notification failure
    def _boom(*_a, **_kw):
        raise RuntimeError("simulated provider outage")

    monkeypatch.setattr(demo_module, "send_notification_for_match", _boom)
    r = client.post("/api/v1/demo/run?village_id=PB-SNG-0142", headers=auth(officer_token()))
    assert r.status_code == 200
    body = r.json()
    notif_step = next(s for s in body["steps"] if s["step"] == "notification")
    assert notif_step["status"] == "failed"
    assert "simulated provider outage" in notif_step["detail"]
    # Should use match_proposed wording (YES reply), not match_confirmed
    assert "YES" in body["notification_body"]
