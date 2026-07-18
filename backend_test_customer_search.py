#!/usr/bin/env python3
"""
Backend test for customer search API with optional 'q' parameter.
Tests /api/owner/customers/search and /api/stylist/{stylist_id}/customers/search
after bug fix to support optional q parameter.
"""
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://go-run-3.preview.emergentagent.com/api"
OWNER_PIN = "9999"
STYLIST_ID = "stylist-elena"  # Using Elena Hart from test_credentials.md

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


def test_owner_login():
    """Test: Owner login with PIN 9999 works."""
    token = owner_login()
    passed = token is not None
    log_test(
        "Owner login with PIN 9999",
        passed,
        f"Token received: {bool(token)}"
    )
    return token


def test_owner_search_no_q(token):
    """Test 1: Owner search endpoint with no q returns list of customers."""
    url = f"{BASE_URL}/owner/customers/search"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    passed = False
    details = f"Status: {response.status_code}"
    
    if response.status_code == 200:
        data = response.json()
        if "customers" in data:
            customers = data["customers"]
            if isinstance(customers, list):
                passed = True
                details = f"Status: 200, Returned {len(customers)} customers"
            else:
                details = f"Status: 200, but 'customers' is not a list: {type(customers)}"
        else:
            details = f"Status: 200, but 'customers' key missing in response"
    elif response.status_code == 422:
        details = f"Status: 422 (Validation Error) - q parameter should be optional"
    
    log_test(
        "Owner search with no q parameter returns customer list",
        passed,
        details
    )
    return customers if passed else []


def test_stylist_search_no_q():
    """Test 2: Stylist search endpoint with no q returns list of customers."""
    url = f"{BASE_URL}/stylist/{STYLIST_ID}/customers/search"
    response = requests.get(url)
    
    passed = False
    details = f"Status: {response.status_code}"
    
    if response.status_code == 200:
        data = response.json()
        if "customers" in data:
            customers = data["customers"]
            if isinstance(customers, list):
                passed = True
                details = f"Status: 200, Returned {len(customers)} customers"
            else:
                details = f"Status: 200, but 'customers' is not a list: {type(customers)}"
        else:
            details = f"Status: 200, but 'customers' key missing in response"
    elif response.status_code == 422:
        details = f"Status: 422 (Validation Error) - q parameter should be optional"
    
    log_test(
        "Stylist search with no q parameter returns customer list",
        passed,
        details
    )
    return customers if passed else []


def test_owner_search_by_name(token):
    """Test 3: Owner search by name still works."""
    # First get all customers to find a name to search for
    url = f"{BASE_URL}/owner/customers/search"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        log_test("Owner search by name", False, "Could not get customer list for test setup")
        return
    
    customers = response.json().get("customers", [])
    if not customers:
        log_test("Owner search by name", False, "No customers available for testing")
        return
    
    # Pick first customer with a name
    test_customer = None
    for c in customers:
        if c.get("customer_name"):
            test_customer = c
            break
    
    if not test_customer:
        log_test("Owner search by name", False, "No customers with names found")
        return
    
    # Search by partial name
    search_name = test_customer["customer_name"].split()[0]  # First name
    url = f"{BASE_URL}/owner/customers/search?q={search_name}"
    response = requests.get(url, headers=headers)
    
    passed = False
    details = f"Status: {response.status_code}"
    
    if response.status_code == 200:
        data = response.json()
        customers = data.get("customers", [])
        # Check if the search returned results
        if len(customers) > 0:
            # Check if any result matches the search
            found = any(search_name.lower() in c.get("customer_name", "").lower() for c in customers)
            passed = found
            details = f"Status: 200, Searched for '{search_name}', Found {len(customers)} results, Match: {found}"
        else:
            details = f"Status: 200, but no results for name '{search_name}'"
    
    log_test("Owner search by name filtering works", passed, details)


def test_owner_search_by_phone(token):
    """Test 4: Owner search by phone still works."""
    # First get all customers to find a phone to search for
    url = f"{BASE_URL}/owner/customers/search"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        log_test("Owner search by phone", False, "Could not get customer list for test setup")
        return
    
    customers = response.json().get("customers", [])
    if not customers:
        log_test("Owner search by phone", False, "No customers available for testing")
        return
    
    # Pick first customer with a phone
    test_customer = customers[0]
    test_phone = test_customer.get("customer_phone", "")
    
    if not test_phone:
        log_test("Owner search by phone", False, "No customers with phone found")
        return
    
    # Search by partial phone (last 4 digits)
    search_phone = test_phone[-4:]
    url = f"{BASE_URL}/owner/customers/search?q={search_phone}"
    response = requests.get(url, headers=headers)
    
    passed = False
    details = f"Status: {response.status_code}"
    
    if response.status_code == 200:
        data = response.json()
        customers = data.get("customers", [])
        # Check if the search returned the customer
        if len(customers) > 0:
            found = any(c.get("customer_phone", "").endswith(search_phone) for c in customers)
            passed = found
            details = f"Status: 200, Searched for phone ending '{search_phone}', Found {len(customers)} results, Match: {found}"
        else:
            details = f"Status: 200, but no results for phone '{search_phone}'"
    
    log_test("Owner search by phone filtering works", passed, details)


