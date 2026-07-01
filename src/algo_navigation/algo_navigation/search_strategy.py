from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Iterable, Sequence


UNKNOWN_CELL = -1


@dataclass(frozen=True)
class SearchArea:
    """矩形任务区域，单位为米，坐标系由调用方保证。"""

    min_x: float
    max_x: float
    min_y: float
    max_y: float

    def validate(self) -> None:
        if self.max_x <= self.min_x:
            raise ValueError("search area max_x must be greater than min_x")
        if self.max_y <= self.min_y:
            raise ValueError("search area max_y must be greater than min_y")

    def contains(self, *, x: float, y: float) -> bool:
        return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y

    def distance_to(self, *, x: float, y: float) -> float:
        dx = max(self.min_x - x, 0.0, x - self.max_x)
        dy = max(self.min_y - y, 0.0, y - self.max_y)
        return math.hypot(dx, dy)


@dataclass(frozen=True)
class NavigationGoal:
    """导航策略输出的二维目标点，yaw 单位为弧度。"""

    label: str
    x: float
    y: float
    yaw: float = 0.0


@dataclass(frozen=True)
class OccupancyGridData:
    """轻量地图结构，用于纯算法测试和 ROS OccupancyGrid 转换。"""

    width: int
    height: int
    resolution: float
    origin_x: float
    origin_y: float
    data: Sequence[int]

    def validate(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("grid width and height must be positive")
        if self.resolution <= 0.0:
            raise ValueError("grid resolution must be positive")
        if len(self.data) != self.width * self.height:
            raise ValueError("grid data length must match width * height")


@dataclass(frozen=True)
class FrontierCluster:
    """一组相邻 frontier cell 的候选探索目标。"""

    label: str
    x: float
    y: float
    cell_count: int
    distance_to_robot_m: float
    distance_to_task_area_m: float
    inside_task_area: bool
    score: float


@dataclass(frozen=True)
class FrontierSelectionConfig:
    """Frontier 选择参数，未实测参数应在调用侧标注待验证。"""

    occupied_threshold: int = 50
    min_cluster_size: int = 3
    task_area: SearchArea | None = None
    task_area_distance_weight: float = 4.0
    task_area_inside_bonus: float = 100.0


def normalize_angle(angle_rad: float) -> float:
    """Normalize angle to [-pi, pi)."""

    return (angle_rad + math.pi) % (2.0 * math.pi) - math.pi


def grid_index(grid: OccupancyGridData, *, cell_x: int, cell_y: int) -> int:
    return cell_y * grid.width + cell_x


def grid_cell_center(grid: OccupancyGridData, *, cell_x: int, cell_y: int) -> tuple[float, float]:
    return (
        grid.origin_x + (cell_x + 0.5) * grid.resolution,
        grid.origin_y + (cell_y + 0.5) * grid.resolution,
    )


def is_free_cell(value: int, *, occupied_threshold: int = 50) -> bool:
    return 0 <= value < occupied_threshold


def is_unknown_cell(value: int) -> bool:
    return value == UNKNOWN_CELL


def _neighbors_4(grid: OccupancyGridData, *, cell_x: int, cell_y: int):
    for next_x, next_y in (
        (cell_x - 1, cell_y),
        (cell_x + 1, cell_y),
        (cell_x, cell_y - 1),
        (cell_x, cell_y + 1),
    ):
        if 0 <= next_x < grid.width and 0 <= next_y < grid.height:
            yield next_x, next_y


def _neighbors_8(grid: OccupancyGridData, *, cell_x: int, cell_y: int):
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            next_x = cell_x + dx
            next_y = cell_y + dy
            if 0 <= next_x < grid.width and 0 <= next_y < grid.height:
                yield next_x, next_y


def is_frontier_cell(
    grid: OccupancyGridData,
    *,
    cell_x: int,
    cell_y: int,
    occupied_threshold: int = 50,
) -> bool:
    value = grid.data[grid_index(grid, cell_x=cell_x, cell_y=cell_y)]
    if not is_free_cell(value, occupied_threshold=occupied_threshold):
        return False

    return any(
        is_unknown_cell(grid.data[grid_index(grid, cell_x=x, cell_y=y)])
        for x, y in _neighbors_4(grid, cell_x=cell_x, cell_y=cell_y)
    )


def find_frontier_clusters(
    grid: OccupancyGridData,
    *,
    robot_x: float,
    robot_y: float,
    config: FrontierSelectionConfig | None = None,
) -> list[FrontierCluster]:
    """Find frontier clusters and score them for exploration.

    A frontier cell is a known free cell adjacent to unknown space. Clusters are
    grouped with 8-connectivity so a ragged boundary becomes one candidate.
    """

    grid.validate()
    config = config or FrontierSelectionConfig()
    if config.task_area is not None:
        config.task_area.validate()

    frontier_cells = set()
    for cell_y in range(grid.height):
        for cell_x in range(grid.width):
            if is_frontier_cell(
                grid,
                cell_x=cell_x,
                cell_y=cell_y,
                occupied_threshold=config.occupied_threshold,
            ):
                frontier_cells.add((cell_x, cell_y))

    clusters: list[FrontierCluster] = []
    visited = set()
    for start_cell in sorted(frontier_cells):
        if start_cell in visited:
            continue

        queue = deque([start_cell])
        visited.add(start_cell)
        cells = []
        while queue:
            cell_x, cell_y = queue.popleft()
            cells.append((cell_x, cell_y))
            for neighbor in _neighbors_8(grid, cell_x=cell_x, cell_y=cell_y):
                if neighbor in frontier_cells and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        if len(cells) < config.min_cluster_size:
            continue

        world_points = [
            grid_cell_center(grid, cell_x=cell_x, cell_y=cell_y)
            for cell_x, cell_y in cells
        ]
        if config.task_area is not None:
            goal_x, goal_y = min(
                world_points,
                key=lambda point: (
                    config.task_area.distance_to(x=point[0], y=point[1]),
                    math.hypot(point[0] - robot_x, point[1] - robot_y),
                ),
            )
        else:
            goal_x = sum(x for x, _ in world_points) / len(world_points)
            goal_y = sum(y for _, y in world_points) / len(world_points)

        robot_distance = math.hypot(goal_x - robot_x, goal_y - robot_y)

        task_distance = 0.0
        inside_task_area = False
        if config.task_area is not None:
            inside_task_area = config.task_area.contains(x=goal_x, y=goal_y)
            task_distance = config.task_area.distance_to(x=goal_x, y=goal_y)

        score = (
            robot_distance
            + task_distance * config.task_area_distance_weight
            - (config.task_area_inside_bonus if inside_task_area else 0.0)
        )
        clusters.append(
            FrontierCluster(
                label=f"frontier_{len(clusters):02d}",
                x=goal_x,
                y=goal_y,
                cell_count=len(cells),
                distance_to_robot_m=robot_distance,
                distance_to_task_area_m=task_distance,
                inside_task_area=inside_task_area,
                score=score,
            )
        )

    return sorted(
        clusters,
        key=lambda cluster: (
            cluster.score,
            -cluster.cell_count,
            cluster.distance_to_robot_m,
            cluster.label,
        ),
    )


def select_frontier_goal(
    grid: OccupancyGridData,
    *,
    robot_x: float,
    robot_y: float,
    config: FrontierSelectionConfig | None = None,
) -> NavigationGoal | None:
    clusters = find_frontier_clusters(
        grid,
        robot_x=robot_x,
        robot_y=robot_y,
        config=config,
    )
    if not clusters:
        return None

    best = clusters[0]
    yaw = math.atan2(best.y - robot_y, best.x - robot_x)
    return NavigationGoal(
        label=best.label,
        x=best.x,
        y=best.y,
        yaw=normalize_angle(yaw),
    )


def frontier_goals(
    grid: OccupancyGridData,
    *,
    robot_x: float,
    robot_y: float,
    config: FrontierSelectionConfig | None = None,
) -> list[NavigationGoal]:
    return [
        NavigationGoal(
            label=cluster.label,
            x=cluster.x,
            y=cluster.y,
            yaw=normalize_angle(math.atan2(cluster.y - robot_y, cluster.x - robot_x)),
        )
        for cluster in find_frontier_clusters(
            grid,
            robot_x=robot_x,
            robot_y=robot_y,
            config=config,
        )
    ]


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


def labels(goals: Iterable[NavigationGoal]) -> list[str]:
    return [goal.label for goal in goals]
