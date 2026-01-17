from enum import IntEnum


class OutputMode(IntEnum):
    TEXT = 0
    IMAGE = 1


R6_OUTPUT_MODE: OutputMode = OutputMode.TEXT
R6_ANALYSE: bool = False
