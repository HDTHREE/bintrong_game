from enum import StrEnum


class Status(StrEnum):
    """Status enum for tracking the state of a game or round."""

    STARTING = "starting"
    """Indicator for not having started."""
    RUNNING = "running"
    """Indicator for not having ended."""
    ENDED = "ended"
    """Indicator for having ended."""
