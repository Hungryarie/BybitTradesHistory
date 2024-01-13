import logging
from enum import Enum


class Loglevels(Enum):
    CRITICAL = 50
    ERROR = 40
    WARNING = 30
    INFO = 20
    DEBUG = 10
    NOTSET = 0

def streaming_logger(name: str, level: int|Loglevels|str) -> logging:
    """Set up a stremodule_nameaming logger instance printing to stdout
    Args:
        name:       name of the logger that gets printed
        level:      set the debug level as threshold
    
    Returns:
        A formatted streaming logging instance"""
    logger = logging.getLogger(name)
    hdlr = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    if isinstance(level, Loglevels):
        level = logging._nameToLevel[level.name]
    elif isinstance(level, str):
        level = logging._nameToLevel[level]
    logger.setLevel(level)
    return logger