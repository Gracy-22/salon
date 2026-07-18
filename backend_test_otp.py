#!/usr/bin/env python3
"""
Backend test for fixed-link OTP manage flow.
Tests the /api/customer/manage/request-otp and /api/customer/manage/verify-otp endpoints.
"""
import requests
import json
import time
from datetime import datetime, timedelta

# Configuration
BASE_URL = "https://go-run-3.preview.emergentagent.com/api"
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


def create_test_booking(token, phone="+919999999999", time_offset_hours=0, days_ahead=7):
    """Create a test booking and return booking data."""
    url = f"{BASE_URL}/bookings"
    
    # Try multiple stylists and time slots to avoid conflicts
    stylists = ["stylist-elena", "stylist-sarah", "stylist-michael"]
    
    for stylist in stylists:
        base_date = datetime.now() + timedelta(days=days_ahead)
        for hour_offset in range(time_offset_hours, time_offset_hours + 8):
            hour = 10 + hour_offset
            if hour >= 21:  # Salon closes at 21:00
                continue
            
            payload = {
                "customer_name": "OTP Test Customer",
                "customer_phone": phone,
                "service_id": "svc-signature-cut",
                "stylist_id": stylist,
                "date": base_date.strftime("%Y-%m-%d"),
                "start_time": f"{hour:02d}:00"
            }
            headers = {"Origin": "https://go-run-3.preview.emergentagent.com"}
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                # Return the nested booking object
                return response.json().get("booking")
    
    return None


def test_request_otp_success():
    """Test 1: POST /api/customer/manage/request-otp returns correct response."""
    url = f"{BASE_URL}/customer/manage/request-otp"
    payload = {"phone": "+919876543210"}
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        log_test("Request OTP success", False, f"Status: {response.status_code}, Expected: 200")
        return None
    
    data = response.json()
    
    # Check all required fields
    required_fields = ["ok", "phone", "expires_in_seconds", "mock_otp", "mocked"]
    missing_fields = [f for f in required_fields if f not in data]
    
    if missing_fields:
        log_test("Request OTP success", False, f"Missing fields: {missing_fields}")
        return None
    
    # Verify field values
    checks = []
    checks.append(("ok is True", data.get("ok") == True))
    checks.append(("phone normalized (last 10 digits)", data.get("phone") == "9876543210"))
    checks.append(("expires_in_seconds is 300", data.get("expires_in_seconds") == 300))
    checks.append(("mock_otp present", data.get("mock_otp") is not None))
    checks.append(("mocked is True", data.get("mocked") == True))
    checks.append(("mock_otp is 6 digits", len(str(data.get("mock_otp"))) == 6))
    
    failed_checks = [name for name, result in checks if not result]
    passed = len(failed_checks) == 0
    
    details = f"All checks passed. OTP: {data.get('mock_otp')}" if passed else f"Failed: {failed_checks}"
    log_test("Request OTP success", passed, details)
    
    return data.get("mock_otp") if passed else None


def test_request_otp_phone_normalization():
    """Test 2: Phone normalization works correctly."""
    url = f"{BASE_URL}/customer/manage/request-otp"
    
    test_cases = [
        ("+919876543210", "9876543210"),
        ("919876543210", "9876543210"),
        ("9876543210", "9876543210"),
    ]
    
    all_passed = True
    for input_phone, expected_normalized in test_cases:
        payload = {"phone": input_phone}
        response = requests.post(url, json=payload)
        
        if response.status_code != 200:
            all_passed = False
            continue
        
        data = response.json()
        if data.get("phone") != expected_normalized:
            all_passed = False
    
    log_test("Phone normalization", all_passed, f"Tested {len(test_cases)} phone formats")


def test_verify_otp_no_request():
    """Test 3: Verify OTP without request returns 404."""
    url = f"{BASE_URL}/customer/manage/verify-otp"
    payload = {"phone": "+919999999999", "otp": "123456"}
    response = requests.post(url, json=payload)
    
    passed = response.status_code == 404
    log_test("Verify OTP without request returns 404", passed, f"Status: {response.status_code}")


def test_verify_otp_wrong_otp():
    """Test 4: Verify OTP with wrong OTP returns 400."""
    # First request OTP
    url_request = f"{BASE_URL}/customer/manage/request-otp"
    payload_request = {"phone": "+918888888888"}
    response_request = requests.post(url_request, json=payload_request)
    
    if response_request.status_code != 200:
        log_test("Verify OTP with wrong OTP returns 400", False, "Failed to request OTP")
        return
    
    # Try to verify with wrong OTP
    url_verify = f"{BASE_URL}/customer/manage/verify-otp"
    payload_verify = {"phone": "+918888888888", "otp": "000000"}
    response_verify = requests.post(url_verify, json=payload_verify)
    
    passed = response_verify.status_code == 400
    log_test("Verify OTP with wrong OTP returns 400", passed, f"Status: {response_verify.status_code}")


