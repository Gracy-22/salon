"""
Phase 2 - Multi-location "Master list + per-salon toggles" tests.

Covers:
 - GET /api/owner/salons/{salon_id}/menu (auth, 404, defaults)
 - PUT /api/owner/salons/{salon_id}/menu (updates, override, invalid salon, unknown svc silently skipped)
 - Public /api/services with & without salon_id filter (overrides + exclusions)
 - POST /api/bookings enforcement of salon menu (off => 400) + price override propagation
 - Default salon (salon-main) still base-priced

Uses REACT_APP_BACKEND_URL and owner PIN login (race-free under parallel workers).
"""
import hashlib
import os
import pytest
import requests

def _load_backend_url():
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        # Fallback: read from frontend/.env so pytest runs work without env export
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

SVC_SIGNATURE = "svc-signature-cut"
SVC_BEARD = "svc-beard-sculpt"
OVERRIDE_PRICE = 1234


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def owner_token(api):
    # Use PIN login (idempotent, race-free under xdist parallel workers).
    # OTP-based owner login would race between workers because the mock OTP
    # is overwritten per phone by whichever request lands last.
    r = api.post(f"{BASE_URL}/api/owner/login", json={"pin": "9999"})
    assert r.status_code == 200, f"PIN login failed: {r.status_code} {r.text}"
    token = r.json().get("token")
    assert token, "No token"
    return token


@pytest.fixture(scope="module")
def owner_headers(owner_token):
    return {"Authorization": f"Bearer {owner_token}", "Content-Type": "application/json"}


def _class_slug(request):
    """Deterministic short suffix per class so parallel classes never share salon rows."""
    name = request.node.cls.__name__ if request.node.cls else "shared"
    return hashlib.md5(name.encode()).hexdigest()[:8]


@pytest.fixture(scope="class")
def qa_salon(request, api, owner_headers):
    """Create a per-class QA Menu Salon (unique name → unique server-derived id
    so parallel classes never step on each other's menu overrides). Menu is
    reset at setup and the salon is archived at teardown.
    """
    slug = _class_slug(request)
    salon_name = f"QA Menu Salon {slug}"
    payload = {
        "name": salon_name,
        "city": "Mumbai",
        "address": "1 QA Lane",
        "phone": "+919999900000",
        "timezone": "Asia/Kolkata",
        "is_active": True,
    }
    r = api.post(f"{BASE_URL}/api/owner/salons", json=payload, headers=owner_headers)
    if r.status_code == 409:
        # Previous run's teardown may have crashed — salon still exists & active.
        # Look it up by name and reuse it (idempotent bootstrap).
        listing = api.get(f"{BASE_URL}/api/owner/salons", headers=owner_headers).json()
        salons = listing.get("salons", listing) if isinstance(listing, dict) else listing
        found = next((s for s in salons if s.get("name") == salon_name), None)
        assert found, f"409 but salon not in listing: {r.text}"
        salon_id = found["id"]
    else:
        assert r.status_code in (200, 201), f"Salon create failed: {r.status_code} {r.text}"
        salon_id = r.json().get("id")
    assert salon_id, f"No salon id in response: {r.text}"
    # Reset menu overrides so tests start fresh (both services offered, no price override)
    api.put(
        f"{BASE_URL}/api/owner/salons/{salon_id}/menu",
        json={"entries": [
            {"service_id": SVC_SIGNATURE, "is_offered": True, "price_override": None},
            {"service_id": SVC_BEARD, "is_offered": True, "price_override": None},
        ]},
        headers=owner_headers,
    )
    yield salon_id
    # Teardown: archive this class's own salon (safe under parallel workers).
    try:
        api.post(f"{BASE_URL}/api/owner/salons/{salon_id}/archive", headers=owner_headers)
    except Exception:
        pass


@pytest.fixture(scope="class")
def qa_stylist(request, api, owner_headers, qa_salon):
    """Create a per-class stylist tied to this class's QA salon."""
    slug = _class_slug(request)
    payload = {
        "name": f"TEST_QA_MenuStylist_{slug}",
        "bio": "QA phase2 stylist",
        "image_url": "",
        "services": [SVC_SIGNATURE, SVC_BEARD],
        "salon_id": qa_salon,
        "is_active": True,
    }
    r = api.post(f"{BASE_URL}/api/owner/stylists", json=payload, headers=owner_headers)
    assert r.status_code in (200, 201), f"Stylist create failed: {r.status_code} {r.text}"
    stylist = r.json().get("stylist", r.json())
    stylist_id = stylist["id"]
    yield stylist_id
    # Teardown: archive this class's own stylist
    try:
        api.post(f"{BASE_URL}/api/owner/stylists/{stylist_id}/archive", headers=owner_headers)
    except Exception:
        pass


