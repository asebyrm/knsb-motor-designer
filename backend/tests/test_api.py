"""API happy-path + auth + validation (Section 13.2 'API' bullet)."""

from __future__ import annotations

import time


def _register(client, email="a@b.com", username="user1", password="longpassword123"):
    r = client.post("/api/auth/register", json={
        "email": email, "username": username, "password": password, "locale": "en"})
    assert r.status_code == 201, r.text
    return r.json()


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_health(api_client):
    assert api_client.get("/api/health").json() == {"status": "ok"}


def test_catalog_lists_everything_the_ui_needs(api_client):
    cat = api_client.get("/api/catalog").json()
    assert "knsb" in {p["file"] for p in cat["propellants"]}
    assert "kndx" in {p["file"] for p in cat["propellants"]}
    assert {"bates", "tubular", "endburner"} <= set(cat["grains"])
    assert any(m["id"] == "pa12" for m in cat["case_materials"])
    assert cat["warning_codes"] and all("i18n_key" in w for w in cat["warning_codes"])


def test_simulate_without_login(api_client, sample_design):
    """Acceptance 1: a BATES KNSB motor simulates with no auth."""
    r = api_client.post("/api/simulate", json={"design": sample_design})
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["designation"]
    assert body["summary"]["total_impulse"] > 0
    assert len(body["series"]["time_s"]) <= 500
    assert body["is_safe"] is (not body["export_locked"])


def test_simulate_invalid_design_returns_422(api_client):
    r = api_client.post("/api/simulate", json={"design": {"grain": {"type": "bates",
        "outer_diameter": 0.02, "core_diameter": 0.05, "segment_length": 0.1}}})
    assert r.status_code == 422


def test_first_user_is_admin_second_is_not(api_client):
    a = _register(api_client, "admin@x.com", "admin")
    b = _register(api_client, "b@x.com", "bob")
    assert a["user"]["role"] == "admin"
    assert b["user"]["role"] == "user"


def test_weak_password_rejected(api_client):
    # too short
    short = api_client.post("/api/auth/register", json={
        "email": "c@x.com", "username": "carol", "password": "short1", "locale": "en"})
    assert short.status_code == 422
    # long enough but a common password
    common = api_client.post("/api/auth/register", json={
        "email": "c2@x.com", "username": "carol2", "password": "password123", "locale": "en"})
    assert common.status_code == 422


def test_design_save_list_share_fork(api_client, sample_design):
    tok = _register(api_client)["access_token"]
    h = _auth_header(tok)
    r = api_client.post("/api/designs", headers=h, json={
        "name": "M1", "config_json": sample_design, "visibility": "unlisted"})
    assert r.status_code == 201
    d = r.json()
    assert d["slug"]

    # public read by slug, no auth
    pub = api_client.get(f"/api/d/{d['slug']}")
    assert pub.status_code == 200 and pub.json()["name"] == "M1"

    # second user forks it
    tok2 = _register(api_client, "d@x.com", "dave")["access_token"]
    fk = api_client.post(f"/api/designs/{d['id']}/fork", headers=_auth_header(tok2))
    assert fk.status_code == 201 and fk.json()["fork_of_id"] == d["id"]

    mine = api_client.get("/api/designs", headers=h).json()
    assert len(mine) == 1


def test_designs_require_auth(api_client, sample_design):
    assert api_client.get("/api/designs").status_code == 401
    assert api_client.post("/api/designs", json={
        "name": "x", "config_json": sample_design}).status_code == 401


def test_export_endpoint_and_lock(api_client, sample_design):
    ok = api_client.post("/api/export", json={"design": sample_design, "fmt": "eng"})
    assert ok.status_code == 200
    assert "attachment" in ok.headers["content-disposition"]

    unsafe = {**sample_design, "case": {**sample_design["case"], "material_id": "pla",
              "wall_thickness": 0.0012, "print_method": "fdm"}, "meop_bar": 20}
    locked = api_client.post("/api/export", json={"design": unsafe, "fmt": "eng"})
    assert locked.status_code == 423  # acceptance 6
    forced = api_client.post("/api/export",
                             json={"design": unsafe, "fmt": "eng", "accept_risk": True})
    assert forced.status_code == 200


def test_export_filename_with_turkish_characters(api_client, sample_design):
    """A design name with Turkish letters (İ, ş, ğ...) must not crash the
    Content-Disposition header - it's outside latin-1, so it has to be
    transliterated for `filename=` and UTF-8 percent-encoded for `filename*=`
    rather than passed through raw (regression: was a 500)."""
    for fmt in ("pdf", "eng", "csv", "json"):
        design = {**sample_design, "name": "İTÜ PARS Referans Motoru"}
        r = api_client.post("/api/export", json={"design": design, "fmt": fmt,
                                                   "accept_risk": True})
        assert r.status_code == 200, r.text
        cd = r.headers["content-disposition"]
        assert "attachment" in cd
        assert "İ" not in cd.split("filename*=")[0]  # ascii-safe fallback stays ascii
        assert "filename*=UTF-8''" in cd


def test_mission_job_lifecycle(api_client):
    r = api_client.post("/api/mission", json={
        "dry_mass": 6.0, "body_diameter": 0.10, "target_apogee": 800.0,
        "meop_bar": 45.0, "time_budget_s": 6.0})
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    for _ in range(60):
        s = api_client.get(f"/api/jobs/{job_id}").json()
        if s["status"] in ("done", "failed"):
            break
        time.sleep(0.4)
    assert s["status"] == "done"
    result = s["result"]
    assert "feasible" in result
    if not result["feasible"]:
        assert result["binding_constraint"]  # acceptance 5: never empty
    assert api_client.get("/api/jobs/does-not-exist").status_code == 404


def test_login_rate_limited(api_client):
    _register(api_client)
    codes = [api_client.post("/api/auth/login", json={
        "email_or_username": "a@b.com", "password": "wrong"}).status_code for _ in range(8)]
    assert 429 in codes
    assert codes.count(401) <= 5


def test_admin_endpoints_guarded(api_client):
    admin_tok = _register(api_client, "admin@x.com", "admin")["access_token"]
    user_tok = _register(api_client, "u@x.com", "user2")["access_token"]
    assert api_client.get("/api/admin/stats", headers=_auth_header(user_tok)).status_code == 403
    stats = api_client.get("/api/admin/stats", headers=_auth_header(admin_tok))
    assert stats.status_code == 200
    body = stats.json()
    assert body["total_users"] == 2
    assert "mission_jobs_memory" in body
    assert api_client.get("/api/admin/health", headers=_auth_header(admin_tok)).status_code == 200