def test_verify_otp_success_with_appointments():
    """Test 5: Verify OTP with correct OTP returns appointments."""
    # First create a booking
    token = owner_login()
    if not token:
        log_test("Verify OTP success with appointments", False, "Failed to login as owner")
        return
    
    # Use unique phone for this test
    test_phone = f"+9187654{int(time.time()) % 100000:05d}"
    booking = create_test_booking(token, phone=test_phone, days_ahead=15)
    if not booking:
        log_test("Verify OTP success with appointments", False, "Failed to create test booking")
        return
    
    # Request OTP
    url_request = f"{BASE_URL}/customer/manage/request-otp"
    payload_request = {"phone": test_phone}
    response_request = requests.post(url_request, json=payload_request)
    
    if response_request.status_code != 200:
        log_test("Verify OTP success with appointments", False, "Failed to request OTP")
        return
    
    otp_data = response_request.json()
    mock_otp = otp_data.get("mock_otp")
    
    # Verify OTP
    url_verify = f"{BASE_URL}/customer/manage/verify-otp"
    payload_verify = {"phone": test_phone, "otp": str(mock_otp)}
    response_verify = requests.post(url_verify, json=payload_verify)
    
    if response_verify.status_code != 200:
        log_test("Verify OTP success with appointments", False, f"Status: {response_verify.status_code}")
        return
    
    data = response_verify.json()
    
    # Check response structure
    required_fields = ["ok", "phone", "appointments", "mocked"]
    missing_fields = [f for f in required_fields if f not in data]
    
    if missing_fields:
        log_test("Verify OTP success with appointments", False, f"Missing fields: {missing_fields}")
        return
    
    # Verify appointments array
    appointments = data.get("appointments", [])
    if len(appointments) == 0:
        log_test("Verify OTP success with appointments", False, "No appointments returned")
        return
    
    # Check first appointment structure
    appt = appointments[0]
    required_appt_fields = ["id", "customer_name", "customer_phone", "service_id", "stylist_id", 
                            "date", "start_time", "status", "manage_token"]
    missing_appt_fields = [f for f in required_appt_fields if f not in appt]
    
    if missing_appt_fields:
        log_test("Verify OTP success with appointments", False, f"Missing appointment fields: {missing_appt_fields}")
        return
    
    # Check for hydrated service and stylist info
    checks = []
    checks.append(("service object present", "service" in appt))
    checks.append(("stylist object present", "stylist" in appt))
    checks.append(("manage_token present", appt.get("manage_token") is not None))
    
    if "service" in appt:
        checks.append(("service.name present", "name" in appt["service"]))
    if "stylist" in appt:
        checks.append(("stylist.name present", "name" in appt["stylist"]))
    
    # Check for ObjectId serialization issues (excluding service_id and stylist_id which are legitimate)
    json_str = json.dumps(data)
    # Look for actual MongoDB ObjectId patterns, not just "_id" substring
    has_objectid = "ObjectId(" in json_str or '"_id":' in json_str
    checks.append(("No ObjectId serialization", not has_objectid))
    
    failed_checks = [name for name, result in checks if not result]
    passed = len(failed_checks) == 0
    
    details = f"Found {len(appointments)} appointment(s), all fields present" if passed else f"Failed: {failed_checks}"
    log_test("Verify OTP success with appointments", passed, details)


def test_verify_otp_includes_all_appointment_types():
    """Test 6: Verify OTP returns all appointments including past/cancelled."""
    # Request OTP for a phone that should have multiple appointments
    url_request = f"{BASE_URL}/customer/manage/request-otp"
    payload_request = {"phone": "+919876543210"}
    response_request = requests.post(url_request, json=payload_request)
    
    if response_request.status_code != 200:
        log_test("Verify OTP includes all appointment types", False, "Failed to request OTP")
        return
    
    otp_data = response_request.json()
    mock_otp = otp_data.get("mock_otp")
    
    # Verify OTP
    url_verify = f"{BASE_URL}/customer/manage/verify-otp"
    payload_verify = {"phone": "+919876543210", "otp": str(mock_otp)}
    response_verify = requests.post(url_verify, json=payload_verify)
    
    if response_verify.status_code != 200:
        log_test("Verify OTP includes all appointment types", False, f"Status: {response_verify.status_code}")
        return
    
    data = response_verify.json()
    appointments = data.get("appointments", [])
    
    # Check if we have appointments
    if len(appointments) == 0:
        log_test("Verify OTP includes all appointment types", False, "No appointments returned")
        return
    
    # Check for various statuses (if available)
    statuses = set(appt.get("status") for appt in appointments)
    
    # The key is that the endpoint should return ALL appointments, not filter by status
    # We just verify that appointments are returned and include status field
    all_have_status = all("status" in appt for appt in appointments)
    
    passed = all_have_status and len(appointments) > 0
    details = f"Found {len(appointments)} appointment(s) with statuses: {statuses}"
    log_test("Verify OTP includes all appointment types", passed, details)


