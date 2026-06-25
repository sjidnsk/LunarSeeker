from __future__ import annotations

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String

    from base_interfaces.msg import MissionState
except ImportError:  # Allows non-ROS unit tests to import this module.
    rclpy = None
    Node = object
    String = None
    MissionState = None


PHASE_MANIPULATION_STATES = {
    "ready": "idle",
    "departure": "stowed",
    "exploration": "stowed",
    "approach": "arm_ready",
    "sample": "pre_grasp_grasp_lift_stow_mock_success",
    "return": "holding_sample",
    "unload": "place_release_mock_success",
    "complete": "sample_released",
    "fault": "safe_stop",
}


def manipulation_state_for_phase(phase_name: str) -> str:
    return PHASE_MANIPULATION_STATES.get(phase_name, "idle")


class MockManipulation(Node):
    """Publish a mock PiPER manipulation state derived from mission phase."""

    def __init__(self) -> None:
        super().__init__("mock_manipulation")
        self.declare_parameter("publish_rate_hz", 2.0)
        self._phase_name = "ready"
        self._collected_count = 0
        self._status_pub = self.create_publisher(
            String, "/mock/manipulation_status", 10
        )
        self._mission_sub = self.create_subscription(
            MissionState,
            "/mission/state",
            self._mission_callback,
            10,
        )

        rate_hz = float(self.get_parameter("publish_rate_hz").value)
        self.create_timer(1.0 / max(rate_hz, 0.1), self._publish_status)

    def _mission_callback(self, state) -> None:
        self._phase_name = state.phase_name
        self._collected_count = state.collected_count

    def _publish_status(self) -> None:
        status = String()
        status.data = (
            f"phase={self._phase_name}; "
            f"manipulation={manipulation_state_for_phase(self._phase_name)}; "
            f"collected_count={self._collected_count}"
        )
        self._status_pub.publish(status)


def main(args=None) -> None:
    if rclpy is None:
        raise RuntimeError("rclpy is required to run mock_manipulation.")

    rclpy.init(args=args)
    node = MockManipulation()
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
