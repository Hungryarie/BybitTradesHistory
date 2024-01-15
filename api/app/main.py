import asyncio
from datetime import datetime
import json
import os
from typing import Annotated

import redis.asyncio as redis
from fastapi import FastAPI, WebSocket, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi import Depends
import numpy as np
from pybit.unified_trading import HTTP
import websockets
from contextlib import asynccontextmanager
from app.backgroundtasks.exchange_trades import fetch_exchange_ws_stream
from app.db.utils import get_redis_conn, sort_stream
from app.logger import streaming_logger
from app.routers import ws


logger = streaming_logger(__name__, os.getenv("API_LOGGING_LEVEL", "ERROR"))


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
app.include_router(ws.router)


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
    result_sorted = await sort_stream(result_raw)
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
            var ws = new WebSocket('ws://{}/trades');
            ws.onmessage = function(event) {{
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
                console.log(message)
            }};
            function sendMessage(event) {{
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }}
        </script>
    </body>
</html>
"""


@app.get("/ws_test")
async def ws_test(request: Request):
    """endpoint for debugging/testing the websocket stream, makes a websocket connection to ws://localhost:port/trades"""
    con_info = get_connectioninfo(request)
    return HTMLResponse(html.format(con_info["server_adress"]))
