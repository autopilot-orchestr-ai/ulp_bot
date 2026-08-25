from enum import Enum


class Route(str, Enum):
    END = "end"
    INFO = "info"
    LEAD = "lead"
    HUMAN = "human"
    OFF_TOPIC = "off_topic"
    CALL_TIMING = "call_timing"