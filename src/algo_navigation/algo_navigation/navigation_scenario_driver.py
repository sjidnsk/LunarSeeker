from __future__ import annotations

import time

from .navigation_sim_common import load_scenario, yaw_to_quaternion_values

try:
    import rclpy
    from geometry_msgs.msg import PoseStamped
    from rclpy._rclpy_pybind11 import RCLError
    from rclpy.node import Node

    from base_interfaces.msg import (
        MissionState,
        NavigationStatus,
        ScienceTarget,
        ScienceTargetArray,
    )
except ImportError:  # Allows non-ROS static tests to import this module.
    rclpy = None
    RCLError = RuntimeError
    Node = object
    PoseStamped = None
    MissionState = None
    NavigationStatus = None
    ScienceTarget = None
    ScienceTargetArray = None


PHASE_TO_CONSTANT = {
    "ready": "PHASE_READY",
    "departure": "PHASE_DEPARTURE",
    "exploration": "PHASE_EXPLORATION",
    "approach": "PHASE_APPROACH",
    "sample": "PHASE_SAMPLE",
    "return": "PHASE_RETURN",
    "unload": "PHASE_UNLOAD",
    "complete": "PHASE_COMPLETE",
    "fault": "PHASE_FAULT",
}


class NavigationScenarioDriver(Node):
    """Drive P3 simulation scenarios through mission phases.

    This node does not replace base_mission. It is a validation fixture that
    publishes MissionState and selected target detections so P1/P2 can be
    exercised without real hardware.
    """

    def __init__(self) -> None:
        super().__init__("navigation_scenario_driver")
        self.declare_parameter("scenario_config", "")
        self.declare_parameter("scenario", "nominal")
        self.declare_parameter("publish_rate_hz", 2.0)
        self.declare_parameter("mission_time_limit_sec", 600.0)

        config_path = str(self.get_parameter("scenario_config").value)
        scenario_name = str(self.get_parameter("scenario").value)
        if not config_path:
            raise RuntimeError("scenario_config parameter is required.")
        self._scenario = load_scenario(config_path, scenario_name)
        frames = self._scenario.get("frames", {})
        self._map_frame_id = str(frames.get("map", "map"))
        self._scenario_name = scenario_name
        self._expected_failure = str(self._scenario.get("expected_failure", "none"))
        self._phase_sequence = list(
            self._scenario.get(
                "phase_sequence",
                ["departure", "exploration", "approach", "return"],
            )
        )
        if not self._phase_sequence:
            self._phase_sequence = ["departure"]

        self._phase_index = 0
        self._phase_entered_at = time.monotonic()
        self._started_at = time.monotonic()
        self._latest_status = None
        self._finished = False
        self._final_summary_logged = False

        self._mission_pub = self.create_publisher(MissionState, "/mission/state", 10)
        self._target_pub = self.create_publisher(
            ScienceTargetArray,
            "/target_detections",
            10,
        )
        self._status_sub = self.create_subscription(
            NavigationStatus,
            "/navigation/status",
            self._status_callback,
            10,
        )

        publish_rate_hz = float(self.get_parameter("publish_rate_hz").value)
        self.create_timer(1.0 / max(publish_rate_hz, 0.5), self._tick)
        self.get_logger().info(f"P3 navigation scenario loaded: {scenario_name}")

    def _status_callback(self, status) -> None:
        self._latest_status = status

    def _tick(self) -> None:
        self._advance_if_ready()
        self._publish_mission_state()
        self._publish_targets()
        self._check_timeout()

    def _advance_if_ready(self) -> None:
        if self._finished or self._latest_status is None:
            return

        phase = self._current_phase()
        status = self._latest_status
        if status.mission_phase_name and status.mission_phase_name != phase:
            return

        if phase == "departure" and self._goal_succeeded(NavigationStatus.GOAL_BASE_EXIT):
            self._set_phase("exploration")
            return

        if self._expected_failure == "frontier_unreachable" and phase == "exploration":
            if status.status == NavigationStatus.STATUS_RETURN_RECOMMENDED:
                self._finish("passed: frontier unreachable produced return recommendation")
            return

        if self._expected_failure == "local_obstacle_blocked" and phase in (
            "exploration",
            "approach",
            "return",
        ):
            if status.recovery_count > 0:
                self._finish("passed: local obstacle triggered Nav2 recovery feedback")
                return
            if (
                status.status == NavigationStatus.STATUS_GOAL_FAILED
                and status.goal_type in (
                    NavigationStatus.GOAL_FRONTIER,
                    NavigationStatus.GOAL_TARGET_APPROACH,
                    NavigationStatus.GOAL_BASE_RETURN,
                )
            ):
                self._finish("passed: local obstacle produced navigation failure")
                return

        if self._expected_failure == "target_approach_failed" and phase == "approach":
            if (
                status.goal_type == NavigationStatus.GOAL_TARGET_APPROACH
                and status.status == NavigationStatus.STATUS_GOAL_FAILED
            ):
                self._finish("passed: target approach goal failed as expected")
            return

        if phase == "exploration" and self._goal_succeeded(NavigationStatus.GOAL_FRONTIER):
            self._set_phase("approach")
        elif phase == "approach" and self._goal_succeeded(
            NavigationStatus.GOAL_TARGET_APPROACH
        ):
            self._set_phase("return")
        elif phase == "return" and self._goal_succeeded(NavigationStatus.GOAL_BASE_RETURN):
            self._set_phase("complete")
            self._finish("passed: nominal navigation sequence completed")

    def _goal_succeeded(self, goal_type: int) -> bool:
        status = self._latest_status
        if status is None:
            return False
        return (
            status.goal_type == goal_type
            and status.status == NavigationStatus.STATUS_GOAL_SUCCEEDED
        )

    def _set_phase(self, phase_name: str) -> None:
        if phase_name in self._phase_sequence:
            self._phase_index = self._phase_sequence.index(phase_name)
        else:
            self._phase_sequence.append(phase_name)
            self._phase_index = len(self._phase_sequence) - 1
        self._phase_entered_at = time.monotonic()
        self.get_logger().info(f"P3 scenario phase: {phase_name}")

    def _finish(self, summary: str) -> None:
        if self._finished:
            return
        self._finished = True
        if "complete" not in self._phase_sequence:
            self._phase_sequence.append("complete")
        self._phase_index = self._phase_sequence.index("complete")
        self._phase_entered_at = time.monotonic()
        self.get_logger().info(f"P3 scenario result: {summary}")

    def _check_timeout(self) -> None:
        if self._finished or self._final_summary_logged:
            return
        phase_timeout_sec = float(self._scenario.get("phase_timeout_sec", 90.0))
        if time.monotonic() - self._phase_entered_at > phase_timeout_sec:
            self._final_summary_logged = True
            self.get_logger().error(
                f"P3 scenario timeout in phase {self._current_phase()}"
            )

    def _current_phase(self) -> str:
        return self._phase_sequence[min(self._phase_index, len(self._phase_sequence) - 1)]

    def _publish_mission_state(self) -> None:
        phase = self._current_phase()
        state = MissionState()
        state.header.stamp = self.get_clock().now().to_msg()
        state.header.frame_id = self._map_frame_id
        state.phase_name = phase
        state.phase = int(getattr(MissionState, PHASE_TO_CONSTANT.get(phase, "PHASE_IDLE")))
        state.collected_count = 1 if phase in ("return", "unload", "complete") else 0
        state.estimated_score = 30 if state.collected_count else 10
        limit = float(self.get_parameter("mission_time_limit_sec").value)
        state.remaining_time_sec = max(0.0, limit - (time.monotonic() - self._started_at))
        state.fault_code = 0
        state.fault_text = ""
        state.remote_intervention_detected = False
        self._mission_pub.publish(state)

    def _publish_targets(self) -> None:
        target_config = self._scenario.get("target", {})
        target_pose = target_config.get("pose", [2.8, 0.0, 0.0])
        detections = ScienceTargetArray()
        detections.header.stamp = self.get_clock().now().to_msg()
        detections.header.frame_id = self._map_frame_id

        target = ScienceTarget()
        target.header = detections.header
        target.target_id = str(target_config.get("target_id", "p3_target_01"))
        target.target_type = str(target_config.get("target_type", "mock_sample"))
        target.confidence = float(target_config.get("confidence", 0.95))
        target.status = ScienceTarget.STATUS_CONFIRMED
        target.selected_for_sampling = bool(target_config.get("selected", True))
        target.pose = self._pose_stamped(
            x=float(target_pose[0]),
            y=float(target_pose[1]),
            yaw=float(target_pose[2]),
        )
        detections.targets = [target]
        self._target_pub.publish(detections)

    def _pose_stamped(self, *, x: float, y: float, yaw: float):
        pose = PoseStamped()
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.header.frame_id = self._map_frame_id
        pose.pose.position.x = x
        pose.pose.position.y = y
        qx, qy, qz, qw = yaw_to_quaternion_values(yaw)
        pose.pose.orientation.x = qx
        pose.pose.orientation.y = qy
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw
        return pose


def main(args=None) -> None:
    if rclpy is None:
        raise RuntimeError("rclpy is required to run navigation_scenario_driver.")

    rclpy.init(args=args)
    node = NavigationScenarioDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node.destroy_node()
        except (KeyboardInterrupt, RCLError):
            pass
        try:
            rclpy.shutdown()
        except RCLError:
            pass
