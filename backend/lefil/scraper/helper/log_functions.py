import logging


def add_logger(name: str,
               default_handler: logging.Handler, default_console_handler: logging.Handler | None = None,
               debug: bool = False, default_log_level: int | str = logging.INFO) -> logging.Logger:
    """
    Add a specified logger name to the project
    :param name: The name of the logger to add
    :param default_handler: The default handler
    :param default_console_handler: The default console handler
    :param debug: When in debug mode, console handler is added and log level is set to DEBUG
    :param default_log_level: The default log level
    :return: The logger updated
    """
    current_logger = logging.getLogger(name)
    if debug:
        current_logger.setLevel(logging.DEBUG)
        if default_console_handler is not None:
            current_logger.addHandler(default_console_handler)
    else:
        current_logger.setLevel(default_log_level)
    current_logger.addHandler(default_handler)
    return current_logger