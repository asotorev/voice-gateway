"""
DynamoDB setup and management utilities.
Provides automated table creation, deletion, and health monitoring with GSI support.
"""
import time
from typing import List, Dict, Any
from botocore.exceptions import ClientError
from app.config.aws_config import aws_config
from app.config.settings import settings
from .table_schemas import TableSchemas


class DynamoDBSetup:
    """
    Manages DynamoDB table creation and setup operations with GSI optimization.
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
        
        # Create Users table (single table design with password GSI)
        results['users'] = self.create_users_table()
        
        return results
    
    def create_users_table(self) -> bool:
        """
        Create the users table with optimized schema including password hash GSI.
        
        Returns:
            True if created successfully, False otherwise
        """
        table_name = settings.users_table_name
        
        try:
            # Check if table already exists
            if self.table_exists(table_name):
                existing_table = self.dynamodb.Table(table_name)
                existing_table.load()
                
                # Check if password GSI exists
                has_password_gsi = self.has_password_hash_gsi(existing_table)
                
                if has_password_gsi:
                    print(f"Table '{table_name}' already exists with password hash GSI")
                    return True
                else:
                    print(f"Table '{table_name}' exists but missing password hash GSI")
                    print("Consider running GSI migration or recreating table")
                    return False
            
            # Create table using schema with GSI
            schema = self.schemas.users_table_schema(table_name)
            table = self.dynamodb.create_table(**schema)
            
            # Wait for table and all GSIs to be created
            print(f"Creating table '{table_name}' with password hash GSI...")
            self.wait_for_table_creation(table)
            
            print(f"Table '{table_name}' created successfully")
            print(f"  - Single table design with embedded voice embeddings")
            print(f"  - Email GSI for flexible user lookup")
            print(f"  - Password hash GSI for immediate uniqueness validation")
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
    
    def add_password_hash_gsi(self, table_name: str) -> bool:
        """
        Add password hash GSI to existing table (migration utility).
        
        WARNING: This operation can be slow and expensive for large tables.
        
        Args:
            table_name: Name of the table to modify
            
        Returns:
            True if GSI was added successfully, False otherwise
        """
        try:
            if not self.table_exists(table_name):
                print(f"Table '{table_name}' does not exist")
                return False
            
            table = self.dynamodb.Table(table_name)
            table.load()
            
            # Check if GSI already exists
            if self.has_password_hash_gsi(table):
                print(f"Password hash GSI already exists on table '{table_name}'")
                return True
            
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
            
            print(f"Adding password hash GSI to table '{table_name}'...")
            print("WARNING: This operation may take several minutes for large tables")
            
            # Wait for GSI to become active
            self.wait_for_gsi_creation(table_name, 'password-hash-index')
            
            print(f"Password hash GSI added successfully to table '{table_name}'")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            print(f"Failed to add GSI to table '{table_name}': {error_code} - {error_message}")
            return False
        except Exception as e:
            print(f"Unexpected error adding GSI to table '{table_name}': {str(e)}")
            return False
    
    def wait_for_gsi_creation(self, table_name: str, index_name: str, max_wait_time: int = 600) -> None:
        """
        Wait for a GSI to be created and become active.
        
        Args:
            table_name: Name of the table
            index_name: Name of the GSI
            max_wait_time: Maximum time to wait in seconds
        """
        start_time = time.time()
        client = aws_config.dynamodb_client
        
        while time.time() - start_time < max_wait_time:
            try:
                response = client.describe_table(TableName=table_name)
                table_desc = response['Table']
                
                if 'GlobalSecondaryIndexes' in table_desc:
                    for gsi in table_desc['GlobalSecondaryIndexes']:
                        if gsi['IndexName'] == index_name:
                            status = gsi['IndexStatus']
                            
                            if status == 'ACTIVE':
                                print(f"GSI '{index_name}' is now active")
                                return
                            elif status in ['CREATING', 'UPDATING']:
                                print(f"GSI '{index_name}' status: {status}")
                            else:
                                raise Exception(f"GSI creation failed with status: {status}")
                
                time.sleep(10)  # Check every 10 seconds for GSI
                
            except ClientError as e:
                print(f"Error checking GSI status: {e}")
                time.sleep(10)
        
        raise TimeoutError(f"GSI creation timed out after {max_wait_time} seconds")
    
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
    
    def wait_for_table_creation(self, table, max_wait_time: int = 600) -> None:
        """
        Wait for a table to be created and become active, including all GSIs.
        
        Args:
            table: DynamoDB table resource
            max_wait_time: Maximum time to wait in seconds
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                table.reload()
                if table.table_status == 'ACTIVE':
                    # Also wait for all GSIs to be active
                    if self.are_indexes_active(table):
                        return
                    
                gsi_status = self.get_gsi_status_summary(table)
                print(f"Waiting for table and indexes to become active... (Table: {table.table_status}, GSIs: {gsi_status})")
                time.sleep(5)
                
            except ClientError:
                print("Table still being created...")
                time.sleep(5)
        
        raise TimeoutError(f"Table creation timed out after {max_wait_time} seconds")
    
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
        Get detailed information about a table including GSI info.
        
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
            
            info = {
                'exists': True,
                'status': table.table_status,
                'item_count': table.item_count,
                'table_size_bytes': table.table_size_bytes,
                'creation_date': str(table.creation_date_time) if hasattr(table, 'creation_date_time') else None,
                'billing_mode': getattr(table, 'billing_mode_summary', {}).get('BillingMode', 'Unknown'),
                'gsi_count': len(table.global_secondary_indexes) if table.global_secondary_indexes else 0,
                'has_password_gsi': has_password_gsi,
                'gsi_details': gsi_info
            }
            
            return info
            
        except Exception as e:
            return {'exists': False, 'error': str(e)}
    
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
            'environment': settings.environment,
            'endpoint': settings.dynamodb_endpoint_url or 'AWS Default',
            'password_gsi_optimization': False
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
                    'item_count': table_info.get('item_count', 0),
                    'gsi_count': table_info.get('gsi_count', 0),
                    'has_password_gsi': table_info.get('has_password_gsi', False)
                }
                
                # Check if password GSI optimization is available
                if table_info.get('has_password_gsi', False):
                    results['password_gsi_optimization'] = True
            
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
        print("Recreating tables with password hash GSI...")
        results = self.create_all_tables()
        
        success = all(results.values())
        if success:
            print("Table reset completed successfully")
            print("Password hash GSI optimization is now available")
        else:
            print("Table reset completed with errors")
            
        return success


# Global setup instance
dynamodb_setup = DynamoDBSetup()