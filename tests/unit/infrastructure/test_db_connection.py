#!/usr/bin/env python3
"""
Verifies DynamoDB Local connectivity and table operations.
Connects to local DynamoDB instance and validates configuration.
"""
import pytest
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from app.infrastructure.config.infrastructure_settings import infra_settings


@pytest.mark.asyncio
@pytest.mark.unit
async def test_dynamodb_connection():
    try:
        dynamodb = boto3.resource(
            'dynamodb',
            endpoint_url=infra_settings.dynamodb_endpoint_url,
            region_name=infra_settings.aws_region,
            aws_access_key_id='fakeMyKeyId',
            aws_secret_access_key='fakeSecretAccessKey'
        )
        tables = list(dynamodb.tables.all())
        assert isinstance(tables, list)
        test_table_name = "connectivity-test-temp"
        test_table = dynamodb.create_table(
            TableName=test_table_name,
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        test_table.wait_until_exists()
        assert test_table.table_status == 'ACTIVE'
        test_table.delete()
    except NoCredentialsError:
        pytest.fail("AWS credentials not configured properly")
    except ClientError as e:
        pytest.fail(f"DynamoDB ClientError: {e.response.get('Error', {}).get('Message', str(e))}")
    except Exception as e:
        pytest.fail(f"Unexpected error: {str(e)}")