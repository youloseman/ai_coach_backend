"""
Redis caching utility for AI Triathlon Coach.
Provides caching for Strava activities, training zones, and user profiles.
"""
import json
import os
from typing import Optional, Any

import redis
from redis.connection import ConnectionPool
from config import logger


class RedisCache:
    """Redis cache manager with connection pooling"""
    
    def __init__(self):
        # Try different environment variable formats that Railway might use
        self.redis_url = self._get_redis_url()
        self.enabled = bool(self.redis_url)
        
        if self.enabled:
            try:
                # Parse Redis URL and create connection pool
                self.pool = ConnectionPool.from_url(
                    self.redis_url,
                    decode_responses=True,
                    max_connections=10,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                self.client = redis.Redis(connection_pool=self.pool)
                # Test connection
                self.client.ping()
                logger.info("redis_connected", url=self.redis_url.split("@")[0] + "@***")
            except Exception as e:
                logger.warning("redis_connection_failed", error=str(e))
                self.enabled = False
                self.client = None
        else:
            # Log available Redis-related env vars for debugging (without exposing secrets)
            redis_env_vars = {
                "REDIS_URL": "set" if os.getenv("REDIS_URL") else "not set",
                "REDIS_HOST": "set" if os.getenv("REDIS_HOST") else "not set",
                "REDIS_PORT": os.getenv("REDIS_PORT", "not set"),
                "REDIS_PASSWORD": "set" if os.getenv("REDIS_PASSWORD") else "not set",
            }
            logger.info(
                "redis_disabled",
                message="Redis URL not found in environment variables, caching disabled",
                env_vars=redis_env_vars
            )
            self.client = None
    
    def _get_redis_url(self) -> Optional[str]:
        """
        Get Redis URL from environment variables.
        Supports multiple formats that Railway and other platforms might use.
        """
        # Try REDIS_URL first (standard format)
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            return redis_url
        
        # Try Railway-specific format: REDIS_HOST, REDIS_PORT, REDIS_PASSWORD
        redis_host = os.getenv("REDIS_HOST")
        redis_port = os.getenv("REDIS_PORT", "6379")
        redis_password = os.getenv("REDIS_PASSWORD")
        
        if redis_host:
            # Build Redis URL from components
            if redis_password:
                return f"redis://:{redis_password}@{redis_host}:{redis_port}"
            else:
                return f"redis://{redis_host}:{redis_port}"
        
        # Try other common formats
        redis_url = os.getenv("REDISCLOUD_URL") or os.getenv("REDISTOGO_URL")
        if redis_url:
            return redis_url
        
        return None
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled or not self.client:
            return None
        
        try:
            value = self.client.get(key)
            if value:
                logger.debug("cache_hit", key=key)
                return json.loads(value)
            logger.debug("cache_miss", key=key)
            return None
        except Exception as e:
            logger.error("cache_get_error", key=key, error=str(e))
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """Set value in cache with TTL"""
        if not self.enabled or not self.client:
            return False
        
        try:
            serialized = json.dumps(value, default=str)
            self.client.setex(key, ttl_seconds, serialized)
            logger.debug("cache_set", key=key, ttl=ttl_seconds)
            return True
        except Exception as e:
            logger.error("cache_set_error", key=key, error=str(e))
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.enabled or not self.client:
            return False
        
        try:
            self.client.delete(key)
            logger.debug("cache_delete", key=key)
            return True
        except Exception as e:
            logger.error("cache_delete_error", key=key, error=str(e))
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self.enabled or not self.client:
            return 0
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                deleted = self.client.delete(*keys)
                logger.info("cache_pattern_delete", pattern=pattern, count=deleted)
                return deleted
            return 0
        except Exception as e:
            logger.error("cache_pattern_delete_error", pattern=pattern, error=str(e))
            return 0
    
    def clear_all(self) -> bool:
        """Clear all cache (use with caution!)"""
        if not self.enabled or not self.client:
            return False
        
        try:
            self.client.flushdb()
            logger.warning("cache_cleared", message="All cache cleared")
            return True
        except Exception as e:
            logger.error("cache_clear_error", error=str(e))
            return False


# Global cache instance
cache = RedisCache()

# Export redis_client for direct access
redis_client = cache.client if cache.enabled else None


# Cache key generators
def strava_activities_key(user_id: int, weeks: int) -> str:
    """Generate cache key for Strava activities"""
    return f"strava:activities:user:{user_id}:weeks:{weeks}"


def training_zones_key(user_id: int) -> str:
    """Generate cache key for training zones"""
    return f"training:zones:user:{user_id}"


def user_profile_key(user_id: int) -> str:
    """Generate cache key for user profile"""
    return f"user:profile:{user_id}"


def athlete_profile_key(user_id: int) -> str:
    """Generate cache key for athlete profile"""
    return f"athlete:profile:user:{user_id}"


def weekly_plan_key(user_id: int, week_start: str) -> str:
    """Generate cache key for weekly plan"""
    return f"plan:weekly:user:{user_id}:week:{week_start}"


# Cache TTL constants (in seconds)
TTL_STRAVA_ACTIVITIES = 30 * 60  # 30 minutes
TTL_TRAINING_ZONES = 24 * 60 * 60  # 24 hours
TTL_USER_PROFILE = 60 * 60  # 1 hour
TTL_ATHLETE_PROFILE = 60 * 60  # 1 hour
TTL_WEEKLY_PLAN = 15 * 60  # 15 minutes


# Helper functions for common cache operations
def cache_strava_activities(user_id: int, weeks: int, activities: list) -> bool:
    """Cache Strava activities"""
    key = strava_activities_key(user_id, weeks)
    return cache.set(key, activities, TTL_STRAVA_ACTIVITIES)


def get_cached_strava_activities(user_id: int, weeks: int) -> Optional[list]:
    """Get cached Strava activities"""
    key = strava_activities_key(user_id, weeks)
    return cache.get(key)


def invalidate_strava_cache(user_id: int) -> int:
    """Invalidate all Strava cache for user"""
    pattern = f"strava:activities:user:{user_id}:*"
    return cache.delete_pattern(pattern)


def cache_training_zones(user_id: int, zones: dict) -> bool:
    """Cache training zones"""
    key = training_zones_key(user_id)
    return cache.set(key, zones, TTL_TRAINING_ZONES)


def get_cached_training_zones(user_id: int) -> Optional[dict]:
    """Get cached training zones"""
    key = training_zones_key(user_id)
    return cache.get(key)


def cache_user_profile(user_id: int, profile: dict) -> bool:
    """Cache user profile"""
    key = user_profile_key(user_id)
    return cache.set(key, profile, TTL_USER_PROFILE)


def get_cached_user_profile(user_id: int) -> Optional[dict]:
    """Get cached user profile"""
    key = user_profile_key(user_id)
    return cache.get(key)


def invalidate_user_cache(user_id: int) -> None:
    """Invalidate all cache for user"""
    cache.delete(user_profile_key(user_id))
    cache.delete(training_zones_key(user_id))
    cache.delete(athlete_profile_key(user_id))
    invalidate_strava_cache(user_id)

