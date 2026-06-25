from __future__ import annotations

import time
from typing import Optional

from .mission_constants import MISSION_TIME_LIMIT_SEC, MissionPhase

try:
    import rclpy
    from rclpy.action import ActionServer
    from rclpy.node import Node
    from base_interfaces.action import ExecuteMission
    from base_interfaces.msg import MissionState
except ImportError:  # Allows non-ROS unit tests to import the package.
    rclpy = None
    ActionServer = None
    Node = object
    ExecuteMission = None
    MissionState = None


PHASE_NAMES = {
    MissionPhase.IDLE: "idle",
    MissionPhase.READY: "ready",
    MissionPhase.DEPARTURE: "departure",
    MissionPhase.EXPLORATION: "exploration",
    MissionPhase.APPROACH: "approach",
    MissionPhase.SAMPLE: "sample",
    MissionPhase.RETURN: "return",
    MissionPhase.UNLOAD: "unload",
    MissionPhase.COMPLETE: "complete",
    MissionPhase.FAULT: "fault",
}


class MissionStateMachine(Node):
    """Thin ROS shell for the autonomous sampling task state machine."""

    def __init__(self) -> None:
        super().__init__("mission_state_machine")
        self.declare_parameter("use_mock_hardware", True)
        self.declare_parameter("mission.time_limit_sec", MISSION_TIME_LIMIT_SEC)

        self._phase = MissionPhase.READY
        self._collected_count = 0
        self._estimated_score = 0
        self._started_at: Optional[float] = None
        self._state_pub = self.create_publisher(MissionState, "/mission/state", 10)
        self._timer = self.create_timer(1.0, self._publish_state)
        self._action_server = ActionServer(
            self,
            ExecuteMission,
            "execute_mission",
            self._execute_mission,
        )

    def _remaining_time(self) -> float:
        limit = float(self.get_parameter("mission.time_limit_sec").value)
        if self._started_at is None:
            return limit
        return max(0.0, limit - (time.monotonic() - self._started_at))

    def _build_state(self, fault_code: int = 0, fault_text: str = ""):
        state = MissionState()
        state.header.stamp = self.get_clock().now().to_msg()
        state.header.frame_id = "base_link"
        state.phase = int(self._phase)
        state.phase_name = PHASE_NAMES.get(self._phase, "unknown")
        state.collected_count = self._collected_count
        state.estimated_score = self._estimated_score
        state.remaining_time_sec = float(self._remaining_time())
        state.fault_code = fault_code
        state.fault_text = fault_text
        state.remote_intervention_detected = False
        return state

    def _publish_state(self) -> None:
        self._state_pub.publish(self._build_state())

    def _set_phase(self, phase: MissionPhase) -> None:
        self._phase = phase
        self.get_logger().info(f"mission phase: {PHASE_NAMES[phase]}")
        self._publish_state()

    async def _execute_mission(self, goal_handle):
        use_mock = bool(goal_handle.request.use_mock_hardware) or bool(
            self.get_parameter("use_mock_hardware").value
        )
        self._started_at = time.monotonic()
        self._estimated_score = 0
        self._collected_count = 0

        if not use_mock:
            self._set_phase(MissionPhase.FAULT)
            result = ExecuteMission.Result()
            result.success = False
            result.estimated_score = 0
            result.collected_count = 0
            result.summary = "Real hardware execution is not implemented in the project skeleton."
            result.fault_code = 1001
            goal_handle.abort()
            return result

        phases = [
            MissionPhase.DEPARTURE,
            MissionPhase.EXPLORATION,
            MissionPhase.APPROACH,
            MissionPhase.SAMPLE,
            MissionPhase.RETURN,
            MissionPhase.UNLOAD,
            MissionPhase.COMPLETE,
        ]
        for index, phase in enumerate(phases, start=1):
            self._set_phase(phase)
            feedback = ExecuteMission.Feedback()
            feedback.state = self._build_state()
            feedback.current_behavior = PHASE_NAMES[phase]
            feedback.progress = index / len(phases)
            goal_handle.publish_feedback(feedback)
            time.sleep(0.05)

        goal_handle.succeed()
        result = ExecuteMission.Result()
        result.success = True
        result.estimated_score = self._estimated_score
        result.collected_count = self._collected_count
        result.summary = "Mock mission cycle completed; autonomy algorithms are pending."
        result.fault_code = 0
        return result


def main(args=None) -> None:
    if rclpy is None:
        raise RuntimeError("rclpy is required to run mission_state_machine.")

    rclpy.init(args=args)
    node = MissionStateMachine()
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
