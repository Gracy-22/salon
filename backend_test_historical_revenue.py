#!/usr/bin/env python3
"""
Backend test for historical demo analytics bookings with revenue validation.
Tests the seeding of 90 days of historical demo bookings with ₹35k-₹42k daily revenue.
"""
import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict

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


def test_backend_running():
    """Test 1: Backend is running and responding."""
    url = f"{BASE_URL}/owner/login"
    try:
        response = requests.post(url, json={"pin": OWNER_PIN}, timeout=10)
        passed = response.status_code in [200, 401]
        log_test(
            "Backend is running",
            passed,
            f"Status: {response.status_code}"
        )
        return passed
    except Exception as e:
        log_test("Backend is running", False, f"Error: {e}")
        return False


def test_owner_login():
    """Test 2: Owner login with PIN 9999 works."""
    token = owner_login()
    passed = token is not None
    log_test(
        "Owner login with PIN 9999",
        passed,
        f"Token received: {bool(token)}"
    )
    return token


def test_demo_bookings_all_90_days(token):
    """Test 3: Demo bookings exist for EXACTLY every one of the 90 dates before today (excluding today)."""
    headers = {"Authorization": f"Bearer {token}"}
    today = datetime.now().date()
    
    days_with_demo = 0
    days_without_demo = []
    total_demo_bookings = 0
    
    print("\n  Checking all 90 days for demo bookings...")
    
    # Check all 90 days before today
    for offset in range(1, 91):
        check_date = (today - timedelta(days=offset)).isoformat()
        url = f"{BASE_URL}/owner/bookings?date={check_date}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            bookings = data.get("bookings", [])
            demo_bookings = [b for b in bookings if b.get("demo_seed") is True]
            
            if len(demo_bookings) > 0:
                days_with_demo += 1
                total_demo_bookings += len(demo_bookings)
            else:
                days_without_demo.append(check_date)
    
    passed = days_with_demo == 90 and len(days_without_demo) == 0
    details = f"Days with demo: {days_with_demo}/90, Total demo bookings: {total_demo_bookings}"
    if days_without_demo:
        details += f"\n    Days without demo: {days_without_demo[:5]}"
    log_test("Demo bookings exist for all 90 days", passed, details)
    
    return passed, total_demo_bookings


def test_demo_booking_ids_format(token):
    """Test 4: All demo booking IDs start with 'demo-historical-' and include date."""
    headers = {"Authorization": f"Bearer {token}"}
    today = datetime.now().date()
    
    valid_ids = 0
    invalid_ids = []
    sample_ids = []
    
    # Check 10 sample dates
    for offset in [1, 10, 20, 30, 40, 50, 60, 70, 80, 90]:
        check_date = (today - timedelta(days=offset)).isoformat()
        url = f"{BASE_URL}/owner/bookings?date={check_date}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            bookings = data.get("bookings", [])
            
            for b in bookings:
                if b.get("demo_seed") is True:
                    booking_id = b.get("id", "")
                    expected_prefix = f"demo-historical-{check_date}"
                    
                    if booking_id.startswith(expected_prefix):
                        valid_ids += 1
                        if len(sample_ids) < 3:
                            sample_ids.append(booking_id)
                    else:
                        invalid_ids.append(booking_id)
    
    passed = valid_ids > 0 and len(invalid_ids) == 0
    details = f"Valid IDs: {valid_ids}, Invalid IDs: {len(invalid_ids)}"
    if sample_ids:
        details += f"\n    Sample IDs: {sample_ids[:2]}"
    if invalid_ids:
        details += f"\n    Invalid IDs: {invalid_ids[:3]}"
    log_test("Demo booking IDs follow correct format", passed, details)


def test_no_duplicate_demo_ids(token):
    """Test 5: No duplicate demo IDs; seed is idempotent."""
    headers = {"Authorization": f"Bearer {token}"}
    today = datetime.now().date()
    
    all_ids = set()
    duplicate_ids = []
    
    # Check all 90 days
    for offset in range(1, 91):
        check_date = (today - timedelta(days=offset)).isoformat()
        url = f"{BASE_URL}/owner/bookings?date={check_date}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            bookings = data.get("bookings", [])
            
            for b in bookings:
                if b.get("demo_seed") is True:
                    booking_id = b.get("id", "")
                    if booking_id in all_ids:
                        duplicate_ids.append(booking_id)
                    all_ids.add(booking_id)
    
    passed = len(duplicate_ids) == 0
    details = f"Total unique demo IDs: {len(all_ids)}, Duplicates: {len(duplicate_ids)}"
    if duplicate_ids:
        details += f"\n    Duplicate IDs: {duplicate_ids[:3]}"
    log_test("No duplicate demo IDs (idempotent seed)", passed, details)


