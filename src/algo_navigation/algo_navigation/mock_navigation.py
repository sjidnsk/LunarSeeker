from __future__ import annotations

import math

try:
    import rclpy
    from geometry_msgs.msg import PoseStamped
    from rclpy.node import Node
    from std_msgs.msg import String

    from base_interfaces.msg import MissionState, ScienceTargetArray
except ImportError:  # Allows non-ROS unit tests to import this module.
    rclpy = None
    PoseStamped = None
    Node = object
    String = None
    MissionState = None
    ScienceTargetArray = None

try:
    from .search_strategy import (
        NavigationGoal,
        SearchArea,
        approach_goal_for_target,
        generate_lawnmower_goals,
        goal_by_index,
        normalize_angle,
    )
except ImportError:  # Allows direct importlib loading in unit tests.
    from algo_navigation.search_strategy import (
        NavigationGoal,
        SearchArea,
        approach_goal_for_target,
        generate_lawnmower_goals,
        goal_by_index,
        normalize_angle,
    )


PHASE_GOALS = {
    "ready": "standby",
    "departure": "base_exit",
    "exploration": "search_zone_a",
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
    "search_zone_a": (2.0, 0.4, 0.0),
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
        self.declare_parameter("search_area.min_x", 1.0)
        self.declare_parameter("search_area.max_x", 2.8)
        self.declare_parameter("search_area.min_y", -0.6)
        self.declare_parameter("search_area.max_y", 0.6)
        self.declare_parameter("search_lane_spacing_m", 0.4)
        self.declare_parameter("search_waypoint_hold_sec", 4.0)
        self.declare_parameter("target_standoff_m", 0.45)

        self._phase_name = "ready"
        self._selected_target_pose = None
        self._search_started_at = None
        self._search_goals = self._build_search_goals()
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

        rate_hz = float(self.get_parameter("publish_rate_hz").value)
        self.create_timer(1.0 / max(rate_hz, 0.1), self._publish_navigation_state)

    def _mission_callback(self, state) -> None:
        if state.phase_name != self._phase_name and state.phase_name == "exploration":
            self._search_started_at = self.get_clock().now()
        self._phase_name = state.phase_name

    def _target_callback(self, detections) -> None:
        selected = [
            target
            for target in detections.targets
            if target.selected_for_sampling and target.pose.header.frame_id
        ]
        if selected:
            self._selected_target_pose = selected[0].pose

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

        if goal_label == "search_zone_a":
            search_goal = goal_by_index(self._search_goals, self._search_goal_index())
            return (
                self._pose_from_navigation_goal(
                    search_goal,
                    str(self.get_parameter("map_frame_id").value),
                ),
                search_goal.label,
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

    def _build_search_goals(self) -> list[NavigationGoal]:
        area = SearchArea(
            min_x=float(self.get_parameter("search_area.min_x").value),
            max_x=float(self.get_parameter("search_area.max_x").value),
            min_y=float(self.get_parameter("search_area.min_y").value),
            max_y=float(self.get_parameter("search_area.max_y").value),
        )
        return generate_lawnmower_goals(
            area,
            float(self.get_parameter("search_lane_spacing_m").value),
        )

    def _search_goal_index(self) -> int:
        if self._search_started_at is None:
            self._search_started_at = self.get_clock().now()

        elapsed_sec = (
            self.get_clock().now() - self._search_started_at
        ).nanoseconds / 1e9
        hold_sec = max(float(self.get_parameter("search_waypoint_hold_sec").value), 0.1)
        return int(elapsed_sec // hold_sec)

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
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
