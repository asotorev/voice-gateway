#!/usr/bin/env python3
"""
Test table schema definitions for Voice Gateway.
Validates optimized single table design and structure.
"""
import sys
from pathlib import Path
import pytest

# Add the app directory to Python path
app_dir = Path(__file__).parent.parent
sys.path.append(str(app_dir))

from app.infrastructure.databases.table_schemas import TableSchemas


@pytest.mark.unit
def test_users_table_schema():
    """
    Test users table schema structure and validity.
    
    """
    schema = TableSchemas.users_table_schema("test-users-table")
    assert isinstance(schema, dict)
    assert schema['TableName'] == "test-users-table"
    required_fields = ['TableName', 'KeySchema', 'AttributeDefinitions']
    for field in required_fields:
        assert field in schema
    key_schema = schema['KeySchema']
    assert len(key_schema) == 1
    assert key_schema[0]['AttributeName'] == 'user_id'
    assert key_schema[0]['KeyType'] == 'HASH'
    attributes = schema['AttributeDefinitions']
    attr_names = [attr['AttributeName'] for attr in attributes]
    assert 'user_id' in attr_names
    assert 'email' in attr_names
    gsi = schema['GlobalSecondaryIndexes'][0]
    assert gsi['IndexName'] == 'email-index'
    assert gsi['KeySchema'][0]['AttributeName'] == 'email'
    assert schema['SSESpecification']['Enabled'] is True
    assert schema['BillingMode'] == 'PAY_PER_REQUEST'


@pytest.mark.unit
def test_schema_validation_utility():
    """
    Test the schema validation utility function.
    
    """
    valid_schema = TableSchemas.users_table_schema("test-table")
    assert TableSchemas.validate_schema(valid_schema) is True
    invalid_schema = {'TableName': 'test'}
    assert TableSchemas.validate_schema(invalid_schema) is False
    empty_key_schema = {
        'TableName': 'test',
        'KeySchema': [],
        'AttributeDefinitions': []
    }
    assert TableSchemas.validate_schema(empty_key_schema) is False
    mismatched_schema = {
        'TableName': 'test',
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [{'AttributeName': 'different_name', 'AttributeType': 'S'}]
    }
    assert TableSchemas.validate_schema(mismatched_schema) is False


@pytest.mark.unit
def test_get_all_schemas():
    """
    Test getting all schemas at once.
    
    """
    all_schemas = TableSchemas.get_all_schemas()
    assert isinstance(all_schemas, dict)
    expected_tables = ['users']
    for table_type in expected_tables:
        assert table_type in all_schemas
        assert isinstance(all_schemas[table_type], dict)
    users_schema = all_schemas['users']
    assert users_schema['TableName'] == 'voice-gateway-users'


@pytest.mark.unit
def test_example_user_structure():
    """
    Test example user structure demonstrates proper design.
    
    """
    example = TableSchemas.get_example_user_structure()
    required_fields = ['user_id', 'name', 'email', 'password_hash', 
                      'voice_embeddings', 'created_at', 'updated_at', 'is_active']
    for field in required_fields:
        assert field in example
    embeddings = example['voice_embeddings']
    assert isinstance(embeddings, list)
    assert len(embeddings) == 3
    for embedding in embeddings:
        assert 'audio_path' in embedding
        assert 'embedding_vector' in embedding
        assert 'generated_at' in embedding
        audio_path = embedding['audio_path']
        assert not audio_path.startswith('http')
        assert not audio_path.startswith('s3://')
        assert '/' in audio_path
    password_hash = example['password_hash']
    assert password_hash.startswith('$2b$')


@pytest.mark.unit
def test_schema_design_approach():
    """
    Test that schema design follows documented optimization approach.
    
    """
    schema = TableSchemas.users_table_schema("test-table")
    all_schemas = TableSchemas.get_all_schemas()
    assert len(all_schemas) == 1
    gsi = schema['GlobalSecondaryIndexes'][0]
    assert gsi['IndexName'] == 'email-index' 