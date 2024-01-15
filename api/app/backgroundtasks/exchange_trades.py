from datetime import datetime
import websockets
from app.db.utils import redis_conn_manager
from app.logger import streaming_logger
import os
from redis import ResponseError
import json


logger = streaming_logger(__name__, os.getenv("API_LOGGING_LEVEL", "ERROR"))


async def fetch_exchange_ws_stream(stream: str = "publicTrade.BTCUSDT") -> None:
    """Connect to the websocket stream of exchange and save to a Redis stream for further use

    Args:
        stream:     name of the stream channel to connect. reference in https://bybit-exchange.github.io/docs/v5/ws/connect"""

    stream_name = stream.replace(".", ":")

    async with redis_conn_manager() as redis_db:
        # check if stream is already connected
        ts_now = datetime.now().timestamp()*1000
        stream_info = await redis_db.xinfo_stream(stream_name)
        last_entry = int(stream_info['last-generated-id'].decode().split("-")[0])
        if abs(ts_now-last_entry) < 5000:   # TODO Hack! need proper checking if websocket connection is made. Could be that there is no trade for 5s => double connection
            logger.warning("Stream already attached, aborting...")
            return
        
        # connect to the bybit ws stream
        uri = "wss://stream.bybit.com/v5/public/linear"
        # uri = "wss://stream-testnet.bybit.com/v5/public/linear"

        try:
            async with websockets.connect(uri) as websocket_exchange:
                logger.info(f"connecting to websocket stream ({uri}) for {stream_name}")
                # suscribe to a stream/channel
                payload = {
                    "op": "subscribe",
                    "args": [
                        stream,
                    ],
                }
                await websocket_exchange.send(json.dumps(payload))

                # read response of the subscription to the exchange
                init_msg = await websocket_exchange.recv()
                logger.debug(init_msg)

                
                try:
                    info = await redis_db.xinfo_stream(stream_name)
                    last_id = info["last-entry"][0].decode("utf-8")
                except ResponseError as e:
                    logger.debug(f"key {stream_name} not found, start at zero ({e})")
                    last_id = "0-0"

                # once connected to the exchanges trade stream, fetch the messages and do something with it
                # ping_prev = datetime.now().timestamp()
                while True:
                    # send a ping one every minute or so (https://websockets.readthedocs.io/en/stable/reference/asyncio/client.html#websockets.client.WebSocketClientProtocol.ping)
                    # ts_now = datetime.now().timestamp()
                    # if ts_now - ping_prev >= 20:  # bybit docs state a recommended ping interval of 20 secs (https://bybit-exchange.github.io/docs/v5/ws/connect#how-to-send-the-heartbeat-packet)
                    #     await websocket_exchange.ping()  
                    #     ping_prev = ts_now
                    msg_q = websocket_exchange.messages
                    msg = await websocket_exchange.recv()
                    obj = json.loads(msg)
                    logger.debug(
                        f"{stream_name} queue length: {len(msg_q)}. data length:{len(obj['data'])}"
                    )

                    # send obj['data'] to redis
                    for data in obj["data"]:
                        if int(data["T"]) > int(last_id.split("-")[0]):
                            new_id = f"{data['T']}-{0}"
                        elif int(data["T"]) == int(last_id.split("-")[0]):
                            id = int(last_id.split("-")[1]) + 1
                            new_id = f"{data['T']}-{id}"
                        else:
                            pass
                        data["BT"] = int(data["BT"])  # redis doesn't accept booleans
                        await redis_db.xadd(
                            name=stream_name,
                            fields=data,
                            id=new_id,
                        )
                        last_id = new_id

        except websockets.exceptions.ConnectionClosedOK as e:
            logger.info(f"connection closed OK! {e}")
        except websockets.ConnectionClosedError as e:
            logger.error(f"connection closed due to an error! {e}")
        except Exception as e:
            logger.error(e)
            # logger.error(e.with_traceback())
            # traceback.print_exc()