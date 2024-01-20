import json
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from websockets import ConnectionClosedError, ConnectionClosedOK
from app.db.consumer.trades import trades_consumer
from app.logger import streaming_logger
from app.websocket.models import TradesStreamModel
from app.websocket.subscribe import check_subscription_call


router = APIRouter(prefix="")

logger = streaming_logger(__name__, os.getenv("API_LOGGING_LEVEL", "ERROR"))
logger.setLevel(10)  # set to debug


@router.websocket("/trades")
async def websocket_trades(websocket: WebSocket):
    """provides a websocket endpoint for realtime trades from the exchanges
    that are cached, so also old trades can be fetched"""
    # based on https://fastapi.tiangolo.com/advanced/websockets/

    # accept the websocket request from the user
    await websocket.accept()
    try:
        subscription = await check_subscription_call(websocket, TradesStreamModel)

        # subscribe to the redis stream
        async for trade in trades_consumer(subscription["stream"], subscription["timestamp"]):            
            await websocket.send_text(json.dumps(trade))

    except (WebSocketDisconnect, ConnectionClosedOK, ConnectionClosedError) as e:
        logger.info(f"connection closed: {e}")
        websocket.client_state = WebSocketState.DISCONNECTED
    finally:
        await handle_websocket_closing(websocket)
    

async def handle_websocket_closing(websocket: WebSocket):
        """handles the closing of the websocket connection"""
        logger.debug(f"App state:{websocket.application_state}, client state: {websocket.client_state}")
        if websocket.client_state == WebSocketState.CONNECTED and websocket.application_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_text(f"goodbye... connecion will be terminated{0}")
                await websocket.close()
                logger.info("finished, connection is closed")
            except (ConnectionClosedError, ConnectionClosedOK) as e:
                logger.info(f"could not disconnect, client already disconnected, error: {e}")
        elif websocket.client_state == WebSocketState.DISCONNECTED:
            logger.info("finished, client is already disconnected")
        else:
            logger.info("finished, connection is closed")
        pass
