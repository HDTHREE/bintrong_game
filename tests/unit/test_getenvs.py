import logging
import os

import pytest
from livetrivia.utils import getenvs


def _clear():
    os.environ["FOO"] = ""
    del os.environ["FOO"]


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


def test_getenvs_strict_exits():
    _clear()

    FOO: None = None
    with pytest.raises(SystemExit, match=r"1"):
        FOO = getenvs(strict=True)

    assert FOO is None


def test_getenvs_strict_pass():
    _clear()

    FOO: None = None
    FOO = getenvs(strict=False)

    assert FOO is None


def test_getenvs_logger_print(capsys):
    _clear()

    FOO = getenvs(strict=False, logger=True)

    assert "Cannot find env variable(s): FOO \n" == capsys.readouterr().out
    assert FOO is None


def test_getenvs_logger_false(capsys):
    _clear()

    FOO = getenvs(strict=False, logger=False)

    assert "" == capsys.readouterr().out
    assert FOO is None


logger: logging.Logger = logging.getLogger(__name__)


def test_getenvs_logger_object(caplog):
    _clear()

    caplog.set_level(logging.DEBUG)

    FOO = getenvs(strict=False, logger=logger)

    assert "Cannot find env variable(s): FOO" in caplog.text
    assert FOO is None
