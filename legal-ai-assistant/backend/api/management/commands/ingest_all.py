# api/management/commands/ingest_all.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import Document
from api.rag.ingestion import ingestion_service
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Ingest all documents into RAG system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Username to ingest documents for (optional)',
        )
        parser.add_argument(
            '--reindex',
            action='store_true',
            help='Reindex existing documents',
        )
        parser.add_argument(
            '--doctype',
            type=str,
            help='Only ingest documents of this type',
        )

    def handle(self, *args, **options):
        username = options.get('user')
        reindex = options.get('reindex', False)
        doctype = options.get('doctype')
        
        # Get documents
        queryset = Document.objects.all()
        
        if username:
            try:
                user = User.objects.get(username=username)
                queryset = queryset.filter(user=user)
                self.stdout.write(f"Filtering for user: {username}")
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User '{username}' not found"))
                return
        
        if doctype:
            queryset = queryset.filter(doctype=doctype)
            self.stdout.write(f"Filtering for doctype: {doctype}")
        
        documents = list(queryset)
        
        if not documents:
            self.stdout.write(self.style.WARNING("No documents found"))
            return
        
        self.stdout.write(f"Ingesting {len(documents)} documents...")
        
        # Ingest
        result = ingestion_service.ingest_multiple(documents, reindex=reindex)
        
        # Report results
        self.stdout.write(
            self.style.SUCCESS(
                f"\nIngestion complete:\n"
                f"  Total: {result['total_documents']}\n"
                f"  Successful: {result['successful']}\n"
                f"  Failed: {result['failed']}\n"
                f"  Total chunks: {result['total_chunks']}"
            )
        )
        
        # Show failures
        if result['failed'] > 0:
            self.stdout.write(self.style.WARNING("\nFailed documents:"))
            for res in result['results']:
                if not res.get('success'):
                    doc_id = res.get('document_id', 'unknown')
                    error = res.get('error', 'unknown error')
                    self.stdout.write(f"  Document {doc_id}: {error}")