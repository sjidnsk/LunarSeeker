import math
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from algo_navigation.search_strategy import (
    SearchArea,
    approach_goal_for_target,
    generate_lawnmower_goals,
    goal_by_index,
    labels,
    nearest_goal_index,
    normalize_angle,
)


def test_generate_lawnmower_goals_sweeps_back_and_forth():
    goals = generate_lawnmower_goals(
        SearchArea(min_x=1.0, max_x=3.0, min_y=-0.5, max_y=0.5),
        lane_spacing_m=0.5,
    )

    assert labels(goals) == [
        "search_00_start",
        "search_00_end",
        "search_01_start",
        "search_01_end",
        "search_02_start",
        "search_02_end",
    ]
    assert [(goal.x, goal.y) for goal in goals] == [
        (1.0, -0.5),
        (3.0, -0.5),
        (3.0, 0.0),
        (1.0, 0.0),
        (1.0, 0.5),
        (3.0, 0.5),
    ]
    assert goals[0].yaw == 0.0
    assert goals[2].yaw == math.pi


def test_generate_lawnmower_goals_validates_area_and_spacing():
    with pytest.raises(ValueError):
        generate_lawnmower_goals(SearchArea(1.0, 1.0, 0.0, 1.0), 0.5)

    with pytest.raises(ValueError):
        generate_lawnmower_goals(SearchArea(0.0, 1.0, 0.0, 1.0), 0.0)


def test_goal_by_index_wraps_sequence():
    goals = generate_lawnmower_goals(SearchArea(0.0, 1.0, 0.0, 0.5), 0.5)

    assert goal_by_index(goals, 0).label == "search_00_start"
    assert goal_by_index(goals, len(goals)).label == "search_00_start"


def test_nearest_goal_index():
    goals = generate_lawnmower_goals(SearchArea(0.0, 2.0, 0.0, 1.0), 1.0)

    assert nearest_goal_index(goals, robot_x=1.9, robot_y=0.1) == 1


def test_approach_goal_for_target_keeps_standoff_and_faces_target():
    goal = approach_goal_for_target(target_x=2.0, target_y=0.0, standoff_m=0.5)

    assert goal.x == pytest.approx(1.5)
    assert goal.y == pytest.approx(0.0)
    assert goal.yaw == pytest.approx(0.0)


def test_approach_goal_for_target_handles_diagonal_target():
    goal = approach_goal_for_target(target_x=1.0, target_y=1.0, standoff_m=0.5)

    assert math.hypot(1.0 - goal.x, 1.0 - goal.y) == pytest.approx(0.5)
    assert goal.yaw == pytest.approx(math.pi / 4.0)


def test_normalize_angle():
    assert normalize_angle(3.0 * math.pi) == pytest.approx(-math.pi)
