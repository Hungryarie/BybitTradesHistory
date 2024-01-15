from contextlib import asynccontextmanager
import redis.asyncio as redis
from redis import ResponseError
import os
import logging
from app.errors import KeyTypeError
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


async def sort_stream(raw_data: list) -> list:
    """Sort the stream based on the timestamp and then on its suffix, (not lexicographically).

    Args:
        raw_data:       raw redis stream output
    Returns:
        sorted data on the timestamp-suffix key

    Example:
        given the raw data:
        ```
        [(b'1705072083138-0', {...}), (b'1705072083137-10', {...}),
        (b'1705072083137-11', {...}), (b'1705072083137-9', {...})]
        ```
        The function sorts on the timestamps first and than according
        to the suffix after the timestamp.

        so the result would be:
        ```
        [(b'1705072083137-9', {...}), (b'1705072083137-10', {...}),
         (b'1705072083137-11', {...}),  (b'1705072083138-0', {...})]
        ```
    """
    split_str = "-"
    if isinstance(raw_data[0][0], bytes):
        split_str = b"-"
    try:
        result_sorted = sorted(
            raw_data,
            key=lambda x: (
                int(x[0].split(split_str)[0]),
                int(x[0].split(split_str)[1]),
            ),
        )
    except TypeError:
        logger.warn("Type of the timestamp representation is not consistent")
        raise KeyTypeError("Type of the timestamp representation is not consistent")
    return result_sorted

async def check_stream_exsists(stream_name: str) -> bool: 
    """check if the redis steam exists"""
    try:
        async with redis_conn_manager() as redis_db:
            info = await redis_db.xinfo_stream(stream_name)
            # last_id = info["last-entry"][0].decode("utf-8")
            logger.debug(f"stream info: {stream_name}: {info}")
            logger.info(f"stream {stream_name} exists, return True")

            return True
    except ResponseError as e:
        logger.warn(f"stream {stream_name} does not exists, return False")
        return False