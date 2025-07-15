#!/usr/bin/env python3
"""
Uniqueness Validation Testing for Voice Gateway.
Tests password uniqueness generation and collision detection.
"""
import sys
import asyncio
import uuid
import pytest
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.models.user import User
from app.core.services.password_service import PasswordService
from app.core.services.unique_password_service import UniquePasswordService
from app.adapters.repositories.dynamodb_user_repository import DynamoDBUserRepository

@pytest.mark.asyncio
@pytest.mark.unit
async def test_unique_password_generation(unique_password_service, password_service, user_repository):
    generated_passwords = []
    created_users = []
    try:
        for i in range(5):
            unique_password = await unique_password_service.generate_unique_password(max_attempts=PasswordService.MAX_GENERATION_ATTEMPTS)
            generated_passwords.append(unique_password)
            password_hash = password_service.hash_password(unique_password)
            test_user = User.create(
                email=f"uniqueness_test_{uuid.uuid4().hex[:8]}@test.com",
                name=f"Test User {i+1}",
                password_hash=password_hash
            )
            saved_user = await user_repository.save(test_user)
            created_users.append(saved_user)
        # Verificar unicidad local
        assert len(set(generated_passwords)) == len(generated_passwords), "Duplicate passwords found in local array"
        # Verificar unicidad en la base de datos
        for i, password in enumerate(generated_passwords):
            password_hash = password_service.hash_password(password)
            exists = await user_repository.check_password_hash_exists(password_hash)
            assert exists, f"Password {i+1} not found in database after saving"
    finally:
        # Cleanup
        for user in created_users:
            await user_repository.delete(str(user.id))

@pytest.mark.asyncio
@pytest.mark.unit
async def test_collision_detection(unique_password_service, password_service, user_repository):
    test_password = "biblioteca tortuga"
    password_hash = password_service.hash_password(test_password)
    exists = await user_repository.check_password_hash_exists(password_hash)
    if not exists:
        test_user = User.create(
            email=f"collision_test_{uuid.uuid4().hex[:8]}@test.com",
            name="Collision Test User",
            password_hash=password_hash
        )
        saved_user = await user_repository.save(test_user)
    # Monkeypatch generate_password para forzar colisión
    original_generate_password = password_service.generate_password
    password_service.generate_password = lambda: test_password
    try:
        with pytest.raises(ValueError, match="Unable to generate unique password"):
            await unique_password_service.generate_unique_password(max_attempts=5)
    finally:
        password_service.generate_password = original_generate_password
        # Cleanup
        if not exists:
            await user_repository.delete(str(test_user.id)) 