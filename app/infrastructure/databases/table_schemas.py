"""
DynamoDB table schema definitions for Voice Gateway.
Implements single table design optimized for voice authentication.

"""
from typing import Dict, Any


class TableSchemas:
    """
    Centralized DynamoDB table schema definitions.
    
    Design principles:
    - Single table design for optimal authentication performance
    - Relative audio paths to eliminate storage provider coupling
    - Granular timestamps for debugging and audit trails
    - Security-first approach with encryption and bcrypt hashing
    """
    
    @staticmethod
    def users_table_schema(table_name: str) -> Dict[str, Any]:
        """
        Users table schema with embedded voice embeddings.
        
        Optimized structure:
        - user_id (PK): UUID string - unique user identifier
        - name: User's full name
        - email: User's email address (unique via GSI)
        - voice_password_hash: bcrypt hash of 2-word Spanish password
        - voice_embeddings: Array of 3 embeddings, each containing:
            * audio_path: Relative path (e.g., 'user123/sample1.wav')
            * embedding_vector: 256-dimension vector from Resemblyzer
            * generated_at: ISO timestamp of embedding generation
        - created_at: ISO timestamp of user registration
        - updated_at: ISO timestamp of last modification
        - is_active: Boolean status for soft deletion
    
        Args:
            table_name: Name for the DynamoDB table
            
        Returns:
            DynamoDB table creation schema dictionary
        """
        return {
            'TableName': table_name,
            'KeySchema': [
                {
                    'AttributeName': 'user_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            'AttributeDefinitions': [
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'  # String
                },
                {
                    'AttributeName': 'email',
                    'AttributeType': 'S'  # String for GSI
                }
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'email-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'email',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    }
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST',  # On-demand pricing for development
            'StreamSpecification': {
                'StreamEnabled': False
            },
            'SSESpecification': {
                'Enabled': True  # Encryption at rest
            },
            'Tags': [
                {
                    'Key': 'Project',
                    'Value': 'VoiceGateway'
                },
                {
                    'Key': 'Environment', 
                    'Value': 'Development'
                },
                {
                    'Key': 'TableType',
                    'Value': 'Users'
                },
                {
                    'Key': 'Design',
                    'Value': 'SingleTable'
                }
            ]
        }
    
    @classmethod
    def get_all_schemas(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get all table schemas for batch operations.
        
        Currently implements single table design with only users table.
        Future schemas (audio_samples, voice_embeddings) may be added
        if separate table storage becomes necessary.
        
        Returns:
            Dictionary mapping table types to their schemas
        """
        return {
            'users': cls.users_table_schema('voice-gateway-users')
        }
    
    @classmethod
    def validate_schema(cls, schema: Dict[str, Any]) -> bool:
        """
        Validate that a schema has required DynamoDB fields.
        
        Args:
            schema: DynamoDB table schema to validate
            
        Returns:
            True if schema is valid, False otherwise
        """
        required_fields = ['TableName', 'KeySchema', 'AttributeDefinitions']
        
        for field in required_fields:
            if field not in schema:
                return False
        
        # Validate KeySchema has at least one key
        if not schema['KeySchema']:
            return False
        
        # Validate AttributeDefinitions match KeySchema
        key_attributes = {key['AttributeName'] for key in schema['KeySchema']}
        defined_attributes = {attr['AttributeName'] for attr in schema['AttributeDefinitions']}
        
        if not key_attributes.issubset(defined_attributes):
            return False
        
        return True
    
    @classmethod
    def get_example_user_structure(cls) -> Dict[str, Any]:
        """
        Get example of how user data will be stored in DynamoDB.
        
        Demonstrates the single table design with embedded voice embeddings
        using relative paths for storage provider independence.
        
        Returns:
            Example user item structure
        """
        return {
            'user_id': 'uuid-12345678-1234-1234-1234-123456789012',
            'name': 'Juan Pérez',
            'email': 'juan@ejemplo.com',
            'voice_password_hash': '$2b$12$abc123def456...',  # bcrypt hash
            'voice_embeddings': [
                {
                    'audio_path': 'user123/sample1.wav',        # Relative path
                    'embedding_vector': [0.1, 0.2, 0.3],       # 256 dimensions (truncated)
                    'generated_at': '2024-01-15T10:31:22.123Z'
                },
                {
                    'audio_path': 'user123/sample2.wav',
                    'embedding_vector': [0.4, 0.5, 0.6],
                    'generated_at': '2024-01-15T10:32:15.456Z'
                },
                {
                    'audio_path': 'user123/sample3.wav',
                    'embedding_vector': [0.7, 0.8, 0.9],
                    'generated_at': '2024-01-15T10:33:01.789Z'
                }
            ],
            'created_at': '2024-01-15T10:30:00.000Z',
            'updated_at': '2024-01-15T10:33:01.789Z',
            'is_active': True
        } 