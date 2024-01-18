import os
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError
from app.errors import (
    SubscriptionError,
    SubscriptionKeyError,
    SubscriptionTerminatedError,
    SubscriptionTypeError,
)
from app.logger import streaming_logger
from app.websocket.models import BaseWebSocketSubscriptionModel

logger = streaming_logger(__name__, os.getenv("API_LOGGING_LEVEL", "ERROR"))

async def check_subscription_call(
    websocket_conn: WebSocket, validation_model: BaseWebSocketSubscriptionModel
):
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
        # wait for the subscription
        while True:
            received = (
                await websocket_conn.receive()
            )  # TODO add a timeout on this receive method
            try:
                if (
                    received["type"] == "websocket.disconnect"
                    and received["code"] == 1012
                ):  # service restarted:
                    logger.info(
                        f"Received code {received['code']}. Service restarted, can not reconnect automaticly..."
                    )
                    raise SubscriptionTerminatedError(
                        "client got disconnected before subscription was finished."
                    )
                elif received["type"] == "websocket.disconnect":
                    logger.debug(
                        f"Received code {received['code']}. Client disconnected before subscripting..."
                    )
                    raise SubscriptionTerminatedError(
                        "client (got) disconnected before subscription finishes"
                    )
                subscripton = await check_subscription_model(
                    received["text"], validation_model
                )
                await (
                    subscripton.extra_async_check()
                )  # will raise  SubscriptionValueError
                subscripton_dict = subscripton.model_dump()

                # check if stream exist in Redis
                # if not await check_stream_exsists(subscripton_dict['stream']):
                #     raise SubscriptionError(f"Stream '{subscripton_dict['stream']}' does not exist")
                # if valid:
                # subscripton: dict = json.loads(received["text"])
                # stream = subscripton["stream"]

                # start_timestamp = subscripton.get(
                #     "timestamp", int(datetime.now().timestamp() * 1000)
                # )
                await websocket_conn.send_text(
                    # f"subscribed to {stream} with timestamp {start_timestamp}"
                    f"subscribed with parameters {subscripton_dict}"
                )
                # if msg:
                #     await websocket_conn.send_text(f"ignoring: {msg}")
                # break
                return subscripton_dict  # out of the subscription without errors
            except SubscriptionTerminatedError as e:
                # terminate and don't send any msgs anymore
                raise WebSocketDisconnect(
                    f"Client disconnected mid subscription process. Error: {e}"
                )
            except SubscriptionError as e:
                await websocket_conn.send_text(f"subscribtion error: {e}")
            except Exception as e:
                logger.error(f"unknown error, closing websocket connection: {e}")
                await websocket_conn.send_text(
                    f"unknown error, closing websocket connection: {e}"
                )
                # await websocket_conn.close()
                raise WebSocketDisconnect(
                    f"Client will be actively disconected mid subscription process. Error: {e}"
                )
    # except websockets.ConnectionClosed as e:
    #     raise e
    except WebSocketDisconnect as e:
        raise e
    except Exception as e:
        logger.error(
            f"unexpected error in `handle_subscription_call`, client should connect again to proceed?: {e}"
        )
        raise WebSocketDisconnect(
            f"unexpected error in `handle_subscription_call`: {e}"
        )


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
            raise SubscriptionTypeError(
                f"subscription should be of type JSON, got: {subscription_msg}"
            )
        else:
            raise SubscriptionError(f"error: {e}")

    except Exception as e:
        logger.error(f"got unknown error: {e}")
        raise SubscriptionError(f"error: {e}")

    # try:
    #     json_data: dict = json.loads(subscription_msg)
    #     json_data.get("invalid_key", "default")  # will fail when this is a list
    # except (AttributeError, TypeError, JSONDecodeError):
    #     raise SubscriptionTypeError(
    #         f"subscription should be of type JSON, got: {subscription_msg}"
    #     )

    # try:
    #     valid_dict = signature(**json_data)
    #     return valid_dict.dict()
    # except ValidationError as e:
    #     error = e.errors()[0]  # only look for the first error
    #     if error["type"] == "missing":
    #         raise SubscriptionKeyError(f"error, {error['msg']}: {error['loc']}")
    #     else:
    #         raise SubscriptionError(f"error: {e}")
    # except Exception as e:
    #     raise SubscriptionError(f"error: {e}")

    # # extract streamname and timestamp
    # try:
    #     stream_name = json_data["stream"]
    # except (KeyError, TypeError):
    #     raise SubscriptionKeyError(
    #         'no correct subscription to stream. Example: {"stream":"publicTrade:ETHUSDT", "timestamp":"1705248815000"}'
    #     )
    # try:
    #     timestamp = json_data["timestamp"]
    #     if not len(timestamp) == 13:
    #         raise SubscriptionValueError(
    #             "no correct subscription with timestamp. Length of timestamp should be 13 (in milliseconds)"
    #         )
    #     if not str(timestamp).isnumeric:
    #         raise SubscriptionValueError(
    #             "no correct subscription with timestamp. Timestamp should be numeric"
    #         )
    # except KeyError:
    #     warning += "No timestamp supplied. Only new data will be used"
    #     # raise SubscriptionKeyError('no correct subscription with timestamp. Example: {"stream":"publicTrade:ETHUSDT", "timestamp":"1705248815000"}')

    # TODO check if stream exist in Redis
    # if not await check_stream_exsists(stream_name):
    #     # return False, f"Stream '{stream_name}' does not exist"
    #     raise SubscriptionError(f"Stream '{stream_name}' does not exist")

    # for key in json_data.keys():
    #     if key not in ["stream", "timestamp"]:
    #         warning += f"key '{key}' will be ignored. "

    # return True, warning
