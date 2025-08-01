#!/usr/bin/env python3
"""
Test for health checks service.
"""
import pytest

from app.infrastructure.config.infrastructure_settings import infra_settings


@pytest.mark.unit
def test_settings_access():
    """Test that settings are accessible."""
    assert infra_settings.environment is not None
    assert infra_settings.aws_region is not None
    assert isinstance(infra_settings.use_local_dynamodb, bool)
    assert isinstance(infra_settings.use_local_s3, bool)


@pytest.mark.unit
def test_comprehensive_health_checks(health_service):
    """Test comprehensive health checks work."""
    comprehensive_results = health_service.check_all_services()
    assert isinstance(comprehensive_results, dict)
    assert len(comprehensive_results) > 0
    
    for service, status in comprehensive_results.items():
        assert isinstance(service, str)
        assert isinstance(status, dict)
        assert 'status' in status
        assert status['status'] in ['healthy', 'unhealthy']


@pytest.mark.unit
def test_basic_connectivity_checks(health_service):
    """Test basic connectivity checks work."""
    basic_results = health_service.check_basic_connectivity()
    assert isinstance(basic_results, dict)
    assert len(basic_results) > 0
    
    for service, status in basic_results.items():
        assert isinstance(service, str)
        assert isinstance(status, dict)
        assert 'status' in status
        assert status['status'] in ['healthy', 'unhealthy']

