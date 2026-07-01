from __future__ import annotations

import math

try:
    import rclpy
    from geometry_msgs.msg import PoseStamped
    from nav_msgs.msg import OccupancyGrid
    from rclpy.node import Node
    from rclpy.executors import ExternalShutdownException
    from std_msgs.msg import String

    from base_interfaces.msg import MissionState, ScienceTargetArray
except ImportError:  # Allows non-ROS unit tests to import this module.
    rclpy = None
    PoseStamped = None
    OccupancyGrid = None
    Node = object
    ExternalShutdownException = RuntimeError
    String = None
    MissionState = None
    ScienceTargetArray = None

try:
    from .search_strategy import (
        FrontierSelectionConfig,
        NavigationGoal,
        OccupancyGridData,
        SearchArea,
        approach_goal_for_target,
        select_frontier_goal,
        normalize_angle,
    )
except ImportError:  # Allows direct importlib loading in unit tests.
    from algo_navigation.search_strategy import (
        FrontierSelectionConfig,
        NavigationGoal,
        OccupancyGridData,
        SearchArea,
        approach_goal_for_target,
        select_frontier_goal,
        normalize_angle,
    )


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


def goal_label_for_phase(phase_name: str) -> str:
    return PHASE_GOALS.get(phase_name, "standby")


class MockNavigation(Node):
    """Publish mock navigation goals from mission phases and selected targets."""

    def __init__(self) -> None:
        super().__init__("mock_navigation")
        self.declare_parameter("map_frame_id", "odom")
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

        self._phase_name = "ready"
        self._selected_target_pose = None
        self._latest_map = None
        self._goal_pub = self.create_publisher(PoseStamped, "/goal_pose", 10)
        self._status_pub = self.create_publisher(String, "/mock/navigation_status", 10)
        self._mission_sub = self.create_subscription(
            MissionState,
            "/mission/state",
            self._mission_callback,
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

        rate_hz = float(self.get_parameter("publish_rate_hz").value)
        self.create_timer(1.0 / max(rate_hz, 0.1), self._publish_navigation_state)

    def _mission_callback(self, state) -> None:
        self._phase_name = state.phase_name

    def _target_callback(self, detections) -> None:
        selected = [
            target
            for target in detections.targets
            if target.selected_for_sampling and target.pose.header.frame_id
        ]
        if selected:
            self._selected_target_pose = selected[0].pose

    def _map_callback(self, occupancy_grid) -> None:
        self._latest_map = occupancy_grid

    def _publish_navigation_state(self) -> None:
        goal_label = goal_label_for_phase(self._phase_name)
        goal, strategy_label = self._build_goal(goal_label)
        status = String()
        status.data = (
            f"phase={self._phase_name}; goal={goal_label}; "
            f"strategy={strategy_label}; "
            f"frame={goal.header.frame_id}; "
            f"x={goal.pose.position.x:.2f}; y={goal.pose.position.y:.2f}"
        )
        self._goal_pub.publish(goal)
        self._status_pub.publish(status)

    def _build_goal(self, goal_label: str):
        if goal_label == "selected_target" and self._selected_target_pose is not None:
            target_pose = self._selected_target_pose.pose
            target_goal = approach_goal_for_target(
                target_x=float(target_pose.position.x),
                target_y=float(target_pose.position.y),
                standoff_m=float(self.get_parameter("target_standoff_m").value),
            )
            return (
                self._pose_from_navigation_goal(
                    target_goal,
                    self._selected_target_pose.header.frame_id,
                ),
                target_goal.label,
            )

        if goal_label == "frontier_exploration":
            frontier_goal = self._build_frontier_goal()
            if frontier_goal is None:
                x, y, z = FIXED_GOAL_POSES["frontier_waiting_for_map"]
                waiting_goal = NavigationGoal(
                    label="frontier_waiting_for_map",
                    x=x,
                    y=y,
                    yaw=0.0,
                )
                goal = self._pose_from_navigation_goal(
                    waiting_goal,
                    str(self.get_parameter("map_frame_id").value),
                )
                goal.pose.position.z = z
                return goal, waiting_goal.label

            return (
                self._pose_from_navigation_goal(
                    frontier_goal,
                    self._latest_map.header.frame_id
                    or str(self.get_parameter("map_frame_id").value),
                ),
                frontier_goal.label,
            )

        x, y, z = FIXED_GOAL_POSES.get(goal_label, FIXED_GOAL_POSES["standby"])
        fixed_goal = NavigationGoal(label=goal_label, x=x, y=y, yaw=0.0)
        goal = self._pose_from_navigation_goal(
            fixed_goal,
            str(self.get_parameter("map_frame_id").value),
        )
        goal.pose.position.z = z
        return goal, fixed_goal.label

    def _pose_from_navigation_goal(self, navigation_goal: NavigationGoal, frame_id: str):
        goal = PoseStamped()
        goal.header.stamp = self.get_clock().now().to_msg()
        goal.header.frame_id = frame_id
        goal.pose.position.x = navigation_goal.x
        goal.pose.position.y = navigation_goal.y
        goal.pose.position.z = 0.0
        qz, qw = self._yaw_to_quaternion_z_w(navigation_goal.yaw)
        goal.pose.orientation.z = qz
        goal.pose.orientation.w = qw
        return goal

    def _build_frontier_goal(self) -> NavigationGoal | None:
        if self._latest_map is None:
            return None

        return select_frontier_goal(
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

    def _build_frontier_config(self) -> FrontierSelectionConfig:
        task_area = None
        if bool(self.get_parameter("task_area.enabled").value):
            task_area = SearchArea(
                min_x=float(self.get_parameter("task_area.min_x").value),
                max_x=float(self.get_parameter("task_area.max_x").value),
                min_y=float(self.get_parameter("task_area.min_y").value),
                max_y=float(self.get_parameter("task_area.max_y").value),
            )

        return FrontierSelectionConfig(
            occupied_threshold=int(self.get_parameter("frontier.occupied_threshold").value),
            min_cluster_size=int(self.get_parameter("frontier.min_cluster_size").value),
            task_area=task_area,
            task_area_distance_weight=float(
                self.get_parameter("task_area.distance_weight").value
            ),
            task_area_inside_bonus=float(
                self.get_parameter("task_area.inside_bonus").value
            ),
        )

    def _yaw_to_quaternion_z_w(self, yaw: float) -> tuple[float, float]:
        normalized = normalize_angle(yaw)
        return math.sin(normalized * 0.5), math.cos(normalized * 0.5)


def main(args=None) -> None:
    if rclpy is None:
        raise RuntimeError("rclpy is required to run mock_navigation.")

    rclpy.init(args=args)
    node = MockNavigation()
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
