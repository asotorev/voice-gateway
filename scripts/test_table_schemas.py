#!/usr/bin/env python3
"""
Test table schema definitions for Voice Gateway.
Validates optimized single table design and structure.
"""
import sys
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent.parent
sys.path.append(str(app_dir))

from app.infrastructure.databases.table_schemas import TableSchemas


def test_users_table_schema():
    """
    Test users table schema structure and validity.
    
    Returns:
        bool: True if schema is valid
    """
    print("Testing users table schema...")
    
    try:
        schema = TableSchemas.users_table_schema("test-users-table")
        
        # Validate basic structure
        assert isinstance(schema, dict), "Schema must be a dictionary"
        assert schema['TableName'] == "test-users-table", "Table name not set correctly"
        
        # Validate required DynamoDB fields
        required_fields = ['TableName', 'KeySchema', 'AttributeDefinitions']
        for field in required_fields:
            assert field in schema, f"Missing required field: {field}"
        
        # Validate key schema
        key_schema = schema['KeySchema']
        assert len(key_schema) == 1, "Users table should have exactly one key"
        assert key_schema[0]['AttributeName'] == 'user_id', "Primary key should be user_id"
        assert key_schema[0]['KeyType'] == 'HASH', "user_id should be HASH key"
        
        # Validate attribute definitions
        attributes = schema['AttributeDefinitions']
        attr_names = [attr['AttributeName'] for attr in attributes]
        assert 'user_id' in attr_names, "user_id must be in AttributeDefinitions"
        assert 'email' in attr_names, "email must be in AttributeDefinitions for GSI"
        
        # Validate GSI for email lookup
        gsi = schema['GlobalSecondaryIndexes'][0]
        assert gsi['IndexName'] == 'email-index', "Email GSI not configured correctly"
        assert gsi['KeySchema'][0]['AttributeName'] == 'email', "Email GSI key incorrect"
        
        # Validate security settings
        assert schema['SSESpecification']['Enabled'] == True, "Encryption should be enabled"
        
        # Validate development-friendly settings
        assert schema['BillingMode'] == 'PAY_PER_REQUEST', "Should use on-demand billing"
        
        print("Users table schema is valid")

        return True
        
    except Exception as e:
        print(f"Users table schema validation failed: {str(e)}")
        return False


def test_schema_validation_utility():
    """
    Test the schema validation utility function.
    
    Returns:
        bool: True if validation utility works correctly
    """
    print("Testing schema validation utility...")
    
    try:
        # Test valid schema
        valid_schema = TableSchemas.users_table_schema("test-table")
        assert TableSchemas.validate_schema(valid_schema) == True, "Valid schema should pass validation"
        
        # Test invalid schema (missing required field)
        invalid_schema = {'TableName': 'test'}  # Missing KeySchema and AttributeDefinitions
        assert TableSchemas.validate_schema(invalid_schema) == False, "Invalid schema should fail validation"
        
        # Test schema with empty KeySchema
        empty_key_schema = {
            'TableName': 'test',
            'KeySchema': [],
            'AttributeDefinitions': []
        }
        assert TableSchemas.validate_schema(empty_key_schema) == False, "Empty KeySchema should fail validation"
        
        # Test schema with mismatched attributes
        mismatched_schema = {
            'TableName': 'test',
            'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
            'AttributeDefinitions': [{'AttributeName': 'different_name', 'AttributeType': 'S'}]
        }
        assert TableSchemas.validate_schema(mismatched_schema) == False, "Mismatched attributes should fail"
        
        print("Schema validation utility works correctly")
        return True
        
    except Exception as e:
        print(f"Schema validation utility test failed: {str(e)}")
        return False


def test_get_all_schemas():
    """
    Test getting all schemas at once.
    
    Returns:
        bool: True if all schemas are returned correctly
    """
    print("Testing get all schemas utility...")
    
    try:
        all_schemas = TableSchemas.get_all_schemas()
        
        # Validate structure
        assert isinstance(all_schemas, dict), "get_all_schemas should return a dictionary"
        
        # Currently only users table is implemented (single table design)
        expected_tables = ['users']
        for table_type in expected_tables:
            assert table_type in all_schemas, f"Missing schema for {table_type}"
            assert isinstance(all_schemas[table_type], dict), f"Schema for {table_type} should be a dict"
        
        # Validate users schema specifically
        users_schema = all_schemas['users']
        assert users_schema['TableName'] == 'voice-gateway-users', "Default users table name incorrect"
        
        print("Get all schemas utility works correctly")
        print("Current implementation: Single table design with users table only")
        print("Future: Additional tables may be added if separate storage is needed")
        return True
        
    except Exception as e:
        print(f"Get all schemas test failed: {str(e)}")
        return False


