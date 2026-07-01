from __future__ import annotations

import math
import time
from collections.abc import Sequence

try:
    import rclpy
    from action_msgs.msg import GoalStatus
    from geometry_msgs.msg import PoseStamped
    from nav2_msgs.action import NavigateToPose
    from nav_msgs.msg import OccupancyGrid
    from rclpy.action import ActionClient
    from rclpy.executors import ExternalShutdownException
    from rclpy.node import Node
    from rclpy.time import Time
    from tf2_geometry_msgs import do_transform_pose
    from tf2_ros import Buffer, TransformException, TransformListener

    from base_interfaces.msg import MissionState, NavigationStatus, ScienceTargetArray
except ImportError:  # Allows non-ROS unit tests to import pure helpers.
    rclpy = None
    GoalStatus = None
    PoseStamped = None
    NavigateToPose = None
    OccupancyGrid = None
    ActionClient = None
    ExternalShutdownException = RuntimeError
    Node = object
    Time = None
    do_transform_pose = None
    Buffer = None
    TransformException = Exception
    TransformListener = None
    MissionState = None
    NavigationStatus = None
    ScienceTargetArray = None

try:
    from .navigation_goals import (
        GOAL_BASE_EXIT,
        GOAL_BASE_RETURN,
        GOAL_FRONTIER,
        GOAL_HOLD_POSITION,
        GOAL_NONE,
        GOAL_SAMPLE_DROP_ZONE,
        GOAL_TARGET_APPROACH,
        BlacklistedGoal,
        approach_goal_from_robot,
        fixed_goal_for_label,
        goal_label_for_phase,
        goal_type_for_label,
        is_goal_blacklisted,
        prune_blacklist,
    )
    from .search_strategy import (
        FrontierSelectionConfig,
        NavigationGoal,
        OccupancyGridData,
        SearchArea,
        frontier_goals,
        normalize_angle,
    )
except ImportError:  # Allows direct importlib loading in unit tests.
    from algo_navigation.navigation_goals import (
        GOAL_BASE_EXIT,
        GOAL_BASE_RETURN,
        GOAL_FRONTIER,
        GOAL_HOLD_POSITION,
        GOAL_NONE,
        GOAL_SAMPLE_DROP_ZONE,
        GOAL_TARGET_APPROACH,
        BlacklistedGoal,
        approach_goal_from_robot,
        fixed_goal_for_label,
        goal_label_for_phase,
        goal_type_for_label,
        is_goal_blacklisted,
        prune_blacklist,
    )
    from algo_navigation.search_strategy import (
        FrontierSelectionConfig,
        NavigationGoal,
        OccupancyGridData,
        SearchArea,
        frontier_goals,
        normalize_angle,
    )


ACTION_PHASES = {"departure", "exploration", "approach", "return", "unload"}
IDLE_PHASES = {"ready", "sample", "complete"}
STATUS_GOAL_TYPES = {
    GOAL_NONE: "none",
    GOAL_BASE_EXIT: "base_exit",
    GOAL_FRONTIER: "frontier",
    GOAL_TARGET_APPROACH: "target_approach",
    GOAL_BASE_RETURN: "base_return",
    GOAL_SAMPLE_DROP_ZONE: "sample_drop_zone",
    GOAL_HOLD_POSITION: "hold_position",
}


def yaw_to_quaternion_z_w(yaw: float) -> tuple[float, float]:
    normalized = normalize_angle(yaw)
    return math.sin(normalized * 0.5), math.cos(normalized * 0.5)


def pose_stamped_from_goal(navigation_goal: NavigationGoal, *, frame_id: str):
    pose = PoseStamped()
    pose.header.frame_id = frame_id
    pose.pose.position.x = navigation_goal.x
    pose.pose.position.y = navigation_goal.y
    pose.pose.position.z = 0.0
    qz, qw = yaw_to_quaternion_z_w(navigation_goal.yaw)
    pose.pose.orientation.z = qz
    pose.pose.orientation.w = qw
    return pose


def goal_key(phase_name: str, goal: NavigationGoal, *, frame_id: str) -> str:
    return f"{phase_name}:{frame_id}:{goal.label}:{goal.x:.3f}:{goal.y:.3f}:{goal.yaw:.3f}"


