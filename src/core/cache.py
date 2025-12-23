# src/core/cache.py
"""
Simple in-memory cache service with TTL (Time To Live) support.
"""
import time
from typing import Any, Optional, Dict, Tuple
from cachetools import TTLCache

class ResponseCache:
    def __init__(self, maxsize: int = 1000, ttl: int = 300):
        """
        Initialize the cache with a maximum size and TTL in seconds.
        
        Args:
            maxsize: Maximum number of items to store in the cache
            ttl: Time to live for cache entries in seconds (default: 5 minutes)
        """
        self.cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self.cache_hits = 0
        self.cache_misses = 0
    
    def get(self, key: str) -> Tuple[Optional[Any], bool]:
        """
        Get a value from the cache.
        
        Returns:
            Tuple of (cached_value, is_hit) where is_hit is True if the key was found.
        """
        try:
            value = self.cache[key]
            self.cache_hits += 1
            return value, True
        except KeyError:
            self.cache_misses += 1
            return None, False
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in the cache."""
        self.cache[key] = value
    
    def clear(self) -> None:
        """Clear all items from the cache."""
        self.cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
    
    def stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            'hits': self.cache_hits,
            'misses': self.cache_misses,
            'size': len(self.cache),
            'max_size': self.cache.maxsize,
            'ttl': self.cache.ttl
        }

# Global cache instance with default 5-minute TTL and max 1000 items
cache = ResponseCache(maxsize=1000, ttl=300)
