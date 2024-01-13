from contextlib import asynccontextmanager
import redis.asyncio as redis
import os
import logging
from app.logger import streaming_logger


logger = streaming_logger("REDIS", logging.INFO)


async def get_redis_conn() -> redis.Redis:
    """Dependency for endpoints to create and manage the Redis connection"""
    redis_conn = redis.Redis(
        host=os.environ.get("REDIS_HOST"), port=os.environ.get("REDIS_PORT")
    )
    try:
        yield redis_conn
    except ConnectionError as e:
        logger.error(f"Unable to connect to Redis: {e}")
        raise e
    finally:
        await redis_conn.aclose()


@asynccontextmanager
async def redis_conn_manager():
    """Connection manager for inside background tasks"""
    redis_conn = redis.Redis(
        host=os.environ.get("REDIS_HOST"), port=os.environ.get("REDIS_PORT")
    )
    try:
        yield redis_conn
    except ConnectionError as e:
        logger.error(f"Unable to connect to Redis: {e}")
        raise e
    finally:
        await redis_conn.aclose()