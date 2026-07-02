import math
import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from algo_navigation.search_strategy import (
    FrontierSelectionConfig,
    OccupancyGridData,
    SearchArea,
    approach_goal_for_target,
    find_frontier_clusters,
    frontier_goals,
    is_frontier_cell,
    labels,
    normalize_angle,
    select_frontier_goal,
)


def _grid(width, height, free_cells=(), occupied_cells=()):
    data = [-1 for _ in range(width * height)]
    for x, y in free_cells:
        data[y * width + x] = 0
    for x, y in occupied_cells:
        data[y * width + x] = 100
    return OccupancyGridData(
        width=width,
        height=height,
        resolution=1.0,
        origin_x=0.0,
        origin_y=0.0,
        data=data,
    )


def test_frontier_cell_is_free_cell_adjacent_to_unknown():
    grid = _grid(
        4,
        3,
        free_cells=[(1, 1), (2, 1)],
        occupied_cells=[(0, 1)],
    )

    assert is_frontier_cell(grid, cell_x=1, cell_y=1)
    assert not is_frontier_cell(grid, cell_x=0, cell_y=1)


def test_find_frontier_clusters_groups_adjacent_boundary_cells():
    grid = _grid(
        6,
        5,
        free_cells=[
            (1, 1),
            (2, 1),
            (3, 1),
            (1, 2),
            (2, 2),
            (3, 2),
        ],
    )

    clusters = find_frontier_clusters(
        grid,
        robot_x=0.0,
        robot_y=0.0,
        config=FrontierSelectionConfig(min_cluster_size=2),
    )

    assert len(clusters) == 1
    assert clusters[0].cell_count == 6
    assert clusters[0].x == pytest.approx(2.5)
    assert clusters[0].y == pytest.approx(2.0)


def test_task_area_priority_selects_frontier_toward_designated_area():
    left_free = [(1, y) for y in range(1, 4)] + [(2, y) for y in range(1, 4)]
    right_free = [(7, y) for y in range(1, 4)] + [(8, y) for y in range(1, 4)]
    grid = _grid(10, 5, free_cells=left_free + right_free)

    goal = select_frontier_goal(
        grid,
        robot_x=0.0,
        robot_y=2.0,
        config=FrontierSelectionConfig(
            min_cluster_size=2,
            task_area=SearchArea(min_x=7.0, max_x=9.0, min_y=1.0, max_y=4.0),
        ),
    )

    assert goal is not None
    assert goal.x > 7.0
    assert goal.label == "frontier_01"


def test_frontier_goals_are_sorted_by_priority():
    left_free = [(1, y) for y in range(1, 4)] + [(2, y) for y in range(1, 4)]
    right_free = [(7, y) for y in range(1, 4)] + [(8, y) for y in range(1, 4)]
    grid = _grid(10, 5, free_cells=left_free + right_free)

    goals = frontier_goals(
        grid,
        robot_x=0.0,
        robot_y=2.0,
        config=FrontierSelectionConfig(
            min_cluster_size=2,
            task_area=SearchArea(min_x=7.0, max_x=9.0, min_y=1.0, max_y=4.0),
        ),
    )

    assert labels(goals) == ["frontier_01", "frontier_00"]


def test_grid_data_validates_shape():
    with pytest.raises(ValueError):
        OccupancyGridData(
            width=2,
            height=2,
            resolution=1.0,
            origin_x=0.0,
            origin_y=0.0,
            data=[0],
        ).validate()


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
