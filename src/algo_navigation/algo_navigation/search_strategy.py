from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence


@dataclass(frozen=True)
class SearchArea:
    """矩形搜索区域，单位为米，坐标系由调用方保证。"""

    min_x: float
    max_x: float
    min_y: float
    max_y: float

    def validate(self) -> None:
        if self.max_x <= self.min_x:
            raise ValueError("search area max_x must be greater than min_x")
        if self.max_y <= self.min_y:
            raise ValueError("search area max_y must be greater than min_y")


@dataclass(frozen=True)
class NavigationGoal:
    """导航策略输出的二维目标点，yaw 单位为弧度。"""

    label: str
    x: float
    y: float
    yaw: float = 0.0


def normalize_angle(angle_rad: float) -> float:
    """Normalize angle to [-pi, pi)."""

    return (angle_rad + math.pi) % (2.0 * math.pi) - math.pi


def _lanes(minimum: float, maximum: float, spacing: float) -> List[float]:
    if spacing <= 0.0:
        raise ValueError("lane spacing must be positive")

    values = []
    current = minimum
    while current < maximum:
        values.append(round(current, 6))
        current += spacing
    if not values or not math.isclose(values[-1], maximum):
        values.append(maximum)
    return values


def generate_lawnmower_goals(
    area: SearchArea,
    lane_spacing_m: float,
    *,
    label_prefix: str = "search",
) -> List[NavigationGoal]:
    """Generate a deterministic boustrophedon search path for a rectangle.

    The path starts at the lower-left corner, sweeps along x, then advances in y.
    It is intentionally simple: obstacle avoidance remains Nav2/local planner work.
    """

    area.validate()
    lanes = _lanes(area.min_y, area.max_y, lane_spacing_m)
    goals: List[NavigationGoal] = []
    for index, y in enumerate(lanes):
        if index % 2 == 0:
            start_x, end_x, yaw = area.min_x, area.max_x, 0.0
        else:
            start_x, end_x, yaw = area.max_x, area.min_x, math.pi

        goals.append(
            NavigationGoal(
                label=f"{label_prefix}_{index:02d}_start",
                x=start_x,
                y=y,
                yaw=yaw,
            )
        )
        goals.append(
            NavigationGoal(
                label=f"{label_prefix}_{index:02d}_end",
                x=end_x,
                y=y,
                yaw=yaw,
            )
        )
    return goals


def goal_by_index(goals: Sequence[NavigationGoal], index: int) -> NavigationGoal:
    if not goals:
        raise ValueError("goals must not be empty")
    return goals[index % len(goals)]


def nearest_goal_index(
    goals: Sequence[NavigationGoal],
    *,
    robot_x: float,
    robot_y: float,
) -> int:
    if not goals:
        raise ValueError("goals must not be empty")

    best_index = 0
    best_distance = float("inf")
    for index, goal in enumerate(goals):
        distance = math.hypot(goal.x - robot_x, goal.y - robot_y)
        if distance < best_distance:
            best_index = index
            best_distance = distance
    return best_index


def approach_goal_for_target(
    *,
    target_x: float,
    target_y: float,
    standoff_m: float,
    label: str = "selected_target_approach",
) -> NavigationGoal:
    """Generate a standoff pose facing the target from the frame origin.

    This is a geometry-only first pass. It assumes the target pose is already in
    a navigation-consumable frame and does not account for obstacles.
    """

    if standoff_m < 0.0:
        raise ValueError("standoff distance must be non-negative")

    distance = math.hypot(target_x, target_y)
    if distance <= 1e-6:
        return NavigationGoal(label=label, x=target_x, y=target_y, yaw=0.0)

    approach_distance = max(0.0, distance - standoff_m)
    unit_x = target_x / distance
    unit_y = target_y / distance
    goal_x = unit_x * approach_distance
    goal_y = unit_y * approach_distance
    yaw = math.atan2(target_y - goal_y, target_x - goal_x)
    return NavigationGoal(label=label, x=goal_x, y=goal_y, yaw=normalize_angle(yaw))


def labels(goals: Iterable[NavigationGoal]) -> List[str]:
    return [goal.label for goal in goals]
