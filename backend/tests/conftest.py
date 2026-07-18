"""Shared pytest fixtures for the multi-location test suite.

Widens ``salon-main``'s booking_window_days for the duration of the test
session (many tests pre-date the booking-window feature and use hardcoded
far-future dates that would otherwise fail the "N days in advance" check),
then restores the original value at teardown so preview state is not left
altered.
"""
import os
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
        raise RuntimeError("REACT_APP_BACKEND_URL is not set")
    return url.rstrip("/")


BASE_URL = _load_backend_url()


@pytest.fixture(scope="session", autouse=True)
def _widen_salon_main_booking_window():
    """Temporarily set salon-main.booking_window_days to 365 during tests."""
    # Owner PIN login (race-free, matches Phase-3 pattern)
    try:
        tok_r = requests.post(f"{BASE_URL}/api/owner/login", json={"pin": "9999"}, timeout=15)
        if tok_r.status_code != 200:
            yield
            return
        headers = {"Authorization": f"Bearer {tok_r.json()['token']}", "Content-Type": "application/json"}
        # Snapshot the current salon-main doc so we restore exactly what was there
        listing = requests.get(f"{BASE_URL}/api/owner/salons", headers=headers, timeout=15).json()
        salons = listing.get("salons", listing)
        main = next((s for s in salons if s.get("id") == "salon-main"), None)
        original_window = int((main or {}).get("booking_window_days") or 30)
        # Widen for the test session
        requests.patch(
            f"{BASE_URL}/api/owner/salons/salon-main",
            json={
                "name": (main or {}).get("name") or "Maison Aurelle — Main",
                "city": (main or {}).get("city") or "",
                "address": (main or {}).get("address") or "",
                "phone": (main or {}).get("phone") or "",
                "timezone": (main or {}).get("timezone") or "Asia/Kolkata",
                "working_hours": (main or {}).get("working_hours"),
                "booking_window_days": 365,
                "is_active": True,
            },
            headers=headers,
            timeout=15,
        )
    except Exception:
        yield
        return

    yield

    # Teardown: restore the original window value
    try:
        requests.patch(
            f"{BASE_URL}/api/owner/salons/salon-main",
            json={
                "name": (main or {}).get("name") or "Maison Aurelle — Main",
                "city": (main or {}).get("city") or "",
                "address": (main or {}).get("address") or "",
                "phone": (main or {}).get("phone") or "",
                "timezone": (main or {}).get("timezone") or "Asia/Kolkata",
                "working_hours": (main or {}).get("working_hours"),
                "booking_window_days": original_window,
                "is_active": True,
            },
            headers=headers,
            timeout=15,
        )
    except Exception:
        pass
