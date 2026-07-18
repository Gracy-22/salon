"""P0 owner dashboard + no-show tracker regression tests."""

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests


def _read_backend_url() -> str:
    # Prefer env var; fallback to frontend/.env key per project convention
    url = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if url:
        return url.rstrip("/")

    env_path = "/app/frontend/.env"
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    _, value = line.split("=", 1)
                    value = value.strip()
                    if value:
                        return value.rstrip("/")

    raise RuntimeError("REACT_APP_BACKEND_URL is required")


BASE_URL = _read_backend_url()
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def api_client():
    """Shared HTTP client for API regression tests."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="session")
def owner_headers(api_client):
    res = api_client.post(f"{API}/owner/login", json={"pin": "9999"}, timeout=20)
    assert res.status_code == 200
    token = res.json()["token"]
    assert token and token != "owner"
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def service_and_stylist(api_client):
    """Load one valid service/stylist pair for booking setup."""
    services = api_client.get(f"{API}/services", timeout=20)
    assert services.status_code == 200
    service = services.json()[0]

    stylists = api_client.get(f"{API}/stylists", params={"service_id": service["id"]}, timeout=20)
    assert stylists.status_code == 200
    stylist = stylists.json()[0]
    return service, stylist


def _future_date(days: int = 2) -> str:
    return (datetime.now(timezone.utc).date() + timedelta(days=days)).isoformat()


def _create_booking(api_client, service: dict, stylist: dict, phone: str, optin: bool = True) -> dict:
    date_str = None
    slot = None
    for offset in range(2, 45):
        candidate_date = _future_date(offset)
        res = api_client.get(
            f"{API}/availability",
            params={"stylist_id": stylist["id"], "service_id": service["id"], "date": candidate_date},
            timeout=20,
        )
        assert res.status_code == 200
        slots = [s for s in res.json().get("slots", []) if s.get("available")]
        if slots:
            date_str = candidate_date
            slot = slots[0]
            break
    assert date_str and slot, "No available slot found in the next 45 days"
    payload = {
        "service_id": service["id"],
        "stylist_id": stylist["id"],
        "date": date_str,
        "start_time": slot["start_time"],
        "customer_name": f"TEST_OWNER_{uuid.uuid4().hex[:6]}",
        "customer_phone": phone,
        "notes": "P0 owner dashboard regression",
        "whatsapp_optin": optin,
    }
    res = api_client.post(f"{API}/bookings", json=payload, timeout=20)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["booking"]["id"]
    assert data["booking"]["customer_phone"] == phone
    return data["booking"]


# Owner auth and dashboard API sanity
def test_owner_login_success(api_client):
    res = api_client.post(f"{API}/owner/login", json={"pin": "9999"}, timeout=20)
    assert res.status_code == 200
    body = res.json()
    assert body["token"]
    assert body["token"] != "owner"
    assert body["token"].count(".") == 2
    assert body["name"] == "Maison Aurelle"


def test_owner_endpoints_require_auth(api_client):
    date_str = datetime.now(timezone.utc).date().isoformat()
    bookings_res = api_client.get(f"{API}/owner/bookings", params={"date": date_str}, timeout=20)
    assert bookings_res.status_code == 401

    noshow_res = api_client.get(f"{API}/owner/no-shows", timeout=20)
    assert noshow_res.status_code == 401

    insights_res = api_client.get(f"{API}/owner/revenue-insights", params={"days": 30}, timeout=20)
    assert insights_res.status_code == 401

    update_res = api_client.patch(
        f"{API}/owner/bookings/non-existent-booking/status",
        json={"status": "done"},
        timeout=20,
    )
    assert update_res.status_code == 401


# Daily book status changes through owner endpoint
def test_owner_daily_book_mark_done(api_client, service_and_stylist, owner_headers):
    service, stylist = service_and_stylist
    booking = _create_booking(api_client, service, stylist, phone="+919990000001", optin=True)

    update = api_client.patch(
        f"{API}/owner/bookings/{booking['id']}/status",
        json={"status": "done"},
        headers=owner_headers,
        timeout=20,
    )
    assert update.status_code == 200
    assert update.json()["booking"]["status"] == "done"

    fetched = api_client.get(f"{API}/bookings/{booking['id']}", timeout=20)
    assert fetched.status_code == 200
    assert fetched.json()["booking"]["status"] == "done"


# No-show metadata behavior for whatsapp opt-in / opt-out
def test_owner_no_show_followup_metadata_optin_true(api_client, service_and_stylist, owner_headers):
    service, stylist = service_and_stylist
    booking = _create_booking(api_client, service, stylist, phone="+919990000002", optin=True)

    update = api_client.patch(
        f"{API}/owner/bookings/{booking['id']}/status",
        json={"status": "no_show"},
        headers=owner_headers,
        timeout=20,
    )
    assert update.status_code == 200
    b = update.json()["booking"]
    assert b["status"] == "no_show"
    assert "no_show_marked_at" in b
    assert b.get("no_show_followup_status") in {"sent", "failed", "skipped"}


def test_owner_no_show_followup_skipped_when_optout(api_client, service_and_stylist, owner_headers):
    service, stylist = service_and_stylist
    booking = _create_booking(api_client, service, stylist, phone="+919990000003", optin=False)

    update = api_client.patch(
        f"{API}/owner/bookings/{booking['id']}/status",
        json={"status": "no_show"},
        headers=owner_headers,
        timeout=20,
    )
    assert update.status_code == 200
    b = update.json()["booking"]
    assert b["status"] == "no_show"
    assert "no_show_marked_at" in b
    assert "no_show_followup_status" not in b


# Monthly no-show report + repeat flag (3+ lifetime no-shows)
def test_owner_no_show_report_includes_repeat_flag(api_client, service_and_stylist, owner_headers):
    service, stylist = service_and_stylist
    repeat_phone = "+919990000099"
    created = []

    for _ in range(3):
        b = _create_booking(api_client, service, stylist, phone=repeat_phone, optin=True)
        created.append(b)
        mark = api_client.patch(
            f"{API}/owner/bookings/{b['id']}/status",
            json={"status": "no_show"},
            headers=owner_headers,
            timeout=20,
        )
        assert mark.status_code == 200

    month = created[0]["date"][:7]
    report = api_client.get(f"{API}/owner/no-shows", params={"month": month}, headers=owner_headers, timeout=20)
    assert report.status_code == 200
    data = report.json()
    assert "no_show_rate" in data
    assert isinstance(data["no_shows"], list)

    matches = [r for r in data["no_shows"] if r.get("customer_phone") == repeat_phone]
    assert len(matches) >= 3
    assert any(r.get("repeat_no_show") is True for r in matches)
    sample = matches[0]
    assert sample.get("service", {}).get("name")
    assert sample.get("stylist", {}).get("name")


# Owner insights aggregation API presence and structure
def test_owner_insights_kpis_and_breakdowns(api_client, owner_headers):
    res = api_client.get(f"{API}/owner/revenue-insights", params={"days": 30}, headers=owner_headers, timeout=20)
    assert res.status_code == 200
    body = res.json()
    assert "kpis" in body
    assert "today_revenue" in body["kpis"]
    assert "week_revenue" in body["kpis"]
    assert "month_revenue" in body["kpis"]
    assert "average_booking_value" in body["kpis"]
    assert isinstance(body.get("revenue_per_stylist"), list)
    assert isinstance(body.get("revenue_per_service"), list)
    assert len(body.get("revenue_by_weekday", [])) == 7


# Regression: stylist status endpoint still supports no_show updates
def test_stylist_endpoint_can_mark_no_show(api_client, service_and_stylist):
    service, stylist = service_and_stylist
    booking = _create_booking(api_client, service, stylist, phone="+919990000004", optin=True)

    res = api_client.patch(
        f"{API}/stylist/{stylist['id']}/bookings/{booking['id']}/status",
        json={"status": "no_show"},
        timeout=20,
    )
    assert res.status_code == 200
    b = res.json()["booking"]
    assert b["status"] == "no_show"
