# api/views/auth_views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from ..serializers import UserSerializer, UserSettingsSerializer, OrgProfileSerializer
from ..models import AuditLog, OrgProfile, UserSettings
from ..utils.helpers import get_client_ip, get_user_agent


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Register a new user
    POST /api/v1/auth/register
    Body: { "username": "...", "email": "...", "password": "..." }
    """
    serializer = UserSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            # Create user
            user = serializer.save()
            
            # Ensure OrgProfile exists
            OrgProfile.objects.get_or_create(
                user=user,
                defaults={
                    'jurisdictions': [],
                    'clause_set': []
                }
            )
            
            # Ensure UserSettings exists
            UserSettings.objects.get_or_create(
                user=user,
                defaults={
                    'temperature': 0.7,
                    'max_tokens': 256,
                    'top_p': 0.9,
                    'top_k': 50
                }
            )
            
            # Create audit log
            AuditLog.objects.create(
                user=user,
                action='register',
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                meta_json={'username': user.username}
            )
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'success': True,
                'data': {
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'date_joined': user.date_joined,
                    },
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Registration failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'success': False,
        'error': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    User login
    POST /api/v1/auth/login
    Body: { "username": "...", "password": "..." }
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response({
            'success': False,
            'error': 'Username and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = authenticate(username=username, password=password)
    
    if user is not None:
        # Create audit log
        AuditLog.objects.create(
            user=user,
            action='login',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'success': True,
            'data': {
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }
        })
    
    return Response({
        'success': False,
        'error': 'Invalid credentials'
    }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    User logout (blacklist refresh token)
    POST /api/v1/auth/logout
    Body: { "refresh": "..." }
    """
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='logout',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        
        return Response({
            'success': True,
            'message': 'Logged out successfully'
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """
    Get user profile with settings and org profile
    GET /api/v1/auth/profile
    """
    user = request.user
    
    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'date_joined': user.date_joined,
    }
    
    # Get or create user settings
    user_settings, _ = UserSettings.objects.get_or_create(
        user=user,
        defaults={
            'temperature': 0.7,
            'max_tokens': 256,
            'top_p': 0.9,
            'top_k': 50
        }
    )
    settings_serializer = UserSettingsSerializer(user_settings)
    user_data['settings'] = settings_serializer.data
    
    # Get or create org profile
    org_profile, _ = OrgProfile.objects.get_or_create(
        user=user,
        defaults={
            'jurisdictions': [],
            'clause_set': []
        }
    )
    org_serializer = OrgProfileSerializer(org_profile)
    user_data['org_profile'] = org_serializer.data
    
    return Response({
        'success': True,
        'data': user_data
    })


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_settings(request):
    """
    Update user settings
    PUT /api/v1/auth/settings
    Body: { "temperature": 0.8, "max_tokens": 512, ... }
    """
    try:
        user_settings, _ = UserSettings.objects.get_or_create(user=request.user)
        serializer = UserSettingsSerializer(user_settings, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            
            # Audit log
            AuditLog.objects.create(
                user=request.user,
                action='settings_change',
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                meta_json={'changes': request.data}
            )
            
            return Response({
                'success': True,
                'data': serializer.data
            })
        
        return Response({
            'success': False,
            'error': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_org_profile(request):
    """
    Update organization profile
    PUT /api/v1/auth/org-profile
    Body: { "jurisdictions": [...], "clause_set": [...] }
    """
    try:
        org_profile, _ = OrgProfile.objects.get_or_create(user=request.user)
        serializer = OrgProfileSerializer(org_profile, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            
            return Response({
                'success': True,
                'data': serializer.data
            })
        
        return Response({
            'success': False,
            'error': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)