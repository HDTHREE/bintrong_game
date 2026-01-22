import os
from livetrivia.utils import getenvs


def test_getenvs():
    os.environ.update({"FOO": "bar"})

    FOO = getenvs()

    assert FOO == "bar"


def test_getenvs_many():
    os.environ.update({"FOO": "a", "BAR": "b"})

    FOO, BAR = getenvs()

    assert FOO == "a"
    assert BAR == "b"


def test_getenvs_with_type():
    os.environ.update({"KEY": "4444"})

    KEY: int = getenvs()

    assert isinstance(KEY, int)
    assert KEY == 4444

    KEY: float = getenvs()

    assert isinstance(KEY, float)
    assert KEY == 4444.0


def test_getenvs_strict(): ...


def test_getenvs_logger(): ...
