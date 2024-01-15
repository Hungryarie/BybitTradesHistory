import json
from json import JSONDecodeError
from app.db.utils import check_stream_exsists
from app.errors import (
    SubscriptionError,
    SubscriptionKeyError,
    SubscriptionTypeError,
    SubscriptionValueError,
)


async def check_subscription(subscription_msg: str) -> tuple[bool, str | None]:
    """check if the websocket subscription message is valid or not"""
    warning = ""
    # check if data is JSON
    try:
        json_data = json.loads(subscription_msg)
    except (TypeError, JSONDecodeError):
        raise SubscriptionTypeError(
            f"subscription should be of type JSON, got: {subscription_msg}"
        )

    # extract streamname and timestamp
    try:
        stream_name = json_data["stream"]
    except (KeyError, TypeError):
        raise SubscriptionKeyError(
            'no correct subscription to stream. Example: {"stream":"publicTrade:ETHUSDT", "timestamp":"1705248815000"}'
        )
    try:
        timestamp = json_data["timestamp"]
        if not len(timestamp) == 13:
            raise SubscriptionValueError(
                "no correct subscription with timestamp. Length of timestamp should be 13 (in milliseconds)"
            )
        if not str(timestamp).isnumeric:
            raise SubscriptionValueError(
                "no correct subscription with timestamp. Timestamp should be numeric"
            )
    except KeyError:
        warning += "No timestamp supplied. Only new data will be used"
        # raise SubscriptionKeyError('no correct subscription with timestamp. Example: {"stream":"publicTrade:ETHUSDT", "timestamp":"1705248815000"}')

    # TODO check if stream exist in Redis
    if not await check_stream_exsists(stream_name):
        # return False, f"Stream '{stream_name}' does not exist"
        raise SubscriptionError(f"Stream '{stream_name}' does not exist")

    for key in json_data.keys():
        if key not in ["stream", "timestamp"]:
            warning += f"key '{key}' will be ignored. "

    return True, warning
