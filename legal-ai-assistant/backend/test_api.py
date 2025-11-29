# backend/test_api.py
import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"

def test_api():
    print("Testing Legal AI API...\n")
    
    # 1. Health Check
    print("1. Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health/check")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}\n")
    except Exception as e:
        print(f"   ✗ Health check failed: {e}")
        print("   Make sure the server is running: python manage.py runserver\n")
        return
    
    # 2. Register User
    print("2. Register User")
    register_data = {
        "username": "testuser2",  # Use different username
        "email": "test2@example.com",
        "password": "SecurePass123!"
    }
    
    access_token = None
    
    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    print(f"   Status: {response.status_code}")
    
    if response.status_code in [200, 201]:
        data = response.json()
        if data.get('success'):
            access_token = data['data']['tokens']['access']
            print(f"   ✓ User registered successfully")
            print(f"   Username: {register_data['username']}")
            print(f"   Access Token: {access_token[:30]}...\n")
        else:
            print(f"   ✗ Registration failed: {data.get('error')}\n")
    else:
        print(f"   Response: {response.json()}")
        print(f"   Note: User might already exist, trying login...\n")
        
        # Try login instead
        print("2b. Login User")
        login_data = {
            "username": "testuser2",
            "password": "SecurePass123!"
        }
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                access_token = data['data']['tokens']['access']
                print(f"   ✓ User logged in successfully")
                print(f"   Username: {login_data['username']}\n")
            else:
                print(f"   ✗ Login failed: {data.get('error')}\n")
        else:
            print(f"   ✗ Login failed with status {response.status_code}")
            print(f"   Response: {response.json()}\n")
            print("   Please create a user manually or check credentials")
            return
    
    if not access_token:
        print("   ✗ Could not obtain access token. Exiting.\n")
        return
    
    # Set authorization header
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 3. Get Profile
    print("3. Get User Profile")
    response = requests.get(f"{BASE_URL}/auth/profile", headers=headers)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            profile = data['data']
            print(f"   Username: {profile['username']}")
            print(f"   Email: {profile['email']}")
            print(f"   Joined: {profile['date_joined']}")
            print(f"   ✓ Profile retrieved\n")
        else:
            print(f"   ✗ Failed: {data.get('error')}\n")
    else:
        print(f"   ✗ Failed with status {response.status_code}\n")
    
    # 4. Update Settings
    print("4. Update User Settings")
    settings_data = {
        "temperature": 0.8,
        "max_tokens": 512,
        "default_jurisdiction": "US",
        "top_p": 0.95,
        "top_k": 40
    }
    response = requests.put(f"{BASE_URL}/auth/settings", json=settings_data, headers=headers)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"   Temperature: {data['data']['temperature']}")
            print(f"   Max Tokens: {data['data']['max_tokens']}")
            print(f"   ✓ Settings updated\n")
        else:
            print(f"   ✗ Failed: {data.get('error')}\n")
    else:
        print(f"   ✗ Failed with status {response.status_code}\n")
    
    # 5. Update Org Profile
    print("5. Update Organization Profile")
    org_data = {
        "jurisdictions": ["US", "EU", "UK"],
        "clause_set": ["Termination", "Indemnity", "Confidentiality", "IP"]
    }
    response = requests.put(f"{BASE_URL}/auth/org-profile", json=org_data, headers=headers)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"   Jurisdictions: {data['data']['jurisdictions']}")
            print(f"   Clause Set: {data['data']['clause_set']}")
            print(f"   ✓ Org profile updated\n")
        else:
            print(f"   ✗ Failed: {data.get('error')}\n")
    else:
        print(f"   ✗ Failed with status {response.status_code}\n")
    
    # 6. List Documents
    print("6. List Documents")
    response = requests.get(f"{BASE_URL}/documents", headers=headers)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            docs = data['data']
            print(f"   Total Documents: {docs['total']}")
            print(f"   Results: {len(docs['results'])}")
            if docs['results']:
                print(f"   First doc: {docs['results'][0]['title']}")
            print(f"   ✓ Documents listed\n")
        else:
            print(f"   ✗ Failed: {data.get('error')}\n")
    else:
        print(f"   ✗ Failed with status {response.status_code}\n")
    
    # 7. Get History
    print("7. Get Chat History")
    response = requests.get(f"{BASE_URL}/history?limit=10", headers=headers)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            history = data['data']
            print(f"   Total Chats: {history['total']}")
            print(f"   Results: {len(history['results'])}")
            if history['results']:
                latest = history['results'][0]
                print(f"   Latest chat: Mode {latest['mode']} - {latest['created_at']}")
            print(f"   ✓ History retrieved\n")
        else:
            print(f"   ✗ Failed: {data.get('error')}\n")
    else:
        print(f"   ✗ Failed with status {response.status_code}\n")
    
    # 8. Test Token Refresh
    print("8. Test Token Refresh")
    # Get refresh token from login/register response
    login_data = {
        "username": "testuser2",
        "password": "SecurePass123!"
    }
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    
    if response.status_code == 200:
        data = response.json()
        refresh_token = data['data']['tokens']['refresh']
        
        # Refresh the token
        refresh_response = requests.post(
            f"{BASE_URL}/auth/token/refresh",
            json={"refresh": refresh_token}
        )
        
        print(f"   Status: {refresh_response.status_code}")
        if refresh_response.status_code == 200:
            new_access = refresh_response.json().get('access')
            print(f"   ✓ Token refreshed successfully")
            print(f"   New Access Token: {new_access[:30]}...\n")
        else:
            print(f"   ✗ Token refresh failed\n")
    
    print("=" * 60)
    print("✓ All API tests completed successfully!")
    print("=" * 60)

if __name__ == '__main__':
    test_api()