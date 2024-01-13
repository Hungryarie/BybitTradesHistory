import re
from app.logger import Loglevels, streaming_logger


def test_streaminglogger_threshold(capsys):
    """test if the logger adheres to the hierarchy and skips messages below the threshold"""
    logger_name = "LOGGERNAME"
    logger_msg = "test message"
    logger = streaming_logger(logger_name, Loglevels.WARNING)

    # should print critical test message
    logger.critical(logger_msg)
    captured = capsys.readouterr()
    assert len(captured.err) > 0

    # should print error test message
    logger.error(logger_msg)
    captured = capsys.readouterr()
    assert len(captured.err) > 0

    # should print warning test message
    logger.warning(logger_msg)
    captured = capsys.readouterr()
    assert len(captured.err) > 0

    # shouldn't print info test message
    logger.info(logger_msg)
    captured = capsys.readouterr()
    assert captured.err == ""

    # shouldn't print debug test message
    logger.debug(logger_msg)
    captured = capsys.readouterr()
    assert captured.err == ""


def test_streaminglogger_output(capsys):
    """check if the logger prints the correct logger name, level and message"""
    logger_name = "LOGGERNAME"
    logger_msg = "test message"
    logger_level = Loglevels.WARNING
    pattern = f".* - {logger_name} - {logger_level.name} - {logger_msg}\\n"
    logger = streaming_logger(logger_name, logger_level)

    # print and captures warning test message
    logger.warning(logger_msg)
    captured = capsys.readouterr()
    match = re.fullmatch(pattern, captured.err)
    print(f"match: {match}")
    print(f"outp: {captured.err}")
    assert len(captured.err) == match.endpos
    assert match.pos == 0
