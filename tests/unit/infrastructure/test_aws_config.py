#!/usr/bin/env python3
"""
Test AWS configuration abstraction layer.
Assumes prerequisites are met (run test_db_connection.py first).
"""
import pytest
from app.infrastructure.config.aws_config import aws_config
from app.infrastructure.config.infrastructure_settings import infra_settings


@pytest.mark.unit
def test_aws_config_layer():
    try:
        dynamodb = aws_config.dynamodb_resource
        tables = list(dynamodb.tables.all())
        assert isinstance(tables, list)
    except Exception as e:
        pytest.fail(f"AWS config abstraction test failed: {str(e)}")


@pytest.mark.unit
def test_aws_config_connectivity():
    """Test that AWS config can establish basic connectivity."""
    try:
        # Test DynamoDB connectivity
        dynamodb = aws_config.dynamodb_resource
        tables = list(dynamodb.tables.all())
        assert isinstance(tables, list), "Should be able to list tables"
        
        # Test S3 connectivity
        s3 = aws_config.s3_client
        buckets = s3.list_buckets()
        assert 'Buckets' in buckets, "Should be able to list buckets"
        
    except Exception as e:
        pytest.fail(f"AWS config connectivity test failed: {str(e)}")


@pytest.mark.unit
def test_table_reference():
    try:
        table_name = infra_settings.users_table_name
        table = aws_config.get_table(table_name)
        assert table.table_name == table_name
    except Exception as e:
        pytest.fail(f"Table reference test failed: {str(e)}")