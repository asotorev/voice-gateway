#!/usr/bin/env python3
"""
Test DynamoDB repository implementation.
Validates real persistence operations and data mapping.
"""
import sys
import asyncio
import uuid
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from app.adapters.repositories.dynamodb_user_repository import DynamoDBUserRepository
from app.core.models.user import User
from app.config.settings import settings


async def test_repository_operations():
    """Test complete CRUD operations with DynamoDB repository."""
    
    print("Voice Gateway - Repository Integration Test")
    print("=" * 50)
    print(f"Environment: {settings.environment}")
    print(f"DynamoDB Endpoint: {settings.dynamodb_endpoint_url}")
    print(f"Table Name: {settings.users_table_name}")
    print()
    
    repository = DynamoDBUserRepository()
    test_results = []
    
    try:
        # Test 1: Create and save user
        print("Testing user creation and save...")
        test_user = User.create(
            email="test@voicegateway.com",
            name="Test User",
            password_hash="hashed_password_123"
        )
        
        saved_user = await repository.save(test_user)
        print(f"✓ User created with ID: {saved_user.id}")
        test_results.append("CREATE: SUCCESS")
        
        # Test 2: Get user by ID
        print("\nTesting get user by ID...")
        retrieved_user = await repository.get_by_id(str(saved_user.id))
        
        if retrieved_user:
            print(f"✓ User retrieved: {retrieved_user.name} ({retrieved_user.email})")
            print(f"  Created at: {retrieved_user.created_at}")
            test_results.append("GET_BY_ID: SUCCESS")
        else:
            print("✗ User not found by ID")
            test_results.append("GET_BY_ID: FAILED")
        
        # Test 3: Get user by email (using GSI)
        print("\nTesting get user by email...")
        retrieved_by_email = await repository.get_by_email("test@voicegateway.com")
        
        if retrieved_by_email:
            print(f"✓ User found by email: {retrieved_by_email.name}")
            print(f"  User ID matches: {str(retrieved_by_email.id) == str(saved_user.id)}")
            test_results.append("GET_BY_EMAIL: SUCCESS")
        else:
            print("✗ User not found by email")
            test_results.append("GET_BY_EMAIL: FAILED")
        
        # Test 4: Test duplicate email validation
        print("\nTesting duplicate email validation...")
        try:
            duplicate_user = User.create(
                email="test@voicegateway.com",  # Same email
                name="Duplicate User",
                password_hash="different_hash"
            )
            await repository.save(duplicate_user)
            print("✗ Duplicate email was allowed (should have failed)")
            test_results.append("DUPLICATE_VALIDATION: FAILED")
        except ValueError as e:
            print(f"✓ Duplicate email properly rejected: {e}")
            test_results.append("DUPLICATE_VALIDATION: SUCCESS")
        
        # Test 5: Test with voice embeddings (optional)
        print("\nTesting user with voice embeddings...")
        user_with_voice = User.create(
            email="voice@voicegateway.com",
            name="Voice User",
            password_hash="voice_hash_123"
        )
        
        # Add sample voice embeddings with relative paths
        user_with_voice.voice_embeddings = [
            {
                'audio_path': f'user{user_with_voice.id}/sample1.wav',
                'embedding_vector': [0.1, 0.2, 0.3] * 85 + [0.15],  # 256 dimensions
                'generated_at': '2024-01-15T10:31:22Z'
            },
            {
                'audio_path': f'user{user_with_voice.id}/sample2.wav',
                'embedding_vector': [0.2, 0.3, 0.4] * 85 + [0.25],  # 256 dimensions
                'generated_at': '2024-01-15T10:32:15Z'
            }
        ]
        
        saved_voice_user = await repository.save(user_with_voice)
        retrieved_voice_user = await repository.get_by_id(str(saved_voice_user.id))
        
        if (retrieved_voice_user and 
            hasattr(retrieved_voice_user, 'voice_embeddings') and 
            len(retrieved_voice_user.voice_embeddings) == 2):
            print("✓ Voice embeddings saved and retrieved correctly")
            print(f"  Embeddings count: {len(retrieved_voice_user.voice_embeddings)}")
            print(f"  Sample audio path: {retrieved_voice_user.voice_embeddings[0]['audio_path']}")
            test_results.append("VOICE_EMBEDDINGS: SUCCESS")
        else:
            print("✗ Voice embeddings not saved/retrieved properly")
            test_results.append("VOICE_EMBEDDINGS: FAILED")
        
        # Test 6: Test non-existent user
        print("\nTesting non-existent user...")
        non_existent = await repository.get_by_id(str(uuid.uuid4()))
        if non_existent is None:
            print("✓ Non-existent user properly returns None")
            test_results.append("NON_EXISTENT: SUCCESS")
        else:
            print("✗ Non-existent user query returned unexpected result")
            test_results.append("NON_EXISTENT: FAILED")
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        test_results.append(f"ERROR: {str(e)}")
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print("-" * 30)
    for result in test_results:
        print(f"  {result}")
    
    success_count = len([r for r in test_results if "SUCCESS" in r])
    total_count = len([r for r in test_results if r != "ERROR"])
    
    print(f"\nTests passed: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("\n All repository tests passed!")
        print("DynamoDB integration is working correctly.")
    else:
        print(f"\n  {total_count - success_count} tests failed.")
        print("Check DynamoDB setup and table configuration.")
    
    return success_count == total_count


async def main():
    """Main test runner."""
    try:
        success = await test_repository_operations()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Test runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 