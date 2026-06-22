# api/views/chat_views.py
import json
import logging
import os

from django.http import StreamingHttpResponse
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..inference.service import inference_service
from ..models import AuditLog, ChatLog, Document
from ..serializers import ChatRequestSerializer
from ..utils.helpers import get_client_ip, get_user_agent

logger = logging.getLogger(__name__)


def _extract_document_text(document: Document) -> str:
    """Extract plain text from a document file (PDF, TXT, MD, or image)."""
    ext = os.path.splitext(document.path)[1].lower()
    if ext in (".txt", ".md"):
        with open(document.path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    elif ext == ".pdf":
        import fitz
        doc = fitz.open(document.path)
        pages = [page.get_text("text") for page in doc]
        doc.close()
        return "\n\n".join(p for p in pages if p.strip())
    elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"):
        from ..rag.vision_extractor import vision_extractor
        return vision_extractor.extract_from_image(document.path)
    raise ValueError(f"Unsupported file type: {ext}")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@ratelimit(key="user", rate="60/h", method="POST")
def chat(request):
    """
    POST /api/v1/chat
    Body: { mode, message, doc_id?, filters?, stream? }

    Mode A (Summarizer)     — doc_id required; full text → LLM, no RAG
    Mode B (Clause Classifier) — doc_id required; full text → LLM, no RAG
    Mode C (Case-Law IRAC)  — RAG retrieval; doc_id optional (scopes to one doc)
    """
    serializer = ChatRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"success": False, "error": serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    mode = data["mode"]
    message = data["message"]
    doc_id = data.get("doc_id")
    filters = data.get("filters", {})
    do_stream = data.get("stream", False)

    # ------------------------------------------------------------------ #
    # Mode A / B — load full document text; no RAG                        #
    # ------------------------------------------------------------------ #
    document = None
    document_text = None
    document_title = None

    if mode in ("A", "B"):
        if not doc_id:
            return Response({"success": False, "error": "doc_id is required for this mode"},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            document = Document.objects.get(id=doc_id, user=request.user)
            document_text = _extract_document_text(document)
            document_title = document.title
        except Document.DoesNotExist:
            return Response({"success": False, "error": f"Document {doc_id} not found"},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error loading document {doc_id}: {e}", exc_info=True)
            return Response({"success": False, "error": "Failed to load document"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ------------------------------------------------------------------ #
    # Mode C — RAG retrieval; optional doc_id scopes to a single doc      #
    # ------------------------------------------------------------------ #
    context_passages = []
    agent_trace = None

    if mode == "C":
        if doc_id:
            try:
                document = Document.objects.get(id=doc_id, user=request.user)
            except Document.DoesNotExist:
                pass

        try:
            from ..rag.retrieval import retrieval_service
            context_passages = retrieval_service.retrieve_for_mode_c(
                question=message,
                document_id=doc_id if doc_id else None,
                jurisdiction=filters.get("jurisdiction"),
                year_from=filters.get("year_from"),
                year_to=filters.get("year_to"),
                keywords_include=filters.get("include", []),
                keywords_exclude=filters.get("exclude", []),
                k=8,
            )
            logger.info(f"Retrieved {len(context_passages)} passages for Mode C"
                        + (f" (doc {doc_id})" if doc_id else " (global)"))
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}", exc_info=True)

    # ------------------------------------------------------------------ #
    # Mode D — Agentic Case Q&A                                           #
    # ------------------------------------------------------------------ #
    elif mode == "D":
        case_id = data.get("case_id")
        try:
            from ..rag.case_retrieval import case_retrieval_service
            retrieval_result = case_retrieval_service.retrieve_for_case(
                query=message,
                case_id=case_id,
                user_id=request.user.id,
                k=8,
            )
            context_passages = retrieval_result.get("passages", [])
            agent_trace = retrieval_result.get("agent_trace")
            logger.info(
                f"Mode D: {len(context_passages)} passages from case {case_id}, "
                f"agent selected {len(agent_trace.get('selected_docs', []))} docs"
            )
        except Exception as e:
            logger.warning(f"Case RAG retrieval failed: {e}", exc_info=True)

    # ------------------------------------------------------------------ #
    # Dispatch                                                             #
    # ------------------------------------------------------------------ #
    if do_stream:
        return _streaming_response(
            request, mode, message, document, document_text,
            document_title, context_passages, filters, agent_trace=agent_trace,
        )

    try:
        result = inference_service.chat(
            mode=mode,
            message=message,
            document_text=document_text,
            document_title=document_title,
            context_passages=context_passages,
            agent_trace=agent_trace,
            filters=filters,
            stream=False,
        )

        if not result.get("success"):
            return Response({"success": False, "error": result.get("error", "Unknown error")},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        citations = result.get("processed", {}).get("citations", []) if result.get("processed") else []

        chat_log = ChatLog.objects.create(
            user=request.user,
            mode=mode,
            prompt=message,
            response=result["response"],
            document=document,
            citations=citations,
            tokens_in=result.get("tokens_in", 0),
            tokens_out=result.get("tokens_out", 0),
            latency_ms=result.get("latency_ms", 0),
            filters_used=filters,
        )

        AuditLog.objects.create(
            user=request.user,
            action="chat",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            meta_json={"mode": mode, "chat_log_id": chat_log.id},
        )

        response_data = {
            "chat_log_id": chat_log.id,
            "mode": mode,
            "response": result["response"],
            "processed": result.get("processed"),
            "citations": citations,
            "tokens_in": result.get("tokens_in", 0),
            "tokens_out": result.get("tokens_out", 0),
            "latency_ms": result.get("latency_ms", 0),
        }
        if agent_trace:
            response_data["agent_trace"] = agent_trace

        return Response({"success": True, "data": response_data})

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return Response({"success": False, "error": str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _streaming_response(
    request, mode, message, document, document_text,
    document_title, context_passages, filters, agent_trace=None,
):
    """Return a Server-Sent Events streaming response."""

    def event_stream():
        try:
            stream = inference_service.chat(
                mode=mode,
                message=message,
                document_text=document_text,
                document_title=document_title,
                context_passages=context_passages,
                agent_trace=agent_trace,
                filters=filters,
                stream=True,
            )

            accumulated = ""
            tokens_in = 0

            for chunk in stream:
                event_type = chunk.get("type")

                if event_type == "start":
                    tokens_in = chunk.get("tokens_in", 0)

                elif event_type == "token":
                    accumulated += chunk.get("token", "")

                elif event_type == "done":
                    try:
                        chat_log = ChatLog.objects.create(
                            user=request.user,
                            mode=mode,
                            prompt=message,
                            response=accumulated,
                            document=document,
                            citations=[],
                            tokens_in=tokens_in,
                            tokens_out=len(accumulated.split()),
                            latency_ms=0,
                            filters_used=filters,
                        )
                        chunk["chat_log_id"] = chat_log.id
                    except Exception as log_err:
                        logger.warning(f"Could not save chat log: {log_err}")

                yield f"data: {json.dumps(chunk)}\n\n"

        except Exception as e:
            logger.error(f"SSE streaming error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    response["Access-Control-Allow-Origin"] = "*"
    return response