def test_stylist_search_by_name():
    """Test 5: Stylist search by name still works."""
    # First get all customers to find a name to search for
    url = f"{BASE_URL}/stylist/{STYLIST_ID}/customers/search"
    response = requests.get(url)
    
    if response.status_code != 200:
        log_test("Stylist search by name", False, "Could not get customer list for test setup")
        return
    
    customers = response.json().get("customers", [])
    if not customers:
        log_test("Stylist search by name", False, "No customers available for testing")
        return
    
    # Pick first customer with a name
    test_customer = None
    for c in customers:
        if c.get("customer_name"):
            test_customer = c
            break
    
    if not test_customer:
        log_test("Stylist search by name", False, "No customers with names found")
        return
    
    # Search by partial name
    search_name = test_customer["customer_name"].split()[0]  # First name
    url = f"{BASE_URL}/stylist/{STYLIST_ID}/customers/search?q={search_name}"
    response = requests.get(url)
    
    passed = False
    details = f"Status: {response.status_code}"
    
    if response.status_code == 200:
        data = response.json()
        customers = data.get("customers", [])
        if len(customers) > 0:
            found = any(search_name.lower() in c.get("customer_name", "").lower() for c in customers)
            passed = found
            details = f"Status: 200, Searched for '{search_name}', Found {len(customers)} results, Match: {found}"
        else:
            details = f"Status: 200, but no results for name '{search_name}'"
    
    log_test("Stylist search by name filtering works", passed, details)


def test_phone_with_plus_sign(token):
    """Test 6: Phone containing + does not cause 500 error."""
    # Test with a phone number containing +
    test_phone = "+918511111593"
    url = f"{BASE_URL}/owner/customers/search?q={test_phone}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    passed = response.status_code != 500
    details = f"Status: {response.status_code}, Expected: not 500"
    
    if response.status_code == 200:
        data = response.json()
        customers = data.get("customers", [])
        details = f"Status: 200, Returned {len(customers)} customers (no 500 error)"
    
    log_test("Phone with + character does not cause 500 error", passed, details)


def test_phone_with_special_chars(token):
    """Test 7: Phone with other regex special chars does not cause 500."""
    # Test with various regex special characters
    special_chars_phones = [
        "+91(851)111-1593",
        "+91.851.111.1593",
        "851*111*1593"
    ]
    
    all_passed = True
    failed_chars = []
    
    for test_phone in special_chars_phones:
        url = f"{BASE_URL}/owner/customers/search?q={test_phone}"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 500:
            all_passed = False
            failed_chars.append(test_phone)
    
    details = "All special char phones handled correctly" if all_passed else f"Failed for: {failed_chars}"
    log_test("Regex special characters in phone do not cause 500", all_passed, details)


def test_no_objectid_in_response(token):
    """Test 8: Response has no ObjectId serialization issues."""
    url = f"{BASE_URL}/owner/customers/search"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    passed = False
    details = f"Status: {response.status_code}"
    
    if response.status_code == 200:
        try:
            data = response.json()
            # Check if response is valid JSON (no ObjectId serialization issues)
            # Look for actual ObjectId issues, not field names containing "_id"
            response_text = response.text
            has_objectid = "ObjectId(" in response_text
            # Also check if any customer has a raw "_id" field (not preferred_stylist_id, etc.)
            customers = data.get("customers", [])
            has_raw_id = any("_id" in c and c.get("_id") is not None for c in customers)
            passed = not has_objectid and not has_raw_id
            details = f"Status: 200, ObjectId() found: {has_objectid}, Raw _id field: {has_raw_id}"
        except json.JSONDecodeError as e:
            details = f"Status: 200, but JSON decode error: {str(e)}"
    
    log_test("No ObjectId serialization issues in response", passed, details)


def test_response_has_required_fields(token):
    """Test 9: Response contains customer_phone and customer_name fields."""
    url = f"{BASE_URL}/owner/customers/search"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    passed = False
    details = f"Status: {response.status_code}"
    
    if response.status_code == 200:
        data = response.json()
        customers = data.get("customers", [])
        
        if len(customers) > 0:
            # Check first customer has required fields
            first_customer = customers[0]
            has_phone = "customer_phone" in first_customer
            has_name = "customer_name" in first_customer
            passed = has_phone and has_name
            details = f"Status: 200, {len(customers)} customers, customer_phone: {has_phone}, customer_name: {has_name}"
        else:
            # If no customers, we can't verify fields, but that's not a failure
            passed = True
            details = f"Status: 200, 0 customers (cannot verify fields but not an error)"
    
    log_test("Response contains customer_phone and customer_name fields", passed, details)


