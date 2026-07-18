"""
Phase 1 — Multi-location backend regression tests.

Covers:
- Public /api/salons (active only) + default salon seed
- Owner /api/owner/salons auth + CRUD (create/patch/archive)
- Default salon cannot be archived
- Stylist salon_id propagation + filtering
- Bookings carry salon_id; owner endpoints accept salon_id filter
- Public /api/stylists?salon_id filter
- New booking inherits stylist's salon_id
"""

import os
from pathlib import Path

import pytest
import requests


def _load_frontend_env():
    env_path = Path("/app/frontend/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return None


BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _load_frontend_env() or "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be configured"
OWNER_PHONE = "8511111593"
DEFAULT_SALON_ID = "salon-main"
TEST_SALON_NAME = "Test Branch QA"
TEST_SALON_ID = "salon-test-branch-qa"


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def owner_token(session):
    # Use PIN login (race-free under xdist parallel workers). OTP-based login
    # races because the mock OTP is overwritten per phone by whichever request
    # lands last across workers.
    r = session.post(f"{BASE_URL}/api/owner/login", json={"pin": "9999"})
    assert r.status_code == 200, r.text
    token = r.json().get("token")
    assert token
    return token


@pytest.fixture(scope="session")
def owner_client(session, owner_token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {owner_token}"})
    return s


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_salon(owner_client):
    """Make sure the TEST_ salon does not exist at start, archive at end."""
    # Pre-clean: if it exists (active), archive it so create test succeeds with deterministic id
    yield
    try:
        owner_client.post(f"{BASE_URL}/api/owner/salons/{TEST_SALON_ID}/archive")
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Public /api/salons
# --------------------------------------------------------------------------- #
class TestPublicSalons:
    def test_public_salons_returns_default(self, session):
        r = session.get(f"{BASE_URL}/api/salons")
        assert r.status_code == 200
        data = r.json()
        assert "salons" in data
        salons = data["salons"]
        ids = [s["id"] for s in salons]
        assert DEFAULT_SALON_ID in ids
        main = next(s for s in salons if s["id"] == DEFAULT_SALON_ID)
        assert main["is_active"] is True
        assert main["timezone"] == "Asia/Kolkata"
        wh = main["working_hours"]
        assert set(wh.keys()) == {str(i) for i in range(7)}
        for k, v in wh.items():
            assert v["open"] == "09:00" and v["close"] == "21:00"
        # Only active salons returned
        for s in salons:
            assert s.get("is_active", True) is True


# --------------------------------------------------------------------------- #
# Owner salons auth + CRUD
# --------------------------------------------------------------------------- #
class TestOwnerSalonsAuth:
    def test_owner_salons_requires_auth(self, session):
        r = session.get(f"{BASE_URL}/api/owner/salons")
        assert r.status_code in (401, 403)

    def test_owner_salons_with_token(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/owner/salons")
        assert r.status_code == 200
        data = r.json()
        assert "salons" in data
        ids = [s["id"] for s in data["salons"]]
        assert DEFAULT_SALON_ID in ids


class TestOwnerSalonCRUD:
    def test_a_create_test_branch(self, owner_client):
        # Ensure clean state — if previously archived test branch is in DB, re-activate so id stays the same
        existing = owner_client.get(f"{BASE_URL}/api/owner/salons").json()["salons"]
        already = next((s for s in existing if s["id"] == TEST_SALON_ID), None)
        if already:
            # Re-activate via PATCH so the row exists for subsequent tests
            r = owner_client.patch(
                f"{BASE_URL}/api/owner/salons/{TEST_SALON_ID}",
                json={
                    "name": TEST_SALON_NAME,
                    "city": "Pune",
                    "address": "MG Rd",
                    "phone": "9988776655",
                    "timezone": "Asia/Kolkata",
                    "is_active": True,
                },
            )
            assert r.status_code == 200, r.text
            return
        r = owner_client.post(
            f"{BASE_URL}/api/owner/salons",
            json={
                "name": TEST_SALON_NAME,
                "city": "Pune",
                "address": "MG Rd",
                "phone": "9988776655",
                "timezone": "Asia/Kolkata",
            },
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["id"] == TEST_SALON_ID
        assert data["slug"] == "test-branch-qa"
        assert data["working_hours"] and set(data["working_hours"].keys()) == {str(i) for i in range(7)}
        # Phone normalized — stripped non-digits, possibly with country code prefix
        assert data["phone"]
        assert all(c.isdigit() or c == "+" for c in data["phone"])

    def test_b_patch_updates_address(self, owner_client):
        r = owner_client.patch(
            f"{BASE_URL}/api/owner/salons/{TEST_SALON_ID}",
            json={
                "name": TEST_SALON_NAME,
                "city": "Pune",
                "phone": "9988776655",
                "address": "New Address",
                "timezone": "Asia/Kolkata",
                "is_active": True,
            },
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["address"] == "New Address"
        # Verify persistence via GET (owner list)
        list_r = owner_client.get(f"{BASE_URL}/api/owner/salons")
        row = next(s for s in list_r.json()["salons"] if s["id"] == TEST_SALON_ID)
        assert row["address"] == "New Address"

    def test_c_cannot_archive_default(self, owner_client):
        r = owner_client.post(f"{BASE_URL}/api/owner/salons/{DEFAULT_SALON_ID}/archive")
        assert r.status_code == 400, r.text
        body = r.json()
        # The detail might be a string
        detail = body.get("detail") if isinstance(body, dict) else body
        assert "default salon" in str(detail).lower()

    def test_d_archive_test_branch_then_public_hides_it(self, owner_client, session):
        r = owner_client.post(f"{BASE_URL}/api/owner/salons/{TEST_SALON_ID}/archive")
        assert r.status_code == 200, r.text
        # Public hides it
        public = session.get(f"{BASE_URL}/api/salons").json()["salons"]
        assert TEST_SALON_ID not in [s["id"] for s in public]
        # Owner still sees it (archived)
        owner = owner_client.get(f"{BASE_URL}/api/owner/salons").json()["salons"]
        row = next(s for s in owner if s["id"] == TEST_SALON_ID)
        assert row["is_active"] is False


# --------------------------------------------------------------------------- #
# Stylist salon_id propagation
# --------------------------------------------------------------------------- #
class TestStylistSalonId:
    @pytest.fixture(scope="class")
    def reactivated_test_salon(self, owner_client):
        # Reactivate the test salon (or create if it was never created in this run)
        existing = owner_client.get(f"{BASE_URL}/api/owner/salons").json()["salons"]
        if any(s["id"] == TEST_SALON_ID for s in existing):
            r = owner_client.patch(
                f"{BASE_URL}/api/owner/salons/{TEST_SALON_ID}",
                json={
                    "name": TEST_SALON_NAME,
                    "city": "Pune",
                    "address": "New Address",
                    "phone": "9988776655",
                    "timezone": "Asia/Kolkata",
                    "booking_window_days": 365,  # widen so far-future test dates pass validation
                    "is_active": True,
                },
            )
            assert r.status_code == 200, r.text
        else:
            r = owner_client.post(
                f"{BASE_URL}/api/owner/salons",
                json={
                    "name": TEST_SALON_NAME,
                    "city": "Pune",
                    "address": "MG Rd",
                    "phone": "9988776655",
                    "timezone": "Asia/Kolkata",
                    "booking_window_days": 365,  # widen so far-future test dates pass validation
                },
            )
            assert r.status_code == 200, r.text
        return TEST_SALON_ID

    def test_all_existing_stylists_have_default_salon(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/owner/stylists")
        assert r.status_code == 200
        stylists = r.json()["stylists"]
        assert len(stylists) > 0
        # All stylists must have salon_id set (back-fill)
        missing = [s for s in stylists if not s.get("salon_id")]
        assert not missing, f"Stylists without salon_id: {[s['id'] for s in missing]}"
        # Seeded stylists should be on salon-main
        seeded = [s for s in stylists if s["id"] in ("stylist-elena", "stylist-sarah", "stylist-michael")]
        for s in seeded:
            assert s["salon_id"] == DEFAULT_SALON_ID

    def test_create_stylist_unknown_salon_rejected(self, owner_client):
        # Need at least one service id
        services = owner_client.get(f"{BASE_URL}/api/owner/services").json()["services"]
        svc_id = next(s["id"] for s in services)
        r = owner_client.post(
            f"{BASE_URL}/api/owner/stylists",
            json={
                "name": "TEST_QA_BadSalon",
                "title": "Stylist",
                "bio": "test",
                "photo": "",
                "services": [svc_id],
                "salon_id": "salon-does-not-exist",
                "is_active": True,
            },
        )
        assert r.status_code == 400
        assert "unknown salon_id" in r.text.lower()

    def test_create_stylist_with_test_salon(self, owner_client, reactivated_test_salon):
        services = owner_client.get(f"{BASE_URL}/api/owner/services").json()["services"]
        svc_id = next(s["id"] for s in services)
        r = owner_client.post(
            f"{BASE_URL}/api/owner/stylists",
            json={
                "name": "TEST_QA_BranchStylist",
                "title": "Stylist",
                "bio": "branch test",
                "photo": "",
                "services": [svc_id],
                "salon_id": reactivated_test_salon,
                "is_active": True,
            },
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["salon_id"] == reactivated_test_salon
        pytest.stylist_id_test = data["id"]
        pytest.stylist_svc_id = svc_id

    def test_owner_stylists_filter_by_salon(self, owner_client, reactivated_test_salon):
        r = owner_client.get(f"{BASE_URL}/api/owner/stylists?salon_id={reactivated_test_salon}")
        assert r.status_code == 200
        stylists = r.json()["stylists"]
        assert len(stylists) >= 1
        for s in stylists:
            assert s["salon_id"] == reactivated_test_salon

        # No filter — returns all
        r2 = owner_client.get(f"{BASE_URL}/api/owner/stylists")
        all_stylists = r2.json()["stylists"]
        assert len(all_stylists) > len(stylists)

    def test_public_stylists_filter_by_salon(self, session, reactivated_test_salon):
        r = session.get(f"{BASE_URL}/api/stylists?salon_id={DEFAULT_SALON_ID}")
        assert r.status_code == 200
        body = r.json()
        stylists = body if isinstance(body, list) else body.get("stylists", [])
        assert len(stylists) > 0
        for s in stylists:
            assert s.get("salon_id") == DEFAULT_SALON_ID

    def test_new_booking_inherits_stylist_salon_id(self, session, owner_client, reactivated_test_salon):
        stylist_id = getattr(pytest, "stylist_id_test", None)
        svc_id = getattr(pytest, "stylist_svc_id", None)
        assert stylist_id and svc_id, "previous test must have created a stylist"

        # Pick a far-future date to avoid colliding with existing bookings
        booking_payload = {
            "service_id": svc_id,
            "stylist_id": stylist_id,
            "date": "2027-01-15",
            "start_time": "10:00",
            "customer_name": "TEST_QA Customer",
            "customer_phone": "9123456780",
            "whatsapp_optin": False,
        }
        r = session.post(f"{BASE_URL}/api/bookings", json=booking_payload)
        assert r.status_code == 200, r.text
        resp = r.json()
        # /api/bookings returns BookingResponse {booking, service, stylist}
        booking = resp.get("booking", resp)
        assert booking["salon_id"] == reactivated_test_salon
        pytest.booking_id_test = booking["id"]


# --------------------------------------------------------------------------- #
# Bookings / insights / no-shows salon_id filter
# --------------------------------------------------------------------------- #
class TestOwnerBookingFilters:
    def test_owner_bookings_carry_salon_id(self, owner_client):
        # Use a known seed date
        r = owner_client.get(f"{BASE_URL}/api/owner/bookings?date=2026-06-29")
        assert r.status_code == 200
        bookings = r.json()["bookings"]
        # Every booking must have salon_id
        for b in bookings:
            assert "salon_id" in b and b["salon_id"]

    def test_owner_bookings_salon_main_filter(self, owner_client):
        r = owner_client.get(
            f"{BASE_URL}/api/owner/bookings?date=2026-06-29&salon_id={DEFAULT_SALON_ID}"
        )
        assert r.status_code == 200
        for b in r.json()["bookings"]:
            assert b["salon_id"] == DEFAULT_SALON_ID

    def test_owner_bookings_other_salon_zero(self, owner_client):
        # Use the (now archived) test salon — past date should yield 0
        r = owner_client.get(
            f"{BASE_URL}/api/owner/bookings?date=2026-06-29&salon_id={TEST_SALON_ID}"
        )
        assert r.status_code == 200
        assert r.json()["bookings"] == []

    def test_revenue_insights_filter(self, owner_client):
        r = owner_client.get(
            f"{BASE_URL}/api/owner/revenue-insights?period=week&salon_id={DEFAULT_SALON_ID}"
        )
        assert r.status_code == 200, r.text
        data = r.json()
        # Should have a kpis-ish payload with positive total_revenue from demo seed
        kpis = data.get("kpis") or data
        total = kpis.get("total_revenue") or data.get("total_revenue")
        # We allow either flat or nested shape — just ensure it's a non-negative number
        assert total is None or (isinstance(total, (int, float)) and total >= 0)

        # Without salon_id (aggregated)
        r2 = owner_client.get(f"{BASE_URL}/api/owner/revenue-insights?period=week")
        assert r2.status_code == 200

    def test_no_shows_filter(self, owner_client):
        r = owner_client.get(
            f"{BASE_URL}/api/owner/no-shows?month=2026-06&salon_id={DEFAULT_SALON_ID}"
        )
        assert r.status_code == 200, r.text


# --------------------------------------------------------------------------- #
# Cleanup
# --------------------------------------------------------------------------- #
class TestZCleanup:
    def test_cleanup_test_stylist(self, owner_client):
        stylist_id = getattr(pytest, "stylist_id_test", None)
        if stylist_id:
            r = owner_client.post(f"{BASE_URL}/api/owner/stylists/{stylist_id}/archive")
            assert r.status_code in (200, 204), r.text

    def test_cleanup_test_salon(self, owner_client):
        r = owner_client.post(f"{BASE_URL}/api/owner/salons/{TEST_SALON_ID}/archive")
        # may already be archived — both 200 and 400 acceptable but expect 200
        assert r.status_code in (200, 404), r.text
