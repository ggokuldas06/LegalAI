from django.db import models

# Create your models here.
# api/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import json


class OrgProfile(models.Model):
    """Extended user profile for organization settings"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='org_profile')
    jurisdictions = models.JSONField(default=list, blank=True)  # ["US", "EU", "UK"]
    clause_set = models.JSONField(default=list, blank=True)  # Custom clause types
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'org_profile'

    def __str__(self):
        return f"Profile for {self.user.username}"


# api/models.py - Update ChatLog class
class ChatLog(models.Model):
    """Stores all chat interactions with the LLM"""
    MODE_CHOICES = [
        ('A', 'Summarizer'),
        ('B', 'Clause Classifier'),
        ('C', 'Case-Law IRAC'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_logs')
    mode = models.CharField(max_length=1, choices=MODE_CHOICES)
    prompt = models.TextField()
    response = models.TextField()
    
    # Add this field
    document = models.ForeignKey(
        'Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_logs',
        help_text='Associated document for modes A/B'
    )
    
    citations = models.JSONField(default=list, blank=True)  # List of citation objects
    tokens_in = models.IntegerField(default=0)
    tokens_out = models.IntegerField(default=0)
    latency_ms = models.IntegerField(default=0)  # Response time in milliseconds
    filters_used = models.JSONField(default=dict, blank=True)  # Filters applied (for mode C)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['mode', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - Mode {self.mode} - {self.created_at}"


class Document(models.Model):
    """Stores uploaded legal documents for RAG"""
    DOCTYPE_CHOICES = [
        ('contract', 'Contract'),
        ('case', 'Case Law'),
        ('regulation', 'Regulation'),
        ('statute', 'Statute'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    doctype = models.CharField(max_length=20, choices=DOCTYPE_CHOICES)
    title = models.CharField(max_length=500)
    jurisdiction = models.CharField(max_length=100, blank=True)  # "US", "EU", "UK-ENG"
    date = models.DateField(null=True, blank=True)  # Document date or case date
    path = models.CharField(max_length=1000)  # File path on disk
    source = models.CharField(max_length=500, blank=True)  # Original source/URL
    sha256 = models.CharField(max_length=64, unique=True)  # File hash for deduplication
    meta_json = models.JSONField(default=dict, blank=True)  # Additional metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'doctype']),
            models.Index(fields=['jurisdiction', '-date']),
            models.Index(fields=['sha256']),
        ]

    def __str__(self):
        return f"{self.title} ({self.doctype})"


class Chunk(models.Model):
    """Stores document chunks with embeddings for RAG"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    ord = models.IntegerField()  # Order within document
    heading = models.CharField(max_length=500, blank=True)  # Section heading if available
    text = models.TextField()  # The actual chunk text
    embedding_json = models.JSONField(null=True, blank=True)  # Vector embedding as list
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chunks'
        ordering = ['document', 'ord']
        indexes = [
            models.Index(fields=['document', 'ord']),
        ]
        unique_together = [['document', 'ord']]

    def __str__(self):
        return f"Chunk {self.ord} of {self.document.title}"

    def get_embedding(self):
        """Parse embedding from JSON"""
        if self.embedding_json:
            return self.embedding_json
        return None

    def set_embedding(self, embedding_vector):
        """Store embedding as JSON"""
        self.embedding_json = embedding_vector


class AuditLog(models.Model):
    """Audit trail for important actions"""
    ACTION_CHOICES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('register', 'User Registration'),
        ('upload', 'Document Upload'),
        ('ingest', 'Document Ingest'),
        ('chat', 'Chat Request'),
        ('export', 'Data Export'),
        ('settings_change', 'Settings Change'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    meta_json = models.JSONField(default=dict, blank=True)  # Additional context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]

    def __str__(self):
        username = self.user.username if self.user else 'Anonymous'
        return f"{username} - {self.action} - {self.created_at}"


class UserSettings(models.Model):
    """User-specific inference and UI settings"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    
    # Inference settings
    temperature = models.FloatField(
        default=0.7,
        validators=[MinValueValidator(0.0), MaxValueValidator(2.0)]
    )
    max_tokens = models.IntegerField(
        default=256,
        validators=[MinValueValidator(50), MaxValueValidator(2048)]
    )
    top_p = models.FloatField(
        default=0.9,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    top_k = models.IntegerField(
        default=50,
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    
    # Default filters for Mode C
    default_jurisdiction = models.CharField(max_length=100, blank=True)
    default_year_from = models.IntegerField(null=True, blank=True)
    default_year_to = models.IntegerField(null=True, blank=True)
    default_keywords_include = models.JSONField(default=list, blank=True)
    default_keywords_exclude = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_settings'

    def __str__(self):
        return f"Settings for {self.user.username}"