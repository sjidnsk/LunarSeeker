from __future__ import annotations

import time
from typing import Optional

from .mission_constants import MISSION_TIME_LIMIT_SEC, MissionPhase

try:
    import rclpy
    from rclpy.action import ActionServer
    from rclpy.node import Node
    from base_interfaces.action import ExecuteMission
    from base_interfaces.msg import MissionState, ScienceTarget, ScienceTargetArray
except ImportError:  # Allows non-ROS unit tests to import the package.
    rclpy = None
    ActionServer = None
    Node = object
    ExecuteMission = None
    MissionState = None
    ScienceTarget = None
    ScienceTargetArray = None


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
        self.declare_parameter("mock.target_wait_timeout_sec", 2.0)
        self.declare_parameter("mock.min_target_confidence", 0.5)

        self._phase = MissionPhase.READY
        self._collected_count = 0
        self._estimated_score = 0
        self._started_at: Optional[float] = None
        self._selected_target: Optional[ScienceTarget] = None
        self._state_pub = self.create_publisher(MissionState, "/mission/state", 10)
        self._target_sub = self.create_subscription(
            ScienceTargetArray,
            "/target_detections",
            self._target_callback,
            10,
        )
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

    def _target_callback(self, detections) -> None:
        min_confidence = float(self.get_parameter("mock.min_target_confidence").value)
        selected_targets = [
            target
            for target in detections.targets
            if target.selected_for_sampling
            and target.confidence >= min_confidence
            and target.status
            in (ScienceTarget.STATUS_CANDIDATE, ScienceTarget.STATUS_CONFIRMED)
        ]
        if selected_targets:
            self._selected_target = selected_targets[0]

    def _wait_for_selected_target(self) -> Optional[ScienceTarget]:
        timeout_sec = float(self.get_parameter("mock.target_wait_timeout_sec").value)
        deadline = time.monotonic() + timeout_sec
        while self._selected_target is None and time.monotonic() < deadline:
            time.sleep(0.05)
        return self._selected_target

    def _publish_feedback(self, goal_handle, behavior: str, progress: float) -> None:
        feedback = ExecuteMission.Feedback()
        feedback.state = self._build_state()
        feedback.current_behavior = behavior
        feedback.progress = progress
        goal_handle.publish_feedback(feedback)

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

        self._set_phase(MissionPhase.DEPARTURE)
        self._estimated_score += 10
        self._publish_feedback(goal_handle, "depart_base", 0.15)
        time.sleep(0.1)

        self._set_phase(MissionPhase.EXPLORATION)
        self._publish_feedback(goal_handle, "search_for_targets", 0.30)
        selected_target = self._wait_for_selected_target()
        if selected_target is None:
            self._set_phase(MissionPhase.FAULT)
            result = ExecuteMission.Result()
            result.success = False
            result.estimated_score = self._estimated_score
            result.collected_count = self._collected_count
            result.summary = "Mock mission could not find a selected target."
            result.fault_code = 2001
            goal_handle.abort()
            return result

        self._set_phase(MissionPhase.APPROACH)
        self._publish_feedback(
            goal_handle,
            f"approach_target:{selected_target.target_id}",
            0.45,
        )
        time.sleep(0.1)

        self._set_phase(MissionPhase.SAMPLE)
        self._collected_count = 1
        self._estimated_score += 10
        self._publish_feedback(
            goal_handle,
            f"sample_target:{selected_target.target_id}",
            0.60,
        )
        time.sleep(0.1)

        self._set_phase(MissionPhase.RETURN)
        self._estimated_score += 10
        self._publish_feedback(goal_handle, "return_to_base", 0.78)
        time.sleep(0.1)

        self._set_phase(MissionPhase.UNLOAD)
        self._estimated_score += 20
        self._publish_feedback(goal_handle, "unload_sample", 0.92)
        time.sleep(0.1)

        self._set_phase(MissionPhase.COMPLETE)
        self._publish_feedback(goal_handle, "complete", 1.0)

        goal_handle.succeed()
        result = ExecuteMission.Result()
        result.success = True
        result.estimated_score = self._estimated_score
        result.collected_count = self._collected_count
        result.summary = (
            f"Mock mission completed with selected target {selected_target.target_id}."
        )
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
