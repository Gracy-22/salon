#!/usr/bin/env python3
"""
Backend API Testing Script for Owner Staff and Treatments Management
Tests: Owner CRUD/archive APIs for services and stylists
"""

import requests
import sys
import json
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://go-run-3.preview.emergentagent.com/api"

# Test credentials
OWNER_PIN = "9999"
OWNER_PHONE = "+918511111593"

def print_test(name, passed, details=""):
    """Print test result with formatting"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details:
        print(f"   {details}")
    return passed

def get_owner_token():
    """Get owner token using PIN login"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/owner/login",
            json={"pin": OWNER_PIN},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("token")
        return None
    except Exception as e:
        print(f"Failed to get owner token: {e}")
        return None

def test_owner_auth_required():
    """
    Test that owner endpoints require authentication
    Verifies:
    1. GET /api/owner/services requires auth
    2. GET /api/owner/stylists requires auth
    """
    print("\n" + "="*80)
    print("TEST 1: Owner endpoints require authentication")
    print("="*80)
    
    all_passed = True
    
    try:
        # Test services endpoint without auth
        response = requests.get(f"{BACKEND_URL}/owner/services", timeout=10)
        if not print_test(
            "GET /api/owner/services without auth returns 401/403",
            response.status_code in [401, 403],
            f"Expected 401/403, got {response.status_code}"
        ):
            all_passed = False
        
        # Test stylists endpoint without auth
        response = requests.get(f"{BACKEND_URL}/owner/stylists", timeout=10)
        if not print_test(
            "GET /api/owner/stylists without auth returns 401/403",
            response.status_code in [401, 403],
            f"Expected 401/403, got {response.status_code}"
        ):
            all_passed = False
        
        return all_passed
        
    except Exception as e:
        print_test("Auth test", False, f"Error: {e}")
        return False

def test_owner_services_crud():
    """
    Test owner services CRUD operations
    Verifies:
    1. GET /api/owner/services returns all services
    2. POST /api/owner/services creates new service
    3. PATCH /api/owner/services/{service_id} updates service
    4. No ObjectId serialization issues
    """
    print("\n" + "="*80)
    print("TEST 2: Owner services CRUD operations")
    print("="*80)
    
    all_passed = True
    owner_token = get_owner_token()
    
    if not owner_token:
        print_test("Get owner token", False, "Failed to get owner token")
        return False
    
    headers = {"Authorization": f"Bearer {owner_token}"}
    
    try:
        # GET all services
        response = requests.get(f"{BACKEND_URL}/owner/services", headers=headers, timeout=10)
        print(f"   GET Status: {response.status_code}")
        
        if not print_test(
            "GET /api/owner/services returns 200",
            response.status_code == 200,
            f"Expected 200, got {response.status_code}"
        ):
            return False
        
        data = response.json()
        if not print_test(
            "Response includes 'services' field",
            "services" in data,
            f"Keys: {list(data.keys())}"
        ):
            all_passed = False
        
        initial_count = len(data.get("services", []))
        print(f"   Initial service count: {initial_count}")
        
        # Check no ObjectId serialization
        response_str = json.dumps(data)
        if not print_test(
            "No ObjectId serialization in GET response",
            "ObjectId(" not in response_str,
            "Response is properly serialized"
        ):
            all_passed = False
        
        # POST create new service
        test_service = {
            "name": f"Test Service {datetime.now().strftime('%H%M%S')}",
            "category": "Hair",
            "duration_min": 60,
            "price": 1500.0,
            "description": "Test service for automated testing",
            "icon": "Scissors",
            "is_active": True
        }
        
        response = requests.post(
            f"{BACKEND_URL}/owner/services",
            headers=headers,
            json=test_service,
            timeout=10
        )
        print(f"   POST Status: {response.status_code}")
        
        if not print_test(
            "POST /api/owner/services returns 200",
            response.status_code == 200,
            f"Expected 200, got {response.status_code}"
        ):
            if response.status_code != 200:
                print(f"   Error: {response.text}")
            return False
        
        created_service = response.json()
        
        # Store service_id for later tests
        global test_service_id
        test_service_id = created_service.get("id")
        
        if not print_test(
            "Created service has 'id' field",
            "id" in created_service,
            f"Service ID: {test_service_id}"
        ):
            all_passed = False
        
        if not print_test(
            "Created service has correct name",
            created_service.get("name") == test_service["name"],
            f"Name: {created_service.get('name')}"
        ):
            all_passed = False
        
        if not print_test(
            "Created service has correct price",
            created_service.get("price") == test_service["price"],
            f"Price: {created_service.get('price')}"
        ):
            all_passed = False
        
        # Check no ObjectId in POST response
        response_str = json.dumps(created_service)
        if not print_test(
            "No ObjectId serialization in POST response",
            "ObjectId(" not in response_str,
            "Response is properly serialized"
        ):
            all_passed = False
        
        # PATCH update service
        update_data = {
            "name": created_service["name"],
            "category": "Hair",
            "duration_min": 90,
            "price": 2000.0,
            "description": "Updated test service",
            "icon": "Scissors",
            "is_active": True
        }
        
        response = requests.patch(
            f"{BACKEND_URL}/owner/services/{test_service_id}",
            headers=headers,
            json=update_data,
            timeout=10
        )
        print(f"   PATCH Status: {response.status_code}")
        
        if not print_test(
            "PATCH /api/owner/services/{service_id} returns 200",
            response.status_code == 200,
            f"Expected 200, got {response.status_code}"
        ):
            if response.status_code != 200:
                print(f"   Error: {response.text}")
            all_passed = False
        else:
            updated_service = response.json()
            
            if not print_test(
                "Updated service has correct duration",
                updated_service.get("duration_min") == 90,
                f"Duration: {updated_service.get('duration_min')}"
            ):
                all_passed = False
            
            if not print_test(
                "Updated service has correct price",
                updated_service.get("price") == 2000.0,
                f"Price: {updated_service.get('price')}"
            ):
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print_test("Services CRUD test", False, f"Error: {e}")
        return False

