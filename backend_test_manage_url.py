#!/usr/bin/env python3
"""
Backend test for manage_url domain fix.
Tests that booking.manage_url uses public preview domain, not internal cluster domain.
"""
import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "https://go-run-3.preview.emergentagent.com/api"
PUBLIC_DOMAIN = "go-run-3.preview.emergentagent.com"
INTERNAL_CLUSTER_DOMAIN = "go-run-3.cluster-12.preview.emergentcf.cloud"
OWNER_PIN = "9999"

# Test results tracking
tests_passed = 0
tests_failed = 0
test_results = []


def log_test(name, passed, details=""):
    global tests_passed, tests_failed
    if passed:
        tests_passed += 1
        status = "✅ PASS"
    else:
        tests_failed += 1
        status = "❌ FAIL"
    result = f"{status}: {name}"
    if details:
        result += f"\n    {details}"
    test_results.append(result)
    print(result)


def owner_login():
    """Login as owner and return auth token."""
    url = f"{BASE_URL}/owner/login"
    response = requests.post(url, json={"pin": OWNER_PIN})
    if response.status_code == 200:
        data = response.json()
        return data.get("token")
    return None


def test_manage_url_with_forwarded_headers():
    """Test 1: Booking with x-forwarded-host returns public domain in manage_url."""
    print("\n=== Test 1: manage_url with x-forwarded-host header ===")
    
    # Get available slot
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    avail_url = f"{BASE_URL}/availability"
    params = {
        "date": tomorrow,
        "service_id": "svc-signature-cut",
        "stylist_id": "stylist-elena"
    }
    avail_response = requests.get(avail_url, params=params)
    
    if avail_response.status_code != 200 or not avail_response.json().get("slots"):
        log_test("Get available slot", False, f"No slots available for {tomorrow}")
        return None
    
    slot = avail_response.json()["slots"][0]
    
    # Create booking with realistic browser-like headers
    # Simulating Kubernetes ingress forwarding headers
    booking_url = f"{BASE_URL}/bookings"
    booking_data = {
        "customer_name": "Priya Sharma",
        "customer_phone": "+919876543210",
        "service_id": "svc-signature-cut",
        "stylist_id": "stylist-elena",
        "date": tomorrow,
        "start_time": slot["start_time"]
    }
    
    # Headers that would come from Kubernetes ingress
    headers = {
        "x-forwarded-host": PUBLIC_DOMAIN,
        "x-forwarded-proto": "https",
        "origin": f"https://{INTERNAL_CLUSTER_DOMAIN}",  # Internal origin should be ignored
        "host": INTERNAL_CLUSTER_DOMAIN  # Internal host should be ignored
    }
    
    response = requests.post(booking_url, json=booking_data, headers=headers)
    
    if response.status_code != 200:
        log_test("Create booking with forwarded headers", False, 
                f"Status: {response.status_code}, Response: {response.text}")
        return None
    
    booking = response.json()
    log_test("Create booking with forwarded headers", True, 
            f"Booking ID: {booking.get('booking_id')}")
    
    # Check manage_url exists
    manage_url = booking.get("manage_url")
    if not manage_url:
        log_test("manage_url exists", False, "manage_url not found in booking response")
        return None
    
    log_test("manage_url exists", True, f"manage_url: {manage_url}")
    
    # Check manage_url uses public domain, not internal cluster domain
    uses_public_domain = PUBLIC_DOMAIN in manage_url
    uses_internal_domain = INTERNAL_CLUSTER_DOMAIN in manage_url
    
    log_test("manage_url uses public domain", uses_public_domain,
            f"Expected domain: {PUBLIC_DOMAIN}, manage_url: {manage_url}")
    
    log_test("manage_url does NOT use internal cluster domain", not uses_internal_domain,
            f"Should NOT contain: {INTERNAL_CLUSTER_DOMAIN}, manage_url: {manage_url}")
    
    # Check manage_url path format
    manage_token = booking.get("manage_token")
    expected_path = f"/manage/{manage_token}"
    has_correct_path = expected_path in manage_url
    
    log_test("manage_url path is /manage/{token}", has_correct_path,
            f"Expected path: {expected_path}, manage_url: {manage_url}")
    
    # Check manage_token matches
    log_test("manage_token matches URL token", manage_token is not None and manage_token in manage_url,
            f"manage_token: {manage_token}")
    
    return booking


