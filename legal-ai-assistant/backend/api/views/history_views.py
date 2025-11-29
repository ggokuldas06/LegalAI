# api/views/history_views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.paginator import Paginator

from ..serializers import ChatLogSerializer
from ..models import ChatLog


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def history(request):
    """
    Get chat history
    GET /api/v1/history?mode=A&limit=50&offset=0&search=...
    """
    user = request.user
    mode = request.query_params.get('mode')
    limit = int(request.query_params.get('limit', 50))
    offset = int(request.query_params.get('offset', 0))
    search = request.query_params.get('search')
    
    # Build query
    queryset = ChatLog.objects.filter(user=user)
    
    if mode:
        queryset = queryset.filter(mode=mode)
    
    if search:
        queryset = queryset.filter(prompt__icontains=search)
    
    # Get total count
    total = queryset.count()
    
    # Paginate
    queryset = queryset[offset:offset + limit]
    
    # Serialize
    serializer = ChatLogSerializer(queryset, many=True)
    
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
def history_detail(request, chat_id):
    """
    Get specific chat log
    GET /api/v1/history/<id>
    """
    try:
        chat_log = ChatLog.objects.get(id=chat_id, user=request.user)
        serializer = ChatLogSerializer(chat_log)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    except ChatLog.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Chat log not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def history_delete(request, chat_id):
    """
    Delete chat log
    DELETE /api/v1/history/<id>
    """
    try:
        chat_log = ChatLog.objects.get(id=chat_id, user=request.user)
        chat_log.delete()
        
        return Response({
            'success': True,
            'message': 'Chat log deleted'
        })
    
    except ChatLog.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Chat log not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def history_export(request):
    """
    Export chat history as JSON
    POST /api/v1/history/export
    Body: { "mode": "A", "from_date": "...", "to_date": "..." }
    """
    mode = request.data.get('mode')
    from_date = request.data.get('from_date')
    to_date = request.data.get('to_date')
    
    queryset = ChatLog.objects.filter(user=request.user)
    
    if mode:
        queryset = queryset.filter(mode=mode)
    
    if from_date:
        queryset = queryset.filter(created_at__gte=from_date)
    
    if to_date:
        queryset = queryset.filter(created_at__lte=to_date)
    
    serializer = ChatLogSerializer(queryset, many=True)
    
    return Response({
        'success': True,
        'data': {
            'count': queryset.count(),
            'history': serializer.data
        }
    })