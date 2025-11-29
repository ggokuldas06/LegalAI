# backend/test_rag.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Document, Chunk
from api.rag.ingestion import ingestion_service
from api.rag.retrieval import retrieval_service
from django.contrib.auth.models import User


def test_rag():
    print("Testing RAG System...\n")
    
    # 1. Check if we have documents
    print("1. Checking Documents")
    doc_count = Document.objects.count()
    print(f"   Total documents: {doc_count}")
    
    if doc_count == 0:
        print("   ⚠ No documents found. Upload some documents first.")
        return
    
    # Get a sample document
    document = Document.objects.first()
    print(f"   Sample document: {document.title}\n")
    
    # 2. Test Ingestion
    print("2. Testing Document Ingestion")
    result = ingestion_service.ingest_document(document, reindex=True)
    
    if result['success']:
        print(f"   ✓ Ingestion successful")
        print(f"   Chunks created: {result['chunks_created']}")
        print(f"   Embeddings generated: {result['embeddings_generated']}")
        print(f"   Text length: {result['text_length']}\n")
    else:
        print(f"   ✗ Ingestion failed: {result.get('error')}\n")
        return
    
    # 3. Check chunks in database
    print("3. Checking Database Chunks")
    chunk_count = Chunk.objects.filter(document=document).count()
    print(f"   Chunks in DB: {chunk_count}")
    
    if chunk_count > 0:
        sample_chunk = Chunk.objects.filter(document=document).first()
        print(f"   Sample chunk text: {sample_chunk.text[:100]}...")
        print(f"   Has embedding: {sample_chunk.embedding_json is not None}\n")
    
    # 4. Test Retrieval
    print("4. Testing Retrieval")
    queries = [
        "What are the termination conditions?",
        "What is the compensation structure?",
        "What are the confidentiality requirements?"
    ]
    
    for query in queries:
        print(f"\n   Query: '{query}'")
        results = retrieval_service.retrieve(query, k=3)
        
        if results:
            print(f"   Found {len(results)} results:")
            for i, result in enumerate(results[:2], 1):
                print(f"     {i}. Score: {result['score']:.3f}")
                print(f"        Text: {result['text'][:80]}...")
        else:
            print(f"   No results found")
    
    # 5. Test Mode C Retrieval
    print("\n5. Testing Mode C Retrieval")
    question = "What is the standard for termination?"
    
    context_passages = retrieval_service.retrieve_for_mode_c(
        question=question,
        k=3
    )
    
    print(f"   Question: '{question}'")
    print(f"   Retrieved {len(context_passages)} passages:")
    
    for i, passage in enumerate(context_passages, 1):
        print(f"\n   {i}. {passage['case_name']} ({passage['year']})")
        print(f"      Score: {passage['score']:.3f}")
        print(f"      Text: {passage['text'][:100]}...")
    
    # 6. Vector Store Stats
    print("\n6. Vector Store Statistics")
    from api.rag.vector_store import get_vector_store
    vector_store = get_vector_store()
    
    print(f"   Total vectors: {vector_store.size}")
    print(f"   Embedding dimension: {vector_store.embedding_dim}")
    
    print("\n" + "="*60)
    print("✓ RAG system test completed!")
    print("="*60)


if __name__ == '__main__':
    test_rag()