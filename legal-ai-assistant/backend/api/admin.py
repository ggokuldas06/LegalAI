from django.contrib import admin

# Register your models here.
# api/admin.py
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    OrgProfile, ChatLog, Document, Chunk, 
    AuditLog, UserSettings
)


class OrgProfileInline(admin.StackedInline):
    model = OrgProfile
    can_delete = False
    verbose_name_plural = 'Organization Profile'


class UserSettingsInline(admin.StackedInline):
    model = UserSettings
    can_delete = False
    verbose_name_plural = 'User Settings'


class UserAdmin(BaseUserAdmin):
    inlines = (OrgProfileInline, UserSettingsInline)


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'mode', 'tokens_in', 'tokens_out', 'latency_ms', 'created_at']
    list_filter = ['mode', 'created_at']
    search_fields = ['user__username', 'prompt', 'response']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'mode', 'created_at')
        }),
        ('Content', {
            'fields': ('prompt', 'response', 'citations')
        }),
        ('Metrics', {
            'fields': ('tokens_in', 'tokens_out', 'latency_ms', 'filters_used')
        }),
    )


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'doctype', 'jurisdiction', 'date', 'user', 'created_at']
    list_filter = ['doctype', 'jurisdiction', 'created_at']
    search_fields = ['title', 'source', 'sha256']
    readonly_fields = ['sha256', 'created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Document Info', {
            'fields': ('user', 'doctype', 'title', 'jurisdiction', 'date')
        }),
        ('File Info', {
            'fields': ('path', 'source', 'sha256')
        }),
        ('Metadata', {
            'fields': ('meta_json', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display = ['id', 'document', 'ord', 'heading', 'text_preview', 'has_embedding']
    list_filter = ['document__doctype', 'created_at']
    search_fields = ['text', 'heading', 'document__title']
    readonly_fields = ['created_at']
    
    def text_preview(self, obj):
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    text_preview.short_description = 'Text Preview'
    
    def has_embedding(self, obj):
        return obj.embedding_json is not None
    has_embedding.boolean = True
    has_embedding.short_description = 'Embedded'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'action', 'ip_address', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['user__username', 'ip_address', 'user_agent']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Action Info', {
            'fields': ('user', 'action', 'created_at')
        }),
        ('Request Info', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Metadata', {
            'fields': ('meta_json',),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'temperature', 'max_tokens', 'default_jurisdiction', 'updated_at']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Inference Settings', {
            'fields': ('temperature', 'max_tokens', 'top_p', 'top_k')
        }),
        ('Default Filters (Mode C)', {
            'fields': (
                'default_jurisdiction',
                'default_year_from',
                'default_year_to',
                'default_keywords_include',
                'default_keywords_exclude'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )