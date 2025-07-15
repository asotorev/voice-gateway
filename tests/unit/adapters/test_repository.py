#!/usr/bin/env python3
"""
Test DynamoDB repository implementation.
Validates real persistence operations and data mapping.
"""
import sys
import asyncio
import uuid
from pathlib import Path
import pytest

# Add the app directory to Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from app.adapters.repositories.dynamodb_user_repository import DynamoDBUserRepository
from app.core.models.user import User
from app.infrastructure.config.infrastructure_settings import infra_settings


@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_and_get_user(user_repository):
    email = "test@voicegateway.com"
    # Cleanup previo
    existing = await user_repository.get_by_email(email)
    if existing:
        await user_repository.delete(str(existing.id))
    test_user = User.create(
        email=email,
        name="Test User",
        password_hash="hashed_password_123"
    )
    saved_user = await user_repository.save(test_user)
    assert saved_user.id is not None
    retrieved_user = await user_repository.get_by_id(str(saved_user.id))
    assert retrieved_user is not None
    assert retrieved_user.email == test_user.email
    assert retrieved_user.name == test_user.name
    # Cleanup
    await user_repository.delete(str(saved_user.id))

@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_user_by_email(user_repository):
    email = "test2@voicegateway.com"
    # Cleanup previo
    existing = await user_repository.get_by_email(email)
    if existing:
        await user_repository.delete(str(existing.id))
    test_user = User.create(
        email=email,
        name="Test User 2",
        password_hash="hashed_password_456"
    )
    saved_user = await user_repository.save(test_user)
    retrieved_by_email = await user_repository.get_by_email(email)
    assert retrieved_by_email is not None
    assert str(retrieved_by_email.id) == str(saved_user.id)
    # Cleanup
    await user_repository.delete(str(saved_user.id))

@pytest.mark.asyncio
@pytest.mark.unit
async def test_duplicate_email_validation(user_repository):
    email = "test3@voicegateway.com"
    # Cleanup previo
    existing = await user_repository.get_by_email(email)
    if existing:
        await user_repository.delete(str(existing.id))
    test_user = User.create(
        email=email,
        name="Test User 3",
        password_hash="hashed_password_789"
    )
    saved_user = await user_repository.save(test_user)
    duplicate_user = User.create(
        email=email,
        name="Duplicate User",
        password_hash="different_hash"
    )
    with pytest.raises(ValueError):
        await user_repository.save(duplicate_user)
    # Cleanup
    await user_repository.delete(str(saved_user.id))

@pytest.mark.asyncio
@pytest.mark.unit
async def test_voice_embeddings(user_repository):
    email = "voice@voicegateway.com"
    # Cleanup previo
    existing = await user_repository.get_by_email(email)
    if existing:
        await user_repository.delete(str(existing.id))
    user_with_voice = User.create(
        email=email,
        name="Voice User",
        password_hash="voice_hash_123"
    )
    user_with_voice.voice_embeddings = [
        {
            'audio_path': f'user{user_with_voice.id}/sample1.wav',
            'embedding_vector': [0.1, 0.2, 0.3] * 85 + [0.15],
            'generated_at': '2024-01-15T10:31:22Z'
        },
        {
            'audio_path': f'user{user_with_voice.id}/sample2.wav',
            'embedding_vector': [0.2, 0.3, 0.4] * 85 + [0.25],
            'generated_at': '2024-01-15T10:32:15Z'
        }
    ]
    saved_voice_user = await user_repository.save(user_with_voice)
    retrieved_voice_user = await user_repository.get_by_id(str(saved_voice_user.id))
    assert retrieved_voice_user is not None
    assert hasattr(retrieved_voice_user, 'voice_embeddings')
    assert len(retrieved_voice_user.voice_embeddings) == 2
    assert retrieved_voice_user.voice_embeddings[0]['audio_path'].endswith('sample1.wav')
    # Cleanup
    await user_repository.delete(str(saved_voice_user.id))

@pytest.mark.asyncio
@pytest.mark.unit
async def test_non_existent_user(user_repository):
    non_existent = await user_repository.get_by_id(str(uuid.uuid4()))
    assert non_existent is None 