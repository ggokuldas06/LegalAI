# api/urls.py
from django.urls import path
from .views import auth_views, chat_views, history_views, document_views, health_views
from .views import auth_views, chat_views, history_views, document_views, health_views, rag_views


urlpatterns = [
    # Health checks
    path('health/check', health_views.health_check, name='health-check'),
    path('health/ready', health_views.readiness, name='health-ready'),
    path('health/live', health_views.liveness, name='health-live'),
    
    # Authentication
    path('auth/register', auth_views.register, name='auth-register'),
    path('auth/login', auth_views.login, name='auth-login'),
    path('auth/logout', auth_views.logout, name='auth-logout'),
    path('auth/profile', auth_views.profile, name='auth-profile'),
    path('auth/settings', auth_views.update_settings, name='auth-settings'),
    path('auth/org-profile', auth_views.update_org_profile, name='auth-org-profile'),
    
    # Chat
    path('chat', chat_views.chat, name='chat'),
    
    # History
    path('history', history_views.history, name='history'),
    path('history/<int:chat_id>', history_views.history_detail, name='history-detail'),
    path('history/<int:chat_id>/delete', history_views.history_delete, name='history-delete'),
    path('history/export', history_views.history_export, name='history-export'),
    
    # Documents
    path('documents', document_views.document_list, name='document-list'),
    path('documents/upload', document_views.document_upload, name='document-upload'),
    path('documents/<int:doc_id>', document_views.document_detail, name='document-detail'),
    path('documents/<int:doc_id>/delete', document_views.document_delete, name='document-delete'),
    path('documents/<int:doc_id>/content', document_views.document_content, name='document-content'),

    path('ingest', rag_views.ingest_document, name='ingest-document'),
    path('ingest/batch', rag_views.ingest_batch, name='ingest-batch'),
    path('search', rag_views.search, name='search'),
    path('rag/stats', rag_views.vector_store_stats, name='rag-stats'),
]

