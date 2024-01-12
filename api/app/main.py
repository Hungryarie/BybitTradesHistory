import asyncio
from datetime import datetime
import json
import os
from typing import Annotated
from redis import ResponseError
import redis.asyncio as redis
from fastapi import FastAPI, WebSocket, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi import Depends
import traceback
import numpy as np

from pybit.unified_trading import HTTP
import websockets
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)
hdlr = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.DEBUG)


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


# Dependency to create and manage the pybit session
def get_bybit_session() -> HTTP:
    session = HTTP(
        testnet=False,
        api_key="...",
        api_secret="...",
    )
    try:
        yield session
    finally:
        # session has no close method
        pass


async def fetch_exchange_ws_stream(stream: str = "publicTrade.BTCUSDT") -> None:
    """Connect to the websocket stream of exchange and save to a Redis stream for further use

    Args:
        stream:     name of the stream channel to connect. reference in https://bybit-exchange.github.io/docs/v5/ws/connect"""

    async with redis_conn_manager() as redis_db:
        # connect to the bybit ws stream
        uri = "wss://stream.bybit.com/v5/public/linear"
        # uri = "wss://stream-testnet.bybit.com/v5/public/linear"
        try:
            async with websockets.connect(uri) as websocket_exchange:
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

                stream_name = stream.replace(".", ":")
                try:
                    info = await redis_db.xinfo_stream(stream_name)
                    last_id = info["last-entry"][0].decode("utf-8")
                except ResponseError as e:
                    logger.debug(f"key {stream_name} not found, start at zero ({e})")
                    last_id = "0-0"

                # once connected to the exchanges trade stream, fetch the messages and do something with it
                ping_prev = datetime.now().timestamp()
                while True:
                    # send a ping one every minute or so (https://websockets.readthedocs.io/en/stable/reference/asyncio/client.html#websockets.client.WebSocketClientProtocol.ping)
                    ts_now = datetime.now().timestamp()
                    if ts_now - ping_prev >= 60:
                        await websocket_exchange.ping()
                        ping_prev = ts_now
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
            logger.info(f"connection closed! {e}")
        except Exception as e:
            logger.error(e)
            logger.error(e.with_traceback())
            traceback.print_exc()


@asynccontextmanager
async def lifespan(app: FastAPI):
    for symbol in get_symbols():
        stream = f"publicTrade.{symbol['symbol']}"
        asyncio.create_task(fetch_exchange_ws_stream(stream))

    # asyncio.create_task(fetch_exchange_ws_stream("publicTrade.ETHUSDT"))
    # asyncio.create_task(fetch_exchange_ws_stream("publicTrade.BTCSDT"))
    # asyncio.create_task(fetch_exchange_ws_stream("publicTrade.SOLUSDT"))
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/start_trades")
# def start_trades(background_tasks: BackgroundTasks, stream:str = "publicTrade.ETHUSDT",  redis_db: redis.Redis = Depends(get_redis_conn)):
def start_trades(
    background_tasks: BackgroundTasks, stream: str = "publicTrade.ETHUSDT"
):
    background_tasks.add_task(
        fetch_exchange_ws_stream,
        stream=stream,
    )  # redis_db=redis_db )
    return {"message": "start with fetching trade info in the background"}


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/api/test_redis")
async def test_redis(redis_db: Annotated[redis.Redis, Depends(get_redis_conn)]):
    await redis_db.set("test", json.dumps({"hoi": "doei"}))
    output = await redis_db.get("test")
    return output


@app.get("/api/test_redis_last")
async def test_redis_last(
    stream_name: str = "publicTrade:ETHUSDT",
    start_timestamp: int = 1704718590000,
    end_timestamp: int | str = "+",
    limit: int = 100,
    redis_db: redis.Redis = Depends(get_redis_conn),
):
    """get the latest records from the stream"""
    result_raw = await redis_db.xrevrange(
        stream_name, max=end_timestamp, min=start_timestamp, count=limit
    )
    # sort with regard to the timestamp AND the suffix
    result_sorted = sorted(
        result_raw, key=lambda x: (int(x[0].split(b"-")[0]), int(x[0].split(b"-")[1]))
    )
    np_array = np.array(result_sorted)
    np_result = np_array[:, 1]  # Extract the second element onwards from each row
    list_of_dicts = [dict(entry) for entry in np_result]
    return list_of_dicts


