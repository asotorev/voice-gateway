#!/usr/bin/env python3
"""
End-to-end integration tests for Voice Gateway.
Tests complete flow from HTTP requests to DynamoDB persistence with audio integration.
"""
import pytest
import requests
import json
import uuid
import base64
from app.infrastructure.config.infrastructure_settings import infra_settings
from app.adapters.repositories.dynamodb_user_repository import DynamoDBUserRepository

BASE_URL = infra_settings.audio_base_url

@pytest.fixture(scope="module")
def user_repository():
    return DynamoDBUserRepository()

@pytest.mark.integration
def test_duplicate_email_validation():
    """Test duplicate email validation during registration."""
    # Use a unique email to avoid conflicts
    unique_email = f"duplicate_email_pytest_{uuid.uuid4()}@test.com"
    test_user = {
        "name": "Duplicate Email Test User",
        "email": unique_email
    }
    
    # First registration should succeed
    response1 = requests.post(
        f"{BASE_URL}/api/auth/register",
        json=test_user,
        headers={"Content-Type": "application/json"}
    )
    
    assert response1.status_code == 200, f"First registration failed: {response1.text}"
    
    # Second registration with same email should fail
    response2 = requests.post(
        f"{BASE_URL}/api/auth/register",
        json=test_user,
        headers={"Content-Type": "application/json"}
    )
    
    assert response2.status_code == 400, "Should reject duplicate email"
    error_response = response2.json()
    assert "email" in error_response["detail"].lower(), "Error should mention email"

@pytest.mark.integration
def test_audio_storage_integration():
    """Test audio storage service integration."""
    response = requests.get(f"{BASE_URL}/api/audio/info")
    assert response.status_code == 200
    
    info = response.json()
    assert "service_type" in info
    assert "bucket_name" in info
    assert info["service_type"] == "s3"

@pytest.mark.integration
def test_openapi_spec():
    """Test OpenAPI specification generation."""
    response = requests.get(f"{BASE_URL}/openapi.json")
    assert response.status_code == 200
    
    openapi_spec = response.json()
    assert "paths" in openapi_spec
    assert "/api/auth/register" in openapi_spec["paths"]
    assert "/api/audio/upload" in openapi_spec["paths"]
    assert "/api/audio/info" in openapi_spec["paths"]

@pytest.mark.integration
def test_swagger_ui():
    """Test Swagger UI accessibility."""
    response = requests.get(f"{BASE_URL}/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")

@pytest.mark.integration
def test_health_ping():
    """Test basic health ping endpoint."""
    response = requests.get(f"{BASE_URL}/api/ping")
    assert response.status_code == 200
    
    ping_response = response.json()
    assert "message" in ping_response
    assert ping_response["message"] == "pong"

@pytest.mark.integration
def test_health_check():
    """Test comprehensive health check endpoint."""
    response = requests.get(f"{BASE_URL}/api/health")
    assert response.status_code == 200
    
    health_response = response.json()
    assert "status" in health_response
    assert "services" in health_response
    assert "dynamodb" in health_response["services"]
    assert "s3" in health_response["services"]

@pytest.mark.asyncio
@pytest.mark.integration
async def test_basic_user_registration_flow(user_repository):
    """Test basic user registration without audio samples."""
    test_user = {
        "name": "Basic Registration User",
        "email": "basic_registration_pytest@test.com"
    }
    
    # Cleanup previous test data
    existing = await user_repository.get_by_email(test_user["email"])
    if existing:
        await user_repository.delete(str(existing.id))
    
    # Test registration
    response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json=test_user,
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 200, f"Registration failed: {response.text}"
    user_response = response.json()
    
    # Verify response structure
    required_fields = ["id", "name", "email", "created_at", "voice_password"]
    for field in required_fields:
        assert field in user_response, f"Missing field: {field}"
    
    # Verify user was created in database
    created_user = await user_repository.get_by_id(user_response["id"])
    assert created_user is not None, "User should be created in database"
    assert created_user.email == test_user["email"]
    assert created_user.name == test_user["name"]
    
    # Cleanup
    await user_repository.delete(user_response["id"])

@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_registration_flow(user_repository):
    """Test complete user registration flow with profile retrieval."""
    test_user = {
        "name": "Complete Flow User",
        "email": "complete_flow_pytest@test.com"
    }
    
    # Cleanup previous test data
    existing = await user_repository.get_by_email(test_user["email"])
    if existing:
        await user_repository.delete(str(existing.id))
    
    # Step 1: Register user
    register_response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json=test_user,
        headers={"Content-Type": "application/json"}
    )
    
    assert register_response.status_code == 200, f"Registration failed: {register_response.text}"
    user_data = register_response.json()
    user_id = user_data["id"]
    
    # Step 2: Get user profile
    profile_response = requests.get(f"{BASE_URL}/api/auth/user/{user_id}/profile")
    assert profile_response.status_code == 200, f"Profile retrieval failed: {profile_response.text}"
    
    profile_data = profile_response.json()
    assert profile_data["id"] == user_id
    assert profile_data["email"] == test_user["email"]
    assert profile_data["name"] == test_user["name"]
    assert "has_voice_password" in profile_data
    assert "voice_setup_complete" in profile_data
    
    # Step 3: Get authentication status
    status_response = requests.get(f"{BASE_URL}/api/auth/user/{user_id}/status")
    assert status_response.status_code == 200, f"Status retrieval failed: {status_response.text}"
    
    status_data = status_response.json()
    assert status_data["user_id"] == user_id
    assert "account_status" in status_data
    assert "voice_setup_complete" in status_data
    
    # Cleanup
    await user_repository.delete(user_id)

