#!/usr/bin/env python3
"""
Backend test for self-serve manage appointment feature.
Tests manage_token/manage_url, customer manage endpoints, cancellation, rescheduling, and owner notifications.
"""
import requests
import json
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
    try:
        response = requests.post(url, json={"pin": OWNER_PIN})
        if response.status_code == 200:
            data = response.json()
            return data.get("token")
    except Exception as e:
        print(f"Owner login error: {e}")
    return None


def get_available_slot(days_ahead=7):
    """Get an available slot for booking."""
    # Get date days_ahead from now
    target_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    # Get availability for that date
    url = f"{BASE_URL}/availability"
    params = {
        "date": target_date,
        "service_id": "svc-hair-wash",  # Use shorter service to have more slots
        "stylist_id": "stylist-sarah"  # Use different stylist
    }
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        slots = data.get("slots", [])
        if slots:
            # Return first available slot - slots are objects with start_time
            first_slot = slots[0]
            if isinstance(first_slot, dict):
                return target_date, first_slot.get("start_time")
            else:
                return target_date, first_slot
    
    return None, None


def create_test_booking(days_ahead=7, phone_suffix="210"):
    """Create a test booking and return booking data with manage_token."""
    date, slot = get_available_slot(days_ahead=days_ahead)
    
    if not date or not slot:
        print(f"DEBUG: No available slot found. Date: {date}, Slot: {slot}")
        return None
    
    url = f"{BASE_URL}/bookings"
    payload = {
        "service_id": "svc-hair-wash",  # Use shorter service
        "stylist_id": "stylist-sarah",  # Use different stylist
        "date": date,
        "start_time": slot,
        "customer_name": "Rajesh Kumar",
        "customer_phone": f"+9198765432{phone_suffix}",
        "notes": "Test booking for manage feature",
        "whatsapp_optin": False
    }
    
    # Send Origin header to simulate frontend request
    headers = {
        "Origin": "https://go-run-3.preview.emergentagent.com"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code != 200:
        print(f"DEBUG: Booking creation failed. Status: {response.status_code}, Response: {response.text}")
        return None
    
    data = response.json()
    booking = data.get("booking", {})
    return booking


def test_booking_has_manage_token():
    """Test 1: New bookings get manage_token and manage_url when created."""
    booking = create_test_booking()
    
    if not booking:
        log_test("New booking has manage_token and manage_url", False, "Failed to create test booking")
        return None
    
    has_token = "manage_token" in booking and booking.get("manage_token")
    has_url = "manage_url" in booking and booking.get("manage_url")
    
    # Verify URL format
    url_format_ok = False
    if has_url:
        manage_url = booking.get("manage_url")
        url_format_ok = "/manage/" in manage_url and booking.get("manage_token") in manage_url
    
    passed = has_token and has_url and url_format_ok
    details = f"Has token: {has_token}, Has URL: {has_url}, URL format valid: {url_format_ok}"
    if has_url:
        details += f", URL: {booking.get('manage_url')}"
    
    log_test("New booking has manage_token and manage_url", passed, details)
    
    return booking if passed else None


def test_customer_manage_detail(manage_token):
    """Test 2: Customer can retrieve booking via GET /api/customer/manage/{token}."""
    url = f"{BASE_URL}/customer/manage/{manage_token}"
    response = requests.get(url)
    
    if response.status_code != 200:
        log_test("Customer can retrieve booking via manage token", False, f"Status: {response.status_code}")
        return None
    
    data = response.json()
    
    # Check required fields
    has_booking = "booking" in data
    has_policy = "policy_notice" in data
    has_within_24h = "within_24h" in data
    has_reasons = "cancellation_reasons" in data
    
    # Verify policy notice text
    policy_text = data.get("policy_notice", "")
    policy_correct = "Please cancel or reschedule at least 24 hours before your appointment." in policy_text
    
    # Verify cancellation reasons list
    reasons = data.get("cancellation_reasons", [])
    reasons_valid = len(reasons) >= 3 and all("value" in r and "label" in r for r in reasons)
    
    # Verify within_24h is boolean
    within_24h_valid = isinstance(data.get("within_24h"), bool)
    
    passed = has_booking and has_policy and has_within_24h and has_reasons and policy_correct and reasons_valid and within_24h_valid
    details = f"Has booking: {has_booking}, Has policy: {has_policy}, Policy correct: {policy_correct}, Has within_24h: {has_within_24h}, Within_24h valid: {within_24h_valid}, Has reasons: {has_reasons}, Reasons valid: {reasons_valid}"
    
    log_test("Customer can retrieve booking via manage token", passed, details)
    
    return data if passed else None


def test_invalid_token_returns_404():
    """Test 3: Invalid manage token returns 404."""
    url = f"{BASE_URL}/customer/manage/invalid-token-12345"
    response = requests.get(url)
    
    passed = response.status_code == 404
    details = f"Status: {response.status_code}, Expected: 404"
    
    log_test("Invalid manage token returns 404", passed, details)


def test_customer_cancel_via_manage_token(manage_token, booking_id):
    """Test 4: Customer can cancel booking via POST /api/customer/manage/{token}/cancel."""
    url = f"{BASE_URL}/customer/manage/{manage_token}/cancel"
    payload = {
        "reason": "schedule_conflict",
        "reason_note": "Have an urgent meeting"
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        log_test("Customer can cancel via manage token", False, f"Status: {response.status_code}, Response: {response.text}")
        return False
    
    data = response.json()
    
    # Verify response has booking with cancelled status
    booking = data.get("booking", {})
    status_cancelled = booking.get("status") == "cancelled"
    has_cancelled_by = booking.get("cancelled_by") == "customer"
    has_cancelled_at = "cancelled_at" in booking
    has_reason = booking.get("cancellation_reason") == "schedule_conflict"
    has_note = booking.get("cancellation_reason_note") == "Have an urgent meeting"
    
    passed = status_cancelled and has_cancelled_by and has_cancelled_at and has_reason and has_note
    details = f"Status cancelled: {status_cancelled}, Cancelled by customer: {has_cancelled_by}, Has cancelled_at: {has_cancelled_at}, Reason correct: {has_reason}, Note correct: {has_note}"
    
    log_test("Customer can cancel via manage token", passed, details)
    
    return passed


def test_cancelled_slot_available(date, start_time, service_id, stylist_id):
    """Test 5: Cancelled slot is immediately available for new bookings."""
    url = f"{BASE_URL}/availability"
    params = {
        "date": date,
        "service_id": service_id,
        "stylist_id": stylist_id
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        log_test("Cancelled slot immediately available", False, f"Status: {response.status_code}")
        return False
    
    data = response.json()
    slots = data.get("slots", [])
    
    # Check if the cancelled slot is now available - slots are objects with start_time
    slot_available = False
    for slot in slots:
        if isinstance(slot, dict):
            if slot.get("start_time") == start_time and slot.get("available") == True:
                slot_available = True
                break
        elif slot == start_time:
            slot_available = True
            break
    
    passed = slot_available
    details = f"Cancelled slot {start_time} available: {slot_available}, Total slots: {len(slots)}"
    
    log_test("Cancelled slot immediately available", passed, details)
    
    return passed


def test_owner_notification_created(token):
    """Test 6: Owner notification created for customer cancellation."""
    url = f"{BASE_URL}/owner/notifications"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        log_test("Owner notification created for cancellation", False, f"Status: {response.status_code}")
        return False
    
    data = response.json()
    notifications = data.get("notifications", [])
    
    # Look for customer_cancelled notification
    cancel_notification = None
    for notif in notifications:
        if notif.get("type") == "customer_cancelled":
            cancel_notification = notif
            break
    
    if not cancel_notification:
        log_test("Owner notification created for cancellation", False, "No customer_cancelled notification found")
        return False
    
    # Verify notification fields
    has_type = cancel_notification.get("type") == "customer_cancelled"
    has_booking_id = "booking_id" in cancel_notification
    has_customer_name = "customer_name" in cancel_notification
    has_message = "message" in cancel_notification and "cancelled" in cancel_notification.get("message", "").lower()
    has_read_flag = "read" in cancel_notification
    has_created_at = "created_at" in cancel_notification
    
    passed = has_type and has_booking_id and has_customer_name and has_message and has_read_flag and has_created_at
    details = f"Type correct: {has_type}, Has booking_id: {has_booking_id}, Has customer_name: {has_customer_name}, Has message: {has_message}, Has read flag: {has_read_flag}, Has created_at: {has_created_at}"
    
    log_test("Owner notification created for cancellation", passed, details)
    
    return passed


def test_customer_reschedule_via_manage_token():
    """Test 7: Customer can reschedule booking via POST /api/customer/manage/{token}/reschedule."""
    # Create a new booking for reschedule test
    booking = create_test_booking()
    
    if not booking:
        log_test("Customer can reschedule via manage token", False, "Failed to create test booking")
        return False
    
    manage_token = booking.get("manage_token")
    original_date = booking.get("date")
    original_time = booking.get("start_time")
    
    # Get a new available slot (10 days ahead)
    new_date, new_slot = get_available_slot(days_ahead=10)
    
    if not new_date or not new_slot:
        log_test("Customer can reschedule via manage token", False, "No available slot for reschedule")
        return False
    
    url = f"{BASE_URL}/customer/manage/{manage_token}/reschedule"
    payload = {
        "new_date": new_date,
        "new_start_time": new_slot
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        log_test("Customer can reschedule via manage token", False, f"Status: {response.status_code}, Response: {response.text}")
        return False
    
    data = response.json()
    
    # Verify response has booking with updated date/time
    booking_updated = data.get("booking", {})
    date_updated = booking_updated.get("date") == new_date
    time_updated = booking_updated.get("start_time") == new_slot
    status_still_upcoming = booking_updated.get("status") == "upcoming"
    reminders_reset = booking_updated.get("reminders_sent", []) == []
    
    passed = date_updated and time_updated and status_still_upcoming and reminders_reset
    details = f"Date updated: {date_updated} ({original_date} -> {new_date}), Time updated: {time_updated} ({original_time} -> {new_slot}), Status upcoming: {status_still_upcoming}, Reminders reset: {reminders_reset}"
    
    log_test("Customer can reschedule via manage token", passed, details)
    
    return passed


def test_owner_notification_for_reschedule(token):
    """Test 8: Owner notification created for customer reschedule."""
    url = f"{BASE_URL}/owner/notifications"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        log_test("Owner notification created for reschedule", False, f"Status: {response.status_code}")
        return False
    
    data = response.json()
    notifications = data.get("notifications", [])
    
    # Look for customer_rescheduled notification
    reschedule_notification = None
    for notif in notifications:
        if notif.get("type") == "customer_rescheduled":
            reschedule_notification = notif
            break
    
    if not reschedule_notification:
        log_test("Owner notification created for reschedule", False, "No customer_rescheduled notification found")
        return False
    
    # Verify notification fields
    has_type = reschedule_notification.get("type") == "customer_rescheduled"
    has_booking_id = "booking_id" in reschedule_notification
    has_customer_name = "customer_name" in reschedule_notification
    has_message = "message" in reschedule_notification and "rescheduled" in reschedule_notification.get("message", "").lower()
    has_read_flag = "read" in reschedule_notification
    has_created_at = "created_at" in reschedule_notification
    
    passed = has_type and has_booking_id and has_customer_name and has_message and has_read_flag and has_created_at
    details = f"Type correct: {has_type}, Has booking_id: {has_booking_id}, Has customer_name: {has_customer_name}, Has message: {has_message}, Has read flag: {has_read_flag}, Has created_at: {has_created_at}"
    
    log_test("Owner notification created for reschedule", passed, details)
    
    return passed


def test_owner_notifications_endpoint(token):
    """Test 9: Owner can fetch in-app notifications via /api/owner/notifications."""
    url = f"{BASE_URL}/owner/notifications"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        log_test("Owner can fetch notifications", False, f"Status: {response.status_code}")
        return False
    
    data = response.json()
    
    # Verify response structure
    has_notifications = "notifications" in data
    has_unread = "unread" in data
    
    notifications = data.get("notifications", [])
    is_array = isinstance(notifications, list)
    
    unread_count = data.get("unread", 0)
    unread_is_number = isinstance(unread_count, int)
    
    passed = has_notifications and has_unread and is_array and unread_is_number
    details = f"Has notifications: {has_notifications}, Has unread: {has_unread}, Is array: {is_array}, Unread is number: {unread_is_number}, Total notifications: {len(notifications)}, Unread count: {unread_count}"
    
    log_test("Owner can fetch notifications", passed, details)
    
    return passed


def test_existing_customer_cancel_still_works():
    """Test 10: Existing customer cancel API still works."""
    # Create a booking
    booking = create_test_booking(days_ahead=11, phone_suffix="211")
    
    if not booking:
        log_test("Existing customer cancel API still works", False, "Failed to create test booking")
        return False
    
    booking_id = booking.get("id")
    customer_phone = booking.get("customer_phone")
    
    url = f"{BASE_URL}/customer/cancel"
    payload = {
        "booking_id": booking_id,
        "phone": customer_phone
    }
    
    response = requests.post(url, json=payload)
    
    passed = response.status_code == 200
    details = f"Status: {response.status_code}, Expected: 200"
    
    log_test("Existing customer cancel API still works", passed, details)
    
    return passed


def test_no_objectid_serialization():
    """Test 11: No ObjectId serialization issues in manage endpoints."""
    # Create a booking
    booking = create_test_booking(days_ahead=16, phone_suffix="216")
    
    if not booking:
        log_test("No ObjectId serialization in manage endpoints", False, "Failed to create test booking")
        return False
    
    manage_token = booking.get("manage_token")
    
    # Test manage detail endpoint
    url = f"{BASE_URL}/customer/manage/{manage_token}"
    response = requests.get(url)
    
    if response.status_code != 200:
        log_test("No ObjectId serialization in manage endpoints", False, f"Status: {response.status_code}")
        return False
    
    response_text = response.text
    has_objectid = "ObjectId" in response_text or '"_id"' in response_text
    
    passed = not has_objectid
    details = "No ObjectId found in response" if passed else "ObjectId or _id found in response"
    
    log_test("No ObjectId serialization in manage endpoints", passed, details)
    
    return passed


def test_cannot_cancel_already_cancelled():
    """Test 12: Cannot cancel an already cancelled booking."""
    # Create and cancel a booking
    booking = create_test_booking(days_ahead=12, phone_suffix="212")
    
    if not booking:
        log_test("Cannot cancel already cancelled booking", False, "Failed to create test booking")
        return False
    
    manage_token = booking.get("manage_token")
    
    # Cancel the booking
    url = f"{BASE_URL}/customer/manage/{manage_token}/cancel"
    payload = {"reason": "other"}
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        log_test("Cannot cancel already cancelled booking", False, f"First cancel failed: {response.status_code}")
        return False
    
    # Try to cancel again
    response = requests.post(url, json=payload)
    
    passed = response.status_code == 400
    details = f"Status: {response.status_code}, Expected: 400"
    
    log_test("Cannot cancel already cancelled booking", passed, details)
    
    return passed


def test_cannot_reschedule_cancelled():
    """Test 13: Cannot reschedule a cancelled booking."""
    # Create and cancel a booking
    booking = create_test_booking(days_ahead=13, phone_suffix="213")
    
    if not booking:
        log_test("Cannot reschedule cancelled booking", False, "Failed to create test booking")
        return False
    
    manage_token = booking.get("manage_token")
    
    # Cancel the booking
    cancel_url = f"{BASE_URL}/customer/manage/{manage_token}/cancel"
    cancel_payload = {"reason": "other"}
    response = requests.post(cancel_url, json=cancel_payload)
    
    if response.status_code != 200:
        log_test("Cannot reschedule cancelled booking", False, f"Cancel failed: {response.status_code}")
        return False
    
    # Try to reschedule
    new_date, new_slot = get_available_slot(days_ahead=15)
    
    if not new_date or not new_slot:
        log_test("Cannot reschedule cancelled booking", False, "No available slot")
        return False
    
    reschedule_url = f"{BASE_URL}/customer/manage/{manage_token}/reschedule"
    reschedule_payload = {
        "new_date": new_date,
        "new_start_time": new_slot
    }
    response = requests.post(reschedule_url, json=reschedule_payload)
    
    passed = response.status_code == 400
    details = f"Status: {response.status_code}, Expected: 400"
    
    log_test("Cannot reschedule cancelled booking", passed, details)
    
    return passed


def test_reschedule_validates_availability():
    """Test 14: Reschedule validates slot availability."""
    # Create a booking
    booking = create_test_booking(days_ahead=14, phone_suffix="214")
    
    if not booking:
        log_test("Reschedule validates slot availability", False, "Failed to create test booking")
        return False
    
    manage_token = booking.get("manage_token")
    
    # Try to reschedule to a past date
    past_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    url = f"{BASE_URL}/customer/manage/{manage_token}/reschedule"
    payload = {
        "new_date": past_date,
        "new_start_time": "10:00"
    }
    
    response = requests.post(url, json=payload)
    
    passed = response.status_code == 400
    details = f"Status: {response.status_code}, Expected: 400 (cannot reschedule to past date)"
    
    log_test("Reschedule validates slot availability", passed, details)
    
    return passed


def main():
    print("=" * 80)
    print("Backend Test: Self-Serve Manage Appointment Feature")
    print("=" * 80)
    print()
    
    # Get owner token for notification tests
    print("Logging in as owner...")
    owner_token = owner_login()
    if not owner_token:
        print("❌ Cannot proceed without valid owner token")
        return
    print(f"✅ Owner logged in successfully\n")
    
    # Test 1: Booking has manage_token and manage_url
    print("-" * 80)
    print("Testing Booking Creation with Manage Token")
    print("-" * 80)
    booking = test_booking_has_manage_token()
    
    if not booking:
        print("\n❌ Cannot proceed without valid booking with manage token")
        return
    
    manage_token = booking.get("manage_token")
    booking_id = booking.get("id")
    booking_date = booking.get("date")
    booking_time = booking.get("start_time")
    service_id = booking.get("service_id")
    stylist_id = booking.get("stylist_id")
    
    print()
    
    # Test 2: Customer can retrieve booking via manage token
    print("-" * 80)
    print("Testing Customer Manage Detail Endpoint")
    print("-" * 80)
    manage_data = test_customer_manage_detail(manage_token)
    print()
    
    # Test 3: Invalid token returns 404
    test_invalid_token_returns_404()
    print()
    
    # Test 4-6: Customer cancel via manage token
    print("-" * 80)
    print("Testing Customer Cancellation via Manage Token")
    print("-" * 80)
    cancel_success = test_customer_cancel_via_manage_token(manage_token, booking_id)
    
    if cancel_success:
        # Test 5: Cancelled slot is available
        test_cancelled_slot_available(booking_date, booking_time, service_id, stylist_id)
        
        # Test 6: Owner notification created
        test_owner_notification_created(owner_token)
    
    print()
    
    # Test 7-8: Customer reschedule via manage token
    print("-" * 80)
    print("Testing Customer Reschedule via Manage Token")
    print("-" * 80)
    reschedule_success = test_customer_reschedule_via_manage_token()
    
    if reschedule_success:
        # Test 8: Owner notification for reschedule
        test_owner_notification_for_reschedule(owner_token)
    
    print()
    
    # Test 9: Owner notifications endpoint
    print("-" * 80)
    print("Testing Owner Notifications Endpoint")
    print("-" * 80)
    test_owner_notifications_endpoint(owner_token)
    print()
    
    # Test 10: Existing customer cancel API still works
    print("-" * 80)
    print("Testing Backward Compatibility")
    print("-" * 80)
    test_existing_customer_cancel_still_works()
    print()
    
    # Test 11: No ObjectId serialization
    print("-" * 80)
    print("Testing Data Integrity")
    print("-" * 80)
    test_no_objectid_serialization()
    print()
    
    # Test 12-14: Edge cases
    print("-" * 80)
    print("Testing Edge Cases")
    print("-" * 80)
    test_cannot_cancel_already_cancelled()
    test_cannot_reschedule_cancelled()
    test_reschedule_validates_availability()
    print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total tests: {tests_passed + tests_failed}")
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")
    print(f"Success rate: {tests_passed / (tests_passed + tests_failed) * 100:.1f}%")
    print("=" * 80)
    
    if tests_failed > 0:
        print("\n❌ SOME TESTS FAILED")
        print("\nFailed tests:")
        for result in test_results:
            if "❌ FAIL" in result:
                print(result)
        exit(1)
    else:
        print("\n✅ ALL TESTS PASSED")
        exit(0)


if __name__ == "__main__":
    main()
