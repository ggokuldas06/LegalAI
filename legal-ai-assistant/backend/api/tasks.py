# api/tasks.py
from celery import shared_task
from django.contrib.auth.models import User
from .models import Document
from .rag.ingestion import ingestion_service
import logging

logger = logging.getLogger(__name__)


@shared_task
def ingest_document_task(document_id: int, reindex: bool = False):
    """
    Celery task to ingest a document asynchronously
    """
    try:
        document = Document.objects.get(id=document_id)
        result = ingestion_service.ingest_document(document, reindex=reindex)
        
        logger.info(f"Async ingestion completed for document {document_id}")
        return result
        
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found")
        return {'success': False, 'error': 'Document not found'}
    except Exception as e:
        logger.error(f"Async ingestion failed for document {document_id}: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def ingest_user_documents_task(user_id: int, reindex: bool = False):
    """
    Celery task to ingest all documents for a user
    """
    try:
        user = User.objects.get(id=user_id)
        documents = Document.objects.filter(user=user)
        
        result = ingestion_service.ingest_multiple(list(documents), reindex=reindex)
        
        logger.info(f"Async ingestion completed for user {user_id}")
        return result
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'success': False, 'error': 'User not found'}
    except Exception as e:
        logger.error(f"Async ingestion failed for user {user_id}: {e}")
        return {'success': False, 'error': str(e)}