@pytest.mark.integration
def test_audio_upload_url_generation():
    """Test audio upload URL generation for individual samples."""
    # First create a real user
    unique_email = f"audio_upload_pytest_{uuid.uuid4()}@test.com"
    test_user = {
        "name": "Audio Upload Test User",
        "email": unique_email
    }
    
    # Register user
    register_response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json=test_user,
        headers={"Content-Type": "application/json"}
    )
    
    assert register_response.status_code == 200, f"User registration failed: {register_response.text}"
    user_data = register_response.json()
    test_user_id = user_data["id"]
    
    # Now test audio upload URL generation
    request_data = {
        "user_id": test_user_id,
        "sample_number": 1,
        "format": "wav",
        "expiration_minutes": 15
    }
    
    response = requests.post(
        f"{BASE_URL}/api/audio/upload",
        json=request_data,
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 200, f"Upload URL generation failed: {response.text}"
    url_response = response.json()
    
    # Verify response structure
    assert "upload_url" in url_response
    assert "file_path" in url_response
    assert "expires_at" in url_response
    assert url_response["user_id"] == test_user_id
    assert url_response["sample_number"] == 1

@pytest.mark.integration
def test_audio_download_url_generation():
    """Test audio download URL generation with proper validation."""
    # First create a real user
    unique_email = f"audio_download_pytest_{uuid.uuid4()}@test.com"
    test_user = {
        "name": "Audio Download Test User",
        "email": unique_email
    }
    
    # Register user
    register_response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json=test_user,
        headers={"Content-Type": "application/json"}
    )
    
    assert register_response.status_code == 200, f"User registration failed: {register_response.text}"
    user_data = register_response.json()
    test_user_id = user_data["id"]
    
    # Test download URL generation with a non-existent file (should fail with proper validation)
    test_file_path = f"{test_user_id}/non-existent-file.wav"
    
    request_data = {
        "user_id": test_user_id,
        "file_path": test_file_path,
        "expiration_minutes": 5
    }
    
    response = requests.post(
        f"{BASE_URL}/api/audio/download-url",
        json=request_data,
        headers={"Content-Type": "application/json"}
    )
    
    # Should fail because file doesn't exist (business validation)
    assert response.status_code == 400, "Should fail when file doesn't exist"
    error_response = response.json()
    assert "File not found" in error_response["detail"], "Error should mention file not found"
    
    # Test with invalid user ID (should fail with authorization)
    invalid_file_path = f"invalid-user-id/sample.wav"
    
    request_data = {
        "user_id": "invalid-user-id",
        "file_path": invalid_file_path,
        "expiration_minutes": 5
    }
    
    response = requests.post(
        f"{BASE_URL}/api/audio/download-url",
        json=request_data,
        headers={"Content-Type": "application/json"}
    )
    
    # Should fail because user doesn't exist
    assert response.status_code == 400, "Should fail when user doesn't exist"
    error_response = response.json()
    assert "User" in error_response["detail"], "Error should mention user not found"

@pytest.mark.integration
def test_audio_file_operations():
    """Test audio file existence check and deletion."""
    # First create a real user
    unique_email = f"audio_file_ops_pytest_{uuid.uuid4()}@test.com"
    test_user = {
        "name": "Audio File Ops Test User",
        "email": unique_email
    }
    
    # Register user
    register_response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json=test_user,
        headers={"Content-Type": "application/json"}
    )
    
    assert register_response.status_code == 200, f"User registration failed: {register_response.text}"
    user_data = register_response.json()
    test_user_id = user_data["id"]
    
    test_file_path = f"{test_user_id}/{uuid.uuid4()}/sample.wav"
    
    # Test file existence check
    exists_response = requests.get(f"{BASE_URL}/api/audio/file/{test_file_path}/exists")
    assert exists_response.status_code == 200
    
    exists_data = exists_response.json()
    assert "exists" in exists_data
    assert "file_path" in exists_data
    
    # Test file deletion (should work even if file doesn't exist)
    delete_response = requests.delete(f"{BASE_URL}/api/audio/file/{test_file_path}?user_id={test_user_id}")
    assert delete_response.status_code == 200
    
    delete_data = delete_response.json()
    assert "deleted" in delete_data
    assert "file_path" in delete_data

@pytest.mark.integration
def test_audio_setup_status():
    """Test audio setup status endpoint."""
    # First create a real user
    unique_email = f"audio_setup_pytest_{uuid.uuid4()}@test.com"
    test_user = {
        "name": "Audio Setup Test User",
        "email": unique_email
    }
    
    # Register user
    register_response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json=test_user,
        headers={"Content-Type": "application/json"}
    )
    
    assert register_response.status_code == 200, f"User registration failed: {register_response.text}"
    user_data = register_response.json()
    test_user_id = user_data["id"]
    
    # Test setup status
    response = requests.get(f"{BASE_URL}/api/audio/user/{test_user_id}/setup-status")
    
    assert response.status_code == 200, f"Setup status failed: {response.text}"
    status_response = response.json()
    
    # Verify response structure
    assert "user_id" in status_response
    assert "completed_samples" in status_response
    assert "total_samples" in status_response
    assert "progress_percentage" in status_response
    assert status_response["user_id"] == test_user_id
    assert status_response["completed_samples"] == 0  # New user has no samples
    assert status_response["total_samples"] == 3
    assert status_response["progress_percentage"] == 0.0  # 0% progress for new user 