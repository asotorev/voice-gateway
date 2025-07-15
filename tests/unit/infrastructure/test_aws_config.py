#!/usr/bin/env python3
"""
Test AWS configuration abstraction layer.
Assumes prerequisites are met (run test_db_connection.py first).
"""
import sys
from pathlib import Path
import pytest

# Add the app directory to Python path
app_dir = Path(__file__).parent.parent
sys.path.append(str(app_dir))

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
def test_health_check():
    try:
        health = aws_config.health_check()
        dynamodb_status = health.get('dynamodb', {})
        status = dynamodb_status.get('status', 'unknown')
        assert status == 'healthy', f"Health check failed: {dynamodb_status.get('error', 'Unknown error')}"
    except Exception as e:
        pytest.fail(f"Health check test failed: {str(e)}")


@pytest.mark.unit
def test_table_reference():
    try:
        table_name = infra_settings.users_table_name
        table = aws_config.get_table(table_name)
        assert table.table_name == table_name
    except Exception as e:
        pytest.fail(f"Table reference test failed: {str(e)}")