class NavigationCoordinator(Node):
    """Coordinate mission phases and strategy goals with Nav2 NavigateToPose."""

    def __init__(self) -> None:
        super().__init__("navigation_coordinator")
        self.declare_parameter("map_frame_id", "map")
        self.declare_parameter("robot_base_frame_id", "base_link")
        self.declare_parameter("navigate_action_name", "/navigate_to_pose")
        self.declare_parameter("status_topic", "/navigation/status")
        self.declare_parameter("target_standoff_m", 0.45)
        self.declare_parameter("frontier.occupied_threshold", 50)
        self.declare_parameter("frontier.min_cluster_size", 3)
        self.declare_parameter("frontier.blacklist_ttl_sec", 30.0)
        self.declare_parameter("frontier.blacklist_radius_m", 0.5)
        self.declare_parameter("task_area.enabled", True)
        self.declare_parameter("task_area.min_x", 1.6)
        self.declare_parameter("task_area.max_x", 3.2)
        self.declare_parameter("task_area.min_y", -0.8)
        self.declare_parameter("task_area.max_y", 0.8)
        self.declare_parameter("task_area.distance_weight", 4.0)
        self.declare_parameter("task_area.inside_bonus", 100.0)
        self.declare_parameter("nav.retry_limit", 1)
        self.declare_parameter("fixed_goal.base_exit", [0.8, 0.0, 0.0])
        self.declare_parameter("fixed_goal.base_return", [0.2, 0.0, 0.0])
        self.declare_parameter("fixed_goal.sample_drop_zone", [-0.3, 0.0, 0.0])

        self._map_frame_id = str(self.get_parameter("map_frame_id").value)
        self._robot_base_frame_id = str(self.get_parameter("robot_base_frame_id").value)
        self._navigate_action_name = str(self.get_parameter("navigate_action_name").value)
        self._status_topic = str(self.get_parameter("status_topic").value)

        self._latest_state = None
        self._latest_map = None
        self._latest_targets = None
        self._goal_handle = None
        self._goal_pending = False
        self._goal_active = False
        self._current_goal_key = ""
        self._current_goal_label = ""
        self._current_goal_type = GOAL_NONE
        self._current_goal_pose = None
        self._retry_counts: dict[str, int] = {}
        self._failure_count = 0
        self._recovery_count = 0
        self._distance_remaining_m = -1.0
        self._last_result = "none"
        self._blacklist: list[BlacklistedGoal] = []
        self._status = NavigationStatus.STATUS_IDLE
        self._status_text = "idle"
        self._detail = ""

        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        self._action_client = ActionClient(
            self,
            NavigateToPose,
            self._navigate_action_name,
        )
        self._status_pub = self.create_publisher(
            NavigationStatus,
            self._status_topic,
            10,
        )
        self._mission_sub = self.create_subscription(
            MissionState,
            "/mission/state",
            self._mission_callback,
            10,
        )
        self._map_sub = self.create_subscription(
            OccupancyGrid,
            "/map",
            self._map_callback,
            10,
        )
        self._target_sub = self.create_subscription(
            ScienceTargetArray,
            "/target_detections",
            self._target_callback,
            10,
        )
        self.create_timer(0.5, self._tick)

    def _mission_callback(self, state) -> None:
        previous_phase = self._phase_name()
        self._latest_state = state
        if previous_phase != self._phase_name():
            self._current_goal_key = ""
            if self._phase_name() in IDLE_PHASES or self._phase_name() == "fault":
                self._cancel_active_goal()

    def _map_callback(self, occupancy_grid) -> None:
        self._latest_map = occupancy_grid

    def _target_callback(self, detections) -> None:
        self._latest_targets = detections

    def _tick(self) -> None:
        phase_name = self._phase_name()
        if self._latest_state is None:
            self._set_status(
                NavigationStatus.STATUS_WAITING_FOR_INPUT,
                "waiting_for_mission_state",
                detail="waiting for /mission/state",
            )
            self._publish_status()
            return

        if phase_name == "fault":
            self._cancel_active_goal()
            self._set_status(NavigationStatus.STATUS_FAULT, "fault")
            self._publish_status()
            return

        if phase_name in IDLE_PHASES:
            self._cancel_active_goal()
            self._set_status(NavigationStatus.STATUS_IDLE, "idle")
            self._publish_status()
            return

        if self._goal_pending or self._goal_active:
            self._publish_status()
            return

        if phase_name not in ACTION_PHASES:
            self._set_status(
                NavigationStatus.STATUS_IDLE,
                "idle",
                detail=f"phase {phase_name} has no navigation action",
            )
            self._publish_status()
            return

        goal = self._build_goal_for_phase(phase_name)
        if goal is None:
            self._publish_status()
            return

        pose = pose_stamped_from_goal(goal, frame_id=self._map_frame_id)
        pose.header.stamp = self.get_clock().now().to_msg()
        key = goal_key(phase_name, goal, frame_id=pose.header.frame_id)
        if key == self._current_goal_key and self._last_result == "succeeded":
            self._publish_status()
            return

        if not self._action_client.wait_for_server(timeout_sec=0.0):
            self._current_goal_label = goal.label
            self._current_goal_type = goal_type_for_label(goal.label)
            self._current_goal_pose = pose
            self._set_status(
                NavigationStatus.STATUS_WAITING_FOR_NAV2,
                "waiting_for_nav2",
                detail=f"action server {self._navigate_action_name} is not available",
            )
            self._publish_status()
            return

        self._send_goal(goal, pose, key)

    def _build_goal_for_phase(self, phase_name: str) -> NavigationGoal | None:
        goal_label = goal_label_for_phase(phase_name)
        if phase_name == "exploration":
            return self._build_frontier_goal()
        if phase_name == "approach":
            return self._build_target_approach_goal()
        return self._fixed_goal_from_parameters(goal_label)

    def _build_frontier_goal(self) -> NavigationGoal | None:
        if self._latest_map is None:
            self._set_status(
                NavigationStatus.STATUS_WAITING_FOR_INPUT,
                "waiting_for_map",
                goal_type=GOAL_FRONTIER,
                goal_label="frontier_exploration",
                detail="waiting for /map",
            )
            return None

        robot_xy = self._robot_xy()
        if robot_xy is None:
            self._set_status(
                NavigationStatus.STATUS_WAITING_FOR_INPUT,
                "waiting_for_tf",
                goal_type=GOAL_FRONTIER,
                goal_label="frontier_exploration",
                detail=f"waiting for {self._map_frame_id}->{self._robot_base_frame_id}",
            )
            return None

        now_sec = time.monotonic()
        self._blacklist = prune_blacklist(self._blacklist, now_sec=now_sec)
        radius_m = float(self.get_parameter("frontier.blacklist_radius_m").value)
        candidates = frontier_goals(
            self._grid_data_from_map(self._latest_map),
            robot_x=robot_xy[0],
            robot_y=robot_xy[1],
            config=self._build_frontier_config(),
        )
        for candidate in candidates:
            if not is_goal_blacklisted(
                candidate,
                self._blacklist,
                now_sec=now_sec,
                radius_m=radius_m,
            ):
                return candidate

        self._set_status(
            NavigationStatus.STATUS_RETURN_RECOMMENDED,
            "return_recommended",
            goal_type=GOAL_FRONTIER,
            goal_label="frontier_exploration",
            detail="no unblocked frontier candidates",
        )
        return None

    def _build_target_approach_goal(self) -> NavigationGoal | None:
        if self._latest_targets is None:
            self._set_status(
                NavigationStatus.STATUS_WAITING_FOR_INPUT,
                "waiting_for_target",
                goal_type=GOAL_TARGET_APPROACH,
                goal_label="selected_target",
                detail="waiting for /target_detections",
            )
            return None

        selected = [
            target
            for target in self._latest_targets.targets
            if target.selected_for_sampling and target.pose.header.frame_id
        ]
        if not selected:
            self._set_status(
                NavigationStatus.STATUS_WAITING_FOR_INPUT,
                "waiting_for_selected_target",
                goal_type=GOAL_TARGET_APPROACH,
                goal_label="selected_target",
            )
            return None

        robot_xy = self._robot_xy()
        target_pose = self._pose_in_map(selected[0].pose)
        if robot_xy is None or target_pose is None:
            self._set_status(
                NavigationStatus.STATUS_WAITING_FOR_INPUT,
                "waiting_for_tf",
                goal_type=GOAL_TARGET_APPROACH,
                goal_label="selected_target",
                detail="target or robot transform is not available",
            )
            return None

        return approach_goal_from_robot(
            robot_x=robot_xy[0],
            robot_y=robot_xy[1],
            target_x=float(target_pose.pose.position.x),
            target_y=float(target_pose.pose.position.y),
            standoff_m=float(self.get_parameter("target_standoff_m").value),
        )

    def _fixed_goal_from_parameters(self, label: str) -> NavigationGoal | None:
        parameter_name = {
            "base_exit": "fixed_goal.base_exit",
            "base_return": "fixed_goal.base_return",
            "sample_drop_zone": "fixed_goal.sample_drop_zone",
        }.get(label)
        if parameter_name is None:
            return fixed_goal_for_label(label)

        value = list(self.get_parameter(parameter_name).value)
        if len(value) < 2:
            self._set_status(
                NavigationStatus.STATUS_FAULT,
                "invalid_fixed_goal",
                goal_label=label,
                detail=f"{parameter_name} must contain at least x and y",
            )
            return None

        yaw = float(value[2]) if len(value) >= 3 else 0.0
        return NavigationGoal(label=label, x=float(value[0]), y=float(value[1]), yaw=yaw)

    def _send_goal(self, goal: NavigationGoal, pose, key: str) -> None:
        self._current_goal_key = key
        self._current_goal_label = goal.label
        self._current_goal_type = goal_type_for_label(goal.label)
        self._current_goal_pose = pose
        self._last_result = "none"
        self._goal_pending = True
        self._goal_active = False
        self._set_status(
            NavigationStatus.STATUS_GOAL_PENDING,
            "goal_pending",
            goal_type=self._current_goal_type,
            goal_label=goal.label,
            goal_pose=pose,
        )
        self._publish_status()

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = pose
        goal_msg.behavior_tree = ""
        future = self._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self._feedback_callback,
        )
        future.add_done_callback(self._goal_response_callback)

    def _goal_response_callback(self, future) -> None:
        self._goal_pending = False
        goal_handle = future.result()
        if not goal_handle.accepted:
            self._handle_failed_goal("rejected")
            return

        self._goal_handle = goal_handle
        self._goal_active = True
        self._set_status(
            NavigationStatus.STATUS_GOAL_ACTIVE,
            "goal_active",
            goal_type=self._current_goal_type,
            goal_label=self._current_goal_label,
            goal_pose=self._current_goal_pose,
        )
        self._publish_status()
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._result_callback)

    def _feedback_callback(self, feedback_msg) -> None:
        feedback = feedback_msg.feedback
        self._distance_remaining_m = float(feedback.distance_remaining)
        self._recovery_count = int(feedback.number_of_recoveries)
        self._set_status(
            NavigationStatus.STATUS_GOAL_ACTIVE,
            "goal_active",
            goal_type=self._current_goal_type,
            goal_label=self._current_goal_label,
            goal_pose=self._current_goal_pose,
        )
        self._publish_status()

    def _result_callback(self, future) -> None:
        result = future.result()
        self._goal_handle = None
        self._goal_active = False
        self._goal_pending = False
        if result.status == GoalStatus.STATUS_SUCCEEDED:
            self._last_result = "succeeded"
            self._set_status(
                NavigationStatus.STATUS_GOAL_SUCCEEDED,
                "goal_succeeded",
                goal_type=self._current_goal_type,
                goal_label=self._current_goal_label,
                goal_pose=self._current_goal_pose,
            )
            self._publish_status()
            return
        if result.status == GoalStatus.STATUS_CANCELED:
            self._last_result = "canceled"
            self._set_status(
                NavigationStatus.STATUS_GOAL_CANCELED,
                "goal_canceled",
                goal_type=self._current_goal_type,
                goal_label=self._current_goal_label,
                goal_pose=self._current_goal_pose,
            )
            self._publish_status()
            return

        self._handle_failed_goal("aborted")

    def _handle_failed_goal(self, result_text: str) -> None:
        self._failure_count += 1
        self._last_result = result_text
        key = self._current_goal_key
        retry_count = self._retry_counts.get(key, 0) + 1
        self._retry_counts[key] = retry_count

        if self._current_goal_type == GOAL_FRONTIER and self._current_goal_pose is not None:
            ttl_sec = float(self.get_parameter("frontier.blacklist_ttl_sec").value)
            self._blacklist.append(
                BlacklistedGoal(
                    x=float(self._current_goal_pose.pose.position.x),
                    y=float(self._current_goal_pose.pose.position.y),
                    expires_at_sec=time.monotonic() + ttl_sec,
                )
            )
            self._current_goal_key = ""
        elif retry_count <= int(self.get_parameter("nav.retry_limit").value):
            self._current_goal_key = ""

        self._goal_active = False
        self._goal_pending = False
        self._set_status(
            NavigationStatus.STATUS_GOAL_FAILED,
            "goal_failed",
            goal_type=self._current_goal_type,
            goal_label=self._current_goal_label,
            goal_pose=self._current_goal_pose,
            detail=result_text,
        )
        self._publish_status()

    def _cancel_active_goal(self) -> None:
        if self._goal_handle is not None:
            self._goal_handle.cancel_goal_async()
        self._goal_handle = None
        self._goal_active = False
        self._goal_pending = False

    def _robot_xy(self) -> tuple[float, float] | None:
        try:
            transform = self._tf_buffer.lookup_transform(
                self._map_frame_id,
                self._robot_base_frame_id,
                Time(),
            )
        except TransformException:
            return None
        return (
            float(transform.transform.translation.x),
            float(transform.transform.translation.y),
        )

    def _pose_in_map(self, pose) -> object | None:
        if pose.header.frame_id == self._map_frame_id:
            return pose
        try:
            transform = self._tf_buffer.lookup_transform(
                self._map_frame_id,
                pose.header.frame_id,
                Time(),
            )
        except TransformException:
            return None
        return do_transform_pose(pose, transform)

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

    def _phase_name(self) -> str:
        if self._latest_state is None:
            return "unknown"
        return str(self._latest_state.phase_name)

    def _set_status(
        self,
        status: int,
        status_text: str,
        *,
        goal_type: int | None = None,
        goal_label: str | None = None,
        goal_pose=None,
        detail: str = "",
    ) -> None:
        self._status = status
        self._status_text = status_text
        self._detail = detail
        if goal_type is not None:
            self._current_goal_type = goal_type
        if goal_label is not None:
            self._current_goal_label = goal_label
        if goal_pose is not None:
            self._current_goal_pose = goal_pose

    def _publish_status(self) -> None:
        status = NavigationStatus()
        status.header.stamp = self.get_clock().now().to_msg()
        status.header.frame_id = self._map_frame_id
        if self._latest_state is not None:
            status.mission_phase = int(self._latest_state.phase)
            status.mission_phase_name = str(self._latest_state.phase_name)
        status.status = int(self._status)
        status.status_text = self._status_text
        status.goal_type = int(self._current_goal_type)
        status.goal_label = self._current_goal_label
        status.goal_pose = self._current_goal_pose or PoseStamped()
        status.nav2_available = self._action_client.server_is_ready()
        status.goal_active = bool(self._goal_pending or self._goal_active)
        status.retry_count = int(
            self._retry_counts.get(self._current_goal_key, 0)
        )
        status.failure_count = int(self._failure_count)
        status.recovery_count = int(self._recovery_count)
        status.distance_remaining_m = float(self._distance_remaining_m)
        status.last_result = self._last_result
        status.detail = self._detail
        self._status_pub.publish(status)


def goal_type_name(goal_type: int) -> str:
    return STATUS_GOAL_TYPES.get(goal_type, "unknown")


def navigation_goal_from_values(
    label: str,
    values: Sequence[float],
) -> NavigationGoal:
    if len(values) < 2:
        raise ValueError("navigation goal values must include x and y")
    yaw = float(values[2]) if len(values) >= 3 else 0.0
    return NavigationGoal(label=label, x=float(values[0]), y=float(values[1]), yaw=yaw)


def main(args=None) -> None:
    if rclpy is None:
        raise RuntimeError("rclpy is required to run navigation_coordinator.")

    rclpy.init(args=args)
    node = NavigationCoordinator()
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
