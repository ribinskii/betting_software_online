

from aioredis import Redis
from fastapi import Request


async def get_redis_global(request: Request) -> Redis:
    return request.app.state.redis