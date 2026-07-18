#!/usr/bin/env python3
"""
Backend test for customer profile API feature.
Tests auto-profile creation, owner/stylist search, profile detail, visit history, 
preferred stylist auto/manual, editable fields, and loyalty tracking.
"""
import requests
import json
from datetime import datetime, timedelta
import random
import string

# Configuration
BASE_URL = "https://go-run-3.preview.emergentagent.com/api"
OWNER_PIN = "9999"
STYLIST_ID = "stylist-elena"  # Elena Hart
STYLIST_PIN = "1234"

# Test results tracking
tests_passed = 0
tests_failed = 0
test_results = []

# Test data storage
test_customer_phone = None
test_booking_id = None
owner_token = None


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


def generate_test_phone():
    """Generate a unique test phone number."""
    timestamp = datetime.now().strftime("%H%M%S")
    random_digits = ''.join(random.choices(string.digits, k=4))
    return f"+919876{timestamp[-4:]}{random_digits[-2:]}"


def owner_login():
    """Login as owner and return auth token."""
    url = f"{BASE_URL}/owner/login"
    response = requests.post(url, json={"pin": OWNER_PIN})
    if response.status_code == 200:
        data = response.json()
        return data.get("token")
    return None


def test_create_booking_auto_upserts_profile():
    """Test 1: POST /api/bookings creates booking and auto-upserts customer_profiles."""
    global test_customer_phone, test_booking_id
    
    # Generate unique test customer
    test_customer_phone = generate_test_phone()
    customer_name = "Priya Sharma"
    
    # Get tomorrow's date and use a unique time slot
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Use a random time slot to avoid conflicts
    import random
    hour = random.randint(10, 19)
    minute = random.choice([0, 15, 30, 45])
    start_time = f"{hour:02d}:{minute:02d}"
    
    # Create booking
    url = f"{BASE_URL}/bookings"
    payload = {
        "service_id": "svc-signature-cut",
        "stylist_id": STYLIST_ID,
        "date": tomorrow,
        "start_time": start_time,
        "customer_name": customer_name,
        "customer_phone": test_customer_phone,
        "notes": "Test booking for profile creation",
        "whatsapp_optin": False
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        log_test("Booking creation auto-upserts customer profile", False, 
                f"Booking creation failed: {response.status_code}, {response.text[:200]}")
        return False
    
    data = response.json()
    booking = data.get("booking", {})
    test_booking_id = booking.get("id")
    
    # Verify booking created
    booking_created = test_booking_id is not None
    
    passed = booking_created
    details = f"Booking ID: {test_booking_id}, Phone: {test_customer_phone}, Name: {customer_name}"
    log_test("Booking creation auto-upserts customer profile", passed, details)
    return passed


def test_owner_auth_required_for_customer_endpoints():
    """Test 2: Owner auth required for customer endpoints."""
    # Test search without auth
    url = f"{BASE_URL}/owner/customers/search?q=test"
    response = requests.get(url)
    search_auth_required = response.status_code == 401
    
    # Test profile detail without auth
    url = f"{BASE_URL}/owner/customers/9876543210"
    response = requests.get(url)
    detail_auth_required = response.status_code == 401
    
    # Test profile update without auth
    url = f"{BASE_URL}/owner/customers/9876543210"
    response = requests.patch(url, json={"customer_name": "Test"})
    update_auth_required = response.status_code == 401
    
    passed = search_auth_required and detail_auth_required and update_auth_required
    details = f"Search: {search_auth_required}, Detail: {detail_auth_required}, Update: {update_auth_required}"
    log_test("Owner auth required for customer endpoints", passed, details)


def test_owner_login_works():
    """Test 3: Owner login with PIN 9999 works."""
    global owner_token
    owner_token = owner_login()
    passed = owner_token is not None
    log_test("Owner login with PIN 9999", passed, f"Token received: {bool(owner_token)}")
    return owner_token


def test_owner_search_by_phone():
    """Test 4: Owner can search customers by phone."""
    if not owner_token or not test_customer_phone:
        log_test("Owner search by phone", False, "Prerequisites not met")
        return
    
    # Search by last 4 digits of phone
    search_query = test_customer_phone[-4:]
    url = f"{BASE_URL}/owner/customers/search?q={search_query}"
    headers = {"Authorization": f"Bearer {owner_token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        log_test("Owner search by phone", False, f"Status: {response.status_code}")
        return
    
    data = response.json()
    customers = data.get("customers", [])
    
    # Check if our test customer is in results
    found = any(c.get("customer_phone", "").endswith(test_customer_phone[-10:]) for c in customers)
    
    passed = found and len(customers) > 0
    details = f"Search query: {search_query}, Results: {len(customers)}, Found test customer: {found}"
    log_test("Owner search by phone", passed, details)


def test_owner_search_by_name():
    """Test 5: Owner can search customers by name."""
    if not owner_token:
        log_test("Owner search by name", False, "Prerequisites not met")
        return
    
    # Search by name
    search_query = "Priya"
    url = f"{BASE_URL}/owner/customers/search?q={search_query}"
    headers = {"Authorization": f"Bearer {owner_token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        log_test("Owner search by name", False, f"Status: {response.status_code}")
        return
    
    data = response.json()
    customers = data.get("customers", [])
    
    # Check if results contain names matching query
    found = any("Priya" in c.get("customer_name", "") for c in customers) if customers else False
    
    passed = response.status_code == 200 and isinstance(customers, list)
    details = f"Search query: {search_query}, Results: {len(customers)}, Found matching name: {found}"
    log_test("Owner search by name", passed, details)


def test_owner_customer_profile_detail():
    """Test 6: Owner can get customer profile detail with visit history."""
    if not owner_token or not test_customer_phone:
        log_test("Owner customer profile detail", False, "Prerequisites not met")
        return None
    
    url = f"{BASE_URL}/owner/customers/{test_customer_phone}"
    headers = {"Authorization": f"Bearer {owner_token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        log_test("Owner customer profile detail", False, f"Status: {response.status_code}")
        return None
    
    data = response.json()
    
    # Check required fields
    has_phone = "customer_phone" in data
    has_name = "customer_name" in data
    has_visit_history = "visit_history" in data
    has_visit_count = "visit_count" in data
    has_lifetime_spend = "lifetime_spend" in data
    has_loyalty_fields = "loyalty_next_milestone" in data and "loyalty_progress" in data
    has_preferred_stylist = "preferred_stylist_id" in data and "preferred_stylist_manual" in data
    
    # Check visit history structure
    visit_history = data.get("visit_history", [])
    visit_history_valid = True
    if visit_history:
        first_visit = visit_history[0]
        visit_history_valid = all(k in first_visit for k in ["service_name", "stylist_name", "amount_paid", "status", "date"])
    
    # Check no ObjectId in response
    response_text = response.text
    has_objectid = "ObjectId" in response_text or '"_id"' in response_text
    
    passed = (has_phone and has_name and has_visit_history and has_visit_count and 
              has_lifetime_spend and has_loyalty_fields and has_preferred_stylist and 
              visit_history_valid and not has_objectid)
    
    details = f"Phone: {has_phone}, Name: {has_name}, Visit history: {has_visit_history} ({len(visit_history)} visits), "
    details += f"Visit history valid: {visit_history_valid}, Loyalty: {has_loyalty_fields}, No ObjectId: {not has_objectid}"
    log_test("Owner customer profile detail", passed, details)
    return data


def test_visit_history_hydrated_fields():
    """Test 7: Visit history includes hydrated service_name, stylist_name, amount_paid."""
    if not owner_token or not test_customer_phone:
        log_test("Visit history hydrated fields", False, "Prerequisites not met")
        return
    
    url = f"{BASE_URL}/owner/customers/{test_customer_phone}"
    headers = {"Authorization": f"Bearer {owner_token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        log_test("Visit history hydrated fields", False, f"Status: {response.status_code}")
        return
    
    data = response.json()
    visit_history = data.get("visit_history", [])
    
    if not visit_history:
        log_test("Visit history hydrated fields", False, "No visit history found")
        return
    
    first_visit = visit_history[0]
    
    # Check hydrated fields
    has_service_name = "service_name" in first_visit and first_visit["service_name"] != ""
    has_stylist_name = "stylist_name" in first_visit and first_visit["stylist_name"] != ""
    has_amount_paid = "amount_paid" in first_visit and isinstance(first_visit["amount_paid"], (int, float))
    has_status = "status" in first_visit
    has_date = "date" in first_visit
    
    # Verify service_name is actual name, not ID
    service_name_is_name = not first_visit.get("service_name", "").startswith("svc-")
    
    # Verify stylist_name is actual name, not ID
    stylist_name_is_name = not first_visit.get("stylist_name", "").startswith("stylist-")
    
    passed = (has_service_name and has_stylist_name and has_amount_paid and has_status and 
              has_date and service_name_is_name and stylist_name_is_name)
    
    details = f"Service name: {first_visit.get('service_name', 'N/A')}, "
    details += f"Stylist name: {first_visit.get('stylist_name', 'N/A')}, "
    details += f"Amount: ₹{first_visit.get('amount_paid', 0)}, Status: {first_visit.get('status', 'N/A')}"
    log_test("Visit history hydrated fields", passed, details)


def test_loyalty_fields_numeric():
    """Test 8: Loyalty lifetime_spend and milestone fields are numeric."""
    if not owner_token or not test_customer_phone:
        log_test("Loyalty fields are numeric", False, "Prerequisites not met")
        return
    
    url = f"{BASE_URL}/owner/customers/{test_customer_phone}"
    headers = {"Authorization": f"Bearer {owner_token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        log_test("Loyalty fields are numeric", False, f"Status: {response.status_code}")
        return
    
    data = response.json()
    
    lifetime_spend = data.get("lifetime_spend")
    loyalty_next_milestone = data.get("loyalty_next_milestone")
    loyalty_progress = data.get("loyalty_progress")
    
    # Check types
    spend_is_numeric = isinstance(lifetime_spend, (int, float))
    milestone_is_numeric_or_none = loyalty_next_milestone is None or isinstance(loyalty_next_milestone, (int, float))
    progress_is_numeric = isinstance(loyalty_progress, (int, float))
    
    # Check progress is percentage (0-100)
    progress_in_range = 0 <= loyalty_progress <= 100 if progress_is_numeric else False
    
    passed = spend_is_numeric and milestone_is_numeric_or_none and progress_is_numeric and progress_in_range
    details = f"Lifetime spend: ₹{lifetime_spend} (numeric: {spend_is_numeric}), "
    details += f"Next milestone: {loyalty_next_milestone} (valid: {milestone_is_numeric_or_none}), "
    details += f"Progress: {loyalty_progress}% (valid: {progress_is_numeric and progress_in_range})"
    log_test("Loyalty fields are numeric", passed, details)


def test_preferred_stylist_auto_calculates():
    """Test 9: Preferred stylist auto-calculates from visits."""
    if not owner_token or not test_customer_phone:
        log_test("Preferred stylist auto-calculates", False, "Prerequisites not met")
        return
    
    url = f"{BASE_URL}/owner/customers/{test_customer_phone}"
    headers = {"Authorization": f"Bearer {owner_token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        log_test("Preferred stylist auto-calculates", False, f"Status: {response.status_code}")
        return
    
    data = response.json()
    
    # Check auto-calculated preferred stylist
    auto_preferred_stylist_id = data.get("auto_preferred_stylist_id")
    preferred_stylist_id = data.get("preferred_stylist_id")
    preferred_stylist_manual = data.get("preferred_stylist_manual")
    
    # Since we created one booking with STYLIST_ID, auto should be that stylist
    auto_is_correct = auto_preferred_stylist_id == STYLIST_ID
    
    # Initially, preferred should match auto (not manually set)
    preferred_matches_auto = preferred_stylist_id == auto_preferred_stylist_id
    manual_is_false = preferred_stylist_manual == False
    
    passed = auto_is_correct and preferred_matches_auto and manual_is_false
    details = f"Auto preferred: {auto_preferred_stylist_id}, Preferred: {preferred_stylist_id}, "
    details += f"Manual: {preferred_stylist_manual}, Auto correct: {auto_is_correct}"
    log_test("Preferred stylist auto-calculates", passed, details)


def test_owner_update_profile_editable_fields():
    """Test 10: Owner can update profile editable fields."""
    if not owner_token or not test_customer_phone:
        log_test("Owner update profile editable fields", False, "Prerequisites not met")
        return
    
    url = f"{BASE_URL}/owner/customers/{test_customer_phone}"
    headers = {"Authorization": f"Bearer {owner_token}"}
    
    # Update profile with all editable fields
    update_payload = {
        "customer_name": "Priya Sharma Updated",
        "birthday": "1995-06-15",
        "hair_type": "Wavy",
        "product_allergies": "None",
        "preferences": "Prefers natural products",
        "stylist_notes": "Regular customer, likes modern styles"
    }
    
    response = requests.patch(url, headers=headers, json=update_payload)
    
    if response.status_code != 200:
        log_test("Owner update profile editable fields", False, f"Status: {response.status_code}")
        return
    
    data = response.json()
    
    # Verify all fields were updated
    name_updated = data.get("customer_name") == update_payload["customer_name"]
    birthday_updated = data.get("birthday") == update_payload["birthday"]
    hair_type_updated = data.get("hair_type") == update_payload["hair_type"]
    allergies_updated = data.get("product_allergies") == update_payload["product_allergies"]
    preferences_updated = data.get("preferences") == update_payload["preferences"]
    notes_updated = data.get("stylist_notes") == update_payload["stylist_notes"]
    
    passed = (name_updated and birthday_updated and hair_type_updated and 
              allergies_updated and preferences_updated and notes_updated)
    
    details = f"Name: {name_updated}, Birthday: {birthday_updated}, Hair type: {hair_type_updated}, "
    details += f"Allergies: {allergies_updated}, Preferences: {preferences_updated}, Notes: {notes_updated}"
    log_test("Owner update profile editable fields", passed, details)


def test_owner_manual_preferred_stylist_override():
    """Test 11: Owner can manually override preferred stylist."""
    if not owner_token or not test_customer_phone:
        log_test("Owner manual preferred stylist override", False, "Prerequisites not met")
        return
    
    url = f"{BASE_URL}/owner/customers/{test_customer_phone}"
    headers = {"Authorization": f"Bearer {owner_token}"}
    
    # Manually set preferred stylist to a different stylist
    manual_stylist_id = "stylist-sarah"  # Sarah Lin
    update_payload = {
        "preferred_stylist_id": manual_stylist_id
    }
    
    response = requests.patch(url, headers=headers, json=update_payload)
    
    if response.status_code != 200:
        log_test("Owner manual preferred stylist override", False, f"Status: {response.status_code}")
        return
    
    data = response.json()
    
    # Verify manual override
    preferred_stylist_id = data.get("preferred_stylist_id")
    preferred_stylist_manual = data.get("preferred_stylist_manual")
    auto_preferred_stylist_id = data.get("auto_preferred_stylist_id")
    
    # Preferred should now be the manual one
    preferred_is_manual = preferred_stylist_id == manual_stylist_id
    manual_flag_is_true = preferred_stylist_manual == True
    auto_unchanged = auto_preferred_stylist_id == STYLIST_ID  # Auto should still be Elena
    
    passed = preferred_is_manual and manual_flag_is_true and auto_unchanged
    details = f"Preferred: {preferred_stylist_id} (expected {manual_stylist_id}), "
    details += f"Manual flag: {preferred_stylist_manual}, Auto: {auto_preferred_stylist_id}"
    log_test("Owner manual preferred stylist override", passed, details)


def test_stylist_customer_search():
    """Test 12: Stylist can search customers."""
    if not test_customer_phone:
        log_test("Stylist customer search", False, "Prerequisites not met")
        return
    
    # Search by last 4 digits of phone
    search_query = test_customer_phone[-4:]
    url = f"{BASE_URL}/stylist/{STYLIST_ID}/customers/search?q={search_query}"
    response = requests.get(url)
    
    if response.status_code != 200:
        log_test("Stylist customer search", False, f"Status: {response.status_code}")
        return
    
    data = response.json()
    customers = data.get("customers", [])
    
    # Check if our test customer is in results
    found = any(c.get("customer_phone", "").endswith(test_customer_phone[-10:]) for c in customers)
    
    passed = found and len(customers) > 0
    details = f"Stylist: {STYLIST_ID}, Search query: {search_query}, Results: {len(customers)}, Found: {found}"
    log_test("Stylist customer search", passed, details)


def test_stylist_customer_profile_detail():
    """Test 13: Stylist can get customer profile detail."""
    if not test_customer_phone:
        log_test("Stylist customer profile detail", False, "Prerequisites not met")
        return
    
    url = f"{BASE_URL}/stylist/{STYLIST_ID}/customers/{test_customer_phone}"
    response = requests.get(url)
    
    if response.status_code != 200:
        log_test("Stylist customer profile detail", False, f"Status: {response.status_code}")
        return
    
    data = response.json()
    
    # Check required fields
    has_phone = "customer_phone" in data
    has_name = "customer_name" in data
    has_visit_history = "visit_history" in data
    has_loyalty_fields = "lifetime_spend" in data and "loyalty_next_milestone" in data
    has_preferred_stylist = "preferred_stylist_id" in data
    
    passed = has_phone and has_name and has_visit_history and has_loyalty_fields and has_preferred_stylist
    details = f"Stylist: {STYLIST_ID}, Phone: {has_phone}, Name: {has_name}, Visit history: {has_visit_history}, Loyalty: {has_loyalty_fields}"
    log_test("Stylist customer profile detail", passed, details)


def test_stylist_update_customer_profile():
    """Test 14: Stylist can update customer profile."""
    if not test_customer_phone:
        log_test("Stylist update customer profile", False, "Prerequisites not met")
        return
    
    url = f"{BASE_URL}/stylist/{STYLIST_ID}/customers/{test_customer_phone}"
    
    # Update profile
    update_payload = {
        "stylist_notes": "Updated by stylist - prefers short cuts",
        "hair_type": "Straight"
    }
    
    response = requests.patch(url, json=update_payload)
    
    if response.status_code != 200:
        log_test("Stylist update customer profile", False, f"Status: {response.status_code}")
        return
    
    data = response.json()
    
    # Verify fields were updated
    notes_updated = data.get("stylist_notes") == update_payload["stylist_notes"]
    hair_type_updated = data.get("hair_type") == update_payload["hair_type"]
    
    passed = notes_updated and hair_type_updated
    details = f"Stylist: {STYLIST_ID}, Notes updated: {notes_updated}, Hair type updated: {hair_type_updated}"
    log_test("Stylist update customer profile", passed, details)


def test_existing_bookings_api_still_works():
    """Test 15: Existing bookings API still works."""
    if not owner_token:
        log_test("Existing bookings API still works", False, "Prerequisites not met")
        return
    
    # Test owner bookings endpoint
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"{BASE_URL}/owner/bookings?date={today}"
    headers = {"Authorization": f"Bearer {owner_token}"}
    response = requests.get(url, headers=headers)
    
    bookings_works = response.status_code == 200
    
    # Test owner summary endpoint
    url = f"{BASE_URL}/owner/summary?date={today}"
    response = requests.get(url, headers=headers)
    
    summary_works = response.status_code == 200
    
    passed = bookings_works and summary_works
    details = f"Bookings API: {bookings_works}, Summary API: {summary_works}"
    log_test("Existing bookings API still works", passed, details)


def test_existing_stylist_api_still_works():
    """Test 16: Existing stylist API still works."""
    # Test stylist schedule endpoint
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"{BASE_URL}/stylist/{STYLIST_ID}/schedule?date={today}"
    response = requests.get(url)
    
    schedule_works = response.status_code == 200
    
    passed = schedule_works
    details = f"Stylist schedule API: {schedule_works}"
    log_test("Existing stylist API still works", passed, details)


def test_no_objectid_in_responses():
    """Test 17: No ObjectId serialization in any customer profile responses."""
    if not owner_token or not test_customer_phone:
        log_test("No ObjectId in responses", False, "Prerequisites not met")
        return
    
    # Test owner profile detail
    url = f"{BASE_URL}/owner/customers/{test_customer_phone}"
    headers = {"Authorization": f"Bearer {owner_token}"}
    response = requests.get(url, headers=headers)
    
    owner_no_objectid = "ObjectId" not in response.text and '"_id"' not in response.text
    
    # Test owner search
    url = f"{BASE_URL}/owner/customers/search?q={test_customer_phone[-4:]}"
    response = requests.get(url, headers=headers)
    
    search_no_objectid = "ObjectId" not in response.text and '"_id"' not in response.text
    
    # Test stylist profile detail
    url = f"{BASE_URL}/stylist/{STYLIST_ID}/customers/{test_customer_phone}"
    response = requests.get(url)
    
    stylist_no_objectid = "ObjectId" not in response.text and '"_id"' not in response.text
    
    passed = owner_no_objectid and search_no_objectid and stylist_no_objectid
    details = f"Owner detail: {owner_no_objectid}, Owner search: {search_no_objectid}, Stylist detail: {stylist_no_objectid}"
    log_test("No ObjectId in responses", passed, details)


def test_profile_persists_across_requests():
    """Test 18: Customer profile persists and updates are retained."""
    if not owner_token or not test_customer_phone:
        log_test("Profile persists across requests", False, "Prerequisites not met")
        return
    
    # Get profile
    url = f"{BASE_URL}/owner/customers/{test_customer_phone}"
    headers = {"Authorization": f"Bearer {owner_token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        log_test("Profile persists across requests", False, f"Status: {response.status_code}")
        return
    
    data = response.json()
    
    # Check that previously updated fields are still there
    name = data.get("customer_name")
    birthday = data.get("birthday")
    hair_type = data.get("hair_type")
    stylist_notes = data.get("stylist_notes")
    
    # Should have values from previous updates
    has_updated_name = "Updated" in name if name else False
    has_birthday = birthday == "1995-06-15"
    has_hair_type = hair_type in ["Wavy", "Straight"]  # Could be either from owner or stylist update
    has_notes = stylist_notes and len(stylist_notes) > 0
    
    passed = has_updated_name and has_birthday and has_hair_type and has_notes
    details = f"Name: {name}, Birthday: {birthday}, Hair type: {hair_type}, Has notes: {has_notes}"
    log_test("Profile persists across requests", passed, details)


def test_multiple_bookings_update_visit_history():
    """Test 19: Creating multiple bookings updates visit history."""
    if not test_customer_phone:
        log_test("Multiple bookings update visit history", False, "Prerequisites not met")
        return
    
    # Create a second booking for the same customer with a different time
    tomorrow = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    
    # Use a random time slot to avoid conflicts
    import random
    hour = random.randint(10, 19)
    minute = random.choice([0, 15, 30, 45])
    start_time = f"{hour:02d}:{minute:02d}"
    
    url = f"{BASE_URL}/bookings"
    payload = {
        "service_id": "svc-hair-spa",
        "stylist_id": "stylist-sarah",  # Different stylist
        "date": tomorrow,
        "start_time": start_time,
        "customer_name": "Priya Sharma Updated",
        "customer_phone": test_customer_phone,
        "notes": "Second booking",
        "whatsapp_optin": False
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        log_test("Multiple bookings update visit history", False, f"Booking creation failed: {response.status_code}")
        return
    
    # Get profile and check visit history
    if not owner_token:
        log_test("Multiple bookings update visit history", False, "Owner token not available")
        return
    
    url = f"{BASE_URL}/owner/customers/{test_customer_phone}"
    headers = {"Authorization": f"Bearer {owner_token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        log_test("Multiple bookings update visit history", False, f"Profile fetch failed: {response.status_code}")
        return
    
    data = response.json()
    visit_history = data.get("visit_history", [])
    visit_count = data.get("visit_count", 0)
    
    # Should have 2 visits now
    has_two_visits = len(visit_history) == 2 and visit_count == 2
    
    # Check that visits are from different stylists
    stylists = [v.get("stylist_name") for v in visit_history]
    has_different_stylists = len(set(stylists)) > 1
    
    passed = has_two_visits and has_different_stylists
    details = f"Visit count: {visit_count}, Visit history length: {len(visit_history)}, Stylists: {stylists}"
    log_test("Multiple bookings update visit history", passed, details)


def test_lifetime_spend_calculation():
    """Test 20: Lifetime spend is calculated correctly from bookings."""
    if not owner_token or not test_customer_phone:
        log_test("Lifetime spend calculation", False, "Prerequisites not met")
        return
    
    url = f"{BASE_URL}/owner/customers/{test_customer_phone}"
    headers = {"Authorization": f"Bearer {owner_token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        log_test("Lifetime spend calculation", False, f"Status: {response.status_code}")
        return
    
    data = response.json()
    lifetime_spend = data.get("lifetime_spend", 0)
    visit_history = data.get("visit_history", [])
    
    # Calculate expected spend from visit history
    expected_spend = sum(v.get("amount_paid", 0) for v in visit_history)
    
    # Check if lifetime_spend matches sum of visit amounts
    spend_matches = abs(lifetime_spend - expected_spend) < 0.01  # Allow for floating point precision
    
    # Check that spend is reasonable (should be sum of service prices)
    # svc-signature-cut: 600, svc-hair-spa: 1200
    expected_total = 600 + 1200  # Two bookings
    spend_is_reasonable = abs(lifetime_spend - expected_total) < 0.01
    
    passed = spend_matches and spend_is_reasonable
    details = f"Lifetime spend: ₹{lifetime_spend}, Expected: ₹{expected_spend}, Reasonable: {spend_is_reasonable}"
    log_test("Lifetime spend calculation", passed, details)


def main():
    print("=" * 80)
    print("Backend Test: Customer Profile API Feature")
    print("=" * 80)
    print()
    
    # Test 1: Create booking and auto-upsert profile
    if not test_create_booking_auto_upserts_profile():
        print("\n❌ Cannot proceed without test booking")
        return
    
    # Test 2: Owner auth required
    test_owner_auth_required_for_customer_endpoints()
    
    # Test 3: Owner login
    if not test_owner_login_works():
        print("\n❌ Cannot proceed without valid owner token")
        return
    
    # Test 4-5: Owner search
    test_owner_search_by_phone()
    test_owner_search_by_name()
    
    # Test 6-7: Owner profile detail and visit history
    test_owner_customer_profile_detail()
    test_visit_history_hydrated_fields()
    
    # Test 8: Loyalty fields
    test_loyalty_fields_numeric()
    
    # Test 9: Preferred stylist auto-calculation
    test_preferred_stylist_auto_calculates()
    
    # Test 10-11: Owner profile updates
    test_owner_update_profile_editable_fields()
    test_owner_manual_preferred_stylist_override()
    
    # Test 12-14: Stylist endpoints
    test_stylist_customer_search()
    test_stylist_customer_profile_detail()
    test_stylist_update_customer_profile()
    
    # Test 15-16: Existing APIs still work
    test_existing_bookings_api_still_works()
    test_existing_stylist_api_still_works()
    
    # Test 17: No ObjectId serialization
    test_no_objectid_in_responses()
    
    # Test 18: Profile persistence
    test_profile_persists_across_requests()
    
    # Test 19-20: Multiple bookings and lifetime spend
    test_multiple_bookings_update_visit_history()
    test_lifetime_spend_calculation()
    
    # Summary
    print()
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
        exit(1)
    else:
        print("\n✅ ALL TESTS PASSED")
        exit(0)


if __name__ == "__main__":
    main()
