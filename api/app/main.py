from datetime import datetime
import json
import os
import redis
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi import Depends
from pybit.unified_trading import HTTP
import websockets


# Dependency to create and manage the Redis connection
def get_redis_conn() -> redis.Redis: 
    redis_conn = redis.Redis(host=os.environ.get("REDIS_HOST"), port=os.environ.get("REDIS_PORT"))
    try:
        yield redis_conn
    finally:
        redis_conn.close()


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
    

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/api/test_redis")
def test_redis(redis_db: redis.Redis = Depends(get_redis_conn)):
    redis_db.set("test", json.dumps({"hoi": "doei"}))
    output = redis_db.get("test")
    return output


@app.get('/api/orderbook')
async def orderbook(symbol:str="BTCUSDT", pybit_session = Depends(get_bybit_session)):
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
    symbols.append({'symbol':'BTCUSDT', 'type':'linear'})
    symbols.append({'symbol':'ETHUSDT', 'type':'linear'})
    symbols.append({'symbol':'SOLUSDT', 'type':'linear'})
    symbols.append({'symbol':'OPUSDT', 'type':'linear'})
    symbols.append({'symbol':'ARBUSDT', 'type':'linear'})
    return symbols


@app.get("/api/connection_info}")
def get_connectioninfo(request: Request):
    client_host = request.client.host
    server = request.base_url.__str__().lstrip("http://").rstrip("/")
    return {"client_host": client_host, 'server_adress':server}


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
                ]
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
        except  websockets.exceptions.ConnectionClosedOK as e:
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
