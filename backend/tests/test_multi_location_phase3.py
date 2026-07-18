"""
Phase 3 - Multi-location: Super-owner + per-location manager tests.

Covers:
 - Owner CRUD /api/owner/managers (auth, create/update/archive)
 - Unified OTP login manager routing + role=manager token
 - Manager scoped endpoints /api/manager/* (me, bookings, revenue-insights,
   no-shows, customers/search, customers/{phone}, PATCH bookings status)
 - Cross-role authorization (owner<->manager tokens rejected on the other side)
 - Salon-scoped isolation for a second salon "Bandra QA"
"""
import os
import time
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
OWNER_PHONE = "8511111593"
QA_SALON_ID = "salon-bandra-qa"
QA_SALON_NAME = "Bandra QA"
MANAGER_MAIN_LOGIN = "9111100020"   # for salon-main
MANAGER_QA_LOGIN = "9111100030"     # for QA salon
# Dedicated phones for TestOwnerManagersCRUD so it never races with the shared
# ``manager_ctx`` bootstrap fixture (each class runs on its own xdist worker).
MANAGER_CRUD_MAIN = "9111100121"
MANAGER_CRUD_QA = "9111100131"
STYLIST_PHONE_CONFLICT = "9111100040"


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="class")
def state():
    """Per-class mutable state — replaces the brittle ``pytest.<attr>`` globals.

    We use ``scope="class"`` because pytest.ini pins tests via ``--dist loadscope``
    (one class → one xdist worker). Class-scope keeps writes visible within a
    single class while remaining safe under parallel workers.
    """
    return {}


# ------- Reusable bootstrap helpers (each class calls these to be self-sufficient
# under --dist loadscope where classes may run on different xdist workers) -------

def _ensure_manager(api, owner_headers, name, phone, salon_id):
    """Idempotent: archive any active manager with this login_phone, then create fresh."""
    r = api.get(f"{BASE_URL}/api/owner/managers", headers=owner_headers)
    assert r.status_code == 200, r.text
    for m in r.json().get("managers", []):
        if m.get("login_phone") == phone and m.get("is_active") is not False:
            api.post(f"{BASE_URL}/api/owner/managers/{m['id']}/archive", headers=owner_headers)
    payload = {"name": name, "phone": phone, "login_phone": phone, "salon_id": salon_id, "is_active": True}
    r = api.post(f"{BASE_URL}/api/owner/managers", json=payload, headers=owner_headers)
    assert r.status_code == 200, r.text
    return r.json()


def _manager_login(api, phone):
    r = api.post(f"{BASE_URL}/api/login/request-otp", json={"phone": phone})
    assert r.status_code == 200, r.text
    otp = r.json()["mock_otp"]
    r2 = api.post(f"{BASE_URL}/api/login/verify-otp", json={"phone": phone, "otp": otp})
    assert r2.status_code == 200, r2.text
    return r2.json()


@pytest.fixture(scope="class")
def manager_ctx(request, api, owner_headers, qa_salon):
    """Class-scoped bootstrap: ensures both managers exist and returns fresh tokens/ids.

    Each class that needs manager tokens/ids depends on this fixture; every class
    runs on its own xdist worker under loadscope. To avoid cross-class races on
    the same DB rows, we derive class-unique login phones so parallel classes
    each own their own manager records. Cleanup happens in this fixture's
    teardown (not in a separate cleanup test) so parallel classes never archive
    each other's records.
    """
    import hashlib
    cls_name = request.node.cls.__name__ if request.node.cls else "shared"
    # Deterministic 5-digit suffix per class (avoids collisions across two
    # classes that happen to land on the same worker with mod-10 hashing).
    suffix = int(hashlib.md5(cls_name.encode()).hexdigest()[:6], 16) % 100000
    main_phone = f"91201{suffix:05d}"
    qa_phone = f"91202{suffix:05d}"
    main = _ensure_manager(api, owner_headers, "Priya QA", main_phone, "salon-main")
    qa = _ensure_manager(api, owner_headers, "QA Bandra Mgr", qa_phone, qa_salon)
    main_login = _manager_login(api, main_phone)
    qa_login = _manager_login(api, qa_phone)
    ctx = {
        "main_id": main["id"],
        "qa_id": qa["id"],
        "main_token": main_login["token"],
        "qa_token": qa_login["token"],
        "main_phone": main_phone,
        "qa_phone": qa_phone,
    }
    yield ctx
    # Teardown: archive only THIS class's managers by ID (safe under parallel workers).
    for mid in (ctx["main_id"], ctx["qa_id"]):
        try:
            api.post(f"{BASE_URL}/api/owner/managers/{mid}/archive", headers=owner_headers)
        except Exception:
            pass


