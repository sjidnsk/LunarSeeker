from enum import IntEnum


class MissionPhase(IntEnum):
    IDLE = 0
    READY = 1
    DEPARTURE = 2
    EXPLORATION = 3
    APPROACH = 4
    SAMPLE = 5
    RETURN = 6
    UNLOAD = 7
    COMPLETE = 8
    FAULT = 255


MISSION_TIME_LIMIT_SEC = 600
MAX_TOTAL_MASS_KG = 30
MAX_START_BOX_MM = (800, 800, 800)
RUN_COUNT_PER_ROUND = 2

SCORE_RULES = {
    "leave_base": 10,
    "collect_target": 10,
    "return_with_target": 10,
    "unload_target": 20,
}

