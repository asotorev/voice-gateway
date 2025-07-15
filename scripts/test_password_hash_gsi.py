#!/usr/bin/env python3
"""
Test script for GSI performance.
Tests password uniqueness validation.
"""
import sys
import time
import asyncio
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.services.password_service import PasswordService
from app.adapters.repositories.dynamodb_user_repository import DynamoDBUserRepository
from app.infrastructure.databases.dynamodb_setup import dynamodb_setup


class GSIOptimizationTester:
    """Test GSI performance."""
    
    def __init__(self):
        """Initialize tester."""
        self.user_repository = DynamoDBUserRepository()
        self.password_service = PasswordService()
    
    async def test_gsi_performance(self):
        """Test GSI password hash existence performance."""
        print("Testing GSI Performance")
        print("=" * 40)
        
        # Check if GSI is available
        table_info = dynamodb_setup.get_table_info(self.user_repository.table_name)
        has_gsi = table_info.get('has_password_gsi', False)
        
        if not has_gsi:
            print("Password hash GSI not available")
            print("Run migration: python scripts/migrate_password_gsi.py")
            return False
        
        print("Password hash GSI is available")
        print()
        
        # Test candidate passwords
        test_passwords = [
            "biblioteca tortuga",
            "castillo mariposa", 
            "medicina jirafa",
            "computadora hospital",
            "escalera rinoceronte"
        ]
        
        results = []
        
        for i, password in enumerate(test_passwords):
            print(f"Test {i+1}/5: Checking '{password}'")
            password_hash = self.password_service.hash_password(password)
            
            # Test GSI method (O(1))
            start_time = time.time()
            try:
                exists_gsi = await self.user_repository.check_password_hash_exists(password_hash)
                gsi_time = (time.time() - start_time) * 1000  # Convert to ms
                results.append(gsi_time)
                print(f"  GSI method: {gsi_time:.1f}ms (exists: {exists_gsi})")
            except Exception as e:
                print(f"  GSI method failed: {e}")
                return False
            print()
        
        # Calculate statistics
        avg_gsi = sum(results) / len(results)
        print("Performance Summary:")
        print("=" * 30)
        print(f"GSI method (O(1)):   {avg_gsi:.1f}ms average")
        print(f"User count tested:   {len(results)} passwords")
        print()
        return True
    

    
    async def test_gsi_table_info(self):
        """Test GSI table information retrieval."""
        print("Testing GSI Table Information")
        print("=" * 35)
        
        table_info = dynamodb_setup.get_table_info(self.user_repository.table_name)
        
        print(f"Table: {self.user_repository.table_name}")
        print(f"Status: {table_info.get('status', 'Unknown')}")
        print(f"Items: {table_info.get('item_count', 0)}")
        print(f"GSI Count: {table_info.get('gsi_count', 0)}")
        print(f"Has Password GSI: {table_info.get('has_password_gsi', False)}")
        print()
        
        if table_info.get('gsi_details'):
            print("GSI Details:")
            for gsi in table_info['gsi_details']:
                print(f"  - {gsi['name']}: {gsi['status']} ({gsi['projection']})")
        
        return table_info.get('has_password_gsi', False)


async def main():
    """Run all GSI optimization tests."""
    print("Voice Gateway - GSI Optimization Testing")
    print("=" * 55)
    print()
    
    tester = GSIOptimizationTester()
    
    tests = [
        ("GSI Table Info", tester.test_gsi_table_info),
        ("GSI Performance", tester.test_gsi_performance)
    ]
    
    results = {}
    for test_name, test_func in tests:
        print()
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"ERROR in {test_name}: {e}")
            results[test_name] = False
    
    # Summary
    print()
    print("=" * 55)
    print("GSI Optimization Test Results:")
    print("-" * 40)
    
    passed_tests = 0
    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"  {test_name}: {status}")
        if passed:
            passed_tests += 1
    
    print(f"\nTests passed: {passed_tests}/{len(tests)}")
    
    if passed_tests == len(tests):
        print("\nGSI is working perfectly!")
        print("Global Secondary Indexes are properly configured and performing well")
        return True
    else:
        print(f"\n{len(tests) - passed_tests} test(s) failed")
        print("Check GSI setup and try migration if needed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 