def test_manage_url_without_forwarded_headers():
    """Test 2: Booking without x-forwarded-host falls back to origin parsing."""
    print("\n=== Test 2: manage_url without x-forwarded-host (origin fallback) ===")
    
    # Get available slot
    tomorrow = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    avail_url = f"{BASE_URL}/availability"
    params = {
        "date": tomorrow,
        "service_id": "svc-hair-wash",
        "stylist_id": "stylist-sarah"
    }
    avail_response = requests.get(avail_url, params=params)
    
    if avail_response.status_code != 200 or not avail_response.json().get("slots"):
        log_test("Get available slot for fallback test", False, f"No slots available for {tomorrow}")
        return None
    
    slot = avail_response.json()["slots"][0]
    
    # Create booking with only origin header (no x-forwarded-host)
    booking_url = f"{BASE_URL}/bookings"
    booking_data = {
        "customer_name": "Rahul Kumar",
        "customer_phone": "+919876543211",
        "service_id": "svc-hair-wash",
        "stylist_id": "stylist-sarah",
        "date": tomorrow,
        "start_time": slot["start_time"]
    }
    
    # Headers without x-forwarded-host (simulating direct access)
    headers = {
        "origin": f"https://{PUBLIC_DOMAIN}"
    }
    
    response = requests.post(booking_url, json=booking_data, headers=headers)
    
    if response.status_code != 200:
        log_test("Create booking with origin header only", False, 
                f"Status: {response.status_code}, Response: {response.text}")
        return None
    
    booking = response.json()
    log_test("Create booking with origin header only", True, 
            f"Booking ID: {booking.get('booking_id')}")
    
    # Check manage_url exists and uses origin domain
    manage_url = booking.get("manage_url")
    if not manage_url:
        log_test("manage_url exists (origin fallback)", False, "manage_url not found")
        return None
    
    log_test("manage_url exists (origin fallback)", True, f"manage_url: {manage_url}")
    
    # Should use public domain from origin
    uses_public_domain = PUBLIC_DOMAIN in manage_url
    log_test("manage_url uses origin domain", uses_public_domain,
            f"Expected domain: {PUBLIC_DOMAIN}, manage_url: {manage_url}")
    
    return booking


def test_manage_endpoint_works(booking):
    """Test 3: GET /api/customer/manage/{token} still works."""
    print("\n=== Test 3: Customer manage endpoint ===")
    
    if not booking:
        log_test("Customer manage endpoint (skipped)", False, "No booking to test")
        return
    
    manage_token = booking.get("manage_token")
    if not manage_token:
        log_test("Customer manage endpoint", False, "No manage_token in booking")
        return
    
    manage_url = f"{BASE_URL}/customer/manage/{manage_token}"
    response = requests.get(manage_url)
    
    if response.status_code != 200:
        log_test("GET /api/customer/manage/{token}", False,
                f"Status: {response.status_code}, Response: {response.text}")
        return
    
    data = response.json()
    log_test("GET /api/customer/manage/{token}", True,
            f"Retrieved booking for {data.get('customer_name')}")
    
    # Check response has required fields
    required_fields = ["booking_id", "customer_name", "service_name", "stylist_name", 
                      "date", "start_time", "status", "cancellation_policy_notice"]
    missing_fields = [f for f in required_fields if f not in data]
    
    log_test("Manage response has required fields", len(missing_fields) == 0,
            f"Missing fields: {missing_fields}" if missing_fields else "All fields present")
    
    # Check no ObjectId serialization
    response_text = response.text
    has_objectid = "ObjectId(" in response_text or '"_id"' in response_text
    log_test("No ObjectId serialization in manage response", not has_objectid,
            "Found ObjectId serialization" if has_objectid else "Clean JSON response")


