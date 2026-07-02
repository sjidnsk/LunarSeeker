from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Iterable, Sequence

try:
    import rclpy
    from geometry_msgs.msg import Point, PoseStamped
    from nav_msgs.msg import OccupancyGrid, Path
    from rclpy.node import Node
    from rclpy.executors import ExternalShutdownException
    from std_msgs.msg import ColorRGBA
    from visualization_msgs.msg import Marker, MarkerArray

    from base_interfaces.msg import MissionState, ScienceTargetArray
except ImportError:  # Allows non-ROS unit tests to import builder functions.
    rclpy = None
    Node = object
    ExternalShutdownException = RuntimeError
    OccupancyGrid = None
    MissionState = None
    ScienceTargetArray = None

    class Point:
        def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
            self.x = x
            self.y = y
            self.z = z

    class ColorRGBA:
        def __init__(
            self,
            r: float = 0.0,
            g: float = 0.0,
            b: float = 0.0,
            a: float = 0.0,
        ):
            self.r = r
            self.g = g
            self.b = b
            self.a = a

    class PoseStamped:
        def __init__(self):
            self.header = SimpleNamespace(frame_id="", stamp=None)
            self.pose = SimpleNamespace(
                position=Point(),
                orientation=SimpleNamespace(x=0.0, y=0.0, z=0.0, w=1.0),
            )

    class Path:
        def __init__(self):
            self.header = SimpleNamespace(frame_id="", stamp=None)
            self.poses = []

    class Marker:
        ARROW = 0
        CUBE = 1
        SPHERE = 2
        LINE_STRIP = 4
        TEXT_VIEW_FACING = 9
        ADD = 0

        def __init__(self):
            self.header = SimpleNamespace(frame_id="", stamp=None)
            self.ns = ""
            self.id = 0
            self.type = self.ARROW
            self.action = self.ADD
            self.pose = SimpleNamespace(
                position=Point(),
                orientation=SimpleNamespace(x=0.0, y=0.0, z=0.0, w=1.0),
            )
            self.scale = SimpleNamespace(x=0.0, y=0.0, z=0.0)
            self.color = ColorRGBA()
            self.points = []
            self.text = ""

    class MarkerArray:
        def __init__(self):
            self.markers = []

try:
    from .search_strategy import (
        FrontierSelectionConfig,
        NavigationGoal,
        OccupancyGridData,
        SearchArea,
        approach_goal_for_target,
        frontier_goals,
        normalize_angle,
    )
except ImportError:  # Allows direct importlib loading in unit tests.
    from algo_navigation.search_strategy import (
        FrontierSelectionConfig,
        NavigationGoal,
        OccupancyGridData,
        SearchArea,
        approach_goal_for_target,
        frontier_goals,
        normalize_angle,
    )


DEFAULT_FRAME_ID = "odom"
SEARCH_PATH_TOPIC = "/navigation/search_path"
SEARCH_MARKERS_TOPIC = "/navigation/search_markers"


def color_rgba(r: float, g: float, b: float, a: float = 1.0) -> ColorRGBA:
    color = ColorRGBA()
    color.r = r
    color.g = g
    color.b = b
    color.a = a
    return color


def yaw_to_quaternion_z_w(yaw: float) -> tuple[float, float]:
    normalized = normalize_angle(yaw)
    return math.sin(normalized * 0.5), math.cos(normalized * 0.5)


def pose_stamped_from_goal(
    goal: NavigationGoal,
    *,
    frame_id: str,
    stamp_msg=None,
) -> PoseStamped:
    pose = PoseStamped()
    pose.header.frame_id = frame_id
    if stamp_msg is not None:
        pose.header.stamp = stamp_msg
    pose.pose.position.x = goal.x
    pose.pose.position.y = goal.y
    pose.pose.position.z = 0.0
    pose.pose.orientation.z, pose.pose.orientation.w = yaw_to_quaternion_z_w(goal.yaw)
    return pose


def goals_to_path(
    goals: Sequence[NavigationGoal],
    *,
    frame_id: str,
    stamp_msg=None,
) -> Path:
    path = Path()
    path.header.frame_id = frame_id
    if stamp_msg is not None:
        path.header.stamp = stamp_msg
    path.poses = [
        pose_stamped_from_goal(goal, frame_id=frame_id, stamp_msg=stamp_msg)
        for goal in goals
    ]
    return path


