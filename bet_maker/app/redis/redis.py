import aioredis

from app.config import settings

from fastapi import Depends, Request
from aioredis import Redis


async def get_redis_global(request: Request) -> Redis:
    return request.app.state.redis