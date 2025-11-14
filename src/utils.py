import typing as tp
import time
import functools as fnt
import logging


__all__: tuple[str] = ("retry_with_backoff",)


ENV_ARGS: tuple[str] = (
    "MAX_ATTEMPTS",
    "INITIAL_DELAY",
    "BACKOFF_FACTOR",
)


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: int = 1,
    backoff_factor: int = 2,
    exceptions_to_catch: tuple[Exception, ...] | Exception = (Exception,),
    logger: logging.Logger | None | bool = False,
):
    def decorator(func: tp.Callable):
        @fnt.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions_to_catch as e:
                    msg: str = f"Attempt {attempt} failed: {e}. Retrying in {delay:.2f} seconds..."
                    isinstance(logger, logging.Logger) and logger.debug(msg)
                    isinstance(logger, bool) and logger and print(msg)
                    if attempt < max_attempts:
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        raise

        return wrapper

    return decorator