def area_outline_points(area: SearchArea) -> list[Point]:
    return [
        Point(x=area.min_x, y=area.min_y, z=0.04),
        Point(x=area.max_x, y=area.min_y, z=0.04),
        Point(x=area.max_x, y=area.max_y, z=0.04),
        Point(x=area.min_x, y=area.max_y, z=0.04),
        Point(x=area.min_x, y=area.min_y, z=0.04),
    ]


def area_center(area: SearchArea) -> tuple[float, float]:
    return ((area.min_x + area.max_x) * 0.5, (area.min_y + area.max_y) * 0.5)


def _new_marker(
    *,
    frame_id: str,
    stamp_msg,
    namespace: str,
    marker_id: int,
    marker_type: int,
) -> Marker:
    marker = Marker()
    marker.header.frame_id = frame_id
    if stamp_msg is not None:
        marker.header.stamp = stamp_msg
    marker.ns = namespace
    marker.id = marker_id
    marker.type = marker_type
    marker.action = Marker.ADD
    marker.pose.orientation.w = 1.0
    return marker


def _goal_sphere_marker(
    goal: NavigationGoal,
    *,
    frame_id: str,
    stamp_msg,
    marker_id: int,
    namespace: str,
    color: ColorRGBA,
    scale: float,
) -> Marker:
    marker = _new_marker(
        frame_id=frame_id,
        stamp_msg=stamp_msg,
        namespace=namespace,
        marker_id=marker_id,
        marker_type=Marker.SPHERE,
    )
    marker.pose.position.x = goal.x
    marker.pose.position.y = goal.y
    marker.pose.position.z = 0.05
    marker.scale.x = scale
    marker.scale.y = scale
    marker.scale.z = scale
    marker.color = color
    return marker


def _goal_text_marker(
    goal: NavigationGoal,
    *,
    frame_id: str,
    stamp_msg,
    marker_id: int,
    namespace: str = "frontier_labels",
) -> Marker:
    marker = _new_marker(
        frame_id=frame_id,
        stamp_msg=stamp_msg,
        namespace=namespace,
        marker_id=marker_id,
        marker_type=Marker.TEXT_VIEW_FACING,
    )
    marker.pose.position.x = goal.x
    marker.pose.position.y = goal.y
    marker.pose.position.z = 0.22
    marker.scale.z = 0.12
    marker.color = color_rgba(0.92, 0.94, 0.96, 0.95)
    marker.text = goal.label
    return marker


def _task_area_fill_marker(
    area: SearchArea,
    *,
    frame_id: str,
    stamp_msg,
) -> Marker:
    marker = _new_marker(
        frame_id=frame_id,
        stamp_msg=stamp_msg,
        namespace="task_area_fill",
        marker_id=0,
        marker_type=Marker.CUBE,
    )
    center_x, center_y = area_center(area)
    marker.pose.position.x = center_x
    marker.pose.position.y = center_y
    marker.pose.position.z = 0.01
    marker.scale.x = area.max_x - area.min_x
    marker.scale.y = area.max_y - area.min_y
    marker.scale.z = 0.02
    marker.color = color_rgba(0.12, 0.74, 0.44, 0.18)
    return marker


def _task_area_border_marker(
    area: SearchArea,
    *,
    frame_id: str,
    stamp_msg,
) -> Marker:
    marker = _new_marker(
        frame_id=frame_id,
        stamp_msg=stamp_msg,
        namespace="task_area_border",
        marker_id=0,
        marker_type=Marker.LINE_STRIP,
    )
    marker.points = area_outline_points(area)
    marker.scale.x = 0.07
    marker.color = color_rgba(0.08, 0.95, 0.58, 0.98)
    return marker


def _task_area_label_marker(
    area: SearchArea,
    *,
    frame_id: str,
    stamp_msg,
) -> Marker:
    marker = _new_marker(
        frame_id=frame_id,
        stamp_msg=stamp_msg,
        namespace="task_area_label",
        marker_id=0,
        marker_type=Marker.TEXT_VIEW_FACING,
    )
    center_x, center_y = area_center(area)
    marker.pose.position.x = center_x
    marker.pose.position.y = center_y
    marker.pose.position.z = 0.45
    marker.scale.z = 0.22
    marker.color = color_rgba(0.78, 1.0, 0.84, 0.98)
    marker.text = "TASK AREA"
    return marker


