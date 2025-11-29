# backend/test_chat_endpoint.py
import requests
import json

# First login to get token
login_response = requests.post(
    'http://localhost:8000/api/v1/auth/login',
    json={
        'username': 'testuser2',
        'password': 'SecurePass123!'
    }
)

if login_response.status_code != 200:
    print("Login failed!")
    print(login_response.text)
    exit(1)

token = login_response.json()['data']['tokens']['access']
print(f"✓ Logged in, got token: {token[:50]}...")

# Get documents
docs_response = requests.get(
    'http://localhost:8000/api/v1/documents',
    headers={'Authorization': f'Bearer {token}'}
)

print(f"\n✓ Got documents: {docs_response.json()}")

docs = docs_response.json()['data']['results']
if not docs:
    print("\n✗ No documents available. Upload one first.")
    exit(1)

doc_id = docs[0]['id']
print(f"\n✓ Using document ID: {doc_id}")

# Test chat
print("\n📤 Sending chat request (Mode A)...")
chat_response = requests.post(
    'http://localhost:8000/api/v1/chat',
    headers={'Authorization': f'Bearer {token}'},
    json={
        'mode': 'A',
        'message': 'Summarize this document',
        'doc_id': doc_id
    },
    timeout=120  # 2 minute timeout
)

print(f"Status: {chat_response.status_code}")

if chat_response.status_code == 200:
    result = chat_response.json()
    print("\n✓ Chat successful!")
    print(f"Response preview: {result['data']['response'][:200]}...")
    print(f"Tokens: {result['data']['tokens_in']} in, {result['data']['tokens_out']} out")
    print(f"Latency: {result['data']['latency_ms']}ms")
else:
    print(f"\n✗ Chat failed!")
    print(chat_response.text)