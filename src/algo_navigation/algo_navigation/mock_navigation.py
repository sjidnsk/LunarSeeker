from __future__ import annotations

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

        self._phase_name = "ready"
        self._selected_target_pose = None
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
        goal = self._build_goal(goal_label)
        status = String()
        status.data = (
            f"phase={self._phase_name}; goal={goal_label}; "
            f"frame={goal.header.frame_id}; "
            f"x={goal.pose.position.x:.2f}; y={goal.pose.position.y:.2f}"
        )
        self._goal_pub.publish(goal)
        self._status_pub.publish(status)

    def _build_goal(self, goal_label: str):
        if goal_label == "selected_target" and self._selected_target_pose is not None:
            goal = PoseStamped()
            goal.header.stamp = self.get_clock().now().to_msg()
            goal.header.frame_id = self._selected_target_pose.header.frame_id
            goal.pose = self._selected_target_pose.pose
            return goal

        x, y, z = FIXED_GOAL_POSES.get(goal_label, FIXED_GOAL_POSES["standby"])
        goal = PoseStamped()
        goal.header.stamp = self.get_clock().now().to_msg()
        goal.header.frame_id = str(self.get_parameter("map_frame_id").value)
        goal.pose.position.x = x
        goal.pose.position.y = y
        goal.pose.position.z = z
        goal.pose.orientation.w = 1.0
        return goal


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
