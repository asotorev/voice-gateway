#!/usr/bin/env python3
"""
Integration testing for Voice Gateway password generation.
Tests complete flow from use case through endpoints with automatic password generation.
"""
import sys
import asyncio
import requests
import json
import uuid
from pathlib import Path
import pytest

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.usecases.register_user import RegisterUserUseCase
from app.adapters.repositories.dynamodb_user_repository import DynamoDBUserRepository
from app.core.services.password_service import PasswordService
from app.core.models.user import User
from app.infrastructure.config.infrastructure_settings import infra_settings
from app.infrastructure.config.aws_config import aws_config

BASE_URL = aws_config.get_api_base_url()

@pytest.fixture(scope="function")
def integration_test_context():
    context = {}
    context["user_repository"] = DynamoDBUserRepository()
    context["password_service"] = PasswordService()
    context["use_case"] = RegisterUserUseCase(context["user_repository"], context["password_service"])
    context["test_users"] = []
    yield context
    # Teardown: clean up test users
    for user in context["test_users"]:
        try:
            import asyncio
            asyncio.run(context["user_repository"].delete(str(user.id)))
        except Exception:
            pass

@pytest.mark.asyncio
@pytest.mark.integration
async def test_use_case_integration(integration_test_context):
    context = integration_test_context
    unique_id = str(uuid.uuid4())[:8]
    user, voice_password = await context["use_case"].execute(
        email=f"usecase{unique_id}@test.com",
        name="Use Case Test User"
    )
    assert user is not None
    assert voice_password
    assert context["password_service"].validate_password_format(voice_password)
    assert not hasattr(user, 'voice_password')
    context["test_users"].append(user)

@pytest.mark.asyncio
@pytest.mark.integration
async def test_http_endpoint_integration(integration_test_context):
    context = integration_test_context
    unique_id = str(uuid.uuid4())[:8]
    test_email = f"http{unique_id}@test.com"
    registration_data = {
        "name": "HTTP Test User",
        "email": test_email
    }
    response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json=registration_data,
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    assert response.status_code == 200, f"HTTP request failed: {response.text}"
    user_data = response.json()
    for field in ['id', 'name', 'email', 'created_at', 'voice_password']:
        assert field in user_data
    voice_password = user_data['voice_password']
    assert voice_password
    assert context["password_service"].validate_password_format(voice_password)
    # Track user for cleanup
    user = await context["user_repository"].get_by_email(test_email)
    if user:
        context["test_users"].append(user)

@pytest.mark.asyncio
@pytest.mark.integration
async def test_duplicate_registration(integration_test_context):
    context = integration_test_context
    unique_id = str(uuid.uuid4())[:8]
    test_email = f"duplicate{unique_id}@test.com"
    registration_data = {
        "name": "First Test User",
        "email": test_email
    }
    response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json=registration_data,
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    assert response.status_code == 200, f"First registration failed: {response.text}"
    user = await context["user_repository"].get_by_email(test_email)
    if user:
        context["test_users"].append(user)
    # Try duplicate registration
    duplicate_data = {
        "name": "Duplicate Test User",
        "email": test_email
    }
    response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json=duplicate_data,
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    assert response.status_code == 400
    error_data = response.json()
    assert "already exists" in error_data.get("detail", "").lower()

@pytest.mark.asyncio
@pytest.mark.integration
async def test_password_service_info(integration_test_context):
    context = integration_test_context
    info = context["password_service"].get_dictionary_info()
    assert info
    for field in ['language', 'version', 'total_words', 'total_combinations', 'entropy_bits']:
        assert field in info 