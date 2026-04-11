"""
asyncpg connection pool — infrastructure layer.

Responsibilities:
- Hold the single pool instance (singleton).
- Expose init/close for lifecycle management (called from main.py).
- Expose get_pool() for logic.py to acquire connections.
"""

import asyncpg

from config import settings

_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(settings.database_url)


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Pool not initialized — call init_pool() first")
    return _pool