# ---------- BACKEND: GET menu ----------
class TestOwnerSalonMenuGet:
    def test_get_menu_default_salon(self, api, owner_headers):
        r = api.get(f"{BASE_URL}/api/owner/salons/salon-main/menu", headers=owner_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["salon_id"] == "salon-main"
        assert isinstance(data["menu"], list)
        assert len(data["menu"]) > 0
        # Compare against active master services
        services = api.get(f"{BASE_URL}/api/services").json()
        assert len(data["menu"]) == len(services)
        for row in data["menu"]:
            assert row["is_offered"] is True
            assert row["price_override"] is None
            assert row["effective_price"] == row["price"]
            for k in ("id", "name", "price", "duration_min"):
                assert k in row

    def test_get_menu_unknown_salon_404(self, api, owner_headers):
        r = api.get(f"{BASE_URL}/api/owner/salons/does-not-exist/menu", headers=owner_headers)
        assert r.status_code == 404
        assert "not found" in r.json().get("detail", "").lower()

    def test_get_menu_requires_auth(self, api):
        r = api.get(f"{BASE_URL}/api/owner/salons/salon-main/menu")
        assert r.status_code == 401


# ---------- BACKEND: PUT menu ----------
class TestOwnerSalonMenuPut:
    def test_put_menu_updates_offer_and_override(self, api, owner_headers, qa_salon):
        payload = {"entries": [
            {"service_id": SVC_SIGNATURE, "is_offered": False},
            {"service_id": SVC_BEARD, "is_offered": True, "price_override": OVERRIDE_PRICE},
        ]}
        r = api.put(f"{BASE_URL}/api/owner/salons/{qa_salon}/menu", json=payload, headers=owner_headers)
        assert r.status_code == 200, r.text
        menu = r.json()["menu"]
        by_id = {row["id"]: row for row in menu}
        assert SVC_SIGNATURE in by_id
        assert by_id[SVC_SIGNATURE]["is_offered"] is False
        beard = by_id[SVC_BEARD]
        assert beard["is_offered"] is True
        assert float(beard["price_override"]) == float(OVERRIDE_PRICE)
        assert float(beard["effective_price"]) == float(OVERRIDE_PRICE)

        # Verify persistence via GET
        r2 = api.get(f"{BASE_URL}/api/owner/salons/{qa_salon}/menu", headers=owner_headers)
        by_id2 = {row["id"]: row for row in r2.json()["menu"]}
        assert by_id2[SVC_SIGNATURE]["is_offered"] is False
        assert float(by_id2[SVC_BEARD]["effective_price"]) == float(OVERRIDE_PRICE)

    def test_put_menu_unknown_service_silently_skipped(self, api, owner_headers, qa_salon):
        payload = {"entries": [
            {"service_id": "svc-nonexistent-xyz", "is_offered": False, "price_override": 999},
        ]}
        r = api.put(f"{BASE_URL}/api/owner/salons/{qa_salon}/menu", json=payload, headers=owner_headers)
        assert r.status_code == 200, r.text
        menu = r.json()["menu"]
        # ensure no phantom row created
        assert not any(row["id"] == "svc-nonexistent-xyz" for row in menu)

    def test_put_menu_invalid_salon_404(self, api, owner_headers):
        r = api.put(
            f"{BASE_URL}/api/owner/salons/does-not-exist/menu",
            json={"entries": []},
            headers=owner_headers,
        )
        assert r.status_code == 404


# ---------- Helper: apply the "off + override" menu state used by public
# services filter + bookings enforcement tests. Each class calls this in its
# own fixture so it doesn't depend on another class's test ordering.
def _apply_off_and_override_menu(api, owner_headers, salon_id):
    r = api.put(
        f"{BASE_URL}/api/owner/salons/{salon_id}/menu",
        json={"entries": [
            {"service_id": SVC_SIGNATURE, "is_offered": False},
            {"service_id": SVC_BEARD, "is_offered": True, "price_override": OVERRIDE_PRICE},
        ]},
        headers=owner_headers,
    )
    assert r.status_code == 200, r.text



# ---------- BACKEND: Public /api/services filter ----------
class TestPublicServicesFilter:
    @staticmethod
    @pytest.fixture(scope="class", autouse=True)
    def _apply_menu(api, owner_headers, qa_salon):
        _apply_off_and_override_menu(api, owner_headers, qa_salon)

    def test_services_no_filter_returns_all(self, api):
        r = api.get(f"{BASE_URL}/api/services")
        assert r.status_code == 200
        services = r.json()
        ids = {s["id"] for s in services}
        assert SVC_SIGNATURE in ids
        assert SVC_BEARD in ids
        # Base prices intact
        sig = next(s for s in services if s["id"] == SVC_SIGNATURE)
        beard = next(s for s in services if s["id"] == SVC_BEARD)
        assert float(sig["price"]) != float(OVERRIDE_PRICE)  # base != override
        # Store base prices for other checks
        assert beard["price"] > 0

    def test_services_qa_salon_excludes_off_and_applies_override(self, api, qa_salon):
        # Ensure PUT applied off+override
        r = api.get(f"{BASE_URL}/api/services", params={"salon_id": qa_salon})
        assert r.status_code == 200
        services = r.json()
        ids = {s["id"] for s in services}
        assert SVC_SIGNATURE not in ids, "signature-cut must be excluded when is_offered=false"
        assert SVC_BEARD in ids
        beard = next(s for s in services if s["id"] == SVC_BEARD)
        assert float(beard["price"]) == float(OVERRIDE_PRICE)

    def test_services_default_salon_no_overrides(self, api):
        r = api.get(f"{BASE_URL}/api/services", params={"salon_id": "salon-main"})
        assert r.status_code == 200
        filtered = r.json()
        all_svcs = api.get(f"{BASE_URL}/api/services").json()
        assert {s["id"] for s in filtered} == {s["id"] for s in all_svcs}
        for s in filtered:
            base = next(x for x in all_svcs if x["id"] == s["id"])
            assert float(s["price"]) == float(base["price"])


# ---------- BACKEND: Bookings enforcement ----------
# ---------- BACKEND: Bookings enforcement ----------
class TestBookingsSalonMenuEnforcement:
    @staticmethod
    @pytest.fixture(scope="class", autouse=True)
    def _apply_menu(api, owner_headers, qa_salon):
        _apply_off_and_override_menu(api, owner_headers, qa_salon)

    def _slot(self, api, stylist_id, service_id, salon_hint=None):
        # Attempt several future dates until we find an open slot
        from datetime import date, timedelta
        for delta in range(1, 30):
            d = (date.today() + timedelta(days=delta)).isoformat()
            r = api.get(f"{BASE_URL}/api/availability", params={
                "stylist_id": stylist_id, "service_id": service_id, "date": d,
            })
            if r.status_code == 200:
                slots = r.json().get("slots") or r.json()
                if isinstance(slots, dict):
                    slots = slots.get("slots", [])
                if slots:
                    return d, slots[0]
        pytest.skip("No availability found for booking test")

    def test_booking_offered_service_uses_override_price(self, api, qa_stylist, qa_salon):
        d, slot = self._slot(api, qa_stylist, SVC_BEARD)
        payload = {
            "service_id": SVC_BEARD,
            "stylist_id": qa_stylist,
            "date": d,
            "start_time": slot if isinstance(slot, str) else slot.get("start_time", slot),
            "customer_name": "TEST_QA_Cust",
            "customer_phone": "9999911111",
        }
        r = api.post(f"{BASE_URL}/api/bookings", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["service"]["price"] == OVERRIDE_PRICE
        assert data["booking"]["salon_id"] == qa_salon

    def test_booking_off_service_rejected(self, api, qa_stylist):
        # signature-cut is turned OFF at qa salon; attempt to book
        from datetime import date, timedelta
        d = (date.today() + timedelta(days=2)).isoformat()
        payload = {
            "service_id": SVC_SIGNATURE,
            "stylist_id": qa_stylist,
            "date": d,
            "start_time": "10:00",
            "customer_name": "TEST_QA_Cust2",
            "customer_phone": "9999922222",
        }
        r = api.post(f"{BASE_URL}/api/bookings", json=payload)
        assert r.status_code == 400, r.text
        assert "not offered at that salon" in r.json().get("detail", "").lower()

    def test_booking_at_default_salon_uses_base_price(self, api):
        # Find a stylist on salon-main who offers signature-cut
        stylists = api.get(f"{BASE_URL}/api/stylists", params={"salon_id": "salon-main", "service_id": SVC_SIGNATURE}).json()
        if not stylists:
            pytest.skip("No stylist on salon-main offering signature-cut")
        stylist_id = stylists[0]["id"]
        # Base price should be 600 per spec; but pull dynamically as safety
        svc = next(s for s in api.get(f"{BASE_URL}/api/services").json() if s["id"] == SVC_SIGNATURE)
        base_price = float(svc["price"])

        # Find availability
        from datetime import date, timedelta
        booked = False
        for delta in range(1, 30):
            d = (date.today() + timedelta(days=delta)).isoformat()
            avail = api.get(f"{BASE_URL}/api/availability", params={
                "stylist_id": stylist_id, "service_id": SVC_SIGNATURE, "date": d,
            })
            if avail.status_code != 200:
                continue
            j = avail.json()
            slots = j.get("slots", j) if isinstance(j, dict) else j
            if not slots:
                continue
            start = slots[0] if isinstance(slots[0], str) else slots[0].get("start_time")
            payload = {
                "service_id": SVC_SIGNATURE,
                "stylist_id": stylist_id,
                "date": d,
                "start_time": start,
                "customer_name": "TEST_QA_DefaultCust",
                "customer_phone": "9999933333",
            }
            r = api.post(f"{BASE_URL}/api/bookings", json=payload)
            if r.status_code == 200:
                data = r.json()
                assert data["booking"]["salon_id"] == "salon-main"
                assert float(data["service"]["price"]) == base_price
                assert float(data["service"]["price"]) == 600.0, f"Expected base price 600, got {data['service']['price']}"
                booked = True
                break
        if not booked:
            pytest.skip("Could not find slot for salon-main signature-cut booking")


# ---------- Cleanup ----------
# Per-class stylist + salon rows are archived via the ``qa_stylist`` and
# ``qa_salon`` fixture teardowns. No global cleanup class needed — that was
# the source of the previous cross-class races under ``-n 2 --dist loadscope``.
