# api/views/case_views.py
import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Case, CaseDocument, Document, AuditLog
from ..serializers import CaseSerializer, CaseListSerializer, CaseDocumentSerializer
from ..utils.helpers import get_client_ip, get_user_agent

logger = logging.getLogger(__name__)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def case_list(request):
    """
    GET  /api/v1/cases        — list user's cases
    POST /api/v1/cases        — create a case
    """
    if request.method == 'GET':
        cases = Case.objects.filter(user=request.user).prefetch_related('documents')
        serializer = CaseListSerializer(cases, many=True)
        return Response({'success': True, 'data': serializer.data})

    # POST
    title = request.data.get('title', '').strip()
    if not title:
        return Response({'success': False, 'error': 'title is required'}, status=status.HTTP_400_BAD_REQUEST)

    case = Case.objects.create(
        user=request.user,
        title=title,
        description=request.data.get('description', ''),
    )

    AuditLog.objects.create(
        user=request.user,
        action='case_create',
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        meta_json={'case_id': case.id, 'title': title},
    )

    serializer = CaseSerializer(case)
    return Response({'success': True, 'data': serializer.data}, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def case_detail(request, case_id):
    """
    GET    /api/v1/cases/<id>  — case detail with documents
    PATCH  /api/v1/cases/<id>  — update title/description
    DELETE /api/v1/cases/<id>  — delete case (not documents)
    """
    try:
        case = Case.objects.get(id=case_id, user=request.user)
    except Case.DoesNotExist:
        return Response({'success': False, 'error': 'Case not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = CaseSerializer(case)
        return Response({'success': True, 'data': serializer.data})

    if request.method == 'PATCH':
        if 'title' in request.data:
            title = request.data['title'].strip()
            if not title:
                return Response({'success': False, 'error': 'title cannot be empty'},
                                status=status.HTTP_400_BAD_REQUEST)
            case.title = title
        if 'description' in request.data:
            case.description = request.data['description']
        case.save()
        serializer = CaseSerializer(case)
        return Response({'success': True, 'data': serializer.data})

    # DELETE
    case.delete()
    AuditLog.objects.create(
        user=request.user,
        action='case_delete',
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        meta_json={'case_id': case_id},
    )
    return Response({'success': True, 'message': 'Case deleted'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def case_add_documents(request, case_id):
    """
    POST /api/v1/cases/<id>/documents
    Body: { "document_ids": [1, 2, 3], "role": "evidence" }
    """
    try:
        case = Case.objects.get(id=case_id, user=request.user)
    except Case.DoesNotExist:
        return Response({'success': False, 'error': 'Case not found'}, status=status.HTTP_404_NOT_FOUND)

    doc_ids = request.data.get('document_ids', [])
    role = request.data.get('role', 'other')

    if not doc_ids:
        return Response({'success': False, 'error': 'document_ids is required'},
                        status=status.HTTP_400_BAD_REQUEST)

    docs = Document.objects.filter(id__in=doc_ids, user=request.user)
    added = []
    skipped = []

    for doc in docs:
        cd, created = CaseDocument.objects.get_or_create(
            case=case,
            document=doc,
            defaults={'role': role},
        )
        if created:
            added.append(doc.id)
        else:
            skipped.append(doc.id)

    case.save()  # updates updated_at
    return Response({
        'success': True,
        'data': {
            'added': added,
            'already_in_case': skipped,
        },
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def case_remove_document(request, case_id, doc_id):
    """
    DELETE /api/v1/cases/<case_id>/documents/<doc_id>
    """
    try:
        case = Case.objects.get(id=case_id, user=request.user)
    except Case.DoesNotExist:
        return Response({'success': False, 'error': 'Case not found'}, status=status.HTTP_404_NOT_FOUND)

    deleted, _ = CaseDocument.objects.filter(case=case, document_id=doc_id).delete()
    if not deleted:
        return Response({'success': False, 'error': 'Document not in case'}, status=status.HTTP_404_NOT_FOUND)

    case.save()  # updates updated_at
    return Response({'success': True, 'message': 'Document removed from case'})