@app.get("/api/orderbook")
async def orderbook(symbol: str = "BTCUSDT", pybit_session=Depends(get_bybit_session)):
    orderbook = pybit_session.get_orderbook(category="linear", symbol=symbol)
    return orderbook


@app.get("/api/symbols/")
def get_symbols():
    # TODO inplement database
    # types:
    #    inverse – Inverse Contracts;
    #    linear  – USDT Perpetual, USDC Contracts;
    #    spot    – Spot Trading;
    #    option  – USDC Options;
    symbols = []
    symbols.append({"symbol": "BTCUSDT", "type": "linear"})
    symbols.append({"symbol": "ETHUSDT", "type": "linear"})
    symbols.append({"symbol": "SOLUSDT", "type": "linear"})
    symbols.append({"symbol": "OPUSDT", "type": "linear"})
    symbols.append({"symbol": "ARBUSDT", "type": "linear"})
    return symbols


@app.get("/api/connection_info}")
def get_connectioninfo(request: Request):
    client_host = request.client.host
    server = request.base_url.__str__().lstrip("http://").rstrip("/")
    return {"client_host": client_host, "server_adress": server}


@app.websocket("/ws_trades")
async def websocket_endpoint3(websocket: WebSocket):
    # based on https://fastapi.tiangolo.com/advanced/websockets/
    # and https://websockets.readthedocs.io/en/stable/reference/asyncio/client.html

    # accept the websocket request from the user
    await websocket.accept()

    # connect to the bybit ws stream
    uri = "wss://stream.bybit.com/v5/public/linear"
    # uri = "wss://stream-testnet.bybit.com/v5/public/linear"
    async with websockets.connect(uri) as websocket_exchange:
        # suscribe to a stream/channel
        payload = {
            "op": "subscribe",
            "args": [
                # "orderbook.1.BTCUSDT",
                "publicTrade.BTCUSDT",
                # "orderbook.1.ETHUSDT"
            ],
        }
        await websocket_exchange.send(json.dumps(payload))

        try:
            # read response of the subscription to the exchange
            msg = await websocket_exchange.recv()

            # send to 'our' internal websocket clients
            await websocket.send_text(f"initial message was: {msg}")

            ts_prev = datetime.now().timestamp()
            # once connected to the exchanges trade stream, fetch the messages and do something with it
            while True:
                # send a ping one every minute or so (https://websockets.readthedocs.io/en/stable/reference/asyncio/client.html#websockets.client.WebSocketClientProtocol.ping)
                ts_now = datetime.now().timestamp()
                if ts_now - ts_prev >= 60:
                    await websocket_exchange.ping()
                    ts_prev = ts_now
                msg_q = websocket_exchange.messages
                msg = await websocket_exchange.recv()
                obj = json.loads(msg)
                print(f"queue length: {len(msg_q)}. data length:{len(obj['data'])}")
                await websocket.send_text(f"Message data was: {obj['data']}")
        except websockets.exceptions.ConnectionClosedOK as e:
            print(f"connection closed! {e}")


# use double {{ }} to escape the string formatting =https://stackoverflow.com/questions/5466451/how-do-i-escape-curly-brace-characters-in-a-string-while-using-format-or
html = """
<!DOCTYPE html>
<html>
    <head>
        <title>trades</title>
    </head>
    <body>
        <h1>WebSocket live trades</h1>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket('ws://{}/ws_trades');
            ws.onmessage = function(event) {{
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
                console.log(message)
            }};
        </script>
    </body>
</html>
"""


@app.get("/ws_test")
async def ws_test(request: Request):
    con_info = get_connectioninfo(request)
    return HTMLResponse(html.format(con_info["server_adress"]))
