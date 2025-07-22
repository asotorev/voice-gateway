#!/usr/bin/env python3
"""Add password hash GSI to users table."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import app.infrastructure.logging.log_config
from app.infrastructure.logging.log_decorators import log_infrastructure_operation, op_config
from app.infrastructure.databases.dynamodb_setup import dynamodb_setup
from app.infrastructure.config.infrastructure_settings import infra_settings

class MigratePasswordGSIScript:
    """Script operations for managing password hash GSI on users table."""

    @log_infrastructure_operation("migrate_password_gsi", **op_config())
    def main(self):
        table_name = infra_settings.users_table_name
        table_info = dynamodb_setup.get_table_info(table_name)
        if not table_info['exists']:
            return {
                "success": False,
                "error": f"Table '{table_name}' does not exist",
                "hint": "Run setup_database.py first"
            }
        if table_info['has_password_gsi']:
            return {
                "success": True,
                "info": "Password hash GSI already exists"
            }
        result = dynamodb_setup.add_password_hash_gsi(table_name)
        if result and result.get("success"):
            return {
                "success": True,
                "info": "GSI added successfully"
            }
        else:
            return {
                "success": False,
                "error": "Failed to add GSI"
            }

    @log_infrastructure_operation("check_password_gsi_status", **op_config())
    def check_status(self):
        table_name = infra_settings.users_table_name
        table_info = dynamodb_setup.get_table_info(table_name)
        if not table_info['exists']:
            return {
                "success": False,
                "error": "Table does not exist"
            }
        if table_info['has_password_gsi']:
            return {
                "success": True,
                "info": "Password hash GSI is active"
            }
        else:
            return {
                "success": False,
                "warning": "Password hash GSI not found"
            }

    @log_infrastructure_operation("rollback_password_gsi", **op_config())
    def rollback(self):
        confirm = input("WARNING: This will remove the password hash GSI. Continue? (y/N): ").strip().lower()
        if confirm != 'y':
            return {
                "success": False,
                "info": "Cancelled"
            }
        table_name = infra_settings.users_table_name
        client = dynamodb_setup.dynamodb.meta.client
        try:
            client.update_table(
                TableName=table_name,
                GlobalSecondaryIndexUpdates=[
                    {'Delete': {'IndexName': 'password-hash-index'}}
                ]
            )
            return {
                "success": True,
                "info": "GSI deletion started"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed: {e}"
            }

def main():
    script = MigratePasswordGSIScript()
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == 'status':
            result = script.check_status()
        elif command == 'rollback':
            result = script.rollback()
        else:
            result = {
                "success": False,
                "error": "Usage:",
                "usage": [
                    "python migrate_password_gsi.py          # Add GSI",
                    "python migrate_password_gsi.py status   # Check status",
                    "python migrate_password_gsi.py rollback # Remove GSI"
                ]
            }
    else:
        result = script.main()
    sys.exit(0 if result.get("success") else 1)

if __name__ == "__main__":
    main() 