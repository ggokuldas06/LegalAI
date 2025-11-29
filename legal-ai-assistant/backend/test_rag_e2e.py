# backend/test_rag_e2e.py
import requests
import json
import uuid  # added

BASE_URL = "http://localhost:8000/api/v1"

def test_rag_e2e():
    print("Testing RAG End-to-End...\n")
    
    # 1. Login
    print("1. Login")
    login_data = {
        "username": "testuser2",
        "password": "SecurePass123!"
    }
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    
    if response.status_code != 200:
        print("   ✗ Login failed")
        return
    
    access_token = response.json()['data']['tokens']['access']
    headers = {"Authorization": f"Bearer {access_token}"}
    print("   ✓ Logged in\n")
    
    # 2. Create sample legal document
    print("2. Upload Sample Legal Document")

    # Unique suffix per run to avoid server-side duplicate-by-content checks
    unique_suffix = uuid.uuid4().hex[:8]
    unique_title = f"Smith v. Jones Corp. [{unique_suffix}]"

    sample_case = f"""SMITH v. JONES CORPORATION
    
United States District Court, Southern District of California
Filed: March 15, 2020

BACKGROUND

This case involves a wrongful termination claim. The plaintiff, Jane Smith, was employed by Jones Corporation from January 2018 to December 2019.

LEGAL STANDARD

Under California Labor Code § 2922, employment relationships are presumed to be at-will unless modified by contract. An at-will employee may be terminated for any lawful reason or no reason at all.

However, wrongful termination claims can proceed when termination violates public policy. See Tameny v. Atlantic Richfield Co., 27 Cal.3d 167 (1980).

ANALYSIS

The plaintiff alleges she was terminated in retaliation for reporting safety violations to OSHA. Retaliation for reporting workplace safety concerns violates public policy.

The court finds that plaintiff has stated a cognizable claim for wrongful termination in violation of public policy.

CONCLUSION

Defendant's motion to dismiss is DENIED. This case will proceed to discovery.

[TEST RUN ID: {unique_suffix}]
"""
    
    # Save to temp file
    temp_path = "/tmp/sample_case.txt"
    with open(temp_path, 'w') as f:
        f.write(sample_case)
    
    # Upload
    with open(temp_path, 'rb') as f:
        files = {'file': ('sample_case.txt', f, 'text/plain')}
        data = {
            'doctype': 'case',
            'title': unique_title,  # changed
            'jurisdiction': 'US-CA',
            'date': '2020-03-15',
            'source': 'Test Case'
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
    
    # 3. Ingest document into RAG
    print("3. Ingest Document into RAG System")
    ingest_data = {
        "document_id": doc_id,
        "reindex": True
    }
    response = requests.post(
        f"{BASE_URL}/ingest",
        json=ingest_data,
        headers=headers
    )
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()['data']
        print(f"   ✓ Ingestion successful")
        print(f"   Chunks created: {result.get('chunks_created', 0)}")
        print(f"   Embeddings: {result.get('embeddings_generated', 0)}\n")
    else:
        print(f"   ✗ Ingestion failed: {response.json()}\n")
        return
    
    # 4. Test semantic search
    print("4. Test Semantic Search")
    search_queries = [
        "wrongful termination standard",
        "at-will employment",
        "retaliation for reporting violations"
    ]
    
    for query in search_queries:
        print(f"\n   Query: '{query}'")
        search_data = {
            "query": query,
            "k": 3
        }
        response = requests.post(
            f"{BASE_URL}/search",
            json=search_data,
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()['data']
            print(f"   Found {data['results_count']} results:")
            for i, result in enumerate(data['results'][:2], 1):
                print(f"     {i}. Score: {result['score']:.3f}")
                print(f"        {result['text'][:80]}...")
    
    # 5. Test Mode C with RAG
    print("\n5. Test Mode C - Case Law IRAC with RAG")
    chat_data = {
        "mode": "C",
        "message": "What is the legal standard for wrongful termination in California?",
        "filters": {
            "jurisdiction": "US-CA",
            "year_from": 2015
        }
    }
    response = requests.post(f"{BASE_URL}/chat", json=chat_data, headers=headers)
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()['data']
        print(f"   ✓ Chat completed")
        print(f"   Latency: {result['latency_ms']}ms")
        print(f"   Citations: {len(result.get('citations', []))}")
        print(f"\n   Response Preview:")
        print(f"   {result['response'][:300]}...\n")
    else:
        print(f"   ✗ Chat failed: {response.json()}\n")
    
    # 6. Get RAG stats
    print("6. RAG Statistics")
    response = requests.get(f"{BASE_URL}/rag/stats", headers=headers)
    
    if response.status_code == 200:
        stats = response.json()['data']
        print(f"   Total vectors: {stats['total_vectors']}")
        print(f"   User chunks: {stats['user_chunks']}")
        print(f"   Embedding dimension: {stats['embedding_dimension']}")
    
    print("\n" + "="*60)
    print("✓ RAG End-to-End test completed!")
    print("="*60)


if __name__ == '__main__':
    test_rag_e2e()
    