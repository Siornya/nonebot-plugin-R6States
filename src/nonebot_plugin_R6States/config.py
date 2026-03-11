from enum import IntEnum
from pathlib import Path

from pydantic import BaseModel


class Config(BaseModel):
    r6data_api_key: str | None = None

    class OutputMode(IntEnum):
        TEXT = 0
        IMAGE = 1

    R6_OUTPUT_MODE: OutputMode = OutputMode.TEXT
    R6_ANALYSE: bool = False

    PLAYERS_FILE: Path = Path("players.yaml")
