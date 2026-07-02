import math
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from algo_navigation.navigation_visualization import (
    Marker,
    area_center,
    area_outline_points,
    build_navigation_marker_array,
    goals_to_path,
    pose_stamped_from_goal,
)
from algo_navigation.search_strategy import (
    NavigationGoal,
    SearchArea,
)


def _target(
    *,
    target_id="target_01",
    x=2.0,
    y=0.0,
    frame_id="odom",
    selected=True,
):
    pose = SimpleNamespace(
        header=SimpleNamespace(frame_id=frame_id),
        pose=SimpleNamespace(
            position=SimpleNamespace(x=x, y=y, z=0.0),
            orientation=SimpleNamespace(x=0.0, y=0.0, z=0.0, w=1.0),
        ),
    )
    return SimpleNamespace(
        target_id=target_id,
        pose=pose,
        selected_for_sampling=selected,
    )


def test_goals_to_path_preserves_order_and_frame():
    goals = [
        NavigationGoal("frontier_00", 1.0, -0.5, 0.0),
        NavigationGoal("frontier_01", 2.0, -0.5, math.pi),
    ]

    path = goals_to_path(goals, frame_id="odom")

    assert path.header.frame_id == "odom"
    assert len(path.poses) == len(goals)
    assert [(pose.pose.position.x, pose.pose.position.y) for pose in path.poses] == [
        (goal.x, goal.y) for goal in goals
    ]
    assert abs(path.poses[1].pose.orientation.z) == pytest.approx(
        math.sin(math.pi / 2.0)
    )


def test_area_outline_closes_rectangle():
    points = area_outline_points(SearchArea(1.0, 2.0, -0.5, 0.5))

    assert len(points) == 5
    assert (points[0].x, points[0].y) == (1.0, -0.5)
    assert (points[-1].x, points[-1].y) == (1.0, -0.5)


def test_area_center():
    assert area_center(SearchArea(1.0, 3.0, -1.0, 1.0)) == (2.0, 0.0)


def test_marker_array_uses_stable_namespaces_and_ids():
    area = SearchArea(1.0, 2.0, -0.5, 0.5)
    goals = [
        NavigationGoal("frontier_00", 1.0, -0.5, 0.0),
        NavigationGoal("frontier_01", 2.0, -0.5, 0.0),
    ]

    markers = build_navigation_marker_array(
        task_area=area,
        frontier_candidates=goals,
        frame_id="odom",
    )

    marker_keys = [(marker.ns, marker.id, marker.type) for marker in markers.markers]
    assert marker_keys == [
        ("task_area_fill", 0, Marker.CUBE),
        ("task_area_border", 0, Marker.LINE_STRIP),
        ("task_area_label", 0, Marker.TEXT_VIEW_FACING),
        ("frontier_candidates", 100, Marker.SPHERE),
        ("frontier_labels", 200, Marker.TEXT_VIEW_FACING),
        ("frontier_candidates", 101, Marker.SPHERE),
        ("frontier_labels", 201, Marker.TEXT_VIEW_FACING),
    ]

    fill_marker = markers.markers[0]
    label_marker = markers.markers[2]
    assert fill_marker.color.a == pytest.approx(0.18)
    assert fill_marker.scale.x == pytest.approx(1.0)
    assert fill_marker.scale.y == pytest.approx(1.0)
    assert label_marker.text == "TASK AREA"


def test_marker_array_highlights_current_goal():
    current_goal = pose_stamped_from_goal(
        NavigationGoal("current", 1.4, 0.2, 0.0),
        frame_id="odom",
    )

    markers = build_navigation_marker_array(
        task_area=SearchArea(1.0, 2.0, -0.5, 0.5),
        frontier_candidates=[],
        frame_id="odom",
        current_goal=current_goal,
    )

    current_markers = [
        marker for marker in markers.markers if marker.ns == "current_goal"
    ]
    assert len(current_markers) == 1
    assert current_markers[0].type == Marker.ARROW
    assert current_markers[0].pose.position.x == pytest.approx(1.4)


def test_marker_array_adds_target_and_standoff_approach_markers():
    markers = build_navigation_marker_array(
        task_area=SearchArea(1.0, 2.0, -0.5, 0.5),
        frontier_candidates=[],
        frame_id="odom",
        targets=[_target(x=2.0, y=0.0, selected=True)],
        target_standoff_m=0.45,
    )

    target_marker = next(
        marker for marker in markers.markers if marker.ns == "target_detection"
    )
    approach_marker = next(
        marker for marker in markers.markers if marker.ns == "approach_goal"
    )
    assert target_marker.pose.position.x == pytest.approx(2.0)
    assert approach_marker.pose.position.x == pytest.approx(1.55)
    assert approach_marker.type == Marker.ARROW
