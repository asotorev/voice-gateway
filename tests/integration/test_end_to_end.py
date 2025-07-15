#!/usr/bin/env python3
"""
End-to-end integration tests for Voice Gateway.
Tests complete flow from HTTP requests to DynamoDB persistence.
"""
import pytest
import requests
import json
import uuid
from app.infrastructure.config.infrastructure_settings import infra_settings
from app.adapters.repositories.dynamodb_user_repository import DynamoDBUserRepository

BASE_URL = infra_settings.audio_base_url

@pytest.fixture(scope="module")
def user_repository():
    return DynamoDBUserRepository()

@pytest.mark.integration
def test_health_ping():
    response = requests.get(f"{BASE_URL}/api/ping")
    assert response.status_code == 200
    assert response.json().get("message") == "pong"

@pytest.mark.integration
def test_health_check():
    response = requests.get(f"{BASE_URL}/api/health")
    assert response.status_code == 200
    health_data = response.json()
    assert health_data.get("status") == "healthy"
    assert "dynamodb" in health_data["services"]
    assert health_data["services"]["dynamodb"]["status"] == "healthy"

@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_registration_flow(user_repository):
    test_users = [
        {"name": "End-to-End Test User", "email": "e2e_pytest@test.com", "password": "testpassword123"},
        {"name": "Second Test User", "email": "e2e2_pytest@test.com", "password": "anotherpassword456"}
    ]
    for user_data in test_users:
        # Cleanup previo: eliminar usuario si existe
        existing = await user_repository.get_by_email(user_data["email"])
        if existing:
            await user_repository.delete(str(existing.id))
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json=user_data,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Registration failed: {response.text}"
        user_response = response.json()
        for field in ["id", "name", "email", "created_at"]:
            assert field in user_response

@pytest.mark.integration
def test_duplicate_email_validation():
    duplicate_user = {"name": "Duplicate User", "email": "e2e_pytest@test.com", "password": "differentpassword"}
    response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json=duplicate_user,
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400
    error_detail = response.json().get("detail", "")
    assert "already exists" in error_detail.lower()

@pytest.mark.integration
def test_openapi_spec():
    response = requests.get(f"{BASE_URL}/openapi.json")
    assert response.status_code == 200
    openapi_spec = response.json()
    assert "paths" in openapi_spec
    assert "/api/auth/register" in openapi_spec["paths"]

@pytest.mark.integration
def test_swagger_ui():
    response = requests.get(f"{BASE_URL}/docs")
    assert response.status_code == 200 