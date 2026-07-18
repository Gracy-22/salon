"""Stylist portal scheduling + break management regression tests."""

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    pytest.skip("REACT_APP_BACKEND_URL is required for public endpoint testing", allow_module_level=True)

API = f"{BASE_URL.rstrip('/')}/api"


@pytest.fixture(scope="session")
def api_client():
    """Shared HTTP client for stylist portal API tests."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="session")
def service_and_stylist(api_client):
    """Load Elena + one long-duration service for booking/block tests."""
    services_res = api_client.get(f"{API}/services", timeout=20)
    assert services_res.status_code == 200
    services = services_res.json()
    long_service = next((s for s in services if s.get("duration_min", 0) > 30), None)
    assert long_service, "Expected at least one >30 min service"

    stylist_id = "stylist-elena"
    stylists_res = api_client.get(f"{API}/stylists", params={"service_id": long_service["id"]}, timeout=20)
    assert stylists_res.status_code == 200
    stylist_ids = {s["id"] for s in stylists_res.json()}
    assert stylist_id in stylist_ids
    return long_service, stylist_id


@pytest.fixture
def cleanup_created_entities(api_client):
    """Track and cleanup test-created blocks, recurring blocks, and bookings."""
    created = {"blocks": [], "recurring_blocks": [], "bookings": [], "stylist_id": "stylist-elena"}
    yield created
    for block_id in created["blocks"]:
        api_client.delete(f"{API}/stylist/{created['stylist_id']}/blocks/{block_id}", timeout=20)
    for block_id in created["recurring_blocks"]:
        api_client.delete(f"{API}/stylist/{created['stylist_id']}/recurring-blocks/{block_id}", timeout=20)
    for booking_id in created["bookings"]:
        api_client.patch(
            f"{API}/stylist/{created['stylist_id']}/bookings/{booking_id}/status",
            json={"status": "cancelled"},
            timeout=20,
        )


def _future_date(days=3):
    return (datetime.now(timezone.utc).date() + timedelta(days=days)).isoformat()


def _book_first_available_slot(api_client, service_id, stylist_id, date_str, phone_suffix="10"):
    chosen_date = None
    slot = None

    # Try requested date first, then search nearby future dates for first available slot.
    for offset in range(0, 21):
        candidate_date = (
            datetime.strptime(date_str, "%Y-%m-%d").date() + timedelta(days=offset)
        ).isoformat()
        availability = api_client.get(
            f"{API}/availability",
            params={"stylist_id": stylist_id, "service_id": service_id, "date": candidate_date},
            timeout=20,
        )
        assert availability.status_code == 200
        slot = next((s for s in availability.json().get("slots", []) if s.get("available")), None)
        if slot:
            chosen_date = candidate_date
            break

    assert slot and chosen_date, f"No available slot found from {date_str} over next 21 days"

    payload = {
        "service_id": service_id,
        "stylist_id": stylist_id,
        "date": chosen_date,
        "start_time": slot["start_time"],
        "customer_name": f"TEST_STYLIST_{uuid.uuid4().hex[:6]}",
        "customer_phone": f"+9199911111{phone_suffix}",
        "notes": "TEST_STYLIST_NOTES",
        "whatsapp_optin": False,
    }
    booking_res = api_client.post(f"{API}/bookings", json=payload, timeout=20)
    assert booking_res.status_code == 200, booking_res.text
    return booking_res.json()["booking"]


# Module: stylist auth and day schedule with complete booking details
def test_stylist_login_elena_pin_works(api_client):
    login = api_client.post(
        f"{API}/stylist/login",
        json={"stylist_id": "stylist-elena", "pin": "1234"},
        timeout=20,
    )
    assert login.status_code == 200
    body = login.json()
    assert body["token"] == "stylist-elena"
    assert body["stylist"]["name"] == "Elena Hart"


# Module: day view data contract should include key booking information
def test_schedule_selected_day_contains_booking_details(api_client, service_and_stylist, cleanup_created_entities):
    service, stylist_id = service_and_stylist
    target_date = _future_date(4)
    booking = _book_first_available_slot(api_client, service["id"], stylist_id, target_date, "21")
    cleanup_created_entities["bookings"].append(booking["id"])

    schedule = api_client.get(
        f"{API}/stylist/{stylist_id}/schedule",
        params={"date": booking["date"]},
        timeout=20,
    )
    assert schedule.status_code == 200
    items = schedule.json().get("bookings", [])
    matched = next((b for b in items if b["id"] == booking["id"]), None)
    assert matched is not None
    assert matched["customer_name"].startswith("TEST_STYLIST_")
    assert matched["customer_phone"].startswith("+91999")
    assert matched["notes"] == "TEST_STYLIST_NOTES"
    assert matched["status"] == "upcoming"
    assert matched.get("service", {}).get("name") == service["name"]
    assert matched.get("service", {}).get("price") == service["price"]
    assert isinstance(matched.get("duration_min"), int)
    assert isinstance(matched.get("start_time"), str)
    assert isinstance(matched.get("end_time"), str)
    assert matched.get("whatsapp_status") == "skipped"


# Module: one-time break block should appear and exclude customer availability
def test_one_time_break_reflected_and_excludes_slots(api_client, service_and_stylist, cleanup_created_entities):
    service, stylist_id = service_and_stylist
    target_date = _future_date(5)

    add_block = api_client.put(
        f"{API}/stylist/{stylist_id}/blocks",
        json={"date": target_date, "start_time": "13:00", "end_time": "14:00", "status": "break"},
        timeout=20,
    )
    assert add_block.status_code == 200
    block = add_block.json()["block"]
    cleanup_created_entities["blocks"].append(block["id"])
    assert block["status"] == "break"

    week_start = (datetime.strptime(target_date, "%Y-%m-%d").date() - timedelta(days=datetime.strptime(target_date, "%Y-%m-%d").date().weekday())).isoformat()
    weekly = api_client.get(f"{API}/stylist/{stylist_id}/availability", params={"week_start": week_start}, timeout=20)
    assert weekly.status_code == 200
    one_time_blocks = [b for b in weekly.json().get("blocks", []) if b.get("id") == block["id"]]
    assert len(one_time_blocks) == 1

    availability = api_client.get(
        f"{API}/availability",
        params={"stylist_id": stylist_id, "service_id": service["id"], "date": target_date},
        timeout=20,
    )
    assert availability.status_code == 200
    slots = availability.json().get("slots", [])
    overlapping = [s for s in slots if not (s["end_time"] <= "13:00" or s["start_time"] >= "14:00")]
    assert overlapping, "Expected overlapping slots around break window"
    assert all(s["available"] is False for s in overlapping)


# Module: recurring weekly break should show up and be removable
def test_recurring_break_add_list_delete(api_client, service_and_stylist, cleanup_created_entities):
    _, stylist_id = service_and_stylist
    add_rec = api_client.put(
        f"{API}/stylist/{stylist_id}/recurring-blocks",
        json={
            "weekdays": [0, 2, 4],
            "start_time": "12:00",
            "end_time": "12:30",
            "status": "break",
            "label": "TEST_WEEKLY_BREAK",
        },
        timeout=20,
    )
    assert add_rec.status_code == 200
    rec = add_rec.json()["block"]
    cleanup_created_entities["recurring_blocks"].append(rec["id"])
    assert rec["label"] == "TEST_WEEKLY_BREAK"

    week_start = (datetime.now(timezone.utc).date() - timedelta(days=datetime.now(timezone.utc).date().weekday())).isoformat()
    weekly = api_client.get(f"{API}/stylist/{stylist_id}/availability", params={"week_start": week_start}, timeout=20)
    assert weekly.status_code == 200
    listed = [b for b in weekly.json().get("recurring_blocks", []) if b.get("id") == rec["id"]]
    assert len(listed) == 1
    assert listed[0]["weekdays"] == [0, 2, 4]

    delete_rec = api_client.delete(f"{API}/stylist/{stylist_id}/recurring-blocks/{rec['id']}", timeout=20)
    assert delete_rec.status_code == 200
    cleanup_created_entities["recurring_blocks"].remove(rec["id"])

    weekly_after = api_client.get(f"{API}/stylist/{stylist_id}/availability", params={"week_start": week_start}, timeout=20)
    assert weekly_after.status_code == 200
    listed_after = [b for b in weekly_after.json().get("recurring_blocks", []) if b.get("id") == rec["id"]]
    assert listed_after == []


# Module: regression - working-hours endpoint and stylist status update remain functional
def test_working_hours_and_status_regression(api_client, service_and_stylist, cleanup_created_entities):
    service, stylist_id = service_and_stylist
    week_start = (datetime.now(timezone.utc).date() - timedelta(days=datetime.now(timezone.utc).date().weekday())).isoformat()
    availability = api_client.get(f"{API}/stylist/{stylist_id}/availability", params={"week_start": week_start}, timeout=20)
    assert availability.status_code == 200
    assert isinstance(availability.json().get("working_hours"), dict)

    target_date = _future_date(6)
    booking = _book_first_available_slot(api_client, service["id"], stylist_id, target_date, "31")
    cleanup_created_entities["bookings"].append(booking["id"])

    status_update = api_client.patch(
        f"{API}/stylist/{stylist_id}/bookings/{booking['id']}/status",
        json={"status": "done"},
        timeout=20,
    )
    assert status_update.status_code == 200
    assert status_update.json().get("booking", {}).get("status") == "done"