def test_daily_revenue_range(token):
    """Test 6: CRITICAL - Each seeded date has revenue between ₹35,000 and ₹42,000, no ₹0 revenue days."""
    headers = {"Authorization": f"Bearer {token}"}
    today = datetime.now().date()
    
    days_in_range = 0
    days_below_range = []
    days_above_range = []
    days_zero_revenue = []
    revenue_by_date = {}
    
    print("\n  Checking daily revenue for all 90 days...")
    
    # Check all 90 days
    for offset in range(1, 91):
        check_date = (today - timedelta(days=offset)).isoformat()
        url = f"{BASE_URL}/owner/bookings?date={check_date}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            bookings = data.get("bookings", [])
            
            # Calculate revenue from done demo bookings
            daily_revenue = 0.0
            demo_done_count = 0
            
            for b in bookings:
                if b.get("demo_seed") is True and b.get("status") == "done":
                    service = b.get("service", {})
                    price = float(service.get("price", 0))
                    daily_revenue += price
                    demo_done_count += 1
            
            revenue_by_date[check_date] = {
                "revenue": daily_revenue,
                "count": demo_done_count
            }
            
            # Check if revenue is in range ₹35,000 - ₹42,000
            if daily_revenue == 0:
                days_zero_revenue.append(check_date)
            elif daily_revenue < 35000:
                days_below_range.append((check_date, daily_revenue))
            elif daily_revenue > 42000:
                days_above_range.append((check_date, daily_revenue))
            else:
                days_in_range += 1
    
    passed = (days_in_range == 90 and 
              len(days_zero_revenue) == 0 and 
              len(days_below_range) == 0 and 
              len(days_above_range) == 0)
    
    details = f"Days in range (₹35k-₹42k): {days_in_range}/90"
    if days_zero_revenue:
        details += f"\n    Days with ₹0 revenue: {len(days_zero_revenue)} - {days_zero_revenue[:3]}"
    if days_below_range:
        details += f"\n    Days below ₹35k: {len(days_below_range)} - {[(d, f'₹{r:,.0f}') for d, r in days_below_range[:3]]}"
    if days_above_range:
        details += f"\n    Days above ₹42k: {len(days_above_range)} - {[(d, f'₹{r:,.0f}') for d, r in days_above_range[:3]]}"
    
    # Show sample revenues
    sample_dates = [1, 30, 60, 90]
    sample_revenues = [(today - timedelta(days=d)).isoformat() for d in sample_dates]
    details += f"\n    Sample revenues: "
    for date in sample_revenues:
        if date in revenue_by_date:
            rev = revenue_by_date[date]["revenue"]
            details += f"{date}: ₹{rev:,.0f}, "
    
    log_test("Daily revenue in range ₹35k-₹42k, no ₹0 days", passed, details)
    
    return passed, revenue_by_date


def test_revenue_insights_current_month(token):
    """Test 7: /api/owner/revenue-insights period=month returns populated daily revenue_series."""
    today = datetime.now().date()
    anchor_date = today.isoformat()
    url = f"{BASE_URL}/owner/revenue-insights?period=month&anchor_date={anchor_date}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        log_test("Revenue insights current month populated", False, f"Status: {response.status_code}")
        return False
    
    data = response.json()
    
    # Check revenue_series exists and has data
    revenue_series = data.get("revenue_series", [])
    series_length = len(revenue_series)
    
    # Count days with non-zero revenue (should be historical days before today)
    days_with_revenue = sum(1 for entry in revenue_series if entry.get("revenue", 0) > 0)
    
    # Check response shape
    has_range = "range" in data
    has_kpis = "kpis" in data
    has_status_counts = "status_counts" in data
    has_revenue_per_stylist = "revenue_per_stylist" in data
    has_revenue_per_service = "revenue_per_service" in data
    has_revenue_series = "revenue_series" in data
    
    response_shape_ok = all([has_range, has_kpis, has_status_counts, 
                             has_revenue_per_stylist, has_revenue_per_service, 
                             has_revenue_series])
    
    # For current month, we should have revenue for days before today
    passed = series_length > 0 and days_with_revenue > 0 and response_shape_ok
    
    details = f"Series length: {series_length}, Days with revenue: {days_with_revenue}, Response shape OK: {response_shape_ok}"
    log_test("Revenue insights current month populated", passed, details)
    
    return passed


def test_revenue_per_stylist_varied(token):
    """Test 8: revenue_per_stylist is populated with varied values."""
    url = f"{BASE_URL}/owner/revenue-insights?period=month"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        log_test("Revenue per stylist varied", False, f"Status: {response.status_code}")
        return False
    
    data = response.json()
    revenue_per_stylist = data.get("revenue_per_stylist", [])
    
    # Check we have multiple stylists
    has_multiple_stylists = len(revenue_per_stylist) >= 2
    
    # Check values are varied (not all the same)
    revenues = [s.get("revenue", 0) for s in revenue_per_stylist]
    unique_revenues = len(set(revenues))
    values_varied = unique_revenues > 1 if len(revenues) > 1 else True
    
    # Check all have non-zero revenue
    all_non_zero = all(r > 0 for r in revenues)
    
    passed = has_multiple_stylists and values_varied and all_non_zero
    
    details = f"Stylists: {len(revenue_per_stylist)}, Unique revenues: {unique_revenues}, All non-zero: {all_non_zero}"
    if revenue_per_stylist:
        sample = revenue_per_stylist[:3]
        sample_str = [(s.get('name'), f"₹{s.get('revenue', 0):,.0f}") for s in sample]
        details += f"\n    Sample: {sample_str}"
    
    log_test("Revenue per stylist varied", passed, details)


