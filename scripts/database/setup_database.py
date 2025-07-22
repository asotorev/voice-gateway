#!/usr/bin/env python3
"""
Database setup script for Voice Gateway.
Creates all required DynamoDB tables and performs health checks.
"""
import sys
import argparse
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent.parent.parent
sys.path.append(str(current_dir))

# Import improved logging - auto-configures on first use
from app.infrastructure.logging.log_config import get_logger
from app.infrastructure.databases.dynamodb_setup import DynamoDBSetup
from app.infrastructure.config.infrastructure_settings import infra_settings
from app.infrastructure.logging.log_decorators import (
    log_infrastructure_operation,
    op_config
)


class DatabaseSetupScript:
    """Database setup operations with improved structured logging."""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.dynamodb_setup = DynamoDBSetup()

    @log_infrastructure_operation("environment_display", **op_config("DEBUG"))
    def show_header(self):
        """Display setup header with environment info."""
        return {
            "environment": infra_settings.environment,
            "dynamodb_endpoint": infra_settings.dynamodb_endpoint_url or "AWS Default",
            "region": infra_settings.aws_region,
            "users_table": infra_settings.users_table_name
        }

    @log_infrastructure_operation("health_check", **op_config())
    def perform_health_check(self):
        """Perform initial health check."""
        health = self.dynamodb_setup.health_check()
        if not health['dynamodb_connection']:
            raise ConnectionError("DynamoDB connection failed")
        return {
            "connection_successful": True,
            "total_tables": health['table_count'],
            "required_tables": health['required_tables']
        }

    @log_infrastructure_operation("table_creation", **op_config())
    def create_tables(self):
        """Create all required tables."""
        results = self.dynamodb_setup.create_all_tables()
        
        # Extract success info from the new structure
        success_count = results['summary']['successful_creations']
        total_count = results['summary']['total_tables']
        
        if success_count != total_count:
            raise RuntimeError(f"Table creation failed: {success_count}/{total_count} successful")
        return {
            "total_tables": total_count,
            "successful_creations": success_count,
            "success_rate": results['summary']['success_rate'],
            "results": results['results']
        }

    @log_infrastructure_operation("table_cleanup", **op_config("CRITICAL"))
    def cleanup_tables(self):
        """Cleanup function to delete all tables."""
        tables = self.dynamodb_setup.list_tables()
        if not tables:
            return {"action": "skipped", "reason": "no_tables_found", "deleted_count": 0}
        deleted_count = 0
        failed_deletions = []
        for table in tables:
            result = self.dynamodb_setup.delete_table(table)
            if result.get('success', False):
                deleted_count += 1
            else:
                failed_deletions.append(table)
        return {
            "total_tables_found": len(tables),
            "deleted_count": deleted_count,
            "failed_deletions": failed_deletions,
            "cleanup_complete": len(failed_deletions) == 0
        }

    @log_infrastructure_operation("table_reset", **op_config("CRITICAL"))
    def reset_tables(self):
        """Reset all tables (delete and recreate)."""
        cleanup_result = self.cleanup_tables()
        import time
        time.sleep(2)
        creation_result = self.create_tables()
        return {
            "cleanup_result": cleanup_result,
            "creation_result": creation_result,
            "reset_successful": cleanup_result.get("cleanup_complete", False) and creation_result.get("success_rate", 0) == 100.0
        }

    @log_infrastructure_operation("status_check", **op_config())
    def show_status(self):
        """Show current database status."""
        health = self.dynamodb_setup.health_check()
        return {
            "environment": health.get('environment', 'unknown'),
            "endpoint": health.get('endpoint', 'unknown'),
            "connection_status": "healthy" if health['dynamodb_connection'] else "failed",
            "total_tables": health['table_count'],
            "required_tables_status": health.get('required_tables', {}),
            "password_gsi_optimization": health.get('password_gsi_optimization', False)
        }

    @log_infrastructure_operation("final_verification", **op_config())
    def final_verification(self):
        """Perform final verification of setup."""
        health = self.dynamodb_setup.health_check()
        ready_tables = []
        failed_tables = []
        for table_name, info in health['required_tables'].items():
            if info['exists'] and info['status'] == 'ACTIVE':
                ready_tables.append(table_name)
            else:
                failed_tables.append({
                    "table_name": table_name,
                    "exists": info['exists'],
                    "status": info.get('status', 'unknown')
                })
        verification_passed = len(failed_tables) == 0
        if not verification_passed:
            raise RuntimeError(f"Verification failed: {len(failed_tables)} tables not ready")
        return {
            "verification_passed": verification_passed,
            "ready_tables": ready_tables,
            "failed_tables": failed_tables,
            "total_ready": len(ready_tables)
        }

    @log_infrastructure_operation("database_setup_main", **op_config())
    def main(self):
        """Main setup function."""
        header_info = self.show_header()
        health_result = self.perform_health_check()
        creation_result = self.create_tables()
        verification_result = self.final_verification()
        return {
            "setup_successful": True,
            "environment_info": header_info,
            "health_check": health_result,
            "table_creation": creation_result,
            "final_verification": verification_result
        }


def main():
    """Entry point with argument parsing and error handling."""
    parser = argparse.ArgumentParser(description="Voice Gateway Database Setup")
    parser.add_argument("--cleanup", action="store_true", help="Delete all tables")
    parser.add_argument("--reset", action="store_true", help="Delete and recreate tables")
    parser.add_argument("--status", action="store_true", help="Show database status")
    
    args = parser.parse_args()
    
    setup_script = DatabaseSetupScript()
    
    try:
        if args.cleanup:
            result = setup_script.cleanup_tables()
            success = result.get("cleanup_complete", False)
        elif args.reset:
            result = setup_script.reset_tables()
            success = result.get("reset_successful", False)
        elif args.status:
            result = setup_script.show_status()
            success = result.get("connection_status") == "healthy"
        else:
            result = setup_script.main()
            success = result.get("setup_successful", False)
        
        sys.exit(0 if success else 1)
            
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        sys.exit(1) 


if __name__ == "__main__":
    main()