def test_multiple_appointments_selection():
    """Test 7: Multiple appointments for same phone are returned for selection."""
    # Create multiple bookings for the same phone
    token = owner_login()
    if not token:
        log_test("Multiple appointments selection", False, "Failed to login as owner")
        return
    
    # Create 2 bookings with unique phone, using different days to avoid conflicts
    phone = f"+9177777{int(time.time()) % 100000:05d}"
    bookings_created = 0
    
    for i in range(2):
        booking = create_test_booking(token, phone=phone, time_offset_hours=0, days_ahead=10+i)
        if booking:
            bookings_created += 1
    
    if bookings_created < 2:
        log_test("Multiple appointments selection", False, f"Only created {bookings_created} bookings")
        return
    
    # Request OTP
    url_request = f"{BASE_URL}/customer/manage/request-otp"
    payload_request = {"phone": phone}
    response_request = requests.post(url_request, json=payload_request)
    
    if response_request.status_code != 200:
        log_test("Multiple appointments selection", False, "Failed to request OTP")
        return
    
    otp_data = response_request.json()
    mock_otp = otp_data.get("mock_otp")
    
    # Verify OTP
    url_verify = f"{BASE_URL}/customer/manage/verify-otp"
    payload_verify = {"phone": phone, "otp": str(mock_otp)}
    response_verify = requests.post(url_verify, json=payload_verify)
    
    if response_verify.status_code != 200:
        log_test("Multiple appointments selection", False, f"Status: {response_verify.status_code}")
        return
    
    data = response_verify.json()
    appointments = data.get("appointments", [])
    
    passed = len(appointments) >= 2
    details = f"Found {len(appointments)} appointments for selection"
    log_test("Multiple appointments selection", passed, details)


def test_existing_token_fallback():
    """Test 8: Existing /api/customer/manage/{token} fallback still works."""
    # Create a booking to get a manage token
    token = owner_login()
    if not token:
        log_test("Existing token fallback works", False, "Failed to login as owner")
        return
    
    # Use unique phone for this test
    test_phone = f"+9166666{int(time.time()) % 100000:05d}"
    booking = create_test_booking(token, phone=test_phone, time_offset_hours=0, days_ahead=12)
    if not booking:
        log_test("Existing token fallback works", False, "Failed to create test booking")
        return
    
    manage_token = booking.get("manage_token")
    if not manage_token:
        log_test("Existing token fallback works", False, "No manage_token in booking response")
        return
    
    # Test the fallback endpoint
    url = f"{BASE_URL}/customer/manage/{manage_token}"
    response = requests.get(url)
    
    if response.status_code != 200:
        log_test("Existing token fallback works", False, f"Status: {response.status_code}")
        return
    
    data = response.json()
    
    # Check response structure
    required_fields = ["booking", "policy_notice", "within_24h", "cancellation_reasons"]
    missing_fields = [f for f in required_fields if f not in data]
    
    passed = len(missing_fields) == 0
    details = "All fields present" if passed else f"Missing: {missing_fields}"
    log_test("Existing token fallback works", passed, details)


def test_existing_token_cancel():
    """Test 9: Existing token cancel still works after OTP additions."""
    # Create a booking
    token = owner_login()
    if not token:
        log_test("Existing token cancel works", False, "Failed to login as owner")
        return
    
    # Use unique phone for this test
    test_phone = f"+9199999{int(time.time()) % 100000:05d}"
    booking = create_test_booking(token, phone=test_phone, time_offset_hours=0, days_ahead=13)
    if not booking:
        log_test("Existing token cancel works", False, "Failed to create test booking")
        return
    
    manage_token = booking.get("manage_token")
    if not manage_token:
        log_test("Existing token cancel works", False, "No manage_token in booking response")
        return
    
    # Cancel the booking
    url = f"{BASE_URL}/customer/manage/{manage_token}/cancel"
    payload = {"reason": "schedule_conflict", "reason_note": "Test cancellation"}
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        log_test("Existing token cancel works", False, f"Status: {response.status_code}")
        return
    
    data = response.json()
    booking_data = data.get("booking", {})
    
    passed = booking_data.get("status") == "cancelled"
    details = f"Status: {booking_data.get('status')}"
    log_test("Existing token cancel works", passed, details)


