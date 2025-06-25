#!/usr/bin/env python3
"""
Database setup script for Voice Gateway.
Creates all required DynamoDB tables and performs health checks.
"""
import sys
import os
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent.parent
sys.path.append(str(app_dir))

from app.infrastructure.databases.dynamodb_setup import dynamodb_setup
from app.config.settings import settings


def show_header():
    """Display setup header with environment info."""
    print("Voice Gateway - Database Setup")
    print("=" * 50)
    print(f"Environment: {settings.environment}")
    print(f"DynamoDB Endpoint: {settings.dynamodb_endpoint_url or 'AWS Default'}")
    print(f"Region: {settings.aws_region}")
    print(f"Users Table: {settings.users_table_name}")
    print()


def perform_health_check():
    """
    Perform initial health check.
    
    Returns:
        bool: True if DynamoDB is accessible
    """
    print("Performing health check...")
    health = dynamodb_setup.health_check()
    
    if health['dynamodb_connection']:
        print("DynamoDB connection successful")
        print(f"Total tables found: {health['table_count']}")
        
        # Show existing required tables
        for table_name, info in health['required_tables'].items():
            status = "EXISTS" if info['exists'] else "MISSING"
            print(f"  - {table_name}: {status}")
            if info['exists']:
                print(f"    Status: {info['status']}, Items: {info['item_count']}")
        
        return True
    else:
        print("DynamoDB connection failed")
        if 'error' in health:
            print(f"Error: {health['error']}")
        return False


def create_tables():
    """
    Create all required tables.
    
    Returns:
        bool: True if all tables created successfully
    """
    print("Creating tables...")
    results = dynamodb_setup.create_all_tables()
    
    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    print()
    print("Setup Results:")
    print("-" * 30)
    
    for table_name, success in results.items():
        status = "SUCCESS" if success else "FAILED"
        print(f"{status}: {table_name}")
    
    print()
    print(f"Summary: {success_count}/{total_count} tables created successfully")
    
    return success_count == total_count


def final_verification():
    """
    Perform final verification of setup.
    
    Returns:
        bool: True if verification passes
    """
    print("Final verification...")
    health = dynamodb_setup.health_check()
    
    print("Required tables status:")
    all_good = True
    
    for table_name, info in health['required_tables'].items():
        if info['exists'] and info['status'] == 'ACTIVE':
            print(f"  ✓ {table_name}: Ready")
        else:
            print(f"  ✗ {table_name}: Not ready")
            all_good = False
    
    return all_good


def cleanup_tables():
    """
    Cleanup function to delete all tables (for testing).
    """
    print("Table Cleanup Utility")
    print("-" * 30)
    
    tables = dynamodb_setup.list_tables()
    
    if not tables:
        print("No tables to clean up")
        return
    
    print(f"Found {len(tables)} tables:")
    for table in tables:
        print(f"  - {table}")
    
    confirm = input("\nAre you sure you want to delete ALL tables? (yes/no): ")
    
    if confirm.lower() == 'yes':
        for table in tables:
            success = dynamodb_setup.delete_table(table)
            status = "DELETED" if success else "FAILED"
            print(f"{status}: {table}")
        print("Cleanup completed")
    else:
        print("Cleanup cancelled")


def reset_tables():
    """
    Reset all tables (delete and recreate).
    """
    print("Table Reset Utility")
    print("-" * 30)
    
    confirm = input("This will delete and recreate ALL tables. Continue? (yes/no): ")
    
    if confirm.lower() == 'yes':
        success = dynamodb_setup.reset_all_tables()
        
        if success:
            print("Reset completed successfully")
        else:
            print("Reset completed with errors")
    else:
        print("Reset cancelled")


def show_status():
    """
    Show current database status.
    """
    print("Database Status")
    print("-" * 30)
    
    health = dynamodb_setup.health_check()
    
    print(f"Environment: {health['environment']}")
    print(f"Endpoint: {health['endpoint']}")
    print(f"Connection: {'OK' if health['dynamodb_connection'] else 'FAILED'}")
    print(f"Total tables: {health['table_count']}")
    print()
    
    if health['required_tables']:
        print("Required tables:")
        for table_name, info in health['required_tables'].items():
            if info['exists']:
                print(f"  ✓ {table_name}")
                print(f"    Status: {info['status']}")
                print(f"    Items: {info['item_count']}")
            else:
                print(f"  ✗ {table_name}: Not found")


def main():
    """
    Main setup function.
    """
    show_header()
    
    # Health check first
    if not perform_health_check():
        print()
        print("Health check failed. Please verify:")
        print("1. DynamoDB Local is running: docker-compose up -d dynamodb-local")
        print("2. Environment configuration is correct")
        return False
    
    print()
    
    # Create tables
    if not create_tables():
        print()
        print("Table creation failed. Check errors above.")
        return False
    
    print()
    
    # Final verification
    if not final_verification():
        print()
        print("Final verification failed. Some tables may not be ready.")
        return False
    
    print()
    print("Database setup completed successfully!")
    print()
    print("Next steps:")
    print("1. Implement repository with DynamoDB integration (Commit 5)")
    print("2. Update use cases to use real persistence")
    print("3. Test end-to-end functionality")
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Voice Gateway Database Setup")
    parser.add_argument(
        "--cleanup", 
        action="store_true", 
        help="Delete all tables instead of creating them"
    )
    parser.add_argument(
        "--reset", 
        action="store_true", 
        help="Delete and recreate all tables"
    )
    parser.add_argument(
        "--status", 
        action="store_true", 
        help="Show current database status"
    )
    
    args = parser.parse_args()
    
    try:
        if args.cleanup:
            cleanup_tables()
        elif args.reset:
            reset_tables()
        elif args.status:
            show_status()
        else:
            success = main()
            sys.exit(0 if success else 1)
            
    except KeyboardInterrupt:
        print("\nSetup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nSetup failed with error: {str(e)}")
        sys.exit(1) 