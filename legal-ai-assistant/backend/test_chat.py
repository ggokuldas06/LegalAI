# backend/test_chat.py
import requests
import json
import os

BASE_URL = "http://localhost:8000/api/v1"

def test_chat_with_document():
    print("Testing Chat with Document Upload...\n")
    
    # 1. Login
    print("1. Login")
    login_data = {
        "username": "testuser2",
        "password": "SecurePass123!"
    }
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    
    if response.status_code != 200:
        print("   ✗ Login failed. Run test_api.py first to create user.")
        return
    
    access_token = response.json()['data']['tokens']['access']
    headers = {"Authorization": f"Bearer {access_token}"}
    print("   ✓ Logged in\n")
    
    # 2. Create sample document
    print("2. Create Sample Document")
    sample_text = """EMPLOYMENT AGREEMENT

This Employment Agreement ("Agreement") is entered into as of January 1, 2024.

Section 1: TERM
The employment term shall commence on January 1, 2024 and continue for two (2) years.

Section 2: COMPENSATION
Employee shall receive an annual base salary of $120,000, payable bi-weekly.

Section 3: TERMINATION
Either party may terminate this Agreement upon thirty (30) days written notice.

Section 4: CONFIDENTIALITY
Employee agrees to maintain confidentiality of all proprietary information.

Section 5: GOVERNING LAW
This Agreement shall be governed by the laws of the State of California.
"""
    
    # Save to temp file
    temp_path = "/tmp/sample_contract.txt"
    with open(temp_path, 'w') as f:
        f.write(sample_text)
    
    # Upload document
    with open(temp_path, 'rb') as f:
        files = {'file': ('sample_contract.txt', f, 'text/plain')}
        data = {
            'doctype': 'contract',
            'title': 'Sample Employment Agreement',
            'jurisdiction': 'US-CA',
            'source': 'Test'
        }
        response = requests.post(
            f"{BASE_URL}/documents/upload",
            headers=headers,
            files=files,
            data=data
        )
    
    if response.status_code != 201:
        print(f"   ✗ Upload failed: {response.json()}")
        return
    
    doc_data = response.json()['data']
    doc_id = doc_data['id']
    print(f"   ✓ Document uploaded (ID: {doc_id})\n")
    
    # 3. Test Mode A - Summarizer
    print("3. Test Mode A - Summarizer")
    chat_data = {
        "mode": "A",
        "message": "Summarize this employment agreement",
        "doc_id": doc_id
    }
    response = requests.post(f"{BASE_URL}/chat", json=chat_data, headers=headers)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()['data']
        print(f"   Tokens In: {result['tokens_in']}")
        print(f"   Tokens Out: {result['tokens_out']}")
        print(f"   Latency: {result['latency_ms']}ms")
        print(f"   Response Preview: {result['response'][:200]}...")
        print(f"   ✓ Mode A completed\n")
    else:
        print(f"   ✗ Chat failed: {response.json()}\n")
    
    # 4. Test Mode B - Clause Classifier
    print("4. Test Mode B - Clause Classifier")
    chat_data = {
        "mode": "B",
        "message": "Extract and classify clauses",
        "doc_id": doc_id
    }
    response = requests.post(f"{BASE_URL}/chat", json=chat_data, headers=headers)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()['data']
        print(f"   Latency: {result['latency_ms']}ms")
        if result.get('processed') and result['processed'].get('clauses'):
            print(f"   Clauses Found: {len(result['processed']['clauses'])}")
            for clause in result['processed']['clauses'][:3]:
                print(f"     - {clause.get('type')}: {clause.get('confidence')}")
        print(f"   ✓ Mode B completed\n")
    else:
        print(f"   ✗ Chat failed: {response.json()}\n")
    
    # 5. Test Mode C - Case Law (without RAG)
    print("5. Test Mode C - Case Law IRAC")
    chat_data = {
        "mode": "C",
        "message": "What is the standard for employment termination?",
    }
    response = requests.post(f"{BASE_URL}/chat", json=chat_data, headers=headers)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()['data']
        print(f"   Latency: {result['latency_ms']}ms")
        print(f"   Response Preview: {result['response'][:200]}...")
        print(f"   ✓ Mode C completed\n")
    else:
        print(f"   ✗ Chat failed: {response.json()}\n")
    
    # Cleanup
    os.remove(temp_path)
    
    print("✓ Chat tests completed!")

if __name__ == '__main__':
    test_chat_with_document()