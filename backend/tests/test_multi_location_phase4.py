"""Phase 4: Booking flow rework (Service → Location → Stylist → Date & Time)
and slot_first mode. Backend endpoints tested:
- GET /api/salons + service_id filter (honors per-salon menu opt-out)
- GET /api/availability/salon-slots (union across stylists)
- GET /api/availability/by-slot (stylists free at slot)
- Regression: /api/availability per-stylist unchanged
"""
import os
import datetime as dt
import pytest
import requests

def _load_backend_url():
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        url = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
    if not url:
        raise RuntimeError("REACT_APP_BACKEND_URL not set")
    return url.rstrip("/")


BASE_URL = _load_backend_url()
OWNER_PHONE = "8511111593"
SERVICE_ID = "svc-signature-cut"
MAIN_SALON = "salon-main"
CUSTOMER_PHONE = "9876543210"

# A comfortably-future date that shouldn't already be fully booked.
FUTURE_DATE = (dt.date.today() + dt.timedelta(days=90)).strftime("%Y-%m-%d")


@pytest.fixture(scope="module")
def owner_token():
    # Use PIN login (race-free under xdist parallel workers).
    r = requests.post(f"{BASE_URL}/api/owner/login", json={"pin": "9999"}, timeout=15)
    assert r.status_code == 200, r.text
    token = r.json().get("token")
    assert token
    return token


@pytest.fixture(scope="module")
def owner_headers(owner_token):
    return {"Authorization": f"Bearer {owner_token}", "Content-Type": "application/json"}