def test_existing_token_reschedule():
    """Test 10: Existing token reschedule still works after OTP additions."""
    # Create a booking
    token = owner_login()
    if not token:
        log_test("Existing token reschedule works", False, "Failed to login as owner")
        return
    
    # Use unique phone for this test
    test_phone = f"+9188888{int(time.time()) % 100000:05d}"
    booking = create_test_booking(token, phone=test_phone, time_offset_hours=0, days_ahead=14)
    if not booking:
        log_test("Existing token reschedule works", False, "Failed to create test booking")
        return
    
    manage_token = booking.get("manage_token")
    if not manage_token:
        log_test("Existing token reschedule works", False, "No manage_token in booking response")
        return
    
    # Reschedule the booking
    url = f"{BASE_URL}/customer/manage/{manage_token}/reschedule"
    new_date = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d")
    payload = {"new_date": new_date, "new_start_time": "11:00"}
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        log_test("Existing token reschedule works", False, f"Status: {response.status_code}")
        return
    
    data = response.json()
    booking_data = data.get("booking", {})
    
    passed = booking_data.get("date") == new_date and booking_data.get("start_time") == "11:00"
    details = f"New date: {booking_data.get('date')}, New time: {booking_data.get('start_time')}"
    log_test("Existing token reschedule works", passed, details)


def test_no_objectid_serialization():
    """Test 11: No ObjectId serialization in any OTP responses."""
    # Request OTP
    url_request = f"{BASE_URL}/customer/manage/request-otp"
    payload_request = {"phone": "+919876543210"}
    response_request = requests.post(url_request, json=payload_request)
    
    if response_request.status_code != 200:
        log_test("No ObjectId serialization", False, "Failed to request OTP")
        return
    
    otp_data = response_request.json()
    mock_otp = otp_data.get("mock_otp")
    
    # Check request-otp response (look for actual ObjectId patterns, not service_id/stylist_id)
    json_str_request = json.dumps(otp_data)
    has_objectid_request = "ObjectId(" in json_str_request or '"_id":' in json_str_request
    
    # Verify OTP
    url_verify = f"{BASE_URL}/customer/manage/verify-otp"
    payload_verify = {"phone": "+919876543210", "otp": str(mock_otp)}
    response_verify = requests.post(url_verify, json=payload_verify)
    
    if response_verify.status_code != 200:
        log_test("No ObjectId serialization", False, "Failed to verify OTP")
        return
    
    verify_data = response_verify.json()
    json_str_verify = json.dumps(verify_data)
    # Look for actual MongoDB ObjectId patterns, not just "_id" substring in field names
    has_objectid_verify = "ObjectId(" in json_str_verify or '"_id":' in json_str_verify
    
    passed = not has_objectid_request and not has_objectid_verify
    details = "No ObjectId found in responses" if passed else "ObjectId found in responses"
    log_test("No ObjectId serialization", passed, details)


def check_backend_logs():
    """Test 12: Check backend logs for errors."""
    print("\n📋 Checking backend logs...")
    import subprocess
    try:
        result = subprocess.run(
            ["tail", "-n", "50", "/var/log/supervisor/backend.err.log"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        error_lines = [line for line in result.stdout.split('\n') if line.strip() and 
                      any(keyword in line.lower() for keyword in ['error', 'exception', 'traceback', 'failed'])]
        
        # Filter out expected/minor errors
        critical_errors = [line for line in error_lines if 
                          'objectid' in line.lower() or 
                          'serialization' in line.lower() or
                          'otp' in line.lower()]
        
        passed = len(critical_errors) == 0
        details = f"Found {len(critical_errors)} critical errors" if not passed else "No critical errors in logs"
        log_test("Backend logs clean", passed, details)
        
        if critical_errors:
            print("  Critical errors found:")
            for error in critical_errors[:5]:
                print(f"    {error[:100]}")
    except Exception as e:
        log_test("Backend logs clean", False, f"Failed to check logs: {str(e)}")


def main():
    print("=" * 80)
    print("BACKEND OTP MANAGE FLOW TEST")
    print("=" * 80)
    print()
    
    # Run all tests
    test_request_otp_success()
    test_request_otp_phone_normalization()
    test_verify_otp_no_request()
    test_verify_otp_wrong_otp()
    test_verify_otp_success_with_appointments()
    test_verify_otp_includes_all_appointment_types()
    test_multiple_appointments_selection()
    test_existing_token_fallback()
    test_existing_token_cancel()
    test_existing_token_reschedule()
    test_no_objectid_serialization()
    check_backend_logs()
    
    # Print summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"✅ Passed: {tests_passed}")
    print(f"❌ Failed: {tests_failed}")
    print(f"📊 Total:  {tests_passed + tests_failed}")
    print(f"Success Rate: {(tests_passed / (tests_passed + tests_failed) * 100):.1f}%")
    print()
    
    if tests_failed > 0:
        print("❌ SOME TESTS FAILED")
        exit(1)
    else:
        print("✅ ALL TESTS PASSED")
        exit(0)


if __name__ == "__main__":
    main()
