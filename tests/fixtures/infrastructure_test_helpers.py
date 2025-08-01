#!/usr/bin/env python3
"""
Shared test helpers for infrastructure tests.
Contains common utilities for DynamoDB and other infrastructure services.
"""
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.infrastructure.services.health_checks import health_check_service


class InfrastructureTestHelpers:
    """Shared test helpers for infrastructure tests."""
    
    @staticmethod
    def check_infrastructure() -> bool:
        """Check if infrastructure services (DynamoDB, etc.) are available."""
        try:
            health = health_check_service.check_all_services()
            dynamodb_health = health.get('dynamodb', {})
            
            if dynamodb_health.get('status') != 'healthy':
                print("ERROR: DynamoDB infrastructure not available")
                print("Please ensure services are running: docker-compose up -d")
                print(f"DynamoDB Status: {dynamodb_health}")
                return False
            
            print("Infrastructure health check: PASSED")
            return True
            
        except Exception as e:
            print(f"ERROR: Cannot check infrastructure health: {e}")
            return False