def test_revenue_per_service_varied(token):
    """Test 9: revenue_per_service is populated with varied values."""
    url = f"{BASE_URL}/owner/revenue-insights?period=month"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        log_test("Revenue per service varied", False, f"Status: {response.status_code}")
        return False
    
    data = response.json()
    revenue_per_service = data.get("revenue_per_service", [])
    
    # Check we have multiple services
    has_multiple_services = len(revenue_per_service) >= 2
    
    # Check values are varied (not all the same)
    revenues = [s.get("revenue", 0) for s in revenue_per_service]
    unique_revenues = len(set(revenues))
    values_varied = unique_revenues > 1 if len(revenues) > 1 else True
    
    # Check all have non-zero revenue
    all_non_zero = all(r > 0 for r in revenues)
    
    passed = has_multiple_services and values_varied and all_non_zero
    
    details = f"Services: {len(revenue_per_service)}, Unique revenues: {unique_revenues}, All non-zero: {all_non_zero}"
    if revenue_per_service:
        sample = revenue_per_service[:3]
        sample_str = [(s.get('name'), f"₹{s.get('revenue', 0):,.0f}") for s in sample]
        details += f"\n    Sample: {sample_str}"
    
    log_test("Revenue per service varied", passed, details)


def test_no_objectid_serialization(token):
    """Test 10: No ObjectId serialization issues in any response."""
    headers = {"Authorization": f"Bearer {token}"}
    today = datetime.now().date()
    
    # Test revenue insights
    url1 = f"{BASE_URL}/owner/revenue-insights?period=month"
    response1 = requests.get(url1, headers=headers)
    
    # Test bookings endpoint
    check_date = (today - timedelta(days=30)).isoformat()
    url2 = f"{BASE_URL}/owner/bookings?date={check_date}"
    response2 = requests.get(url2, headers=headers)
    
    objectid_found = False
    error_details = []
    
    if response1.status_code == 200:
        text1 = response1.text
        if "ObjectId" in text1 or '"_id"' in text1:
            objectid_found = True
            error_details.append("revenue-insights")
    
    if response2.status_code == 200:
        text2 = response2.text
        if "ObjectId" in text2 or '"_id"' in text2:
            objectid_found = True
            error_details.append("bookings")
    
    passed = not objectid_found
    details = "No ObjectId found" if passed else f"ObjectId found in: {error_details}"
    log_test("No ObjectId serialization issues", passed, details)


def main():
    print("=" * 80)
    print("Backend Test: Historical Demo Analytics Bookings with Revenue Validation")
    print("Testing: 90 days of demo bookings with ₹35k-₹42k daily revenue")
    print("=" * 80)
    print()
    
    # Test 1: Backend running
    if not test_backend_running():
        print("\n❌ Backend not running, cannot proceed")
        return
    
    # Test 2: Owner login
    token = test_owner_login()
    if not token:
        print("\n❌ Cannot proceed without valid owner token")
        return
    
    print("\n" + "-" * 80)
    print("Testing Demo Bookings Coverage")
    print("-" * 80)
    
    # Test 3: All 90 days have demo bookings
    has_all_days, total_bookings = test_demo_bookings_all_90_days(token)
    
    # Test 4: Demo booking IDs format
    test_demo_booking_ids_format(token)
    
    # Test 5: No duplicate IDs
    test_no_duplicate_demo_ids(token)
    
    print("\n" + "-" * 80)
    print("Testing Daily Revenue Range (CRITICAL)")
    print("-" * 80)
    
    # Test 6: CRITICAL - Daily revenue in range ₹35k-₹42k
    revenue_ok, revenue_data = test_daily_revenue_range(token)
    
    print("\n" + "-" * 80)
    print("Testing Revenue Insights API")
    print("-" * 80)
    
    # Test 7: Revenue insights current month
    test_revenue_insights_current_month(token)
    
    # Test 8: Revenue per stylist varied
    test_revenue_per_stylist_varied(token)
    
    # Test 9: Revenue per service varied
    test_revenue_per_service_varied(token)
    
    # Test 10: No ObjectId serialization
    test_no_objectid_serialization(token)
    
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
        print("\nFailed tests:")
        for result in test_results:
            if "❌ FAIL" in result:
                print(f"  {result}")
        exit(1)
    else:
        print("\n✅ ALL TESTS PASSED")
        print(f"\nVerified: {total_bookings} demo bookings across 90 days")
        print("All days have revenue between ₹35,000 and ₹42,000")
        print("No days with ₹0 revenue")
        print("Business open 7 days/week with consistent demo data")
        exit(0)


if __name__ == "__main__":
    main()
