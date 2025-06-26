#!/usr/bin/env python3
"""
Verifies DynamoDB Local connectivity and table operations.
Connects to local DynamoDB instance and validates configuration.
"""
import sys
import os
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent.parent
sys.path.append(str(app_dir))

import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from app.config.settings import settings


def test_dynamodb_connection():
    """
    Connect to DynamoDB and verify table operations work correctly.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    print("Testing DynamoDB connection...")
    print(f"   Environment: {settings.environment}")
    print(f"   Endpoint: {settings.dynamodb_endpoint_url}")
    print(f"   Region: {settings.aws_region}")
    print()
    
    try:
        # Connect to DynamoDB using configured settings
        dynamodb = boto3.resource(
            'dynamodb',
            endpoint_url=settings.dynamodb_endpoint_url,
            region_name=settings.aws_region,
            aws_access_key_id='fakeMyKeyId',
            aws_secret_access_key='fakeSecretAccessKey'
        )
        
        # Verify basic connectivity by listing existing tables
        print("Attempting to list tables...")
        tables = list(dynamodb.tables.all())
        
        print(f"Connection successful!")
        print(f"Found {len(tables)} existing tables")
        
        if tables:
            print("Existing tables:")
            for table in tables:
                print(f"   - {table.name}")
        else:
            print("No tables found (normal for fresh setup)")
        
        # Verify table creation/deletion operations work
        print()
        print("Verifying table creation capability...")
        test_table_name = "connectivity-test-temp"
        
        # Create temporary table to test operations
        test_table = dynamodb.create_table(
            TableName=test_table_name,
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Wait for table to become active
        test_table.wait_until_exists()
        print(f"Test table '{test_table_name}' created successfully")
        
        # Clean up temporary resources
        test_table.delete()
        print(f"Test table '{test_table_name}' cleaned up")
        
        print()
        print("DynamoDB setup verified successfully!")
        
        return True
        
    except NoCredentialsError:
        print("AWS credentials not configured properly")
        return False
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        print(f"DynamoDB ClientError: {error_code}")
        print(f"   Message: {error_message}")
        
        if 'ConnectionError' in str(e) or 'EndpointConnectionError' in str(e):
            print()
            print("Troubleshooting steps:")
            print("   1. Ensure DynamoDB Local is running:")
            print("      docker-compose up -d dynamodb-local")
            print("   2. Verify port 8000 is available")
            print("   3. Check Docker daemon status")
        
        return False
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        return False


def check_prerequisites():
    """
    Verify all required dependencies are available.
    
    Returns:
        bool: True if prerequisites are met
    """
    print("Checking prerequisites...")
    
    # Verify environment configuration exists
    env_file = Path(".env.local")
    if not env_file.exists():
        print("Environment file .env.local not found")
        
        # Check if template exists
        template_file = Path(".env.example")
        if template_file.exists():
            print("Copy template: cp .env.example .env.local")
        else:
            print("Create .env.local with DynamoDB configuration")
        
        return False
    
    print("Environment configuration found")
    
    # Verify DynamoDB Local is accessible
    try:
        import requests
        response = requests.get(settings.dynamodb_endpoint_url, timeout=5)
        print("DynamoDB Local is responding")
        return True
    except Exception:
        print("DynamoDB Local not responding on port 8000")
        print("Start with: docker-compose up -d dynamodb-local")
        return False


def main():
    """
    Execute connection verification workflow.
    """
    print("Voice Gateway - DynamoDB Connection Test")
    print("=" * 50)
    print()
    
    # Verify prerequisites before testing
    if not check_prerequisites():
        print()
        print("Prerequisites not met. Address issues above.")
        return False
    
    print()
    
    # Execute connection test
    success = test_dynamodb_connection()
    
    print()
    if success:
        print("Connection verification completed successfully!")
    else:
        print("Connection verification failed.")
        print("Review error messages above.")
    
    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed with unexpected error: {str(e)}")
        sys.exit(1)