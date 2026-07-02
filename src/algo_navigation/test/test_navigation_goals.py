import math
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from algo_navigation.navigation_goals import (
    GOAL_BASE_EXIT,
    GOAL_FRONTIER,
    GOAL_TARGET_APPROACH,
    BlacklistedGoal,
    approach_goal_from_robot,
    goal_label_for_phase,
    goal_type_for_label,
    is_goal_blacklisted,
    prune_blacklist,
)
from algo_navigation.search_strategy import NavigationGoal


def test_phase_and_goal_type_mapping_match_navigation_status_contract():
    assert goal_label_for_phase("departure") == "base_exit"
    assert goal_label_for_phase("exploration") == "frontier_exploration"
    assert goal_type_for_label("base_exit") == GOAL_BASE_EXIT
    assert goal_type_for_label("frontier_00") == GOAL_FRONTIER
    assert goal_type_for_label("selected_target_approach") == GOAL_TARGET_APPROACH


def test_approach_goal_from_robot_keeps_standoff_and_faces_target():
    goal = approach_goal_from_robot(
        robot_x=1.0,
        robot_y=0.0,
        target_x=3.0,
        target_y=0.0,
        standoff_m=0.5,
    )

    assert goal.x == pytest.approx(2.5)
    assert goal.y == pytest.approx(0.0)
    assert goal.yaw == pytest.approx(0.0)


def test_approach_goal_from_robot_handles_diagonal_target():
    goal = approach_goal_from_robot(
        robot_x=0.0,
        robot_y=0.0,
        target_x=1.0,
        target_y=1.0,
        standoff_m=0.5,
    )

    assert math.hypot(1.0 - goal.x, 1.0 - goal.y) == pytest.approx(0.5)
    assert goal.yaw == pytest.approx(math.pi / 4.0)


def test_blacklist_filters_nearby_goals_until_expiry():
    blacklist = [BlacklistedGoal(x=1.0, y=1.0, expires_at_sec=20.0)]

    assert is_goal_blacklisted(
        NavigationGoal("frontier_00", 1.1, 1.1),
        blacklist,
        now_sec=10.0,
        radius_m=0.5,
    )
    assert not is_goal_blacklisted(
        NavigationGoal("frontier_01", 2.0, 2.0),
        blacklist,
        now_sec=10.0,
        radius_m=0.5,
    )
    assert prune_blacklist(blacklist, now_sec=21.0) == []
