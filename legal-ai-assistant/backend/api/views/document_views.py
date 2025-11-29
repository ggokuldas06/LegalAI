# api/views/document_views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.core.files.storage import default_storage
from django.conf import settings
import os
import hashlib
import PyPDF2

from ..serializers import DocumentSerializer
from ..models import Document, AuditLog
from ..utils.helpers import get_client_ip, get_user_agent

import logging
logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_list(request):
    """
    List user's documents
    GET /api/v1/documents?doctype=contract&limit=50&offset=0
    """
    doctype = request.query_params.get('doctype')
    limit = int(request.query_params.get('limit', 50))
    offset = int(request.query_params.get('offset', 0))
    
    queryset = Document.objects.filter(user=request.user)
    
    if doctype:
        queryset = queryset.filter(doctype=doctype)
    
    total = queryset.count()
    documents = queryset[offset:offset + limit]
    
    serializer = DocumentSerializer(documents, many=True)
    
    return Response({
        'success': True,
        'data': {
            'total': total,
            'limit': limit,
            'offset': offset,
            'results': serializer.data
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_detail(request, doc_id):
    """
    Get document details
    GET /api/v1/documents/<id>
    """
    try:
        document = Document.objects.get(id=doc_id, user=request.user)
        serializer = DocumentSerializer(document)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    except Document.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Document not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def document_upload(request):
    """
    Upload a document
    POST /api/v1/documents/upload
    Form data:
        - file: PDF or TXT file
        - doctype: contract|case|regulation|statute|other
        - title: Document title
        - jurisdiction: (optional)
        - date: (optional)
        - source: (optional)
    """
    file_obj = request.FILES.get('file')
    
    if not file_obj:
        return Response({'success': False,
            'error': 'No file provided'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    doctype = request.data.get('doctype')
    title = request.data.get('title')
    jurisdiction = request.data.get('jurisdiction', '')
    date = request.data.get('date')
    source = request.data.get('source', '')
    
    # Validate required fields
    if not doctype or not title:
        return Response({
            'success': False,
            'error': 'doctype and title are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate file type
    file_ext = os.path.splitext(file_obj.name)[1].lower()
    if file_ext not in ['.pdf', '.txt']:
        return Response({
            'success': False,
            'error': 'Only PDF and TXT files are supported'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Calculate file hash
        file_obj.seek(0)
        file_hash = hashlib.sha256()
        for chunk in file_obj.chunks():
            file_hash.update(chunk)
        sha256 = file_hash.hexdigest()
        
        # Check for duplicates
        if Document.objects.filter(sha256=sha256, user=request.user).exists():
            return Response({
                'success': False,
                'error': 'Document already exists (duplicate detected)'
            }, status=status.HTTP_409_CONFLICT)
        
        # Save file to disk
        file_obj.seek(0)
        upload_dir = os.path.join(settings.BASE_DIR.parent, 'data', 'documents', str(request.user.id))
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        filename = f"{sha256}{file_ext}"
        file_path = os.path.join(upload_dir, filename)
        
        with open(file_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)
        
        # Extract metadata
        meta_json = {}
        page_count = 0
        
        if file_ext == '.pdf':
            try:
                with open(file_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    page_count = len(pdf_reader.pages)
                    
                    # Extract metadata
                    if pdf_reader.metadata:
                        meta_json['pdf_metadata'] = {
                            'author': pdf_reader.metadata.get('/Author'),
                            'creator': pdf_reader.metadata.get('/Creator'),
                            'producer': pdf_reader.metadata.get('/Producer'),
                            'subject': pdf_reader.metadata.get('/Subject'),
                        }
            except Exception as e:
                logger.warning(f"Could not extract PDF metadata: {e}")
        
        # Create document record
        document = Document.objects.create(
            user=request.user,
            doctype=doctype,
            title=title,
            jurisdiction=jurisdiction,
            date=date if date else None,
            path=file_path,
            source=source,
            sha256=sha256,
            meta_json=meta_json
        )
        
        # Audit log
        AuditLog.objects.create(
            user=request.user,
            action='upload',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            meta_json={
                'document_id': document.id,
                'title': title,
                'doctype': doctype,
                'file_size': file_obj.size,
            }
        )
        
        serializer = DocumentSerializer(document)
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Document upload error: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def document_delete(request, doc_id):
    """
    Delete a document
    DELETE /api/v1/documents/<id>
    """
    try:
        document = Document.objects.get(id=doc_id, user=request.user)
        
        # Delete file from disk
        if os.path.exists(document.path):
            os.remove(document.path)
        
        # Delete database record (cascades to chunks)
        document.delete()
        
        # Audit log
        AuditLog.objects.create(
            user=request.user,
            action='delete',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            meta_json={
                'document_id': doc_id,
                'title': document.title,
            }
        )
        
        return Response({
            'success': True,
            'message': 'Document deleted successfully'
        })
        
    except Document.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Document not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Document delete error: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_content(request, doc_id):
    """
    Get document text content
    GET /api/v1/documents/<id>/content
    """
    try:
        document = Document.objects.get(id=doc_id, user=request.user)
        
        # Read file content
        file_ext = os.path.splitext(document.path)[1].lower()
        
        if file_ext == '.txt':
            with open(document.path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        elif file_ext == '.pdf':
            content = ""
            with open(document.path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
        
        else:
            return Response({
                'success': False,
                'error': 'Unsupported file type'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': True,
            'data': {
                'document_id': document.id,
                'title': document.title,
                'content': content,
                'length': len(content),
            }
        })
        
    except Document.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Document not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error reading document: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)