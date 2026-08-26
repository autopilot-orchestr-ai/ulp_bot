from enum import Enum


class Route(str, Enum):
    END = "end"
    LEAD = "lead"
    CHAT = "chat"