@pytest.fixture(scope="module")
def owner_token(api):
    # Use PIN login (idempotent, race-free under xdist parallel workers).
    # OTP-based owner login would race between workers because the mock OTP
    # is overwritten per phone by whichever request lands last.
    r = api.post(f"{BASE_URL}/api/owner/login", json={"pin": "9999"})
    assert r.status_code == 200, r.text
    tok = r.json().get("token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def owner_headers(owner_token):
    return {"Authorization": f"Bearer {owner_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def qa_salon(api, owner_headers):
    # Ensure a second salon exists for cross-salon isolation
    r = api.get(f"{BASE_URL}/api/owner/salons", headers=owner_headers)
    assert r.status_code == 200
    existing = {s["id"]: s for s in r.json().get("salons", [])}
    payload = {"id": QA_SALON_ID, "name": QA_SALON_NAME, "address": "Bandra West", "phone": "9999999999", "booking_window_days": 365, "is_active": True}
    if QA_SALON_ID not in existing or existing[QA_SALON_ID].get("is_active") is False:
        r2 = api.post(f"{BASE_URL}/api/owner/salons", json=payload, headers=owner_headers)
        assert r2.status_code in (200, 201), f"create salon failed: {r2.status_code} {r2.text}"
    else:
        # Ensure window is wide enough for the far-future test dates
        api.patch(f"{BASE_URL}/api/owner/salons/{QA_SALON_ID}", json=payload, headers=owner_headers)
    return QA_SALON_ID


# --------- Owner /api/owner/managers ---------

class TestOwnerManagersCRUD:
    def test_list_requires_auth(self, api):
        r = api.get(f"{BASE_URL}/api/owner/managers")
        assert r.status_code == 401

    def test_list_authorized(self, api, owner_headers):
        r = api.get(f"{BASE_URL}/api/owner/managers", headers=owner_headers)
        assert r.status_code == 200
        body = r.json()
        assert "managers" in body and isinstance(body["managers"], list)

    def test_create_manager_main(self, api, owner_headers, state):
        # cleanup any active with this phone from previous run
        r = api.get(f"{BASE_URL}/api/owner/managers", headers=owner_headers)
        for m in r.json().get("managers", []):
            if m.get("login_phone") == MANAGER_CRUD_MAIN and m.get("is_active") is not False:
                api.post(f"{BASE_URL}/api/owner/managers/{m['id']}/archive", headers=owner_headers)
        payload = {
            "name": "Priya QA",
            "phone": MANAGER_CRUD_MAIN,
            "login_phone": MANAGER_CRUD_MAIN,
            "salon_id": "salon-main",
            "is_active": True,
        }
        r = api.post(f"{BASE_URL}/api/owner/managers", json=payload, headers=owner_headers)
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["id"].startswith("manager-priya-qa")
        assert doc["login_phone"] == MANAGER_CRUD_MAIN
        assert doc["salon_id"] == "salon-main"
        assert doc["is_active"] is True
        state["main_manager_id"] = doc["id"]

    def test_reject_owner_phone(self, api, owner_headers):
        payload = {
            "name": "Bad Owner Alias",
            "phone": OWNER_PHONE,
            "login_phone": OWNER_PHONE,
            "salon_id": "salon-main",
            "is_active": True,
        }
        r = api.post(f"{BASE_URL}/api/owner/managers", json=payload, headers=owner_headers)
        assert r.status_code == 400
        assert "reserved" in r.text.lower()

    def test_reject_unknown_salon(self, api, owner_headers):
        payload = {
            "name": "Ghost Salon Mgr",
            "phone": "9111100099",
            "login_phone": "9111100099",
            "salon_id": "salon-does-not-exist",
            "is_active": True,
        }
        r = api.post(f"{BASE_URL}/api/owner/managers", json=payload, headers=owner_headers)
        assert r.status_code == 400
        assert "unknown salon" in r.text.lower()

    def test_duplicate_manager_phone_conflict(self, api, owner_headers):
        payload = {
            "name": "Dup Priya",
            "phone": MANAGER_CRUD_MAIN,
            "login_phone": MANAGER_CRUD_MAIN,
            "salon_id": "salon-main",
            "is_active": True,
        }
        r = api.post(f"{BASE_URL}/api/owner/managers", json=payload, headers=owner_headers)
        assert r.status_code == 409

    def test_conflict_with_active_stylist(self, api, owner_headers, state):
        # Create an active stylist with a login_phone
        stylist_payload = {"name": "TEST_QA_ConflictStylist", "phone": STYLIST_PHONE_CONFLICT, "login_phone": STYLIST_PHONE_CONFLICT, "is_active": True}
        rs = api.post(f"{BASE_URL}/api/owner/stylists", json=stylist_payload, headers=owner_headers)
        assert rs.status_code in (200, 201), rs.text
        stylist_id = rs.json().get("id")
        state["conflict_stylist_id"] = stylist_id
        try:
            payload = {
                "name": "Should Conflict",
                "phone": STYLIST_PHONE_CONFLICT,
                "login_phone": STYLIST_PHONE_CONFLICT,
                "salon_id": "salon-main",
                "is_active": True,
            }
            r = api.post(f"{BASE_URL}/api/owner/managers", json=payload, headers=owner_headers)
            assert r.status_code == 409, r.text
        finally:
            pass  # cleanup at end

    def test_create_qa_manager(self, api, owner_headers, qa_salon, state):
        # cleanup previous run
        r = api.get(f"{BASE_URL}/api/owner/managers", headers=owner_headers)
        for m in r.json().get("managers", []):
            if m.get("login_phone") == MANAGER_CRUD_QA and m.get("is_active") is not False:
                api.post(f"{BASE_URL}/api/owner/managers/{m['id']}/archive", headers=owner_headers)
        payload = {"name": "QA Bandra Mgr", "phone": MANAGER_CRUD_QA, "login_phone": MANAGER_CRUD_QA, "salon_id": qa_salon, "is_active": True}
        r = api.post(f"{BASE_URL}/api/owner/managers", json=payload, headers=owner_headers)
        assert r.status_code == 200, r.text
        state["qa_manager_id"] = r.json()["id"]
        assert r.json()["salon_id"] == qa_salon

    def test_patch_manager(self, api, owner_headers, state):
        mid = state["main_manager_id"]
        payload = {"name": "Priya QA Sr", "phone": MANAGER_CRUD_MAIN, "login_phone": MANAGER_CRUD_MAIN, "salon_id": "salon-main", "is_active": True}
        r = api.patch(f"{BASE_URL}/api/owner/managers/{mid}", json=payload, headers=owner_headers)
        assert r.status_code == 200, r.text
        assert r.json()["name"] == "Priya QA Sr"


# --------- Unified login manager routing ---------

class TestUnifiedLoginManager:
    def _login(self, api, phone):
        r = api.post(f"{BASE_URL}/api/login/request-otp", json={"phone": phone})
        assert r.status_code == 200, r.text
        otp = r.json()["mock_otp"]
        r2 = api.post(f"{BASE_URL}/api/login/verify-otp", json={"phone": phone, "otp": otp})
        assert r2.status_code == 200, r2.text
        return r2.json()

    def test_manager_login_main(self, api, manager_ctx):
        body = self._login(api, manager_ctx["main_phone"])
        assert body.get("role") == "manager", body
        assert body.get("token")
        assert body.get("manager", {}).get("salon_id") == "salon-main"
        assert body.get("salon", {}).get("id") == "salon-main"

    def test_manager_login_qa(self, api, qa_salon, manager_ctx):
        body = self._login(api, manager_ctx["qa_phone"])
        assert body.get("role") == "manager"
        assert body.get("manager", {}).get("salon_id") == qa_salon


# --------- Manager scoped endpoints ---------

class TestManagerEndpoints:
    @staticmethod
    def _mh(manager_ctx):
        return {"Authorization": f"Bearer {manager_ctx['main_token']}", "Content-Type": "application/json"}

    @staticmethod
    def _qh(manager_ctx):
        return {"Authorization": f"Bearer {manager_ctx['qa_token']}", "Content-Type": "application/json"}

    def test_manager_me(self, api, manager_ctx):
        r = api.get(f"{BASE_URL}/api/manager/me", headers=self._mh(manager_ctx))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["manager"]["login_phone"] == manager_ctx["main_phone"]
        assert body["salon"]["id"] == "salon-main"

    def test_manager_bookings_scoped(self, api, owner_headers, qa_salon, state, manager_ctx):
        # Ensure QA salon menu offers svc-signature-cut
        api.put(f"{BASE_URL}/api/owner/salons/{qa_salon}/menu", json={"entries": [{"service_id": "svc-signature-cut", "is_offered": True, "price_override": None}]}, headers=owner_headers)

        # Derive class-unique slot/customer identifiers so we don't collide with
        # other test classes hitting the same shared salon-main stylists.
        suffix = manager_ctx["main_phone"][-4:]
        qa_stylist_phone = f"92050{suffix}"
        qa_cust_phone = f"93061{suffix}"
        main_cust_phone = f"93062{suffix}"

        # Create a stylist tied to QA salon + booking for isolation check
        stylist_payload = {"name": "TEST_QA_BandraStylist", "phone": qa_stylist_phone, "salon_id": qa_salon, "services": ["svc-signature-cut"], "working_hours": {str(i): {"open": "09:00", "close": "21:00"} for i in range(7)}, "is_active": True}
        rs = api.post(f"{BASE_URL}/api/owner/stylists", json=stylist_payload, headers=owner_headers)
        assert rs.status_code in (200, 201), rs.text
        state["qa_stylist_id"] = rs.json()["id"]

        # Class-unique + run-unique future date. Uses nanosecond-resolution
        # timestamp + class suffix so consecutive test runs (even in the same
        # second) never share a date, and no modular collision recurs.
        from datetime import date as _date, timedelta as _td
        import hashlib as _hl
        entropy = _hl.md5(f"{time.time_ns()}-{suffix}".encode()).hexdigest()
        day_offset = int(entropy[:6], 16) % 350 + 3
        booking_date = _date.today() + _td(days=day_offset)
        date = booking_date.isoformat()
        # Slot hour also randomized per-run so date-collision alone doesn't
        # cause an overlap on the shared salon-main stylist calendar.
        slot_hour = 9 + (int(entropy[6:8], 16) % 8)  # 09:XX .. 16:XX
        slot_qa = f"{slot_hour:02d}:00"
        slot_main = f"{(slot_hour + 2):02d}:00"  # non-overlapping window vs slot_qa
        booking_qa = {
            "customer_name": "TEST_QA_BandraCust",
            "customer_phone": qa_cust_phone,
            "service_id": "svc-signature-cut",
            "stylist_id": state["qa_stylist_id"],
            "date": date,
            "start_time": slot_qa,
        }
        rb = api.post(f"{BASE_URL}/api/bookings", json=booking_qa)
        assert rb.status_code == 200, rb.text
        state["qa_booking_id"] = rb.json().get("id") or rb.json().get("booking", {}).get("id")
        assert state["qa_booking_id"], rb.text

        # Also make a booking on salon-main
        stylists_main = api.get(f"{BASE_URL}/api/stylists").json()
        if isinstance(stylists_main, dict):
            stylists_main = stylists_main.get("stylists", [])
        main_stylist = None
        for s in stylists_main:
            if s.get("salon_id") in (None, "salon-main"):
                main_stylist = s
                break
        assert main_stylist, "no salon-main stylist to test with"
        booking_main = {
            "customer_name": "TEST_QA_MainCust",
            "customer_phone": main_cust_phone,
            "service_id": "svc-signature-cut",
            "stylist_id": main_stylist["id"],
            "date": date,
            "start_time": slot_main,
        }
        rb2 = api.post(f"{BASE_URL}/api/bookings", json=booking_main)
        assert rb2.status_code == 200, rb2.text
        state["main_booking_id"] = rb2.json().get("id") or rb2.json().get("booking", {}).get("id")
        state["qa_cust_phone"] = qa_cust_phone
        state["main_cust_phone"] = main_cust_phone

        # QA manager sees only QA booking
        r = api.get(f"{BASE_URL}/api/manager/bookings?date={date}", headers=self._qh(manager_ctx))
        assert r.status_code == 200, r.text
        ids = [b["id"] for b in r.json()["bookings"]]
        assert state["qa_booking_id"] in ids
        assert state["main_booking_id"] not in ids

        # Main manager sees only main booking
        r2 = api.get(f"{BASE_URL}/api/manager/bookings?date={date}", headers=self._mh(manager_ctx))
        assert r2.status_code == 200
        ids2 = [b["id"] for b in r2.json()["bookings"]]
        assert state["main_booking_id"] in ids2
        assert state["qa_booking_id"] not in ids2

    def test_manager_revenue_insights(self, api, manager_ctx):
        r = api.get(f"{BASE_URL}/api/manager/revenue-insights?period=week", headers=self._mh(manager_ctx))
        assert r.status_code == 200, r.text
        body = r.json()
        assert "kpis" in body
        assert "status_counts" in body
        assert "revenue_series" in body

    def test_manager_no_shows(self, api, manager_ctx):
        r = api.get(f"{BASE_URL}/api/manager/no-shows?month=2027-01", headers=self._mh(manager_ctx))
        assert r.status_code == 200, r.text
        body = r.json()
        # must be same shape as owner endpoint
        assert "month" in body or "month_label" in body

    def test_manager_customers_search(self, api, manager_ctx):
        r = api.get(f"{BASE_URL}/api/manager/customers/search", headers=self._mh(manager_ctx))
        assert r.status_code == 200
        assert "customers" in r.json()

    def test_manager_customer_profile_not_at_salon(self, api, state, manager_ctx):
        # QA manager should not see the salon-main customer
        r = api.get(f"{BASE_URL}/api/manager/customers/{state['main_cust_phone']}", headers=self._qh(manager_ctx))
        assert r.status_code == 404
        assert "not seen" in r.text.lower()

    def test_manager_customer_profile_at_salon(self, api, state, manager_ctx):
        r = api.get(f"{BASE_URL}/api/manager/customers/{state['qa_cust_phone']}", headers=self._qh(manager_ctx))
        assert r.status_code == 200, r.text

    def test_manager_patch_booking_status_own_salon(self, api, state, manager_ctx):
        r = api.patch(f"{BASE_URL}/api/manager/bookings/{state['qa_booking_id']}/status", json={"status": "done"}, headers=self._qh(manager_ctx))
        assert r.status_code == 200, r.text
        assert r.json()["booking"]["status"] == "done"

    def test_manager_patch_booking_status_other_salon(self, api, state, manager_ctx):
        # QA manager tries to change salon-main booking status
        r = api.patch(f"{BASE_URL}/api/manager/bookings/{state['main_booking_id']}/status", json={"status": "done"}, headers=self._qh(manager_ctx))
        assert r.status_code == 404


# --------- Cross-role authorization ---------

class TestCrossRoleAuth:
    def test_owner_token_on_manager_me(self, api, owner_headers):
        r = api.get(f"{BASE_URL}/api/manager/me", headers=owner_headers)
        assert r.status_code == 401

    def test_manager_token_on_owner_salons(self, api, manager_ctx):
        headers = {"Authorization": f"Bearer {manager_ctx['main_token']}"}
        r = api.get(f"{BASE_URL}/api/owner/salons", headers=headers)
        assert r.status_code == 401

    def test_manager_token_on_owner_stylists(self, api, manager_ctx):
        headers = {"Authorization": f"Bearer {manager_ctx['main_token']}"}
        r = api.get(f"{BASE_URL}/api/owner/stylists", headers=headers)
        assert r.status_code == 401

    def test_manager_token_on_owner_managers(self, api, manager_ctx):
        headers = {"Authorization": f"Bearer {manager_ctx['main_token']}"}
        r = api.get(f"{BASE_URL}/api/owner/managers", headers=headers)
        assert r.status_code == 401

    def test_manager_token_on_owner_services(self, api, manager_ctx):
        headers = {"Authorization": f"Bearer {manager_ctx['main_token']}"}
        r = api.get(f"{BASE_URL}/api/owner/services", headers=headers)
        assert r.status_code == 401


# --------- Archive falls through to customer ---------

class TestArchiveFallthrough:
    def test_archive_then_login_falls_through(self, api, owner_headers, manager_ctx):
        main_phone = manager_ctx["main_phone"]
        # Archive main manager
        r = api.post(f"{BASE_URL}/api/owner/managers/{manager_ctx['main_id']}/archive", headers=owner_headers)
        assert r.status_code == 200
        assert r.json().get("ok") is True

        # Verify in list is_active=false
        rl = api.get(f"{BASE_URL}/api/owner/managers", headers=owner_headers)
        entry = next((m for m in rl.json()["managers"] if m["id"] == manager_ctx["main_id"]), None)
        assert entry is not None
        assert entry.get("is_active") is False

        # OTP login should now fall through to customer role
        r1 = api.post(f"{BASE_URL}/api/login/request-otp", json={"phone": main_phone})
        otp = r1.json()["mock_otp"]
        r2 = api.post(f"{BASE_URL}/api/login/verify-otp", json={"phone": main_phone, "otp": otp})
        assert r2.status_code == 200
        assert r2.json().get("role") == "customer"


# --------- Cleanup ---------
# Per-class managers are archived in the ``manager_ctx`` fixture teardown.
# Stylist / salon rows created inside individual test bodies are left in the
# DB — subsequent runs are idempotent because ``_ensure_manager`` archives-
# then-creates and each class uses its own class-unique login phones.