def test_profile_detail_still_works(token):
    """Test 10: Existing profile detail endpoint still works."""
    # First get a customer phone
    url = f"{BASE_URL}/owner/customers/search"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        log_test("Profile detail endpoint", False, "Could not get customer list for test setup")
        return
    
    customers = response.json().get("customers", [])
    if not customers:
        log_test("Profile detail endpoint", False, "No customers available for testing")
        return
    
    test_phone = customers[0].get("customer_phone", "")
    if not test_phone:
        log_test("Profile detail endpoint", False, "No customer phone found")
        return
    
    # Get profile detail
    url = f"{BASE_URL}/owner/customers/{test_phone}"
    response = requests.get(url, headers=headers)
    
    passed = False
    details = f"Status: {response.status_code}"
    
    if response.status_code == 200:
        data = response.json()
        # Check for expected profile fields
        required_fields = ["customer_phone", "customer_name", "visit_history", "visit_count", "lifetime_spend"]
        has_all_fields = all(field in data for field in required_fields)
        passed = has_all_fields
        missing = [f for f in required_fields if f not in data]
        details = f"Status: 200, All fields present: {has_all_fields}" + (f", Missing: {missing}" if missing else "")
    
    log_test("Profile detail endpoint still works", passed, details)


def test_profile_patch_still_works(token):
    """Test 11: Existing profile PATCH endpoint still works."""
    # First get a customer phone
    url = f"{BASE_URL}/owner/customers/search"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        log_test("Profile PATCH endpoint", False, "Could not get customer list for test setup")
        return
    
    customers = response.json().get("customers", [])
    if not customers:
        log_test("Profile PATCH endpoint", False, "No customers available for testing")
        return
    
    test_phone = customers[0].get("customer_phone", "")
    if not test_phone:
        log_test("Profile PATCH endpoint", False, "No customer phone found")
        return
    
    # Update profile with a test note
    test_note = f"Test note at {datetime.now().isoformat()}"
    url = f"{BASE_URL}/owner/customers/{test_phone}"
    payload = {"stylist_notes": test_note}
    response = requests.patch(url, json=payload, headers=headers)
    
    passed = False
    details = f"Status: {response.status_code}"
    
    if response.status_code == 200:
        data = response.json()
        # Verify the update was applied
        updated_note = data.get("stylist_notes", "")
        passed = updated_note == test_note
        details = f"Status: 200, Note updated correctly: {passed}"
    
    log_test("Profile PATCH endpoint still works", passed, details)


def test_stylist_profile_detail_still_works():
    """Test 12: Stylist profile detail endpoint still works."""
    # First get a customer phone
    url = f"{BASE_URL}/stylist/{STYLIST_ID}/customers/search"
    response = requests.get(url)
    
    if response.status_code != 200:
        log_test("Stylist profile detail endpoint", False, "Could not get customer list for test setup")
        return
    
    customers = response.json().get("customers", [])
    if not customers:
        log_test("Stylist profile detail endpoint", False, "No customers available for testing")
        return
    
    test_phone = customers[0].get("customer_phone", "")
    if not test_phone:
        log_test("Stylist profile detail endpoint", False, "No customer phone found")
        return
    
    # Get profile detail
    url = f"{BASE_URL}/stylist/{STYLIST_ID}/customers/{test_phone}"
    response = requests.get(url)
    
    passed = False
    details = f"Status: {response.status_code}"
    
    if response.status_code == 200:
        data = response.json()
        # Check for expected profile fields
        required_fields = ["customer_phone", "customer_name", "visit_history", "visit_count", "lifetime_spend"]
        has_all_fields = all(field in data for field in required_fields)
        passed = has_all_fields
        missing = [f for f in required_fields if f not in data]
        details = f"Status: 200, All fields present: {has_all_fields}" + (f", Missing: {missing}" if missing else "")
    
    log_test("Stylist profile detail endpoint still works", passed, details)


def run_all_tests():
    """Run all customer search API tests."""
    print("=" * 80)
    print("CUSTOMER SEARCH API TESTS - Optional 'q' Parameter")
    print("=" * 80)
    print()
    
    # Login first
    token = test_owner_login()
    if not token:
        print("\n❌ CRITICAL: Owner login failed. Cannot proceed with tests.")
        return
    
    print()
    
    # Run all tests
    test_owner_search_no_q(token)
    test_stylist_search_no_q()
    test_owner_search_by_name(token)
    test_owner_search_by_phone(token)
    test_stylist_search_by_name()
    test_phone_with_plus_sign(token)
    test_phone_with_special_chars(token)
    test_no_objectid_in_response(token)
    test_response_has_required_fields(token)
    test_profile_detail_still_works(token)
    test_profile_patch_still_works(token)
    test_stylist_profile_detail_still_works()
    
    # Summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {tests_passed + tests_failed}")
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")
    print(f"Success Rate: {(tests_passed / (tests_passed + tests_failed) * 100):.1f}%")
    print()
    
    if tests_failed > 0:
        print("❌ SOME TESTS FAILED")
        print("\nFailed tests:")
        for result in test_results:
            if "❌ FAIL" in result:
                print(f"  {result}")
    else:
        print("✅ ALL TESTS PASSED")
    
    print("=" * 80)


if __name__ == "__main__":
    run_all_tests()
