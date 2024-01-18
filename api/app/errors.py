class KeyTypeError(Exception):
    pass

class SubscriptionError(Exception):
    """base class for websocet subscription Errors"""
    pass

class SubscriptionTypeError(SubscriptionError):
    pass

class SubscriptionKeyError(SubscriptionError):
    pass

class SubscriptionValueError(SubscriptionError):
    pass

class SubscriptionTerminatedError(SubscriptionError):
    """raised when the subscription to a websocket server is not completed or aborted"""