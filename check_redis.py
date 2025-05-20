import redis
import sys
from app.config import Config

def check_redis_connection():
    """Check Redis connection and configuration."""
    try:
        # Get Redis URL from config
        redis_url = Config.RATELIMIT_STORAGE_URL
        
        # Create Redis client
        r = redis.from_url(redis_url)
        
        # Test connection
        r.ping()
        print("✅ Redis connection successful!")
        
        # Test rate limiter storage
        test_key = "test_rate_limit"
        r.set(test_key, "test_value")
        value = r.get(test_key)
        r.delete(test_key)
        
        if value == b"test_value":
            print("✅ Redis rate limiter storage working!")
        else:
            print("❌ Redis rate limiter storage test failed!")
            
    except redis.ConnectionError as e:
        print("❌ Redis connection failed!")
        print(f"Error: {str(e)}")
        print("\nPlease check:")
        print("1. Redis server is running")
        print("2. Redis URL is correct in your .env file")
        print("3. Redis port is accessible")
        sys.exit(1)
    except Exception as e:
        print("❌ Unexpected error!")
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    check_redis_connection() 