def test_invalid_token():
    """Test 4: Invalid manage token returns 404."""
    print("\n=== Test 4: Invalid manage token ===")
    
    invalid_token = "invalid-token-12345"
    manage_url = f"{BASE_URL}/customer/manage/{invalid_token}"
    response = requests.get(manage_url)
    
    passed = response.status_code == 404
    log_test("Invalid manage token returns 404", passed,
            f"Status: {response.status_code}")


def test_cancel_endpoint(booking):
    """Test 5: POST /api/customer/manage/{token}/cancel still works."""
    print("\n=== Test 5: Customer cancel endpoint ===")
    
    if not booking:
        log_test("Customer cancel endpoint (skipped)", False, "No booking to test")
        return
    
    manage_token = booking.get("manage_token")
    if not manage_token:
        log_test("Customer cancel endpoint", False, "No manage_token in booking")
        return
    
    cancel_url = f"{BASE_URL}/customer/manage/{manage_token}/cancel"
    cancel_data = {
        "reason": "schedule_conflict",
        "note": "Testing cancel endpoint after domain fix"
    }
    
    response = requests.post(cancel_url, json=cancel_data)
    
    if response.status_code != 200:
        log_test("POST /api/customer/manage/{token}/cancel", False,
                f"Status: {response.status_code}, Response: {response.text}")
        return
    
    data = response.json()
    log_test("POST /api/customer/manage/{token}/cancel", True,
            f"Cancelled booking, status: {data.get('status')}")
    
    # Verify status is cancelled
    is_cancelled = data.get("status") == "cancelled"
    log_test("Booking status is cancelled", is_cancelled,
            f"Status: {data.get('status')}")
    
    # Check cancellation fields
    has_cancellation_fields = all(k in data for k in ["cancelled_by", "cancelled_at", "cancellation_reason"])
    log_test("Cancellation fields present", has_cancellation_fields,
            f"cancelled_by: {data.get('cancelled_by')}, reason: {data.get('cancellation_reason')}")


def test_reschedule_endpoint():
    """Test 6: POST /api/customer/manage/{token}/reschedule still works."""
    print("\n=== Test 6: Customer reschedule endpoint ===")
    
    # Create a new booking for reschedule test
    tomorrow = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    avail_url = f"{BASE_URL}/availability"
    params = {
        "date": tomorrow,
        "service_id": "svc-signature-cut",
        "stylist_id": "stylist-elena"
    }
    avail_response = requests.get(avail_url, params=params)
    
    if avail_response.status_code != 200 or not avail_response.json().get("slots"):
        log_test("Get slot for reschedule test", False, f"No slots available")
        return
    
    slot = avail_response.json()["slots"][0]
    
    # Create booking
    booking_url = f"{BASE_URL}/bookings"
    booking_data = {
        "customer_name": "Anjali Verma",
        "customer_phone": "+919876543212",
        "service_id": "svc-signature-cut",
        "stylist_id": "stylist-elena",
        "date": tomorrow,
        "start_time": slot["start_time"]
    }
    
    headers = {
        "x-forwarded-host": PUBLIC_DOMAIN,
        "x-forwarded-proto": "https"
    }
    
    response = requests.post(booking_url, json=booking_data, headers=headers)
    
    if response.status_code != 200:
        log_test("Create booking for reschedule test", False, f"Status: {response.status_code}")
        return
    
    booking = response.json()
    manage_token = booking.get("manage_token")
    log_test("Create booking for reschedule test", True, f"Booking ID: {booking.get('booking_id')}")
    
    # Get new slot for reschedule
    new_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    params["date"] = new_date
    avail_response = requests.get(avail_url, params=params)
    
    if avail_response.status_code != 200 or not avail_response.json().get("slots"):
        log_test("Get new slot for reschedule", False, f"No slots available")
        return
    
    new_slot = avail_response.json()["slots"][0]
    
    # Reschedule booking
    reschedule_url = f"{BASE_URL}/customer/manage/{manage_token}/reschedule"
    reschedule_data = {
        "new_date": new_date,
        "new_start_time": new_slot["start_time"]
    }
    
    response = requests.post(reschedule_url, json=reschedule_data)
    
    if response.status_code != 200:
        log_test("POST /api/customer/manage/{token}/reschedule", False,
                f"Status: {response.status_code}, Response: {response.text}")
        return
    
    data = response.json()
    log_test("POST /api/customer/manage/{token}/reschedule", True,
            f"Rescheduled to {data.get('date')} at {data.get('start_time')}")
    
    # Verify new date and time
    date_updated = data.get("date") == new_date
    time_updated = data.get("start_time") == new_slot["start_time"]
    
    log_test("Booking date updated", date_updated,
            f"New date: {data.get('date')}")
    log_test("Booking time updated", time_updated,
            f"New time: {data.get('start_time')}")