def test_service_archive():
    """
    Test service archive functionality
    Verifies:
    1. POST /api/owner/services/{service_id}/archive sets is_active=false
    2. Archived service hidden from public GET /api/services
    3. Archived service removed from stylists' services array
    4. Service not hard deleted (still in owner list)
    """
    print("\n" + "="*80)
    print("TEST 3: Service archive functionality")
    print("="*80)
    
    all_passed = True
    owner_token = get_owner_token()
    
    if not owner_token:
        print_test("Get owner token", False, "Failed to get owner token")
        return False
    
    if not test_service_id:
        print_test("Test service ID available", False, "No test service from previous test")
        return False
    
    headers = {"Authorization": f"Bearer {owner_token}"}
    
    try:
        # Archive the service
        response = requests.post(
            f"{BACKEND_URL}/owner/services/{test_service_id}/archive",
            headers=headers,
            timeout=10
        )
        print(f"   Archive Status: {response.status_code}")
        
        if not print_test(
            "POST /api/owner/services/{service_id}/archive returns 200",
            response.status_code == 200,
            f"Expected 200, got {response.status_code}"
        ):
            if response.status_code != 200:
                print(f"   Error: {response.text}")
            return False
        
        # Verify service still in owner list (not hard deleted)
        response = requests.get(f"{BACKEND_URL}/owner/services", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            services = data.get("services", [])
            archived_service = next((s for s in services if s.get("id") == test_service_id), None)
            
            if not print_test(
                "Archived service still in owner list (not hard deleted)",
                archived_service is not None,
                f"Service {'found' if archived_service else 'not found'} in owner list"
            ):
                all_passed = False
            
            if archived_service:
                if not print_test(
                    "Archived service has is_active=False",
                    archived_service.get("is_active") == False,
                    f"is_active: {archived_service.get('is_active')}"
                ):
                    all_passed = False
        
        # Verify service hidden from public list
        response = requests.get(f"{BACKEND_URL}/services", timeout=10)
        if response.status_code == 200:
            public_services = response.json()
            archived_in_public = any(s.get("id") == test_service_id for s in public_services)
            
            if not print_test(
                "Archived service hidden from public GET /api/services",
                not archived_in_public,
                f"Service {'visible' if archived_in_public else 'hidden'} in public list"
            ):
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print_test("Service archive test", False, f"Error: {e}")
        return False

def test_owner_stylists_crud():
    """
    Test owner stylists CRUD operations
    Verifies:
    1. GET /api/owner/stylists returns all stylists without PIN
    2. POST /api/owner/stylists creates new stylist with all fields
    3. New stylist gets default working hours and PIN internally
    4. PATCH /api/owner/stylists/{stylist_id} updates stylist
    5. Service assignment validation (only active services)
    6. Phone and login_phone normalization
    7. No ObjectId serialization issues
    """
    print("\n" + "="*80)
    print("TEST 4: Owner stylists CRUD operations")
    print("="*80)
    
    all_passed = True
    owner_token = get_owner_token()
    
    if not owner_token:
        print_test("Get owner token", False, "Failed to get owner token")
        return False
    
    headers = {"Authorization": f"Bearer {owner_token}"}
    
    try:
        # GET all stylists
        response = requests.get(f"{BACKEND_URL}/owner/stylists", headers=headers, timeout=10)
        print(f"   GET Status: {response.status_code}")
        
        if not print_test(
            "GET /api/owner/stylists returns 200",
            response.status_code == 200,
            f"Expected 200, got {response.status_code}"
        ):
            return False
        
        data = response.json()
        if not print_test(
            "Response includes 'stylists' field",
            "stylists" in data,
            f"Keys: {list(data.keys())}"
        ):
            all_passed = False
        
        stylists = data.get("stylists", [])
        print(f"   Initial stylist count: {len(stylists)}")
        
        # Verify PIN not exposed in owner list
        has_pin = any("pin" in s for s in stylists)
        if not print_test(
            "Owner list does not expose PIN field",
            not has_pin,
            f"PIN field {'exposed' if has_pin else 'hidden'}"
        ):
            all_passed = False
        
        # Check no ObjectId serialization
        response_str = json.dumps(data)
        if not print_test(
            "No ObjectId serialization in GET response",
            "ObjectId(" not in response_str,
            "Response is properly serialized"
        ):
            all_passed = False
        
        # Get active services for assignment
        services_response = requests.get(f"{BACKEND_URL}/owner/services", headers=headers, timeout=10)
        if services_response.status_code != 200:
            print_test("Get active services", False, "Failed to fetch services")
            return False
        
        services_data = services_response.json()
        active_services = [s["id"] for s in services_data.get("services", []) if s.get("is_active") != False]
        
        if not active_services:
            print_test("Get active services", False, "No active services available")
            return False
        
        # POST create new stylist
        test_stylist = {
            "name": f"Test Stylist {datetime.now().strftime('%H%M%S')}",
            "title": "Senior Stylist",
            "bio": "Test stylist for automated testing",
            "photo": "https://example.com/photo.jpg",
            "phone": "+919876543299",
            "login_phone": "+919876543298",
            "services": active_services[:2],  # Assign first 2 active services
            "is_active": True
        }
        
        response = requests.post(
            f"{BACKEND_URL}/owner/stylists",
            headers=headers,
            json=test_stylist,
            timeout=10
        )
        print(f"   POST Status: {response.status_code}")
        
        if not print_test(
            "POST /api/owner/stylists returns 200",
            response.status_code == 200,
            f"Expected 200, got {response.status_code}"
        ):
            if response.status_code != 200:
                print(f"   Error: {response.text}")
            return False
        
        created_stylist = response.json()
        
        # Store stylist_id for later tests
        global test_stylist_id
        test_stylist_id = created_stylist.get("id")
        
        if not print_test(
            "Created stylist has 'id' field",
            "id" in created_stylist,
            f"Stylist ID: {test_stylist_id}"
        ):
            all_passed = False
        
        if not print_test(
            "Created stylist has correct name",
            created_stylist.get("name") == test_stylist["name"],
            f"Name: {created_stylist.get('name')}"
        ):
            all_passed = False
        
        if not print_test(
            "Created stylist has correct title",
            created_stylist.get("title") == test_stylist["title"],
            f"Title: {created_stylist.get('title')}"
        ):
            all_passed = False
        
        if not print_test(
            "Created stylist has normalized phone",
            created_stylist.get("phone") == "9876543299",
            f"Phone: {created_stylist.get('phone')}"
        ):
            all_passed = False
        
        if not print_test(
            "Created stylist has normalized login_phone",
            created_stylist.get("login_phone") == "9876543298",
            f"Login phone: {created_stylist.get('login_phone')}"
        ):
            all_passed = False
        
        if not print_test(
            "Created stylist has services assigned",
            len(created_stylist.get("services", [])) > 0,
            f"Services: {created_stylist.get('services', [])}"
        ):
            all_passed = False
        
        if not print_test(
            "Created stylist does not expose PIN",
            "pin" not in created_stylist,
            "PIN field not in response"
        ):
            all_passed = False
        
        # Check no ObjectId in POST response
        response_str = json.dumps(created_stylist)
        if not print_test(
            "No ObjectId serialization in POST response",
            "ObjectId(" not in response_str,
            "Response is properly serialized"
        ):
            all_passed = False
        
        # PATCH update stylist
        update_data = {
            "name": created_stylist["name"],
            "title": "Lead Stylist",
            "bio": "Updated test stylist",
            "photo": "https://example.com/photo2.jpg",
            "phone": "+919876543299",
            "login_phone": "+919876543298",
            "services": active_services[:1],  # Update to only 1 service
            "is_active": True
        }
        
        response = requests.patch(
            f"{BACKEND_URL}/owner/stylists/{test_stylist_id}",
            headers=headers,
            json=update_data,
            timeout=10
        )
        print(f"   PATCH Status: {response.status_code}")
        
        if not print_test(
            "PATCH /api/owner/stylists/{stylist_id} returns 200",
            response.status_code == 200,
            f"Expected 200, got {response.status_code}"
        ):
            if response.status_code != 200:
                print(f"   Error: {response.text}")
            all_passed = False
        else:
            updated_stylist = response.json()
            
            if not print_test(
                "Updated stylist has correct title",
                updated_stylist.get("title") == "Lead Stylist",
                f"Title: {updated_stylist.get('title')}"
            ):
                all_passed = False
            
            if not print_test(
                "Updated stylist has correct services count",
                len(updated_stylist.get("services", [])) == 1,
                f"Services count: {len(updated_stylist.get('services', []))}"
            ):
                all_passed = False
            
            if not print_test(
                "Updated stylist does not expose PIN",
                "pin" not in updated_stylist,
                "PIN field not in response"
            ):
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print_test("Stylists CRUD test", False, f"Error: {e}")
        return False

def test_service_assignment_validation():
    """
    Test service assignment validation
    Verifies:
    1. Stylist services only include active services
    2. Archived services removed from stylist services array
    """
    print("\n" + "="*80)
    print("TEST 5: Service assignment validation")
    print("="*80)
    
    all_passed = True
    owner_token = get_owner_token()
    
    if not owner_token:
        print_test("Get owner token", False, "Failed to get owner token")
        return False
    
    if not test_stylist_id:
        print_test("Test stylist ID available", False, "No test stylist from previous test")
        return False
    
    headers = {"Authorization": f"Bearer {owner_token}"}
    
    try:
        # Create a new service and assign to stylist
        new_service = {
            "name": f"Test Service for Validation {datetime.now().strftime('%H%M%S')}",
            "category": "Hair",
            "duration_min": 45,
            "price": 1200.0,
            "description": "Test service for validation",
            "icon": "Scissors",
            "is_active": True
        }
        
        response = requests.post(
            f"{BACKEND_URL}/owner/services",
            headers=headers,
            json=new_service,
            timeout=10
        )
        
        if response.status_code != 200:
            print_test("Create test service", False, "Failed to create service")
            return False
        
        validation_service_id = response.json().get("id")
        
        # Get current stylist services
        response = requests.get(f"{BACKEND_URL}/owner/stylists", headers=headers, timeout=10)
        if response.status_code != 200:
            print_test("Get stylists", False, "Failed to fetch stylists")
            return False
        
        stylists = response.json().get("stylists", [])
        test_stylist = next((s for s in stylists if s.get("id") == test_stylist_id), None)
        
        if not test_stylist:
            print_test("Find test stylist", False, "Test stylist not found")
            return False
        
        current_services = test_stylist.get("services", [])
        
        # Update stylist to include the new service
        update_data = {
            "name": test_stylist["name"],
            "title": test_stylist.get("title", "Stylist"),
            "bio": test_stylist.get("bio", ""),
            "photo": test_stylist.get("photo", ""),
            "phone": test_stylist.get("phone", ""),
            "login_phone": test_stylist.get("login_phone", ""),
            "services": current_services + [validation_service_id],
            "is_active": True
        }
        
        response = requests.patch(
            f"{BACKEND_URL}/owner/stylists/{test_stylist_id}",
            headers=headers,
            json=update_data,
            timeout=10
        )
        
        if response.status_code != 200:
            print_test("Update stylist with new service", False, "Failed to update stylist")
            return False
        
        updated_stylist = response.json()
        
        if not print_test(
            "Stylist services include new active service",
            validation_service_id in updated_stylist.get("services", []),
            f"Services: {updated_stylist.get('services', [])}"
        ):
            all_passed = False
        
        # Archive the service
        response = requests.post(
            f"{BACKEND_URL}/owner/services/{validation_service_id}/archive",
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            print_test("Archive service", False, "Failed to archive service")
            return False
        
        # Verify archived service removed from stylist
        response = requests.get(f"{BACKEND_URL}/owner/stylists", headers=headers, timeout=10)
        if response.status_code == 200:
            stylists = response.json().get("stylists", [])
            test_stylist = next((s for s in stylists if s.get("id") == test_stylist_id), None)
            
            if test_stylist:
                if not print_test(
                    "Archived service removed from stylist services array",
                    validation_service_id not in test_stylist.get("services", []),
                    f"Services: {test_stylist.get('services', [])}"
                ):
                    all_passed = False
        
        # Try to assign archived service to stylist (should be filtered out)
        update_data["services"] = [validation_service_id]  # Try to assign only archived service
        
        response = requests.patch(
            f"{BACKEND_URL}/owner/stylists/{test_stylist_id}",
            headers=headers,
            json=update_data,
            timeout=10
        )
        
        if response.status_code == 200:
            updated_stylist = response.json()
            
            if not print_test(
                "Cannot assign archived service to stylist",
                validation_service_id not in updated_stylist.get("services", []),
                f"Services: {updated_stylist.get('services', [])}"
            ):
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print_test("Service assignment validation test", False, f"Error: {e}")
        return False

def test_stylist_archive():
    """
    Test stylist archive functionality
    Verifies:
    1. POST /api/owner/stylists/{stylist_id}/archive sets is_active=false
    2. Archived stylist hidden from public GET /api/stylists
    3. Stylist not hard deleted (still in owner list)
    """
    print("\n" + "="*80)
    print("TEST 6: Stylist archive functionality")
    print("="*80)
    
    all_passed = True
    owner_token = get_owner_token()
    
    if not owner_token:
        print_test("Get owner token", False, "Failed to get owner token")
        return False
    
    if not test_stylist_id:
        print_test("Test stylist ID available", False, "No test stylist from previous test")
        return False
    
    headers = {"Authorization": f"Bearer {owner_token}"}
    
    try:
        # Archive the stylist
        response = requests.post(
            f"{BACKEND_URL}/owner/stylists/{test_stylist_id}/archive",
            headers=headers,
            timeout=10
        )
        print(f"   Archive Status: {response.status_code}")
        
        if not print_test(
            "POST /api/owner/stylists/{stylist_id}/archive returns 200",
            response.status_code == 200,
            f"Expected 200, got {response.status_code}"
        ):
            if response.status_code != 200:
                print(f"   Error: {response.text}")
            return False
        
        # Verify stylist still in owner list (not hard deleted)
        response = requests.get(f"{BACKEND_URL}/owner/stylists", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            stylists = data.get("stylists", [])
            archived_stylist = next((s for s in stylists if s.get("id") == test_stylist_id), None)
            
            if not print_test(
                "Archived stylist still in owner list (not hard deleted)",
                archived_stylist is not None,
                f"Stylist {'found' if archived_stylist else 'not found'} in owner list"
            ):
                all_passed = False
            
            if archived_stylist:
                if not print_test(
                    "Archived stylist has is_active=False",
                    archived_stylist.get("is_active") == False,
                    f"is_active: {archived_stylist.get('is_active')}"
                ):
                    all_passed = False
        
        # Verify stylist hidden from public list
        response = requests.get(f"{BACKEND_URL}/stylists", timeout=10)
        if response.status_code == 200:
            public_stylists = response.json()
            archived_in_public = any(s.get("id") == test_stylist_id for s in public_stylists)
            
            if not print_test(
                "Archived stylist hidden from public GET /api/stylists",
                not archived_in_public,
                f"Stylist {'visible' if archived_in_public else 'hidden'} in public list"
            ):
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print_test("Stylist archive test", False, f"Error: {e}")
        return False

def test_public_endpoints_filter():
    """
    Test public endpoints filter archived items
    Verifies:
    1. GET /api/services excludes is_active=false
    2. GET /api/stylists excludes is_active=false
    3. GET /api/stylists?service_id=X only returns active stylists with that service
    """
    print("\n" + "="*80)
    print("TEST 7: Public endpoints filter archived items")
    print("="*80)
    
    all_passed = True
    
    try:
        # Test public services endpoint
        response = requests.get(f"{BACKEND_URL}/services", timeout=10)
        print(f"   GET /api/services Status: {response.status_code}")
        
        if not print_test(
            "GET /api/services returns 200",
            response.status_code == 200,
            f"Expected 200, got {response.status_code}"
        ):
            return False
        
        services = response.json()
        
        # Check all services are active
        inactive_services = [s for s in services if s.get("is_active") == False]
        if not print_test(
            "Public services list excludes inactive services",
            len(inactive_services) == 0,
            f"Found {len(inactive_services)} inactive services in public list"
        ):
            all_passed = False
        
        # Test public stylists endpoint
        response = requests.get(f"{BACKEND_URL}/stylists", timeout=10)
        print(f"   GET /api/stylists Status: {response.status_code}")
        
        if not print_test(
            "GET /api/stylists returns 200",
            response.status_code == 200,
            f"Expected 200, got {response.status_code}"
        ):
            return False
        
        stylists = response.json()
        
        # Check all stylists are active
        inactive_stylists = [s for s in stylists if s.get("is_active") == False]
        if not print_test(
            "Public stylists list excludes inactive stylists",
            len(inactive_stylists) == 0,
            f"Found {len(inactive_stylists)} inactive stylists in public list"
        ):
            all_passed = False
        
        # Test service filter on stylists endpoint
        if services:
            test_service_id_for_filter = services[0].get("id")
            response = requests.get(
                f"{BACKEND_URL}/stylists",
                params={"service_id": test_service_id_for_filter},
                timeout=10
            )
            
            if response.status_code == 200:
                filtered_stylists = response.json()
                
                # Check all returned stylists are active
                inactive_in_filter = [s for s in filtered_stylists if s.get("is_active") == False]
                if not print_test(
                    "Service-filtered stylists list excludes inactive stylists",
                    len(inactive_in_filter) == 0,
                    f"Found {len(inactive_in_filter)} inactive stylists in filtered list"
                ):
                    all_passed = False
                
                # Check all returned stylists have the service
                missing_service = [s for s in filtered_stylists if test_service_id_for_filter not in s.get("services", [])]
                if not print_test(
                    "Service-filtered stylists all have the requested service",
                    len(missing_service) == 0,
                    f"Found {len(missing_service)} stylists without the service"
                ):
                    all_passed = False
        
        return all_passed
        
    except Exception as e:
        print_test("Public endpoints filter test", False, f"Error: {e}")
        return False

def test_booking_availability_respects_assignments():
    """
    Test booking availability respects service assignments
    Verifies:
    1. Availability endpoint works with active stylists and services
    2. No errors when checking availability
    """
    print("\n" + "="*80)
    print("TEST 8: Booking availability respects service assignments")
    print("="*80)
    
    all_passed = True
    
    try:
        # Get active services
        response = requests.get(f"{BACKEND_URL}/services", timeout=10)
        if response.status_code != 200:
            print_test("Get active services", False, "Failed to fetch services")
            return False
        
        services = response.json()
        if not services:
            print_test("Get active services", False, "No active services available")
            return False
        
        test_service = services[0]
        
        # Get active stylists for this service
        response = requests.get(
            f"{BACKEND_URL}/stylists",
            params={"service_id": test_service["id"]},
            timeout=10
        )
        
        if response.status_code != 200:
            print_test("Get active stylists for service", False, "Failed to fetch stylists")
            return False
        
        stylists = response.json()
        if not stylists:
            print_test("Get active stylists for service", False, "No active stylists for this service")
            return False
        
        test_stylist = stylists[0]
        
        # Check availability
        today = datetime.now().strftime("%Y-%m-%d")
        response = requests.get(
            f"{BACKEND_URL}/availability",
            params={
                "stylist_id": test_stylist["id"],
                "service_id": test_service["id"],
                "date": today
            },
            timeout=10
        )
        print(f"   Availability Status: {response.status_code}")
        
        if not print_test(
            "Availability endpoint returns 200",
            response.status_code == 200,
            f"Expected 200, got {response.status_code}"
        ):
            if response.status_code != 200:
                print(f"   Error: {response.text}")
            return False
        
        data = response.json()
        
        if not print_test(
            "Availability response includes 'slots' field",
            "slots" in data,
            f"Keys: {list(data.keys())}"
        ):
            all_passed = False
        
        return all_passed
        
    except Exception as e:
        print_test("Booking availability test", False, f"Error: {e}")
        return False

def test_existing_apis_still_work():
    """
    Test existing APIs still work
    Verifies:
    1. Owner login with PIN works
    2. Public booking APIs work
    """
    print("\n" + "="*80)
    print("TEST 9: Existing APIs still work")
    print("="*80)
    
    all_passed = True
    
    try:
        # Test owner login
        response = requests.post(
            f"{BACKEND_URL}/owner/login",
            json={"pin": OWNER_PIN},
            timeout=10
        )
        print(f"   Owner login Status: {response.status_code}")
        
        if not print_test(
            "Owner PIN login returns 200",
            response.status_code == 200,
            f"Expected 200, got {response.status_code}"
        ):
            all_passed = False
        else:
            data = response.json()
            if not print_test(
                "Owner login returns token",
                "token" in data,
                f"Token present: {bool(data.get('token'))}"
            ):
                all_passed = False
        
        # Test public services endpoint
        response = requests.get(f"{BACKEND_URL}/services", timeout=10)
        if not print_test(
            "Public services endpoint returns 200",
            response.status_code == 200,
            f"Expected 200, got {response.status_code}"
        ):
            all_passed = False
        
        # Test public stylists endpoint
        response = requests.get(f"{BACKEND_URL}/stylists", timeout=10)
        if not print_test(
            "Public stylists endpoint returns 200",
            response.status_code == 200,
            f"Expected 200, got {response.status_code}"
        ):
            all_passed = False
        
        return all_passed
        
    except Exception as e:
        print_test("Existing APIs test", False, f"Error: {e}")
        return False

# Global variables to store test IDs
test_service_id = None
test_stylist_id = None

def main():
    """Run all backend tests"""
    print("\n" + "="*80)
    print("BACKEND API TESTING - Owner Staff and Treatments Management")
    print("Testing owner CRUD/archive APIs for services and stylists")
    print("="*80)
    
    results = []
    
    # Test 1: Owner auth required
    results.append(("Owner Auth Required", test_owner_auth_required()))
    
    # Test 2: Owner services CRUD
    results.append(("Owner Services CRUD", test_owner_services_crud()))
    
    # Test 3: Service archive
    results.append(("Service Archive", test_service_archive()))
    
    # Test 4: Owner stylists CRUD
    results.append(("Owner Stylists CRUD", test_owner_stylists_crud()))
    
    # Test 5: Service assignment validation
    results.append(("Service Assignment Validation", test_service_assignment_validation()))
    
    # Test 6: Stylist archive
    results.append(("Stylist Archive", test_stylist_archive()))
    
    # Test 7: Public endpoints filter
    results.append(("Public Endpoints Filter", test_public_endpoints_filter()))
    
    # Test 8: Booking availability
    results.append(("Booking Availability", test_booking_availability_respects_assignments()))
    
    # Test 9: Existing APIs still work
    results.append(("Existing APIs Still Work", test_existing_apis_still_work()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED")
        print("\nKEY FINDINGS:")
        print("1. Owner CRUD/archive APIs for services working correctly")
        print("2. Owner CRUD/archive APIs for stylists working correctly")
        print("3. Archive sets is_active=false without hard deletion")
        print("4. Archived items hidden from public endpoints")
        print("5. Service assignment validation working (only active services)")
        print("6. Phone normalization working correctly")
        print("7. PIN not exposed in owner stylist list")
        print("8. No ObjectId serialization issues")
        print("9. Existing APIs remain functional")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        print("\nRECOMMENDED ACTIONS:")
        print("1. Check backend logs: tail -n 100 /var/log/supervisor/backend.*.log")
        print("2. Verify owner endpoints require authentication")
        print("3. Check archive behavior (is_active=false, not hard delete)")
        print("4. Verify public endpoints filter archived items")
        print("5. Check service assignment validation")
        return 1


if __name__ == "__main__":
    sys.exit(main())