def test_example_user_structure():
    """
    Test example user structure demonstrates proper design.
    
    Returns:
        bool: True if example structure is valid
    """
    print("Testing example user structure...")
    
    try:
        example = TableSchemas.get_example_user_structure()
        
        # Validate required fields
        required_fields = ['user_id', 'name', 'email', 'password_hash', 
                          'voice_embeddings', 'created_at', 'updated_at', 'is_active']
        
        for field in required_fields:
            assert field in example, f"Missing required field: {field}"
        
        # Validate voice embeddings structure
        embeddings = example['voice_embeddings']
        assert isinstance(embeddings, list), "voice_embeddings should be a list"
        assert len(embeddings) == 3, "Should have exactly 3 voice embeddings"
        
        # Validate each embedding structure
        for i, embedding in enumerate(embeddings):
            assert 'audio_path' in embedding, f"Embedding {i} missing audio_path"
            assert 'embedding_vector' in embedding, f"Embedding {i} missing embedding_vector"
            assert 'generated_at' in embedding, f"Embedding {i} missing generated_at"
            
            # Validate audio path is relative (no protocol/domain)
            audio_path = embedding['audio_path']
            assert not audio_path.startswith('http'), f"audio_path should be relative, not URL"
            assert not audio_path.startswith('s3://'), f"audio_path should not contain S3 protocol"
            assert '/' in audio_path, f"audio_path should have folder structure"
        
        # Validate password is hashed
        password_hash = example['password_hash']
        assert password_hash.startswith('$2b$'), "Password should be bcrypt hashed"
        
        print("Example user structure is valid")

        return True
        
    except Exception as e:
        print(f"Example user structure test failed: {str(e)}")
        return False


def test_schema_design_approach():
    """
    Test that schema design follows documented optimization approach.
    
    Returns:
        bool: True if design approach is properly implemented
    """
    print("Testing schema design approach...")
    
    try:
        schema = TableSchemas.users_table_schema("test-table")
        
        # Single table design verification
        all_schemas = TableSchemas.get_all_schemas()
        assert len(all_schemas) == 1, "Should implement single table design for optimal performance"
        
        # Email GSI for flexible lookups
        gsi = schema['GlobalSecondaryIndexes'][0]
        assert gsi['IndexName'] == 'email-index', "Should support email-based user lookup"
        assert gsi['Projection']['ProjectionType'] == 'ALL', "Should project all attributes for flexibility"
        
        # Security configurations
        assert schema['SSESpecification']['Enabled'] == True, "Should encrypt data at rest"
        
        # Development-friendly configurations
        assert schema['BillingMode'] == 'PAY_PER_REQUEST', "Should use on-demand billing for development"
        
        # Proper tagging
        tags = {tag['Key']: tag['Value'] for tag in schema['Tags']}
        assert 'Design' in tags, "Should tag design pattern"
        assert tags['Design'] == 'SingleTable', "Should identify single table design"
        
        print("Schema design approach is properly implemented")

        return True
        
    except Exception as e:
        print(f"Schema design approach test failed: {str(e)}")
        return False


def main():
    """
    Run all schema validation tests.
    """
    print("Voice Gateway - Table Schema Validation")
    print("=" * 45)
    print("Testing optimized single table design with relative paths")
    print()
    
    tests = [
        test_users_table_schema,
        test_schema_validation_utility,
        test_get_all_schemas,
        test_example_user_structure,
        test_schema_design_approach
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("All schema validation tests passed!")
        print("Schema optimizations verified:")
        print("  - Single table design for performance")
        print("  - Relative audio paths eliminate storage coupling")
        print("  - Granular timestamps enable precise debugging")
        print("  - Security configurations properly enabled")

        return True
    else:
        print("Some schema tests failed.")
        print("Review the errors above before proceeding.")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed with unexpected error: {str(e)}")
        sys.exit(1) 