def test_owner_notifications():
    """Test 7: Owner notifications API still works."""
    print("\n=== Test 7: Owner notifications ===")
    
    token = owner_login()
    if not token:
        log_test("Owner login for notifications", False, "Failed to get owner token")
        return
    
    log_test("Owner login for notifications", True, f"Token: {token[:20]}...")
    
    notifications_url = f"{BASE_URL}/owner/notifications"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(notifications_url, headers=headers)
    
    if response.status_code != 200:
        log_test("GET /api/owner/notifications", False,
                f"Status: {response.status_code}, Response: {response.text}")
        return
    
    data = response.json()
    log_test("GET /api/owner/notifications", True,
            f"Unread count: {data.get('unread_count')}, Total notifications: {len(data.get('notifications', []))}")
    
    # Check response structure
    has_required_fields = "notifications" in data and "unread_count" in data
    log_test("Notifications response has required fields", has_required_fields,
            f"Fields: {list(data.keys())}")
    
    # Check no ObjectId serialization
    response_text = response.text
    has_objectid = "ObjectId(" in response_text or '"_id"' in response_text
    log_test("No ObjectId in notifications response", not has_objectid,
            "Found ObjectId serialization" if has_objectid else "Clean JSON response")


def test_owner_login_returns_token():
    """Test 8: Owner login still returns a token (regression check)."""
    print("\n=== Test 8: Owner login regression check ===")
    
    token = owner_login()
    
    if not token:
        log_test("Owner login returns token", False, "No token returned")
        return
    
    log_test("Owner login returns token", True, f"Token: {token[:20]}...")
    
    # Verify token is a non-empty string
    is_valid_token = isinstance(token, str) and len(token) > 0
    log_test("Token is valid string", is_valid_token,
            f"Token type: {type(token)}, length: {len(token) if token else 0}")


def main():
    print("=" * 80)
    print("Backend Test: manage_url Domain Fix")
    print("=" * 80)
    print(f"Testing against: {BASE_URL}")
    print(f"Public domain: {PUBLIC_DOMAIN}")
    print(f"Internal cluster domain (should NOT appear): {INTERNAL_CLUSTER_DOMAIN}")
    print("=" * 80)
    
    # Run tests
    booking1 = test_manage_url_with_forwarded_headers()
    booking2 = test_manage_url_without_forwarded_headers()
    test_manage_endpoint_works(booking1)
    test_invalid_token()
    test_cancel_endpoint(booking2)
    test_reschedule_endpoint()
    test_owner_notifications()
    test_owner_login_returns_token()
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    for result in test_results:
        print(result)
    print("=" * 80)
    print(f"Total: {tests_passed + tests_failed} tests")
    print(f"✅ Passed: {tests_passed}")
    print(f"❌ Failed: {tests_failed}")
    print("=" * 80)
    
    if tests_failed == 0:
        print("\n🎉 All tests passed! manage_url domain fix is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {tests_failed} test(s) failed. Please review the failures above.")
        return 1


if __name__ == "__main__":
    exit(main())
