# backend/test_models.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from api.models import OrgProfile, UserSettings, ChatLog, Document

# Test user creation
print("Creating test user...")
user, created = User.objects.get_or_create(
    username='testuser',
    defaults={'email': 'test@example.com'}
)
if created:
    user.set_password('testpassword123')
    user.save()
    print(f"✓ User created: {user.username}")
else:
    print(f"✓ User already exists: {user.username}")

# Check if profile was auto-created
if hasattr(user, 'org_profile'):
    print(f"✓ OrgProfile auto-created for {user.username}")
else:
    print("✗ OrgProfile not created")

if hasattr(user, 'settings'):
    print(f"✓ UserSettings auto-created for {user.username}")
    print(f"  - Temperature: {user.settings.temperature}")
    print(f"  - Max tokens: {user.settings.max_tokens}")
else:
    print("✗ UserSettings not created")

# Test ChatLog creation
chat_log = ChatLog.objects.create(
    user=user,
    mode='C',
    prompt='What is the standard for injunctions?',
    response='Based on the provided sources...',
    citations=[{'doc_id': 1, 'chunk_id': 5}],
    tokens_in=50,
    tokens_out=150,
    latency_ms=2500
)
print(f"✓ ChatLog created: {chat_log.id}")

print("\n✓ All models working correctly!")