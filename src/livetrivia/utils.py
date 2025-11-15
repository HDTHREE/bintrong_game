import time
import functools as fnt
import typing_extensions as tp
import importlib
import asyncio
import logging


__all__: tuple[str] = ("retry_with_backoff", "ENV_ARGS")


ENV_ARGS: tuple[str] = (
    "MAX_ATTEMPTS",
    "INITIAL_DELAY",
    "BACKOFF_FACTOR",
)


def retry_with_backoff[P: dict[str, tp.Any], R: tp.Any](
    max_attempts: int = 3,
    initial_delay: int | float = 1,
    backoff_factor: int | float = 2,
    exceptions_to_catch: tuple[Exception, ...] | Exception = (Exception,),
    logger: logging.Logger | None | bool = False,
    *args: tp.Callable[[tp.Unpack[P]], R | tp.Awaitable[R]],
) -> (
    tp.Callable[[tp.Unpack[P]], R | tp.Awaitable[R]]
    | tp.Callable[
        [tp.Callable[[tp.Unpack[P]], R | tp.Awaitable[R]]],
        tp.Callable[[tp.Unpack[P]], R | tp.Awaitable[R]],
    ]
):
    def decorator[T: tp.Callable[[tp.Unpack[P]], R | tp.Awaitable[R]]](func: T) -> T:
        def _make_sync_wrapper(func: T) -> T:
            @fnt.wraps(func)
            def wrapper(*args, **kwargs) -> R:
                delay: float = initial_delay + 0.0
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

        def _make_async_wrapper(func: T) -> T:
            @fnt.wraps(func)
            async def wrapper(*args, **kwargs) -> tp.Awaitable[R]:
                delay: float = initial_delay + 0.0
                for attempt in range(1, max_attempts + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions_to_catch as e:
                        msg: str = f"Attempt {attempt} failed: {e}. Retrying in {delay:.2f} seconds..."
                        isinstance(logger, logging.Logger) and logger.debug(msg)
                        isinstance(logger, bool) and logger and print(msg)
                        if attempt < max_attempts:
                            await asyncio.sleep(delay)
                            delay *= backoff_factor
                        else:
                            raise

            return wrapper

        try:
            is_coro = asyncio.iscoroutinefunction(func)
        except Exception as _:
            is_coro = False

        return _make_async_wrapper(func) if is_coro else _make_sync_wrapper(func)

    if args:
        *_, f = args
        return decorator(f)

    return decorator


def load_pages() -> None:
    importlib.import_module("livetrivia._fe_app.pages")


def getmod(dunder_name: str) -> str:
    *_, mod = dunder_name.split(".")
    return mod
