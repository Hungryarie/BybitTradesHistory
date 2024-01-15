from datetime import datetime
import json
import os
from fastapi import APIRouter, WebSocketDisconnect, WebSocket
from websockets import ConnectionClosedOK
from websockets.exceptions import ConnectionClosed

from app.db.consumer.trades import trades_consumer
from app.errors import (
    SubscriptionError,
)
from app.logger import streaming_logger
from app.utils import check_subscription


router = APIRouter(prefix="")
logger = streaming_logger(__name__, os.getenv("API_LOGGING_LEVEL", "ERROR"))


@router.websocket("/trades")
async def websocket_trades(websocket: WebSocket):
    """provides a websocket endpoint for realtime trades from the exchanges 
    that are cached, so also old trades can be fetched"""
    # based on https://fastapi.tiangolo.com/advanced/websockets/

    # accept the websocket request from the user
    await websocket.accept()
    try:
        await websocket.send_text("connection established!")
        # wait for the subscription
        while True:
            received = await websocket.receive()
            try:
                valid, msg = await check_subscription(received["text"])
                if valid:
                    # stream:str = "publicTrade:ETHUSDT"
                    # start_timestamp:int = 1705248815000
                    # start_timestamp = 1705214500000
                    subscripton: dict = json.loads(received["text"])
                    stream = subscripton["stream"]
                    start_timestamp = subscripton.get(
                        "timestamp", int(datetime.now().timestamp() * 1000)
                    )
                    await websocket.send_text(
                        f"subscribed to {stream} with timestamp {start_timestamp}"
                    )
                    if msg:
                        await websocket.send_text(f"ignoring: {msg}")
                    break
            except SubscriptionError as e:
                await websocket.send_text(f"subscribtion error: {e}")
            except Exception as e:
                logger.error(f"unknown error, closing websocket connection: {e}")
                await websocket.send_text(
                    f"unknown error, closing websocket connection: {e}"
                )
                await websocket.close()
                return

        # subscribe to the redis stream
        async for trade in trades_consumer(stream, start_timestamp):
            await websocket.send_text(f"Message data was: {trade}")

            # # break for test
            # if i>10:
            #     await websocket.close()
            #     return
            # i+=1
    except (WebSocketDisconnect, ConnectionClosed, ConnectionClosedOK) as e:
        logger.info(f"connection closed: {e}")
        # await websocket.close()  NOT needed because we are already disconnected
