import os
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from websockets import ConnectionClosedError
from app.errors import (
    SubscriptionError,
    SubscriptionKeyError,
    SubscriptionTerminatedError,
    SubscriptionTypeError,
)
from app.logger import streaming_logger
from app.websocket.models import BaseWebSocketSubscriptionModel


logger = streaming_logger(__name__, os.getenv("API_LOGGING_LEVEL", "ERROR"))
logger.setLevel(10)  # set to debug


async def check_subscription_call(websocket_conn: WebSocket, validation_model: BaseWebSocketSubscriptionModel):
    """Check the subscription messages to the websocket server,
    when valid returns the message as a dict.

    Args:
        websocket_conn:         The (accepted) websocket connection
        validation_model:       The validation model. Should have at least a async
                                `extra_async_check` method.

    Returns:
        Upon receiving a valid input message (JSON), returns the message as a dict.
        Otherwise let the client retry.

    Raises:
        Upon disconnection raises "WebSocketDisconnect"
    """
    try:
        await websocket_conn.send_text("connection established!")
    except WebSocketDisconnect as e:
        raise e
    except ConnectionClosedError as e:
        raise WebSocketDisconnect(f"Client (got) disconnected at start of subscription process. Error: {e}")

    # wait for the subscription message
    while True:
        try:
            received = await websocket_conn.receive()  # TODO add a timeout on this receive method
            if received["type"] == "websocket.disconnect" and received["code"] == 1012:  # service restarted:
                logger.info(f"Received code {received['code']}. Service restarted, can not reconnect automaticly...")
                raise SubscriptionTerminatedError("client got disconnected before subscription was finished.")
            elif received["type"] == "websocket.disconnect":
                logger.debug(f"Received code {received['code']}. Client disconnected before subscripting...")
                raise SubscriptionTerminatedError("client (got) disconnected before subscription finishes")
            subscripton = await check_subscription_model(received["text"], validation_model)
            await subscripton.extra_async_check()  # will raise  SubscriptionValueError
            subscripton_dict = subscripton.model_dump()
            await websocket_conn.send_text(f"subscribed with parameters {subscripton_dict}")
            return subscripton_dict
        except SubscriptionTerminatedError as e:
            # terminate and don't send any msgs anymore
            raise WebSocketDisconnect(f"Client disconnected mid subscription process. Error: {e}")
        except SubscriptionError as e:
            await websocket_conn.send_text(f"subscribtion error: {e}")
        except Exception as e:
            logger.error(f"unknown error in `handle_subscription_call`, closing websocket connection: {e}")
            await websocket_conn.send_text(f"unknown error in, closing websocket connection: {e}")
            # await websocket_conn.close()
            raise WebSocketDisconnect(f"Client will be actively disconected mid subscription process. Error: {e}")


async def check_subscription_model(
    subscription_msg: str, validation_model: BaseWebSocketSubscriptionModel
) -> BaseWebSocketSubscriptionModel:  # tuple[bool, str | None]:
    """Check if the websocket subscription message is valid or not.

    Args:
        ubscription_msg:   a string representation of the supplied message
                            from the websocket client
        validation_model:   The validation model. Should have at least a async
                            `extra_async_check` method.

    Returns:
        An instance of the validation_model


    Raises:
        SubscriptionError:  When a unknown error arrises
        SubscriptionKeyError:   Wehen a key is missing
        SubscriptionTypeError:  When the type is not JSON
    """

    try:
        valid_model = validation_model.model_validate_json(subscription_msg)
        return valid_model
    except ValidationError as e:
        logger.debug(e)
        error = e.errors()[0]  # only look for the first error
        if error["type"] == "missing":
            raise SubscriptionKeyError(f"error, {error['msg']}: {error['loc']}")
        elif error["type"] == "json_invalid":
            raise SubscriptionTypeError(f"subscription should be of type JSON, got: {subscription_msg}")
        else:
            raise SubscriptionError(f"error: {e}")

    except Exception as e:
        logger.error(f"got unknown error in `check_subscription_model`: {e}")
        raise SubscriptionError(f"error: {e}")
