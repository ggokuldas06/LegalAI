# api/views/rag_views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import logging

from ..models import Document
from ..rag.ingestion import ingestion_service
from ..rag.retrieval import retrieval_service
from ..utils.helpers import get_client_ip, get_user_agent
from ..models import AuditLog

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ingest_document(request):
    """
    Ingest a document into RAG system
    POST /api/v1/ingest
    Body: { "document_id": 123, "reindex": false }
    """
    document_id = request.data.get('document_id')
    reindex = request.data.get('reindex', False)
    
    if not document_id:
        return Response({
            'success': False,
            'error': 'document_id is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get document
        document = Document.objects.get(id=document_id, user=request.user)
        
        # Ingest
        result = ingestion_service.ingest_document(document, reindex=reindex)
        
        # Audit log
        AuditLog.objects.create(
            user=request.user,
            action='ingest',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            meta_json={
                'document_id': document_id,
                'chunks_created': result.get('chunks_created', 0),
            }
        )
        
        return Response({
            'success': result.get('success', False),
            'data': result
        })
        
    except Document.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Document not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Ingest endpoint error: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ingest_batch(request):
    """
    Ingest multiple documents
    POST /api/v1/ingest/batch
    Body: { "document_ids": [1, 2, 3], "reindex": false }
    """
    document_ids = request.data.get('document_ids', [])
    reindex = request.data.get('reindex', False)
    
    if not document_ids:
        return Response({
            'success': False,
            'error': 'document_ids is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get documents
        documents = Document.objects.filter(
            id__in=document_ids,
            user=request.user
        )
        
        if not documents:
            return Response({
                'success': False,
                'error': 'No documents found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Ingest
        result = ingestion_service.ingest_multiple(list(documents), reindex=reindex)
        
        return Response({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Batch ingest error: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def search(request):
    """
    Search for relevant document chunks
    POST /api/v1/search
    Body: {
        "query": "...",
        "k": 10,
        "filters": {
            "jurisdiction": "US",
            "year_from": 2015,
            "year_to": 2024,
            "include": ["keyword1"],
            "exclude": ["keyword2"]
        }
    }
    """
    query = request.data.get('query')
    k = request.data.get('k', 10)
    filters = request.data.get('filters', {})
    
    if not query:
        return Response({
            'success': False,
            'error': 'query is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Retrieve relevant chunks
        results = retrieval_service.retrieve(
            query=query,
            k=k,
            filters=filters
        )
        
        return Response({
            'success': True,
            'data': {
                'query': query,
                'results_count': len(results),
                'results': results
            }
        })
        
    except Exception as e:
        logger.error(f"Search endpoint error: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vector_store_stats(request):
    """
    Get vector store statistics
    GET /api/v1/rag/stats
    """
    try:
        from ..rag.vector_store import get_vector_store
        from ..models import Chunk
        
        vector_store = get_vector_store()
        
        # Get user's chunk count
        user_chunks = Chunk.objects.filter(
            document__user=request.user
        ).count()
        
        return Response({
            'success': True,
            'data': {
                'total_vectors': vector_store.size,
                'user_chunks': user_chunks,
                'embedding_dimension': vector_store.embedding_dim,
            }
        })
        
    except Exception as e:
        logger.error(f"Stats endpoint error: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)