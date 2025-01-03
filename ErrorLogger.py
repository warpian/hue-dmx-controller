import logging
from functools import wraps
from typing import Callable, Any

class ErrorLogger:
    logger: logging.Logger

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger()

    def __call__(self, func: Callable) -> Callable:
        """
        Make the class instance callable to use it as a decorator.
        :param func: The function to wrap in try-except with error logging.
        :return: The wrapped function.
        """
        @wraps(func)
        def wrapped(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"An error occurred in {func.__name__}: {e}", exc_info=True)
                raise
        return wrapped
