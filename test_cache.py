#!/usr/bin/env python3
"""
Simple test script to verify the caching system works correctly.
Run this to test the cache implementation.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.utils.cache import cache_manager, cached
from app.config import get_settings

async def test_cache_operations():
    """Test basic cache operations."""
    print("🧪 Testing Cache System")
    print("=" * 50)
    
    # Test basic set/get operations
    test_key = "test_key"
    test_value = {"message": "Hello, Cache!", "number": 42}
    
    print(f"1. Setting cache key: {test_key}")
    success = await cache_manager.set(test_key, test_value, 60)
    print(f"   Set result: {success}")
    
    print(f"2. Getting cache key: {test_key}")
    retrieved = await cache_manager.get(test_key)
    print(f"   Retrieved: {retrieved}")
    
    if retrieved == test_value:
        print("   ✅ Cache set/get test PASSED")
    else:
        print("   ❌ Cache set/get test FAILED")
        return False
    
    # Test cache decorator
    print("\n3. Testing cache decorator")
    
    @cached("test_operation", ttl=60)
    async def expensive_operation(x: int, y: str) -> dict:
        """Simulate an expensive operation."""
        await asyncio.sleep(0.1)  # Simulate work
        return {"result": x * 2, "text": y.upper(), "expensive": True}
    
    # First call (should be slow)
    print("   First call (should be slow)...")
    start_time = asyncio.get_event_loop().time()
    result1 = await expensive_operation(21, "hello")
    first_call_time = asyncio.get_event_loop().time() - start_time
    print(f"   Result: {result1}")
    print(f"   Time: {first_call_time:.3f}s")
    
    # Second call (should be fast - from cache)
    print("   Second call (should be fast - from cache)...")
    start_time = asyncio.get_event_loop().time()
    result2 = await expensive_operation(21, "hello")
    second_call_time = asyncio.get_event_loop().time() - start_time
    print(f"   Result: {result2}")
    print(f"   Time: {second_call_time:.3f}s")
    
    if result1 == result2 and second_call_time < first_call_time:
        print("   ✅ Cache decorator test PASSED")
    else:
        print("   ❌ Cache decorator test FAILED")
        return False
    
    # Test cache stats
    print("\n4. Cache statistics")
    stats = cache_manager.get_stats()
    print(f"   Backend: {stats['backend']}")
    print(f"   Hits: {stats['hits']}")
    print(f"   Misses: {stats['misses']}")
    print(f"   Hit Rate: {stats['hit_rate']}%")
    
    # Test cache health
    print("\n5. Cache health check")
    health_pattern = "ai_cache:*:test_operation:*"
    cleared = await cache_manager.clear_pattern(health_pattern)
    print(f"   Cleared {cleared} test cache entries")
    
    print("\n🎉 All cache tests completed successfully!")
    return True

def test_configuration():
    """Test cache configuration."""
    print("\n⚙️ Testing Cache Configuration")
    print("=" * 50)
    
    settings = get_settings()
    
    print(f"Cache Enabled: {settings.CACHE_ENABLED}")
    print(f"Cache Backend: {settings.CACHE_BACKEND}")
    print(f"Redis URL: {settings.REDIS_URL}")
    
    print("\nTTL Configuration:")
    for operation, ttl in settings.cache_ttl_config.items():
        print(f"  {operation}: {ttl}s")
    
    return True

async def main():
    """Main test function."""
    print("🚀 Confida Cache System Test")
    print("=" * 60)
    
    # Test configuration
    config_ok = test_configuration()
    
    # Test cache operations
    cache_ok = await test_cache_operations()
    
    if config_ok and cache_ok:
        print("\n✅ All tests PASSED! Cache system is working correctly.")
        return 0
    else:
        print("\n❌ Some tests FAILED! Please check the cache implementation.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
