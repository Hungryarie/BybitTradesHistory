from app.db.utils import redis_conn_manager
from app.logger import streaming_logger
import os


logger = streaming_logger(__name__, os.getenv("API_LOGGING_LEVEL", "ERROR"))


def make_data_package(type: str, content: str|dict) -> dict:
    assert type in ['info', 'data'], "only types 'info' and 'data' are allowed"
    try:
        content = {k.decode(): v.decode() for k, v in content.items()}
    except AttributeError:
        pass
    if type=="info":
        return {"type":"info", "msg":content}
    else:
        return {"type":"data", "data":content}


async def trades_consumer(stream: str, start_timestamp: int) -> dict:
    err = None
    try:
        yield make_data_package("info", "start message")
   
        async with redis_conn_manager() as redis_db:
        
            yield make_data_package("info", "connected to redis")
            yield make_data_package("info", "fetch cached data")
            last_key = start_timestamp
            try:
                while True:
                    # fetch in chuncks of 10000
                    init_messages = await redis_db.xrange(stream, last_key, count=10000 )
                    for message in init_messages:
                        yield make_data_package("data", message[1])
                    last_key = init_messages[-1][0].decode()
            except IndexError:
                last_key = '$'  # special redis key that only new data will be supplied
            yield make_data_package("info", "wait for new data")
            while True:
                messages = await redis_db.xread({stream: last_key}, count=10000, block=10000)
                if not messages:
                    logger.warn("got no incomming messages from redis in 10seconds. Error?")
                    yield make_data_package("info", "got no incomming messages from redis in 10seconds. Error?")
                    continue
                stream_msgs = messages[0]  # TODO make sure the correct stream is the first one
                for message in stream_msgs[1]:
                    yield make_data_package("data", message[1])
                # set last key
                if stream_msgs[1]:
                    last_key = message[0].decode()
    except Exception as e:
        logger.error(f"unknow error in `trades_consumer`: {e}")
        err = e
    finally:
        if err:
            logger.error(f"closing the trades_consumer, due to error: {err}")
        else:
            logger.info("closing the trades_consumer")
