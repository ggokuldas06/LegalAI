# api/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    OrgProfile, ChatLog, Document, Chunk, 
    AuditLog, UserSettings
)


# api/serializers.py - Update the UserSerializer class
class UserSerializer(serializers.ModelSerializer):
    """User serializer for registration and profile"""
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'date_joined']
        read_only_fields = ['id', 'date_joined']
    
    def create(self, validated_data):
        # Create user only - profiles will be created in the view
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user


class UserSettingsSerializer(serializers.ModelSerializer):
    """User inference and UI settings"""
    
    class Meta:
        model = UserSettings
        fields = [
            'temperature', 'max_tokens', 'top_p', 'top_k',
            'default_jurisdiction', 'default_year_from', 'default_year_to',
            'default_keywords_include', 'default_keywords_exclude',
            'updated_at'
        ]
        read_only_fields = ['updated_at']


class OrgProfileSerializer(serializers.ModelSerializer):
    """Organization profile serializer"""
    
    class Meta:
        model = OrgProfile
        fields = ['jurisdictions', 'clause_set', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class DocumentSerializer(serializers.ModelSerializer):
    """Document serializer"""
    chunk_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'doctype', 'title', 'jurisdiction', 'date',
            'source', 'sha256', 'meta_json', 'created_at', 'chunk_count'
        ]
        read_only_fields = ['id', 'sha256', 'created_at', 'chunk_count']
    
    def get_chunk_count(self, obj):
        return obj.chunks.count()


class ChunkSerializer(serializers.ModelSerializer):
    """Chunk serializer"""
    
    class Meta:
        model = Chunk
        fields = ['id', 'document', 'ord', 'heading', 'text', 'created_at']
        read_only_fields = ['id', 'created_at']


class ChatLogSerializer(serializers.ModelSerializer):
    """Chat log serializer"""
    user_username = serializers.CharField(source='user.username', read_only=True)
    document_title = serializers.CharField(source='document.title', read_only=True, allow_null=True)
    
    class Meta:
        model = ChatLog
        fields = [
            'id', 'user', 'user_username', 'mode', 'prompt', 'response',
            'document', 'document_title', 'citations', 'tokens_in', 'tokens_out',
            'latency_ms', 'filters_used', 'created_at'
        ]
        read_only_fields = [
            'id', 'user', 'user_username', 'document_title', 
            'tokens_in', 'tokens_out', 'latency_ms', 'created_at'
        ]


class ChatRequestSerializer(serializers.Serializer):
    """Chat request validation"""
    mode = serializers.ChoiceField(choices=['A', 'B', 'C'], required=True)
    message = serializers.CharField(required=True, max_length=10000)
    doc_id = serializers.IntegerField(required=False, allow_null=True)
    filters = serializers.JSONField(required=False, default=dict)
    settings = serializers.JSONField(required=False, default=dict)
    stream = serializers.BooleanField(required=False, default=False)
    
    def validate(self, data):
        """Custom validation based on mode"""
        mode = data['mode']
        
        # Modes A and B require a document
        if mode in ['A', 'B'] and not data.get('doc_id'):
            raise serializers.ValidationError({
                'doc_id': f'doc_id is required for mode {mode}'
            })
        
        return data


class AuditLogSerializer(serializers.ModelSerializer):
    """Audit log serializer"""
    user_username = serializers.CharField(source='user.username', read_only=True, allow_null=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_username', 'action', 'meta_json',
            'ip_address', 'user_agent', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'user_username', 'created_at']