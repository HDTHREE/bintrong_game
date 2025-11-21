import os
import time
import inspect
import functools as fnt
import typing_extensions as tp
import types
import importlib
import asyncio
import itertools as itt
import logging
import pydoc as pdc


__all__: tuple[str] = ("retry_with_backoff", "ENV_ARGS")


ENV_ARGS: tuple[str] = (
    "MAX_ATTEMPTS",
    "INITIAL_DELAY",
    "BACKOFF_FACTOR",
)



def _log_wrap(msg: tp.Any, logger: logging.Logger | None | bool = False) -> None:
    isinstance(logger, logging.Logger) and logger.debug(msg)
    if isinstance(logger, bool):
        logger and print(msg)
        return
    if logger is not None:
        raise ValueError(f"Invalid logger input was provided. {msg}")


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
    backoff_factor = max(1.0, backoff_factor)

    def decorator[T: tp.Callable[[tp.Unpack[P]], R | tp.Awaitable[R]]](func: T) -> T:
        def _make_sync_wrapper(func: T) -> T:
            @fnt.wraps(func)
            def wrapper(*args, **kwargs) -> R:
                delay: float = initial_delay + 0.0
                for attempt in range(1, max_attempts + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions_to_catch as e:
                        _log_wrap(msg=f"Attempt {attempt} failed: {e}. Retrying in {delay:.2f} seconds...", logger=logger) # TODO This can be background in an async application
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
                        _log_wrap(msg=f"Attempt {attempt} failed: {e}. Retrying in {delay:.2f} seconds...", logger=logger)
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


def getenvs[T: tp.Any](strict: bool = True, logger: logging.Logger | None | bool = True) -> tuple[T, ...] | T:
    frame = inspect.currentframe()
    labels: tuple[str, ...] | str | None = None
    try:
        caller_frame: types.FrameType = frame.f_back
        lines, line_number = inspect.getsourcelines(caller_frame)
        current_line: str = lines[caller_frame.f_lineno - line_number - 1]
        assignment: str = current_line.strip()
        if "=" in assignment and "getenvs" in assignment:
            labels, call = assignment.split("=")
        if labels and ", " in labels:
            labels = tuple(labels.replace(" ", "").split(","))
        elif labels:
            labels = (labels.strip(),)
        else:
            return None
    finally:
        del frame

    if "*_" in labels:
        raise RuntimeError("Cannot call `getenv` on line with `'*_'`")
    
    labels, *types_ = tuple(zip(*map(lambda s: s.replace(" ", "").split(":"), labels)))
    if types_:
        types_, *_ = types_

    if len(labels) == 1:
        types_: tuple[type] = tuple(map(pdc.locate, types_))
    elif len(types_):
        raise AssertionError("Something went wrong")
    types_ = types_ or [str] * len(labels)
        

    values = tuple(map(os.getenv, labels))

    none_values: tuple[str, ...] = tuple(label for (value, label, type_) in zip(values, labels, types_) if value is None or type_ is None)

    if none_values:
        first, *rest = none_values
        _log_wrap(msg=f"Cannot find env variable(s): {first} {", ".join(rest)}", logger=logger)
        strict and exit(1)
    
    values = tuple(itt.starmap(lambda t, d: t(d), zip(types_, values)))

    if len(values) == 1:
        values, *_ = values
        return values
    
    return values

