# api/utils/helpers.py
from django.http import JsonResponse
from functools import wraps
import logging

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Extract client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """Extract user agent"""
    return request.META.get('HTTP_USER_AGENT', '')[:500]


def api_response(success=True, data=None, error=None, status=200):
    """Standardized API response format"""
    response_data = {
        'success': success,
    }
    
    if data is not None:
        response_data['data'] = data
    
    if error is not None:
        response_data['error'] = error
    
    return JsonResponse(response_data, status=status)


def handle_exceptions(func):
    """Decorator to handle exceptions in views"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            return api_response(
                success=False,
                error=str(e),
                status=500
            )
    return wrapper