# -----------------------------------------------------------
# /api/salons — plain + service filter
# -----------------------------------------------------------
class TestSalonsFilter:
    def test_all_active_salons(self):
        r = requests.get(f"{BASE_URL}/api/salons", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "salons" in data
        assert isinstance(data["salons"], list)
        assert len(data["salons"]) >= 1
        ids = {s["id"] for s in data["salons"]}
        assert MAIN_SALON in ids

    def test_service_filter_excludes_off_salons(self, owner_headers):
        # Create a temp salon
        temp_name = "TEST_Phase4_TempSalon"
        r = requests.post(
            f"{BASE_URL}/api/owner/salons",
            headers=owner_headers,
            json={
                "name": temp_name,
                "slug": "test-phase4-tempsalon",
                "city": "Test City",
                "timezone": "Asia/Kolkata",
            },
            timeout=15,
        )
        assert r.status_code in (200, 201), r.text
        temp_id = r.json()["id"]

        try:
            # Confirm temp is included by default
            r = requests.get(f"{BASE_URL}/api/salons?service_id={SERVICE_ID}", timeout=15)
            assert r.status_code == 200
            ids_before = {s["id"] for s in r.json()["salons"]}
            assert temp_id in ids_before
            assert MAIN_SALON in ids_before

            # Turn OFF svc-signature-cut at temp salon
            r = requests.put(
                f"{BASE_URL}/api/owner/salons/{temp_id}/menu",
                headers=owner_headers,
                json={"entries": [{"service_id": SERVICE_ID, "is_offered": False}]},
                timeout=15,
            )
            assert r.status_code == 200, r.text

            # Filtered call excludes temp
            r = requests.get(f"{BASE_URL}/api/salons?service_id={SERVICE_ID}", timeout=15)
            assert r.status_code == 200
            ids_after = {s["id"] for s in r.json()["salons"]}
            assert temp_id not in ids_after, "Temp salon should be excluded when service is off"
            assert MAIN_SALON in ids_after, "Main salon should still be included"

            # Restore (turn back on)
            r = requests.put(
                f"{BASE_URL}/api/owner/salons/{temp_id}/menu",
                headers=owner_headers,
                json={"entries": [{"service_id": SERVICE_ID, "is_offered": True}]},
                timeout=15,
            )
            assert r.status_code == 200
            r = requests.get(f"{BASE_URL}/api/salons?service_id={SERVICE_ID}", timeout=15)
            ids_restored = {s["id"] for s in r.json()["salons"]}
            assert temp_id in ids_restored, "After restore, temp salon must be included"
        finally:
            # Archive the temp salon
            requests.post(
                f"{BASE_URL}/api/owner/salons/{temp_id}/archive", headers=owner_headers, timeout=15
            )


# -----------------------------------------------------------
# /api/availability/salon-slots
# -----------------------------------------------------------
class TestSalonSlots:
    def test_returns_slots_for_valid_salon_service_date(self):
        r = requests.get(
            f"{BASE_URL}/api/availability/salon-slots",
            params={"salon_id": MAIN_SALON, "service_id": SERVICE_ID, "date": FUTURE_DATE},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["salon_id"] == MAIN_SALON
        assert data["service_id"] == SERVICE_ID
        assert data["date"] == FUTURE_DATE
        assert isinstance(data.get("duration_min"), int)
        assert data["duration_min"] > 0
        assert isinstance(data["slots"], list)
        assert len(data["slots"]) > 0, "Expected at least one available slot in the future date"
        s0 = data["slots"][0]
        assert "start_time" in s0 and "end_time" in s0
        assert s0.get("available") is True
        # Slots must be sorted ascending
        starts = [s["start_time"] for s in data["slots"]]
        assert starts == sorted(starts)

    def test_salon_with_service_off_returns_empty_slots(self, owner_headers):
        temp_name = "TEST_Phase4_TempSalon2"
        r = requests.post(
            f"{BASE_URL}/api/owner/salons",
            headers=owner_headers,
            json={
                "name": temp_name,
                "slug": "test-phase4-tempsalon2",
                "city": "Test City",
                "timezone": "Asia/Kolkata",
            },
            timeout=15,
        )
        assert r.status_code in (200, 201), r.text
        temp_id = r.json()["id"]

        try:
            # Turn service off
            r = requests.put(
                f"{BASE_URL}/api/owner/salons/{temp_id}/menu",
                headers=owner_headers,
                json={"entries": [{"service_id": SERVICE_ID, "is_offered": False}]},
                timeout=15,
            )
            assert r.status_code == 200

            r = requests.get(
                f"{BASE_URL}/api/availability/salon-slots",
                params={"salon_id": temp_id, "service_id": SERVICE_ID, "date": FUTURE_DATE},
                timeout=15,
            )
            assert r.status_code == 200
            data = r.json()
            assert data["slots"] == []
        finally:
            requests.post(
                f"{BASE_URL}/api/owner/salons/{temp_id}/archive", headers=owner_headers, timeout=15
            )

    def test_unknown_salon_returns_404(self):
        r = requests.get(
            f"{BASE_URL}/api/availability/salon-slots",
            params={
                "salon_id": "salon-does-not-exist-xyz-999",
                "service_id": SERVICE_ID,
                "date": FUTURE_DATE,
            },
            timeout=15,
        )
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"


# -----------------------------------------------------------
# /api/availability/by-slot
# -----------------------------------------------------------
class TestByslot:
    def test_by_slot_returns_stylists_offering_service_at_salon(self):
        # Find a slot with at least one free stylist
        slots_r = requests.get(
            f"{BASE_URL}/api/availability/salon-slots",
            params={"salon_id": MAIN_SALON, "service_id": SERVICE_ID, "date": FUTURE_DATE},
            timeout=15,
        )
        assert slots_r.status_code == 200
        slots = slots_r.json()["slots"]
        assert slots, "Need at least one slot for by-slot test"
        start_time = slots[0]["start_time"]

        r = requests.get(
            f"{BASE_URL}/api/availability/by-slot",
            params={
                "salon_id": MAIN_SALON,
                "service_id": SERVICE_ID,
                "date": FUTURE_DATE,
                "start_time": start_time,
            },
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["salon_id"] == MAIN_SALON
        assert data["service_id"] == SERVICE_ID
        assert data["start_time"] == start_time
        assert isinstance(data["stylists"], list)
        assert len(data["stylists"]) > 0, "Expected at least one free stylist"
        for s in data["stylists"]:
            assert s.get("salon_id") == MAIN_SALON, f"Stylist salon_id mismatch: {s}"
            assert SERVICE_ID in s.get("services", []), f"Stylist doesn't offer service: {s}"
            assert s.get("is_active", True) is not False

    def test_booking_removes_stylist_from_by_slot(self):
        # Use a time-of-day unlikely to be already booked on this future date: 15:00
        target_start = "15:00"

        # Get free stylists before
        before = requests.get(
            f"{BASE_URL}/api/availability/by-slot",
            params={
                "salon_id": MAIN_SALON,
                "service_id": SERVICE_ID,
                "date": FUTURE_DATE,
                "start_time": target_start,
            },
            timeout=15,
        )
        assert before.status_code == 200, before.text
        free_stylists = before.json()["stylists"]
        if not free_stylists:
            pytest.skip("No stylists free at 15:00 on target future date")
        target_stylist_id = free_stylists[0]["id"]

        # Create a booking
        booking_payload = {
            "service_id": SERVICE_ID,
            "stylist_id": target_stylist_id,
            "date": FUTURE_DATE,
            "start_time": target_start,
            "customer_name": "TEST Phase4 Customer",
            "customer_phone": CUSTOMER_PHONE,
            "notes": "TEST_PHASE4_by_slot_test",
            "whatsapp_optin": False,
        }
        b = requests.post(f"{BASE_URL}/api/bookings", json=booking_payload, timeout=20)
        assert b.status_code in (200, 201), b.text
        booking_id = b.json()["booking"]["id"]

        try:
            after = requests.get(
                f"{BASE_URL}/api/availability/by-slot",
                params={
                    "salon_id": MAIN_SALON,
                    "service_id": SERVICE_ID,
                    "date": FUTURE_DATE,
                    "start_time": target_start,
                },
                timeout=15,
            )
            assert after.status_code == 200
            after_ids = {s["id"] for s in after.json()["stylists"]}
            assert target_stylist_id not in after_ids, (
                f"Stylist {target_stylist_id} should be busy after booking"
            )
        finally:
            # Best-effort cleanup: mark booking cancelled through manage token
            # (no auth needed via cancel endpoint if it exists; else leave it)
            try:
                # Cancel via customer manage endpoint
                token = b.json()["booking"].get("manage_token")
                if token:
                    requests.post(
                        f"{BASE_URL}/api/bookings/{booking_id}/cancel",
                        json={"manage_token": token},
                        timeout=10,
                    )
            except Exception:
                pass


# -----------------------------------------------------------
# Regression: /api/availability per-stylist unchanged
# -----------------------------------------------------------
class TestPerStylistAvailabilityRegression:
    def test_per_stylist_availability_still_works(self):
        # Pick a stylist at main salon
        slot_r = requests.get(
            f"{BASE_URL}/api/availability/salon-slots",
            params={"salon_id": MAIN_SALON, "service_id": SERVICE_ID, "date": FUTURE_DATE},
            timeout=15,
        )
        assert slot_r.status_code == 200
        stylists_r = requests.get(
            f"{BASE_URL}/api/availability/by-slot",
            params={
                "salon_id": MAIN_SALON,
                "service_id": SERVICE_ID,
                "date": FUTURE_DATE,
                "start_time": slot_r.json()["slots"][0]["start_time"],
            },
            timeout=15,
        )
        stylist_id = stylists_r.json()["stylists"][0]["id"]

        r = requests.get(
            f"{BASE_URL}/api/availability",
            params={
                "stylist_id": stylist_id,
                "service_id": SERVICE_ID,
                "date": FUTURE_DATE,
            },
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        # Shape: should contain slots list with available boolean
        assert "slots" in data
        assert isinstance(data["slots"], list)
        assert len(data["slots"]) > 0
        # Regression: expects mixed available/unavailable entries — at least the boolean field exists
        assert all("available" in s for s in data["slots"])
        # Original response includes both true and false depending on hours; verify at least one true
        assert any(s["available"] for s in data["slots"])
