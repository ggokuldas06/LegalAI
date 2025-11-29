# api/views/chat_views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import StreamingHttpResponse
from django_ratelimit.decorators import ratelimit
import json
import logging

from ..serializers import ChatRequestSerializer, ChatLogSerializer
from ..models import ChatLog, Document, AuditLog
from ..inference.service import inference_service
from ..utils.helpers import get_client_ip, get_user_agent

logger = logging.getLogger(__name__)

# api/views/chat_views.py - Add at the very start of the chat function

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='30/h', method='POST')
def chat(request):
    """Chat endpoint"""
    import sys
    
    # Log to console immediately
    print("\n" + "="*80, file=sys.stderr)
    print(f"CHAT REQUEST RECEIVED", file=sys.stderr)
    print(f"User: {request.user.username}", file=sys.stderr)
    print(f"Data: {request.data}", file=sys.stderr)
    print("="*80 + "\n", file=sys.stderr)
    
    logger.info(f"Chat request received from user: {request.user.username}")
    
    # Rest of your code...
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='30/h', method='POST')
def chat(request):
    """
    Chat endpoint - sends message to LLM
    POST /api/v1/chat
    Body: {
        "mode": "A"|"B"|"C",
        "message": "...",
        "doc_id": 123,  // Required for A/B
        "filters": {},  // Optional for C
        "settings": {}, // Optional inference settings
        "stream": false
    }
    """
    # Validate request
    serializer = ChatRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    mode = data['mode']
    message = data['message']
    doc_id = data.get('doc_id')
    filters = data.get('filters', {})
    settings_override = data.get('settings', {})
    stream = data.get('stream', False)
    
    # Get document if needed
    document = None
    document_text = None
    document_title = None
    
    if mode in ['A', 'B']:
        try:
            document = Document.objects.get(id=doc_id, user=request.user)
            
            # Load document text from file
            with open(document.path, 'r', encoding='utf-8') as f:
                document_text = f.read()
            
            document_title = document.title
            
        except Document.DoesNotExist:
            return Response({
                'success': False,
                'error': f'Document {doc_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error loading document: {e}")
            return Response({
                'success': False,
                'error': 'Failed to load document'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Get context passages for mode C (TODO: implement RAG retrieval)
    context_passages = []
    if mode == 'C':
        # Use RAG retrieval for Mode C
        try:
            from ..rag.retrieval import retrieval_service
            
            context_passages = retrieval_service.retrieve_for_mode_c(
                question=message,
                jurisdiction=filters.get('jurisdiction'),
                year_from=filters.get('year_from'),
                year_to=filters.get('year_to'),
                keywords_include=filters.get('include', []),
                keywords_exclude=filters.get('exclude', []),
                k=5  # Top 5 most relevant chunks
            )
            
            logger.info(f"Retrieved {len(context_passages)} context passages for Mode C")
            
        except Exception as e:
            logger.warning(f"RAG retrieval failed, using empty context: {e}")
            context_passages = []

    
    # Merge user settings with override
    user_settings = {}
    try:
        user_settings = {
            'temperature': request.user.settings.temperature,
            'max_tokens': request.user.settings.max_tokens,
            'top_p': request.user.settings.top_p,
            'top_k': request.user.settings.top_k,
        }
    except:
        pass
    
    user_settings.update(settings_override)
    
    # Handle streaming
    if stream:
        return handle_streaming_chat(
            request, mode, message, document, document_text, 
            document_title, context_passages, filters, user_settings
        )
    
    # Non-streaming response
    try:
        # Call inference service
        result = inference_service.chat(
            mode=mode,
            message=message,
            document_text=document_text,
            document_title=document_title,
            context_passages=context_passages,
            filters=filters,
            settings_override=user_settings,
            stream=False,
        )
        
        if not result.get('success'):
            return Response({
                'success': False,
                'error': result.get('error', 'Unknown error')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Extract citations from processed response
        citations = []
        if result.get('processed'):
            citations = result['processed'].get('citations', [])
        
        # Save to chat log
        chat_log = ChatLog.objects.create(
            user=request.user,
            mode=mode,
            prompt=message,
            response=result['response'],
            document=document,
            citations=citations,
            tokens_in=result.get('tokens_in', 0),
            tokens_out=result.get('tokens_out', 0),
            latency_ms=result.get('latency_ms', 0),
            filters_used=filters,
        )
        
        # Audit log
        AuditLog.objects.create(
            user=request.user,
            action='chat',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            meta_json={
                'mode': mode,
                'chat_log_id': chat_log.id,
                'tokens_out': result.get('tokens_out', 0),
            }
        )
        
        return Response({
            'success': True,
            'data': {
                'chat_log_id': chat_log.id,
                'mode': mode,
                'response': result['response'],
                'processed': result.get('processed'),
                'citations': citations,
                'tokens_in': result.get('tokens_in', 0),
                'tokens_out': result.get('tokens_out', 0),
                'latency_ms': result.get('latency_ms', 0),
            }
        })
        
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def handle_streaming_chat(request, mode, message, document, document_text, 
                          document_title, context_passages, filters, user_settings):
    """Handle streaming chat response"""
    
    def event_stream():
        try:
            # Get streaming generator
            stream = inference_service.chat(
                mode=mode,
                message=message,
                document_text=document_text,
                document_title=document_title,
                context_passages=context_passages,
                filters=filters,
                settings_override=user_settings,
                stream=True,
            )
            
            accumulated_text = ""
            tokens_in = 0
            
            for chunk in stream:
                if chunk['type'] == 'start':
                    tokens_in = chunk.get('tokens_in', 0)
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                elif chunk['type'] == 'token':
                    token = chunk.get('token', '')
                    accumulated_text += token
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                elif chunk['type'] == 'done':
                    # Save to chat log
                    chat_log = ChatLog.objects.create(
                        user=request.user,
                        mode=mode,
                        prompt=message,
                        response=accumulated_text,
                        document=document,
                        citations=[],  # TODO: extract from accumulated_text
                        tokens_in=tokens_in,
                        tokens_out=len(accumulated_text.split()),  # Approximate
                        latency_ms=0,
                        filters_used=filters,
                    )
                    
                    chunk['chat_log_id'] = chat_log.id
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                elif chunk['type'] == 'error':
                    yield f"data: {json.dumps(chunk)}\n\n"
        
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            error_chunk = {'type': 'error', 'error': str(e)}
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    
    return response