# api/views/health_views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connection
from django.conf import settings
import redis
import os

from ..inference.service import inference_service


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint
    GET /api/v1/health/check
    """
    health_status = {
        'status': 'healthy',
        'checks': {}
    }
    
    # Check database
    try:
        connection.ensure_connection()
        health_status['checks']['database'] = 'ok'
    except Exception as e:
        health_status['checks']['database'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Check Redis
    try:
        redis_client = redis.from_url(settings.CELERY_BROKER_URL)
        redis_client.ping()
        health_status['checks']['redis'] = 'ok'
    except Exception as e:
        health_status['checks']['redis'] = f'error: {str(e)}'
        health_status['status'] = 'degraded'
    
    # Check LLM model
    try:
        model_health = inference_service.health_check()
        if model_health['model_loaded']:
            health_status['checks']['llm_model'] = 'loaded'
        else:
            health_status['checks']['llm_model'] = 'not loaded'
            health_status['status'] = 'degraded'
    except Exception as e:
        health_status['checks']['llm_model'] = f'error: {str(e)}'
        health_status['status'] = 'degraded'
    
    # Check model file exists
    model_path = settings.MODEL_CONFIG.get('model_path')
    if model_path and os.path.exists(model_path):
        health_status['checks']['model_file'] = 'exists'
    else:
        health_status['checks']['model_file'] = 'missing'
        health_status['status'] = 'unhealthy'
    
    # Overall status code
    status_code = 200
    if health_status['status'] == 'degraded':
        status_code = 200  # Still operational
    elif health_status['status'] == 'unhealthy':
        status_code = 503  # Service unavailable
    
    return Response(health_status, status=status_code)


@api_view(['GET'])
@permission_classes([AllowAny])
def readiness(request):
    """
    Readiness probe for k8s/docker
    GET /api/v1/health/ready
    """
    try:
        # Check if model is loaded
        if not inference_service.engine.is_loaded():
            return Response({
                'ready': False,
                'reason': 'Model not loaded'
            }, status=503)
        
        # Check database
        connection.ensure_connection()
        
        return Response({'ready': True})
        
    except Exception as e:
        return Response({
            'ready': False,
            'reason': str(e)
        }, status=503)


@api_view(['GET'])
@permission_classes([AllowAny])
def liveness(request):
    """
    Liveness probe
    GET /api/v1/health/live
    """
    return Response({'alive': True})