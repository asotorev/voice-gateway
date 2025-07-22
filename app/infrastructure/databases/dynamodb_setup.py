"""
DynamoDB setup and management utilities.
Provides automated table creation, deletion, and health monitoring with GSI support.
"""
import sys
import time
import argparse
from typing import List, Dict, Any
from botocore.exceptions import ClientError
from app.infrastructure.config.aws_config import aws_config
from app.infrastructure.config.infrastructure_settings import infra_settings
from app.infrastructure.logging.log_decorators import (
    log_infrastructure_operation,
    op_config
)
from .table_schemas import TableSchemas


class DynamoDBSetup:
    """
    Manages DynamoDB table creation and setup operations with GSI optimization.
    """
    
    def __init__(self):
        self.dynamodb = aws_config.dynamodb_resource
        self.schemas = TableSchemas()
        
    @log_infrastructure_operation("create_all_tables", **op_config())
    def create_all_tables(self) -> Dict[str, Any]:
        """
        Create all required tables for the application.
        
        Returns:
            Dict with table names and creation status details
        """
        results = {}
        
        # Create Users table (single table design with password GSI)
        users_result = self.create_users_table()
        results['users'] = {
            'success': users_result['success'],
            'table_name': users_result['table_name'],
            'features': users_result.get('features', []),
            'gsi_count': users_result.get('gsi_count', 0)
        }
        
        # Calculate summary metrics
        success_count = sum(1 for table in results.values() if table['success'])
        total_count = len(results)
        
        return {
            'results': results,
            'summary': {
                'total_tables': total_count,
                'successful_creations': success_count,
                'failed_creations': total_count - success_count,
                'success_rate': round((success_count / total_count) * 100, 1) if total_count > 0 else 0
            }
        }
    
    @log_infrastructure_operation("create_users_table", **op_config())
    def create_users_table(self) -> Dict[str, Any]:
        """
        Create the users table with optimized schema including password hash GSI.
        
        Returns:
            Dict with creation result and table details
        """
        table_name = infra_settings.users_table_name
        
        try:
            # Check if table already exists
            if self.table_exists(table_name):
                existing_table = self.dynamodb.Table(table_name)
                existing_table.load()
                
                # Check if password GSI exists
                has_password_gsi = self.has_password_hash_gsi(existing_table)
                
                if has_password_gsi:
                    return {
                        'success': True,
                        'table_name': table_name,
                        'action': 'skipped',
                        'reason': 'table_exists_with_gsi',
                        'features': ['password_gsi', 'email_gsi', 'encryption'],
                        'gsi_count': len(existing_table.global_secondary_indexes or [])
                    }
                else:
                    return {
                        'success': False,
                        'table_name': table_name,
                        'action': 'failed',
                        'reason': 'missing_password_gsi',
                        'recommendation': 'run_gsi_migration_or_recreate_table'
                    }
            
            # Create table using schema with GSI
            schema = self.schemas.users_table_schema(table_name)
            table = self.dynamodb.create_table(**schema)
            
            # Wait for table and all GSIs to be created
            self.wait_for_table_creation(table)
            
            return {
                'success': True,
                'table_name': table_name,
                'action': 'created',
                'features': [
                    'single_table_design',
                    'embedded_voice_embeddings',
                    'email_gsi',
                    'password_hash_gsi',
                    'encryption_at_rest'
                ],
                'gsi_count': len(table.global_secondary_indexes or []),
                'design_type': 'single_table'
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            raise RuntimeError(f"Failed to create table '{table_name}': {error_code} - {error_message}")
            
        except Exception as e:
            raise RuntimeError(f"Unexpected error creating table '{table_name}': {str(e)}")
    
    @log_infrastructure_operation("check_password_gsi", **op_config())
    def has_password_hash_gsi(self, table) -> bool:
        """
        Check if table has the password hash GSI.
        
        Args:
            table: DynamoDB table resource
            
        Returns:
            True if password hash GSI exists, False otherwise
        """
        if not hasattr(table, 'global_secondary_indexes') or not table.global_secondary_indexes:
            return False
        
        for gsi in table.global_secondary_indexes:
            if gsi['IndexName'] == 'password-hash-index':
                return True
        
        return False
    
    @log_infrastructure_operation("add_password_gsi", **op_config("CRITICAL"))
    def add_password_hash_gsi(self, table_name: str) -> Dict[str, Any]:
        """
        Add password hash GSI to existing table (migration utility).
        
        WARNING: This operation can be slow and expensive for large tables.
        
        Args:
            table_name: Name of the table to modify
            
        Returns:
            Dict with migration results
        """
        try:
            if not self.table_exists(table_name):
                raise ValueError(f"Table '{table_name}' does not exist")
            
            table = self.dynamodb.Table(table_name)
            table.load()
            
            # Check if GSI already exists
            if self.has_password_hash_gsi(table):
                return {
                    'success': True,
                    'table_name': table_name,
                    'action': 'skipped',
                    'reason': 'gsi_already_exists',
                    'gsi_name': 'password-hash-index'
                }
            
            # Get table metrics before migration
            pre_migration_metrics = {
                'item_count': getattr(table, 'item_count', 0),
                'table_size_bytes': getattr(table, 'table_size_bytes', 0)
            }
            
            # Add GSI using update_table
            client = aws_config.dynamodb_client
            
            response = client.update_table(
                TableName=table_name,
                AttributeDefinitions=[
                    {
                        'AttributeName': 'password_hash',
                        'AttributeType': 'S'
                    }
                ],
                GlobalSecondaryIndexUpdates=[
                    {
                        'Create': {
                            'IndexName': 'password-hash-index',
                            'KeySchema': [
                                {
                                    'AttributeName': 'password_hash',
                                    'KeyType': 'HASH'
                                }
                            ],
                            'Projection': {
                                'ProjectionType': 'KEYS_ONLY'
                            }
                        }
                    }
                ]
            )
            
            # Wait for GSI to become active
            self.wait_for_gsi_creation(table_name, 'password-hash-index')
            
            return {
                'success': True,
                'table_name': table_name,
                'action': 'gsi_added',
                'gsi_name': 'password-hash-index',
                'projection_type': 'KEYS_ONLY',
                'pre_migration_metrics': pre_migration_metrics,
                'aws_request_id': response.get('ResponseMetadata', {}).get('RequestId'),
                'performance_impact': 'O(n) to O(1) password uniqueness validation'
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            raise RuntimeError(f"Failed to add GSI to table '{table_name}': {error_code} - {error_message}")
            
        except Exception as e:
            raise RuntimeError(f"Unexpected error adding GSI to table '{table_name}': {str(e)}")
    
    @log_infrastructure_operation("wait_gsi_creation", **op_config())
    def wait_for_gsi_creation(self, table_name: str, index_name: str, max_wait_time: int = 600) -> Dict[str, Any]:
        """
        Wait for a GSI to be created and become active.
        
        Args:
            table_name: Name of the table
            index_name: Name of the GSI
            max_wait_time: Maximum time to wait in seconds
            
        Returns:
            Dict with waiting results
        """
        start_time = time.time()
        client = aws_config.dynamodb_client
        
        while time.time() - start_time < max_wait_time:
            try:
                response = client.describe_table(TableName=table_name)
                table_desc = response['Table']
                elapsed_time = time.time() - start_time
                
                if 'GlobalSecondaryIndexes' in table_desc:
                    for gsi in table_desc['GlobalSecondaryIndexes']:
                        if gsi['IndexName'] == index_name:
                            status = gsi['IndexStatus']
                            
                            if status == 'ACTIVE':
                                return {
                                    'success': True,
                                    'index_name': index_name,
                                    'final_status': status,
                                    'total_wait_time_seconds': round(elapsed_time, 2)
                                }
                            elif status in ['CREATING', 'UPDATING']:
                                # Continue waiting
                                pass
                            else:
                                raise RuntimeError(f"GSI creation failed with status: {status}")
                
                time.sleep(10)  # Check every 10 seconds for GSI
                
            except ClientError as e:
                # Temporary error, continue waiting
                time.sleep(10)
        
        raise TimeoutError(f"GSI creation timed out after {max_wait_time} seconds")
    
    @log_infrastructure_operation("table_exists_check", **op_config())
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in DynamoDB.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
        """
        try:
            table = self.dynamodb.Table(table_name)
            table.load()  # This will raise an exception if table doesn't exist
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            raise  # Re-raise other errors
    
    @log_infrastructure_operation("wait_table_creation", **op_config())
    def wait_for_table_creation(self, table, max_wait_time: int = 600) -> Dict[str, Any]:
        """
        Wait for a table to be created and become active, including all GSIs.
        
        Args:
            table: DynamoDB table resource
            max_wait_time: Maximum time to wait in seconds
            
        Returns:
            Dict with waiting results
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                table.reload()
                elapsed_time = time.time() - start_time
                
                if table.table_status == 'ACTIVE':
                    # Also wait for all GSIs to be active
                    if self.are_indexes_active(table):
                        return {
                            'success': True,
                            'table_name': table.name,
                            'table_status': table.table_status,
                            'total_wait_time_seconds': round(elapsed_time, 2),
                            'gsi_status': self.get_gsi_status_summary(table)
                        }
                
                time.sleep(5)
                
            except ClientError:
                # Table still being created
                time.sleep(5)
        
        raise TimeoutError(f"Table creation timed out after {max_wait_time} seconds")
    
    @log_infrastructure_operation("get_gsi_status", **op_config())
    def get_gsi_status_summary(self, table) -> str:
        """
        Get a summary of all GSI statuses.
        
        Args:
            table: DynamoDB table resource
            
        Returns:
            String summarizing GSI statuses
        """
        if not hasattr(table, 'global_secondary_indexes') or not table.global_secondary_indexes:
            return "No GSIs"
        
        statuses = []
        for index in table.global_secondary_indexes:
            name = index['IndexName']
            status = index['IndexStatus']
            statuses.append(f"{name}:{status}")
        
        return ", ".join(statuses)
    
    @log_infrastructure_operation("check_indexes_active", **op_config())
    def are_indexes_active(self, table) -> bool:
        """
        Check if all Global Secondary Indexes are active.
        
        Args:
            table: DynamoDB table resource
            
        Returns:
            True if all indexes are active, False otherwise
        """
        if not hasattr(table, 'global_secondary_indexes') or not table.global_secondary_indexes:
            return True
        
        for index in table.global_secondary_indexes:
            if index['IndexStatus'] != 'ACTIVE':
                return False
        
        return True
    
    @log_infrastructure_operation("delete_table", **op_config("CRITICAL"))
    def delete_table(self, table_name: str) -> Dict[str, Any]:
        """
        Delete a table (useful for testing and cleanup).
        
        Args:
            table_name: Name of the table to delete
            
        Returns:
            Dict with deletion results
        """
        try:
            if not self.table_exists(table_name):
                return {
                    'success': True,
                    'table_name': table_name,
                    'action': 'skipped',
                    'reason': 'table_does_not_exist'
                }
            
            # Get table info before deletion for logging
            table_info = self.get_table_info(table_name)
            
            table = self.dynamodb.Table(table_name)
            table.delete()
            
            return {
                'success': True,
                'table_name': table_name,
                'action': 'deleted',
                'pre_deletion_info': {
                    'item_count': table_info.get('item_count', 0),
                    'table_size_bytes': table_info.get('table_size_bytes', 0),
                    'gsi_count': table_info.get('gsi_count', 0)
                },
                'data_recovery': 'not_possible'
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            raise RuntimeError(f"Failed to delete table '{table_name}': {error_code} - {error_message}")
    
    @log_infrastructure_operation("list_tables", **op_config())
    def list_tables(self) -> List[str]:
        """
        List all tables in the DynamoDB instance.
        
        Returns:
            List of table names
        """
        try:
            tables = list(self.dynamodb.tables.all())
            table_names = [table.name for table in tables]
            return table_names
        except Exception as e:
            raise RuntimeError(f"Error listing tables: {str(e)}")
    
    @log_infrastructure_operation("get_table_info", **op_config())
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a table including GSI info.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary with table information
        """
        try:
            if not self.table_exists(table_name):
                return {'exists': False, 'table_name': table_name}
            
            table = self.dynamodb.Table(table_name)
            table.load()
            
            # Check for password hash GSI
            has_password_gsi = self.has_password_hash_gsi(table)
            gsi_info = []
            
            if hasattr(table, 'global_secondary_indexes') and table.global_secondary_indexes:
                for gsi in table.global_secondary_indexes:
                    gsi_info.append({
                        'name': gsi['IndexName'],
                        'status': gsi['IndexStatus'],
                        'projection': gsi['Projection']['ProjectionType']
                    })
            
            return {
                'exists': True,
                'table_name': table_name,
                'status': table.table_status,
                'item_count': table.item_count,
                'table_size_bytes': table.table_size_bytes,
                'creation_date': str(table.creation_date_time) if hasattr(table, 'creation_date_time') else None,
                'billing_mode': getattr(table, 'billing_mode_summary', {}).get('BillingMode', 'Unknown'),
                'gsi_count': len(table.global_secondary_indexes) if table.global_secondary_indexes else 0,
                'has_password_gsi': has_password_gsi,
                'gsi_details': gsi_info
            }
            
        except Exception as e:
            raise RuntimeError(f"Error getting table info for '{table_name}': {str(e)}")
    
    @log_infrastructure_operation("health_check", **op_config())
    def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check on DynamoDB setup including GSI status.
        
        Returns:
            Dictionary with health check results
        """
        results = {
            'dynamodb_connection': False,
            'required_tables': {},
            'table_count': 0,
            'environment': infra_settings.aws_region,
            'endpoint': infra_settings.dynamodb_endpoint_url or 'AWS Default',
            'password_gsi_optimization': False
        }
        
        try:
            # Test connection
            tables = self.list_tables()
            results['dynamodb_connection'] = True
            results['table_count'] = len(tables)
            
            # Check required tables
            required_tables = [infra_settings.users_table_name]
            
            for table_name in required_tables:
                table_info = self.get_table_info(table_name)
                results['required_tables'][table_name] = {
                    'exists': table_info['exists'],
                    'status': table_info.get('status', 'Unknown'),
                    'item_count': table_info.get('item_count', 0),
                    'gsi_count': table_info.get('gsi_count', 0),
                    'has_password_gsi': table_info.get('has_password_gsi', False)
                }
                
                # Check if password GSI optimization is available
                if table_info.get('has_password_gsi', False):
                    results['password_gsi_optimization'] = True
            
            return results
            
        except Exception as e:
            raise RuntimeError(f"Health check failed: {str(e)}")
    
    @log_infrastructure_operation("reset_all_tables", **op_config("CRITICAL"))
    def reset_all_tables(self) -> Dict[str, Any]:
        """
        Delete and recreate all tables (useful for development).
        
        Returns:
            Dict with reset operation results
        """
        # Delete existing tables
        tables_to_delete = [infra_settings.users_table_name]
        deletion_results = []
        
        for table_name in tables_to_delete:
            if self.table_exists(table_name):
                deletion_result = self.delete_table(table_name)
                deletion_results.append(deletion_result)
                
                # Wait for deletion to complete
                while self.table_exists(table_name):
                    time.sleep(2)
        
        # Recreate tables
        creation_results = self.create_all_tables()
        
        success = creation_results['summary']['success_rate'] == 100.0
        
        return {
            'reset_successful': success,
            'deletion_results': deletion_results,
            'creation_results': creation_results,
            'password_gsi_optimization': True,
            'total_tables_processed': len(tables_to_delete)
        }


def main():
    """Entry point for CLI operations on DynamoDB setup (class-based, setup_database style)."""
    parser = argparse.ArgumentParser(description="DynamoDB Setup Utility")
    parser.add_argument("--health", action="store_true", help="Run health check")
    parser.add_argument("--create", action="store_true", help="Create all tables")
    parser.add_argument("--delete", metavar="TABLE", help="Delete a specific table by name")
    parser.add_argument("--list", action="store_true", help="List all tables")
    parser.add_argument("--info", metavar="TABLE", help="Get info for a specific table")
    args = parser.parse_args()

    setup = DynamoDBSetup()
    try:
        if args.health:
            result = setup.health_check()
            success = result.get("dynamodb_connection", False)
        elif args.create:
            result = setup.create_all_tables()
            success = result["summary"]["success_rate"] == 100.0
        elif args.delete:
            result = setup.delete_table(args.delete)
            success = result.get("success", False)
        elif args.list:
            result = setup.list_tables()
            success = isinstance(result, list)
        elif args.info:
            result = setup.get_table_info(args.info)
            success = result.get("exists", False)
        else:
            parser.print_help()
            return 1
        return 0 if success else 1
    except KeyboardInterrupt:
        return 1
    except Exception:
        return 1

if __name__ == "__main__":
    sys.exit(main())