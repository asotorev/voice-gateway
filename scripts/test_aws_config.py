#!/usr/bin/env python3
"""
Test AWS configuration abstraction layer.
Assumes prerequisites are met (run test_db_connection.py first).
"""
import sys
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent.parent
sys.path.append(str(app_dir))

from app.infrastructure.config.aws_config import aws_config
from app.infrastructure.config.infrastructure_settings import infra_settings


def test_aws_config_layer():
    """
    Test AWS configuration abstraction layer functionality.
    
    Returns:
        bool: True if abstraction layer works correctly
    """
    print("Testing AWS configuration abstraction...")
    print(f"   Environment: {infra_settings.aws_region}")
    print(f"   Local DynamoDB: {infra_settings.use_local_dynamodb}")
    print(f"   Region: {infra_settings.aws_region}")
    print()
    
    try:
        # Test DynamoDB resource through abstraction
        print("Creating DynamoDB resource via aws_config...")
        dynamodb = aws_config.dynamodb_resource
        print("DynamoDB resource created successfully")
        
        # Test table listing through abstraction
        print("Testing table listing via abstraction...")
        tables = list(dynamodb.tables.all())
        print(f"Found {len(tables)} tables via abstraction layer")
        
        return True
        
    except Exception as e:
        print(f"AWS config abstraction test failed: {str(e)}")
        return False


def test_health_check():
    """
    Test integrated health check functionality.
    
    Returns:
        bool: True if health check works
    """
    print("Testing health check functionality...")
    
    try:
        health = aws_config.health_check()
        
        dynamodb_status = health.get('dynamodb', {})
        status = dynamodb_status.get('status', 'unknown')
        db_type = dynamodb_status.get('type', 'unknown')
        
        print(f"Health check result: {status} ({db_type})")
        
        if status == 'healthy':
            print("Health check passed")
            return True
        else:
            error = dynamodb_status.get('error', 'Unknown error')
            print(f"Health check failed: {error}")
            return False
            
    except Exception as e:
        print(f"Health check test failed: {str(e)}")
        return False


def test_table_reference():
    """
    Test getting table references through abstraction.
    
    Returns:
        bool: True if table reference works
    """
    print("Testing table reference functionality...")
    
    try:
        table_name = infra_settings.users_table_name
        print(f"Getting reference to table: {table_name}")
        
        table = aws_config.get_table(table_name)
        print(f"Table reference obtained: {table.table_name}")
        
        return True
        
    except Exception as e:
        print(f"Table reference test failed: {str(e)}")
        return False


def main():
    """
    Test AWS configuration abstraction layer.
    """
    print("Voice Gateway - AWS Configuration Abstraction Test")
    print("=" * 55)
    print()
    
    # Test abstraction layer
    config_success = test_aws_config_layer()
    print()
    
    # Test health check
    health_success = test_health_check()
    print()
    
    # Test table reference
    table_success = test_table_reference()
    print()
    
    overall_success = config_success and health_success and table_success
    
    if overall_success:
        print("AWS configuration abstraction layer works correctly!")
    else:
        print("Some abstraction tests failed.")
        print("Ensure basic connectivity works first:")
        print("   python scripts/test_db_connection.py")
    
    return overall_success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        sys.exit(1)