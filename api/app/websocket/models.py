from datetime import datetime
import math
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.db.utils import check_stream_exsists
from app.errors import SubscriptionValueError


class BaseWebSocketSubscriptionModel(BaseModel):
    """Pydantic Base model for the subscription validation.
    functions `extra_async_check` and `extra_check` can be overwritten."""
    model_config = ConfigDict(extra='forbid')

    async def extra_async_check(self) -> bool:
        """extra check that will be called with the await keyword"""
        return True
    
    async def extra_check(self) -> bool:
        """extra check that will be called"""
        return True


def make_str_timestamp() -> str:
    return str(math.floor(datetime.now().timestamp() * 1000))


class TradesStreamModel(BaseWebSocketSubscriptionModel):
    """Validation model that checks the subscription to a trades stream. 
    when timestamp is not supplied it will be created with the current timestamp"""
    model_config = ConfigDict(extra='forbid')
    stream: str
    timestamp: str|None = Field(max_length=13,  min_length=13, default_factory=make_str_timestamp)
    
    async def extra_async_check(self) -> bool:
        if not await check_stream_exsists(self.stream):
            raise SubscriptionValueError(f"Stream '{0}' does not exist")
        return True
    
    @field_validator('timestamp', mode="before")
    def int_to_str(cls, v: int|str) -> str:
        v=str(v)
        return v

    @field_validator('timestamp', mode='after')
    def check_if_number(cls,  v: str) -> str:
        if not v.isnumeric():
            raise ValueError("Timestamp should be a number")
        return v
    
    