def _pose_arrow_marker(
    pose: PoseStamped,
    *,
    stamp_msg,
    marker_id: int,
    namespace: str,
    color: ColorRGBA,
    scale_x: float = 0.38,
) -> Marker:
    frame_id = pose.header.frame_id or DEFAULT_FRAME_ID
    marker = _new_marker(
        frame_id=frame_id,
        stamp_msg=stamp_msg,
        namespace=namespace,
        marker_id=marker_id,
        marker_type=Marker.ARROW,
    )
    marker.pose = pose.pose
    marker.scale.x = scale_x
    marker.scale.y = 0.08
    marker.scale.z = 0.08
    marker.color = color
    return marker


def _target_goal(target) -> NavigationGoal:
    position = target.pose.pose.position
    return NavigationGoal(
        label=target.target_id or "target",
        x=float(position.x),
        y=float(position.y),
        yaw=0.0,
    )


def build_navigation_marker_array(
    *,
    task_area: SearchArea | None,
    frontier_candidates: Sequence[NavigationGoal],
    frame_id: str,
    stamp_msg=None,
    current_goal: PoseStamped | None = None,
    targets: Iterable | None = None,
    target_standoff_m: float = 0.45,
) -> MarkerArray:
    markers = MarkerArray()

    if task_area is not None:
        markers.markers.append(
            _task_area_fill_marker(
                task_area,
                frame_id=frame_id,
                stamp_msg=stamp_msg,
            )
        )
        markers.markers.append(
            _task_area_border_marker(
                task_area,
                frame_id=frame_id,
                stamp_msg=stamp_msg,
            )
        )
        markers.markers.append(
            _task_area_label_marker(
                task_area,
                frame_id=frame_id,
                stamp_msg=stamp_msg,
            )
        )

    for index, goal in enumerate(frontier_candidates):
        markers.markers.append(
            _goal_sphere_marker(
                goal,
                frame_id=frame_id,
                stamp_msg=stamp_msg,
                marker_id=100 + index,
                namespace="frontier_candidates",
                color=color_rgba(0.22, 0.45, 0.95, 0.85),
                scale=0.12,
            )
        )
        markers.markers.append(
            _goal_text_marker(
                goal,
                frame_id=frame_id,
                stamp_msg=stamp_msg,
                marker_id=200 + index,
            )
        )

    if current_goal is not None:
        markers.markers.append(
            _pose_arrow_marker(
                current_goal,
                stamp_msg=stamp_msg,
                marker_id=0,
                namespace="current_goal",
                color=color_rgba(1.0, 0.78, 0.12, 0.95),
                scale_x=0.5,
            )
        )

    for index, target in enumerate(targets or []):
        target_frame = target.pose.header.frame_id or frame_id
        target_goal = _target_goal(target)
        target_color = (
            color_rgba(0.96, 0.26, 0.22, 0.95)
            if target.selected_for_sampling
            else color_rgba(0.75, 0.75, 0.75, 0.75)
        )
        markers.markers.append(
            _goal_sphere_marker(
                target_goal,
                frame_id=target_frame,
                stamp_msg=stamp_msg,
                marker_id=300 + index,
                namespace="target_detection",
                color=target_color,
                scale=0.16,
            )
        )

        if target.selected_for_sampling:
            approach_goal = approach_goal_for_target(
                target_x=target_goal.x,
                target_y=target_goal.y,
                standoff_m=target_standoff_m,
                label=f"{target_goal.label}_approach",
            )
            approach_pose = pose_stamped_from_goal(
                approach_goal,
                frame_id=target_frame,
                stamp_msg=stamp_msg,
            )
            markers.markers.append(
                _pose_arrow_marker(
                    approach_pose,
                    stamp_msg=stamp_msg,
                    marker_id=400 + index,
                    namespace="approach_goal",
                    color=color_rgba(0.72, 0.34, 0.94, 0.95),
                    scale_x=0.42,
                )
            )

    return markers


