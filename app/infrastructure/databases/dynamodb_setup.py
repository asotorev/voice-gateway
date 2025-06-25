"""
DynamoDB setup and management utilities.
Provides automated table creation, deletion, and health monitoring.
"""
import time
from typing import List, Dict, Any
from botocore.exceptions import ClientError
from app.config.aws_config import aws_config
from app.config.settings import settings
from .table_schemas import TableSchemas


class DynamoDBSetup:
    """
    Manages DynamoDB table creation and setup operations.
    """
    
    def __init__(self):
        self.dynamodb = aws_config.dynamodb_resource
        self.schemas = TableSchemas()
        
    def create_all_tables(self) -> Dict[str, bool]:
        """
        Create all required tables for the application.
        
        Returns:
            Dict with table names and creation status
        """
        results = {}
        
        # Create Users table (single table design)
        results['users'] = self.create_users_table()
        
        return results
    
    def create_users_table(self) -> bool:
        """
        Create the users table with optimized schema.
        
        Returns:
            True if created successfully, False otherwise
        """
        table_name = settings.users_table_name
        
        try:
            # Check if table already exists
            if self.table_exists(table_name):
                print(f"Table '{table_name}' already exists")
                return True
            
            # Create table using schema
            schema = self.schemas.users_table_schema(table_name)
            table = self.dynamodb.create_table(**schema)
            
            # Wait for table to be created
            print(f"Creating table '{table_name}'...")
            self.wait_for_table_creation(table)
            
            print(f"Table '{table_name}' created successfully")
            print(f"  - Single table design with embedded voice embeddings")
            print(f"  - Email GSI for flexible user lookup")
            print(f"  - Encryption at rest enabled")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            print(f"Failed to create table '{table_name}': {error_code} - {error_message}")
            return False
        except Exception as e:
            print(f"Unexpected error creating table '{table_name}': {str(e)}")
            return False
    
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
    
    def wait_for_table_creation(self, table, max_wait_time: int = 300) -> None:
        """
        Wait for a table to be created and become active.
        
        Args:
            table: DynamoDB table resource
            max_wait_time: Maximum time to wait in seconds
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                table.reload()
                if table.table_status == 'ACTIVE':
                    # Also wait for GSI to be active
                    if self.are_indexes_active(table):
                        return
                    
                print(f"Waiting for table and indexes to become active... (Status: {table.table_status})")
                time.sleep(5)
                
            except ClientError:
                print("Table still being created...")
                time.sleep(5)
        
        raise TimeoutError(f"Table creation timed out after {max_wait_time} seconds")
    
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
    
    def delete_table(self, table_name: str) -> bool:
        """
        Delete a table (useful for testing and cleanup).
        
        Args:
            table_name: Name of the table to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            if not self.table_exists(table_name):
                print(f"Table '{table_name}' does not exist")
                return True
            
            table = self.dynamodb.Table(table_name)
            table.delete()
            
            print(f"Table '{table_name}' deleted successfully")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            print(f"Failed to delete table '{table_name}': {error_code} - {error_message}")
            return False
    
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
            print(f"Error listing tables: {str(e)}")
            return []
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary with table information
        """
        try:
            if not self.table_exists(table_name):
                return {'exists': False}
            
            table = self.dynamodb.Table(table_name)
            table.load()
            
            info = {
                'exists': True,
                'status': table.table_status,
                'item_count': table.item_count,
                'table_size_bytes': table.table_size_bytes,
                'creation_date': str(table.creation_date_time) if hasattr(table, 'creation_date_time') else None,
                'billing_mode': getattr(table, 'billing_mode_summary', {}).get('BillingMode', 'Unknown'),
                'gsi_count': len(table.global_secondary_indexes) if table.global_secondary_indexes else 0
            }
            
            return info
            
        except Exception as e:
            return {'exists': False, 'error': str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check on DynamoDB setup.
        
        Returns:
            Dictionary with health check results
        """
        results = {
            'dynamodb_connection': False,
            'required_tables': {},
            'table_count': 0,
            'environment': settings.environment,
            'endpoint': settings.dynamodb_endpoint_url or 'AWS Default'
        }
        
        try:
            # Test connection
            tables = self.list_tables()
            results['dynamodb_connection'] = True
            results['table_count'] = len(tables)
            
            # Check required tables
            required_tables = [settings.users_table_name]
            
            for table_name in required_tables:
                table_info = self.get_table_info(table_name)
                results['required_tables'][table_name] = {
                    'exists': table_info['exists'],
                    'status': table_info.get('status', 'Unknown'),
                    'item_count': table_info.get('item_count', 0)
                }
            
        except Exception as e:
            results['error'] = str(e)
        
        return results
    
    def reset_all_tables(self) -> bool:
        """
        Delete and recreate all tables (useful for development).
        
        Returns:
            True if reset was successful
        """
        print("Resetting all tables...")
        
        # Delete existing tables
        tables_to_delete = [settings.users_table_name]
        for table_name in tables_to_delete:
            if self.table_exists(table_name):
                print(f"Deleting table: {table_name}")
                self.delete_table(table_name)
                
                # Wait for deletion to complete
                while self.table_exists(table_name):
                    print("Waiting for table deletion...")
                    time.sleep(2)
        
        # Recreate tables
        print("Recreating tables...")
        results = self.create_all_tables()
        
        success = all(results.values())
        if success:
            print("Table reset completed successfully")
        else:
            print("Table reset completed with errors")
            
        return success


# Global setup instance
dynamodb_setup = DynamoDBSetup() 