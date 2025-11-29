#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

'''
    # Terminal 1 - Start Redis
redis-server

# Terminal 2 - Start Celery Worker (optional for async tasks)
cd backend
source venv/bin/activate
celery -A config worker -l info

# Terminal 3 - Start Django Server
cd backend
source venv/bin/activate
python manage.py runserver

# Terminal 4 - Run Tests
cd backend
source venv/bin/activate

# Test RAG locally
python test_rag.py

# Test RAG via API
python test_rag_e2e.py

'''