class NavigationVisualizer(Node):
    """Publish RViz debug visualization for frontier exploration."""

    def __init__(self) -> None:
        super().__init__("navigation_visualizer")
        self.declare_parameter("map_frame_id", DEFAULT_FRAME_ID)
        self.declare_parameter("publish_rate_hz", 2.0)
        self.declare_parameter("robot_pose.x", 0.0)
        self.declare_parameter("robot_pose.y", 0.0)
        self.declare_parameter("frontier.occupied_threshold", 50)
        self.declare_parameter("frontier.min_cluster_size", 3)
        self.declare_parameter("task_area.enabled", True)
        self.declare_parameter("task_area.min_x", 1.6)
        self.declare_parameter("task_area.max_x", 3.2)
        self.declare_parameter("task_area.min_y", -0.8)
        self.declare_parameter("task_area.max_y", 0.8)
        self.declare_parameter("task_area.distance_weight", 4.0)
        self.declare_parameter("task_area.inside_bonus", 100.0)
        self.declare_parameter("target_standoff_m", 0.45)

        self._latest_map = None
        self._current_goal = None
        self._targets = []
        self._phase_name = "unknown"

        self._path_pub = self.create_publisher(Path, SEARCH_PATH_TOPIC, 10)
        self._marker_pub = self.create_publisher(MarkerArray, SEARCH_MARKERS_TOPIC, 10)
        self._goal_sub = self.create_subscription(
            PoseStamped,
            "/goal_pose",
            self._goal_callback,
            10,
        )
        self._target_sub = self.create_subscription(
            ScienceTargetArray,
            "/target_detections",
            self._target_callback,
            10,
        )
        self._map_sub = self.create_subscription(
            OccupancyGrid,
            "/map",
            self._map_callback,
            10,
        )
        self._mission_sub = self.create_subscription(
            MissionState,
            "/mission/state",
            self._mission_callback,
            10,
        )

        rate_hz = float(self.get_parameter("publish_rate_hz").value)
        self.create_timer(1.0 / max(rate_hz, 0.1), self._publish_visualization)

    def _goal_callback(self, goal: PoseStamped) -> None:
        self._current_goal = goal

    def _target_callback(self, detections: ScienceTargetArray) -> None:
        self._targets = list(detections.targets)

    def _map_callback(self, occupancy_grid: OccupancyGrid) -> None:
        self._latest_map = occupancy_grid

    def _mission_callback(self, state: MissionState) -> None:
        self._phase_name = state.phase_name

    def _publish_visualization(self) -> None:
        stamp_msg = self.get_clock().now().to_msg()
        frame_id = str(self.get_parameter("map_frame_id").value)
        task_area = self._build_task_area()
        candidates = self._build_frontier_goals()
        if self._latest_map is not None and self._latest_map.header.frame_id:
            frame_id = self._latest_map.header.frame_id

        self._path_pub.publish(
            goals_to_path(
                candidates,
                frame_id=frame_id,
                stamp_msg=stamp_msg,
            )
        )
        self._marker_pub.publish(
            build_navigation_marker_array(
                task_area=task_area,
                frontier_candidates=candidates,
                frame_id=frame_id,
                stamp_msg=stamp_msg,
                current_goal=self._current_goal,
                targets=self._targets,
                target_standoff_m=float(
                    self.get_parameter("target_standoff_m").value
                ),
            )
        )

    def _build_frontier_goals(self) -> list[NavigationGoal]:
        if self._latest_map is None:
            return []

        return frontier_goals(
            self._grid_data_from_map(self._latest_map),
            robot_x=float(self.get_parameter("robot_pose.x").value),
            robot_y=float(self.get_parameter("robot_pose.y").value),
            config=self._build_frontier_config(),
        )

    def _grid_data_from_map(self, occupancy_grid) -> OccupancyGridData:
        return OccupancyGridData(
            width=int(occupancy_grid.info.width),
            height=int(occupancy_grid.info.height),
            resolution=float(occupancy_grid.info.resolution),
            origin_x=float(occupancy_grid.info.origin.position.x),
            origin_y=float(occupancy_grid.info.origin.position.y),
            data=list(occupancy_grid.data),
        )

    def _build_task_area(self) -> SearchArea | None:
        if not bool(self.get_parameter("task_area.enabled").value):
            return None

        return SearchArea(
            min_x=float(self.get_parameter("task_area.min_x").value),
            max_x=float(self.get_parameter("task_area.max_x").value),
            min_y=float(self.get_parameter("task_area.min_y").value),
            max_y=float(self.get_parameter("task_area.max_y").value),
        )

    def _build_frontier_config(self) -> FrontierSelectionConfig:
        return FrontierSelectionConfig(
            occupied_threshold=int(self.get_parameter("frontier.occupied_threshold").value),
            min_cluster_size=int(self.get_parameter("frontier.min_cluster_size").value),
            task_area=self._build_task_area(),
            task_area_distance_weight=float(
                self.get_parameter("task_area.distance_weight").value
            ),
            task_area_inside_bonus=float(
                self.get_parameter("task_area.inside_bonus").value
            ),
        )


def main(args=None) -> None:
    if rclpy is None:
        raise RuntimeError("rclpy is required to run navigation_visualizer.")

    rclpy.init(args=args)
    node = NavigationVisualizer()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
