#!/usr/bin/env python3
"""Add password hash GSI to users table."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app.infrastructure.databases.dynamodb_setup import dynamodb_setup
from app.config.settings import settings


def main():
    """Add password hash GSI to existing users table."""
    table_name = settings.users_table_name
    
    # Check if table exists
    table_info = dynamodb_setup.get_table_info(table_name)
    if not table_info['exists']:
        print(f"Table '{table_name}' does not exist")
        print("Run setup_database.py first")
        return False
    
    # Check if GSI already exists
    if table_info['has_password_gsi']:
        print("Password hash GSI already exists")
        return True
    
    print(f"Adding password hash GSI to {table_name}...")
    print("This may take a few minutes for large tables")
    
    # Add the GSI
    success = dynamodb_setup.add_password_hash_gsi(table_name)
    
    if success:
        print("GSI added successfully")
    else:
        print("Failed to add GSI")
    
    return success


def check_status():
    """Check if password GSI exists."""
    table_name = settings.users_table_name
    table_info = dynamodb_setup.get_table_info(table_name)
    
    if not table_info['exists']:
        print("Table does not exist")
        return False
    
    if table_info['has_password_gsi']:
        print("Password hash GSI is active")
        return True
    else:
        print("Password hash GSI not found")
        return False


def rollback():
    """Remove password GSI (for testing)."""
    print("WARNING: This will remove the password hash GSI")
    confirm = input("Continue? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Cancelled")
        return False
    
    table_name = settings.users_table_name
    client = dynamodb_setup.dynamodb.meta.client
    
    try:
        client.update_table(
            TableName=table_name,
            GlobalSecondaryIndexUpdates=[
                {'Delete': {'IndexName': 'password-hash-index'}}
            ]
        )
        print("GSI deletion started")
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'status':
            success = check_status()
        elif command == 'rollback':
            success = rollback()
        else:
            print("Usage:")
            print("  python migrate_password_gsi.py          # Add GSI")
            print("  python migrate_password_gsi.py status   # Check status")
            print("  python migrate_password_gsi.py rollback # Remove GSI")
            success = False
    else:
        success = main()
    
    sys.exit(0 if success else 1) 