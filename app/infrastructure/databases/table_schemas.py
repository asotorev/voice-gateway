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
    - GSI optimization for password uniqueness validation
    """
    
    @staticmethod
    def users_table_schema(table_name: str) -> Dict[str, Any]:
        """
        Users table schema with embedded voice embeddings and password hash GSI.
        
        Optimized structure:
        - user_id (PK): UUID string - unique user identifier
        - name: User's full name
        - email: User's email address (unique via GSI)
        - password_hash: SHA-256 hash of 2-word Spanish password (indexed for immediate lookup)
        - voice_embeddings: Array of embeddings, each containing:
            * embedding: 256-dimension vector from Resemblyzer
            * created_at: ISO timestamp of embedding generation
            * audio_metadata: Dict with file_name, file_size, processed_at
        - voice_embeddings_count: Integer count of embeddings
        - voice_setup_complete: Boolean indicating if voice setup is complete
        - registration_complete: Boolean indicating if voice registration is complete
        - registration_completed_at: ISO timestamp when registration was completed
        - created_at: ISO timestamp of user registration
        - updated_at: ISO timestamp of last modification
        - is_active: Boolean status for soft deletion
    
        GSI Indexes:
        1. email-index: For user lookup by email
        2. password-hash-index: For password uniqueness validation
    
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
                    'AttributeType': 'S'  # String for email GSI
                },
                {
                    'AttributeName': 'password_hash',
                    'AttributeType': 'S'  # String for password hash GSI
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
                },
                {
                    'IndexName': 'password-hash-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'password_hash',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'KEYS_ONLY'  # Only need to check existence
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
                },
                {
                    'Key': 'Optimization',
                    'Value': 'PasswordUniquenessO1Lookup'
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
        
        # Validate AttributeDefinitions match KeySchema and GSI keys
        key_attributes = {key['AttributeName'] for key in schema['KeySchema']}
        defined_attributes = {attr['AttributeName'] for attr in schema['AttributeDefinitions']}
        
        # Also check GSI key attributes if they exist
        if 'GlobalSecondaryIndexes' in schema:
            for gsi in schema['GlobalSecondaryIndexes']:
                gsi_attributes = {key['AttributeName'] for key in gsi['KeySchema']}
                key_attributes.update(gsi_attributes)
        
        if not key_attributes.issubset(defined_attributes):
            return False
        
        return True
    
    @classmethod
    def get_example_user_structure(cls) -> Dict[str, Any]:
        """
        Get example of how user data will be stored in DynamoDB.
        
        Demonstrates the single table design with embedded voice embeddings
        using relative paths for storage provider independence and password hash
        for uniqueness validation.
        
        Returns:
            Example user item structure
        """
        return {
            'user_id': 'uuid-12345678-1234-1234-1234-123456789012',
            'name': 'Juan Pérez',
            'email': 'juan@ejemplo.com',
            'password_hash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.gS8C.m',  # bcrypt hash (indexed for immediate lookup)
            'voice_embeddings': [
                {
                    'embedding': [0.1, 0.2, 0.3],              # 256 dimensions (truncated)
                    'created_at': '2024-01-15T10:31:22.123Z',
                    'audio_metadata': {
                        'file_name': 'sample1.wav',
                        'file_size': 1024,
                        'processed_at': '2024-01-15T10:31:22.123Z'
                    }
                },
                {
                    'embedding': [0.4, 0.5, 0.6],
                    'created_at': '2024-01-15T10:32:15.456Z',
                    'audio_metadata': {
                        'file_name': 'sample2.wav',
                        'file_size': 1024,
                        'processed_at': '2024-01-15T10:32:15.456Z'
                    }
                },
                {
                    'embedding': [0.7, 0.8, 0.9],
                    'created_at': '2024-01-15T10:33:01.789Z',
                    'audio_metadata': {
                        'file_name': 'sample3.wav',
                        'file_size': 1024,
                        'processed_at': '2024-01-15T10:33:01.789Z'
                    }
                }
            ],
            'voice_embeddings_count': 3,                        
            'voice_setup_complete': True,                       
            'registration_complete': True,                      
            'registration_completed_at': '2024-01-15T10:33:01.789Z',  
            'created_at': '2024-01-15T10:30:00.000Z',
            'updated_at': '2024-01-15T10:33:01.789Z',
            'is_active': True
        }
    
