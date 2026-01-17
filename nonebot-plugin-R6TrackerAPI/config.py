from enum import IntEnum
from pathlib import Path


class OutputMode(IntEnum):
    TEXT = 0
    IMAGE = 1


R6_OUTPUT_MODE: OutputMode = OutputMode.TEXT
R6_ANALYSE: bool = False

PLAYERS_FILE = Path("players.yaml")