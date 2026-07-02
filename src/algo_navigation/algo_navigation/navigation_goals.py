from __future__ import annotations

import math
from dataclasses import dataclass

try:
    from .search_strategy import NavigationGoal, normalize_angle
except ImportError:  # Allows direct importlib loading in unit tests.
    from algo_navigation.search_strategy import NavigationGoal, normalize_angle


GOAL_NONE = 0
GOAL_BASE_EXIT = 1
GOAL_FRONTIER = 2
GOAL_TARGET_APPROACH = 3
GOAL_BASE_RETURN = 4
GOAL_SAMPLE_DROP_ZONE = 5
GOAL_HOLD_POSITION = 6

PHASE_GOALS = {
    "ready": "standby",
    "departure": "base_exit",
    "exploration": "frontier_exploration",
    "approach": "selected_target",
    "sample": "hold_position",
    "return": "base_return",
    "unload": "sample_drop_zone",
    "complete": "mission_complete",
    "fault": "safe_stop",
}

FIXED_GOAL_POSES = {
    "standby": (0.0, 0.0, 0.0),
    "base_exit": (0.8, 0.0, 0.0),
    "frontier_waiting_for_map": (0.0, 0.0, 0.0),
    "hold_position": (1.2, 0.22, 0.0),
    "base_return": (0.2, 0.0, 0.0),
    "sample_drop_zone": (-0.3, 0.0, 0.0),
    "mission_complete": (0.0, 0.0, 0.0),
    "safe_stop": (0.0, 0.0, 0.0),
}

GOAL_TYPE_BY_LABEL = {
    "base_exit": GOAL_BASE_EXIT,
    "base_return": GOAL_BASE_RETURN,
    "sample_drop_zone": GOAL_SAMPLE_DROP_ZONE,
    "hold_position": GOAL_HOLD_POSITION,
}


@dataclass(frozen=True)
class BlacklistedGoal:
    x: float
    y: float
    expires_at_sec: float


def goal_label_for_phase(phase_name: str) -> str:
    return PHASE_GOALS.get(phase_name, "standby")


def goal_type_for_label(label: str) -> int:
    if label.startswith("frontier_"):
        return GOAL_FRONTIER
    if label.startswith("selected_target"):
        return GOAL_TARGET_APPROACH
    return GOAL_TYPE_BY_LABEL.get(label, GOAL_NONE)


def fixed_goal_for_label(label: str) -> NavigationGoal | None:
    pose = FIXED_GOAL_POSES.get(label)
    if pose is None:
        return None
    x, y, _ = pose
    return NavigationGoal(label=label, x=x, y=y, yaw=0.0)


def approach_goal_from_robot(
    *,
    robot_x: float,
    robot_y: float,
    target_x: float,
    target_y: float,
    standoff_m: float,
    label: str = "selected_target_approach",
) -> NavigationGoal:
    if standoff_m < 0.0:
        raise ValueError("standoff distance must be non-negative")

    dx = target_x - robot_x
    dy = target_y - robot_y
    distance = math.hypot(dx, dy)
    if distance <= 1e-6:
        return NavigationGoal(label=label, x=target_x, y=target_y, yaw=0.0)

    approach_distance = max(0.0, distance - standoff_m)
    unit_x = dx / distance
    unit_y = dy / distance
    goal_x = robot_x + unit_x * approach_distance
    goal_y = robot_y + unit_y * approach_distance
    yaw = math.atan2(target_y - goal_y, target_x - goal_x)
    return NavigationGoal(label=label, x=goal_x, y=goal_y, yaw=normalize_angle(yaw))


def is_goal_blacklisted(
    goal: NavigationGoal,
    blacklist: list[BlacklistedGoal],
    *,
    now_sec: float,
    radius_m: float,
) -> bool:
    for item in blacklist:
        if item.expires_at_sec <= now_sec:
            continue
        if math.hypot(goal.x - item.x, goal.y - item.y) <= radius_m:
            return True
    return False


def prune_blacklist(
    blacklist: list[BlacklistedGoal],
    *,
    now_sec: float,
) -> list[BlacklistedGoal]:
    return [item for item in blacklist if item.expires_at_sec > now_sec]
