#!/usr/bin/env python3
"""
Test script for GSI performance.
Tests password uniqueness validation.
"""
import sys
import time
import asyncio
from pathlib import Path
import pytest

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.services.password_service import PasswordService
from app.adapters.repositories.dynamodb_user_repository import DynamoDBUserRepository
from app.infrastructure.databases.dynamodb_setup import DynamoDBSetup

dynamodb_setup = DynamoDBSetup()

@pytest.mark.performance
def test_gsi_table_info(user_repository):
    table_info = dynamodb_setup.get_table_info(user_repository.table_name)
    assert 'status' in table_info
    assert 'item_count' in table_info
    assert 'gsi_count' in table_info
    assert 'has_password_gsi' in table_info
    if table_info.get('gsi_details'):
        for gsi in table_info['gsi_details']:
            assert 'name' in gsi
            assert 'status' in gsi
            assert 'projection' in gsi
    assert table_info.get('has_password_gsi', False), "Password hash GSI not available. Run migration if needed."

@pytest.mark.performance
def test_gsi_performance(user_repository, password_service):
    table_info = dynamodb_setup.get_table_info(user_repository.table_name)
    assert table_info.get('has_password_gsi', False), "Password hash GSI not available. Run migration if needed."
    test_passwords = [
        "biblioteca tortuga",
        "castillo mariposa",
        "medicina jirafa",
        "computadora hospital",
        "escalera rinoceronte"
    ]
    results = []
    for password in test_passwords:
        password_hash = password_service.hash_password(password)
        start_time = time.time()
        exists_gsi = asyncio.get_event_loop().run_until_complete(user_repository.check_password_hash_exists(password_hash))
        gsi_time = (time.time() - start_time) * 1000
        results.append(gsi_time)
        assert isinstance(exists_gsi, bool)
    avg_gsi = sum(results) / len(results)
    assert avg_gsi < 500, f"GSI method is too slow: {avg_gsi:.1f}ms average" 