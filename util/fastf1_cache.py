"""Project-wide FastF1 cache setup."""

from pathlib import Path

import fastf1

CACHE_DIR = Path(__file__).resolve().parents[1] / "cache"

def enable_fastf1_cache():
    """Enable FastF1's on-disk cache and return the cache directory."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))
    return CACHE_DIR
