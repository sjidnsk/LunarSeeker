from __future__ import annotations

import math
import time

from .navigation_sim_common import (
    load_scenario,
    normalize_angle,
    point_in_rect,
    rect_cells,
    yaw_to_quaternion_values,
)

try:
    import rclpy
    from rclpy._rclpy_pybind11 import RCLError
    from geometry_msgs.msg import TransformStamped, Twist
    from nav_msgs.msg import OccupancyGrid, Odometry
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
    from sensor_msgs.msg import JointState, LaserScan
    from tf2_ros import TransformBroadcaster

    from base_interfaces.msg import MissionState
except ImportError:  # Allows non-ROS static tests to import this module.
    rclpy = None
    RCLError = RuntimeError
    Node = object
    TransformBroadcaster = None
    TransformStamped = None
    Twist = None
    OccupancyGrid = None
    Odometry = None
    JointState = None
    LaserScan = None
    MissionState = None
    QoSProfile = None
    DurabilityPolicy = None
    ReliabilityPolicy = None


class NavigationSimWorld(Node):
    """Lightweight 2D world for P3 Nav2 simulation validation.

    The world is intentionally simple: it publishes a fixed OccupancyGrid,
    ray-cast LaserScan, odometry and TF while integrating the robot pose from
    Nav2's final velocity command. All geometry values are P3 validation
    fixtures and remain 待验证 for real hardware.
    """

    def __init__(self) -> None:
        super().__init__("navigation_sim_world")
        self.declare_parameter("scenario_config", "")
        self.declare_parameter("scenario", "nominal")
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("publish_rate_hz", 20.0)
        self.declare_parameter("scan_rate_hz", 10.0)
        self.declare_parameter("map_rate_hz", 1.0)

        config_path = str(self.get_parameter("scenario_config").value)
        scenario_name = str(self.get_parameter("scenario").value)
        if not config_path:
            raise RuntimeError("scenario_config parameter is required.")
        self._scenario = load_scenario(config_path, scenario_name)

        frames = self._scenario.get("frames", {})
        self._map_frame_id = str(frames.get("map", "map"))
        self._odom_frame_id = str(frames.get("odom", "odom"))
        self._base_footprint_frame_id = str(
            frames.get("base_footprint", "base_footprint")
        )
        self._base_frame_id = str(frames.get("base_link", "base_link"))
        self._scan_frame_id = str(frames.get("scan", self._base_frame_id))

        robot_config = self._scenario.get("robot", {})
        initial_pose = robot_config.get("initial_pose", [0.0, 0.0, 0.0])
        self._x = float(initial_pose[0])
        self._y = float(initial_pose[1])
        self._yaw = float(initial_pose[2])
        self._robot_radius_m = float(robot_config.get("collision_radius_m", 0.45))
        self._wheel_radius_m = float(robot_config.get("wheel_radius_m", 0.13))
        self._wheel_track_m = float(robot_config.get("wheel_track_m", 0.60))
        self._left_wheel_position_rad = 0.0
        self._right_wheel_position_rad = 0.0
        self._left_wheel_velocity_radps = 0.0
        self._right_wheel_velocity_radps = 0.0
        self._max_linear_vel_mps = float(robot_config.get("max_linear_vel_mps", 0.3))
        self._max_angular_vel_radps = float(
            robot_config.get("max_angular_vel_radps", 0.8)
        )
        self._cmd = Twist()
        self._actual_linear_x = 0.0
        self._actual_angular_z = 0.0
        self._current_phase = ""
        self._phase_started_at = time.monotonic()

        self._map_msg = self._build_map()
        self._dynamic_obstacles = self._scenario.get("dynamic_obstacles", [])

        map_qos = QoSProfile(depth=1)
        map_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        map_qos.reliability = ReliabilityPolicy.RELIABLE
        self._map_pub = self.create_publisher(OccupancyGrid, "/map", map_qos)
        self._odom_pub = self.create_publisher(Odometry, "/odom", 10)
        self._scan_pub = self.create_publisher(LaserScan, "/scan", 10)
        self._joint_state_pub = self.create_publisher(JointState, "/joint_states", 10)
        self._tf_broadcaster = TransformBroadcaster(self)
        self._cmd_sub = self.create_subscription(
            Twist,
            str(self.get_parameter("cmd_vel_topic").value),
            self._cmd_callback,
            10,
        )
        self._mission_sub = self.create_subscription(
            MissionState,
            "/mission/state",
            self._mission_callback,
            10,
        )

        self._last_tick = time.monotonic()
        self._last_map_publish = 0.0
        self._last_scan_publish = 0.0
        publish_rate_hz = float(self.get_parameter("publish_rate_hz").value)
        self.create_timer(1.0 / max(publish_rate_hz, 1.0), self._tick)
        self._publish_map()
        self.get_logger().info(f"P3 navigation sim world loaded scenario: {scenario_name}")

    def _cmd_callback(self, command) -> None:
        self._cmd = command

    def _mission_callback(self, state) -> None:
        phase_name = str(state.phase_name)
        if phase_name != self._current_phase:
            self._current_phase = phase_name
            self._phase_started_at = time.monotonic()
            self.get_logger().info(f"P3 sim phase trigger: {phase_name}")

    def _tick(self) -> None:
        now = time.monotonic()
        dt = max(0.0, min(now - self._last_tick, 0.2))
        self._last_tick = now

        self._integrate_pose(dt)
        self._publish_tf_and_odom()

        map_period = 1.0 / max(float(self.get_parameter("map_rate_hz").value), 0.1)
        if now - self._last_map_publish >= map_period:
            self._publish_map()

        scan_period = 1.0 / max(float(self.get_parameter("scan_rate_hz").value), 0.1)
        if now - self._last_scan_publish >= scan_period:
            self._publish_scan()

    def _integrate_pose(self, dt: float) -> None:
        linear_x = max(
            -self._max_linear_vel_mps,
            min(self._max_linear_vel_mps, float(self._cmd.linear.x)),
        )
        angular_z = max(
            -self._max_angular_vel_radps,
            min(self._max_angular_vel_radps, float(self._cmd.angular.z)),
        )
        next_yaw = normalize_angle(self._yaw + angular_z * dt)
        next_x = self._x + linear_x * math.cos(self._yaw) * dt
        next_y = self._y + linear_x * math.sin(self._yaw) * dt

        if not self._pose_collides(next_x, next_y):
            self._x = next_x
            self._y = next_y
            self._actual_linear_x = linear_x
        else:
            self._actual_linear_x = 0.0
        self._yaw = next_yaw
        self._actual_angular_z = angular_z
        self._integrate_wheel_joints(dt)

    def _integrate_wheel_joints(self, dt: float) -> None:
        wheel_radius = max(self._wheel_radius_m, 0.01)
        left_linear_mps = (
            self._actual_linear_x - self._actual_angular_z * self._wheel_track_m / 2.0
        )
        right_linear_mps = (
            self._actual_linear_x + self._actual_angular_z * self._wheel_track_m / 2.0
        )
        self._left_wheel_velocity_radps = left_linear_mps / wheel_radius
        self._right_wheel_velocity_radps = right_linear_mps / wheel_radius
        self._left_wheel_position_rad = normalize_angle(
            self._left_wheel_position_rad + self._left_wheel_velocity_radps * dt
        )
        self._right_wheel_position_rad = normalize_angle(
            self._right_wheel_position_rad + self._right_wheel_velocity_radps * dt
        )

    def _publish_tf_and_odom(self) -> None:
        stamp = self.get_clock().now().to_msg()
        map_to_odom = TransformStamped()
        map_to_odom.header.stamp = stamp
        map_to_odom.header.frame_id = self._map_frame_id
        map_to_odom.child_frame_id = self._odom_frame_id
        map_to_odom.transform.rotation.w = 1.0

        odom_to_base_footprint = TransformStamped()
        odom_to_base_footprint.header.stamp = stamp
        odom_to_base_footprint.header.frame_id = self._odom_frame_id
        odom_to_base_footprint.child_frame_id = self._base_footprint_frame_id
        odom_to_base_footprint.transform.translation.x = float(self._x)
        odom_to_base_footprint.transform.translation.y = float(self._y)
        qx, qy, qz, qw = yaw_to_quaternion_values(self._yaw)
        odom_to_base_footprint.transform.rotation.x = qx
        odom_to_base_footprint.transform.rotation.y = qy
        odom_to_base_footprint.transform.rotation.z = qz
        odom_to_base_footprint.transform.rotation.w = qw
        self._tf_broadcaster.sendTransform([map_to_odom, odom_to_base_footprint])

        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = self._odom_frame_id
        odom.child_frame_id = self._base_footprint_frame_id
        odom.pose.pose.position.x = float(self._x)
        odom.pose.pose.position.y = float(self._y)
        odom.pose.pose.orientation.x = qx
        odom.pose.pose.orientation.y = qy
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        odom.twist.twist.linear.x = float(self._actual_linear_x)
        odom.twist.twist.angular.z = float(self._actual_angular_z)
        self._odom_pub.publish(odom)
        self._publish_joint_states(stamp)

    def _publish_joint_states(self, stamp) -> None:
        joint_state = JointState()
        joint_state.header.stamp = stamp
        joint_state.name = [
            "front_left_wheel_joint",
            "front_right_wheel_joint",
            "rear_left_wheel_joint",
            "rear_right_wheel_joint",
        ]
        joint_state.position = [
            float(self._left_wheel_position_rad),
            float(self._right_wheel_position_rad),
            float(self._left_wheel_position_rad),
            float(self._right_wheel_position_rad),
        ]
        joint_state.velocity = [
            float(self._left_wheel_velocity_radps),
            float(self._right_wheel_velocity_radps),
            float(self._left_wheel_velocity_radps),
            float(self._right_wheel_velocity_radps),
        ]
        self._joint_state_pub.publish(joint_state)

    def _publish_map(self) -> None:
        self._map_msg.header.stamp = self.get_clock().now().to_msg()
        self._map_pub.publish(self._map_msg)
        self._last_map_publish = time.monotonic()

    def _publish_scan(self) -> None:
        scan_config = self._scenario.get("scan", {})
        range_min = float(scan_config.get("range_min_m", 0.05))
        range_max = float(scan_config.get("range_max_m", 4.0))
        beam_count = int(scan_config.get("beam_count", 181))
        ray_step_m = float(scan_config.get("ray_step_m", 0.04))
        angle_min = -math.pi
        angle_max = math.pi
        angle_increment = (angle_max - angle_min) / max(beam_count - 1, 1)

        scan = LaserScan()
        scan.header.stamp = self.get_clock().now().to_msg()
        scan.header.frame_id = self._scan_frame_id
        scan.angle_min = angle_min
        scan.angle_max = angle_max
        scan.angle_increment = angle_increment
        scan.time_increment = 0.0
        scan.scan_time = 1.0 / max(float(self.get_parameter("scan_rate_hz").value), 0.1)
        scan.range_min = range_min
        scan.range_max = range_max
        scan.ranges = [
            self._raycast(self._yaw + angle_min + index * angle_increment, range_min, range_max, ray_step_m)
            for index in range(beam_count)
        ]
        self._scan_pub.publish(scan)
        self._last_scan_publish = time.monotonic()

    def _raycast(
        self,
        world_angle: float,
        range_min: float,
        range_max: float,
        ray_step_m: float,
    ) -> float:
        distance = range_min
        while distance <= range_max:
            x = self._x + math.cos(world_angle) * distance
            y = self._y + math.sin(world_angle) * distance
            if self._is_occupied(x, y):
                return float(distance)
            distance += ray_step_m
        return float("inf")

    def _build_map(self):
        map_config = self._scenario.get("map", {})
        width = int(map_config.get("width", 160))
        height = int(map_config.get("height", 120))
        resolution = float(map_config.get("resolution", 0.05))
        origin = map_config.get("origin", [-2.0, -3.0])
        default_value = int(map_config.get("default", -1))

        grid = [default_value for _ in range(width * height)]
        for rect in map_config.get("free_rects", []):
            self._fill_rect(
                grid=grid,
                width=width,
                height=height,
                resolution=resolution,
                origin_x=float(origin[0]),
                origin_y=float(origin[1]),
                rect=rect,
                value=0,
            )
        for rect in map_config.get("occupied_rects", []):
            self._fill_rect(
                grid=grid,
                width=width,
                height=height,
                resolution=resolution,
                origin_x=float(origin[0]),
                origin_y=float(origin[1]),
                rect=rect,
                value=100,
            )

        occupancy_grid = OccupancyGrid()
        occupancy_grid.header.frame_id = self._map_frame_id
        occupancy_grid.info.width = width
        occupancy_grid.info.height = height
        occupancy_grid.info.resolution = resolution
        occupancy_grid.info.origin.position.x = float(origin[0])
        occupancy_grid.info.origin.position.y = float(origin[1])
        occupancy_grid.info.origin.orientation.w = 1.0
        occupancy_grid.data = grid
        return occupancy_grid

    def _fill_rect(
        self,
        *,
        grid: list[int],
        width: int,
        height: int,
        resolution: float,
        origin_x: float,
        origin_y: float,
        rect: list[float],
        value: int,
    ) -> None:
        x_range, y_range = rect_cells(
            rect=rect,
            origin_x=origin_x,
            origin_y=origin_y,
            resolution=resolution,
            width=width,
            height=height,
        )
        for cell_y in y_range:
            for cell_x in x_range:
                grid[cell_y * width + cell_x] = value

    def _pose_collides(self, x: float, y: float) -> bool:
        samples = [(x, y)]
        for index in range(16):
            angle = index * math.tau / 16.0
            samples.append(
                (
                    x + math.cos(angle) * self._robot_radius_m,
                    y + math.sin(angle) * self._robot_radius_m,
                )
            )
        return any(self._is_occupied(sample_x, sample_y) for sample_x, sample_y in samples)

    def _is_occupied(self, x: float, y: float) -> bool:
        if self._point_in_active_dynamic_obstacle(x, y):
            return True

        info = self._map_msg.info
        cell_x = int(math.floor((x - info.origin.position.x) / info.resolution))
        cell_y = int(math.floor((y - info.origin.position.y) / info.resolution))
        if cell_x < 0 or cell_x >= info.width or cell_y < 0 or cell_y >= info.height:
            return True
        value = self._map_msg.data[cell_y * info.width + cell_x]
        return int(value) >= 50

    def _point_in_active_dynamic_obstacle(self, x: float, y: float) -> bool:
        now = time.monotonic()
        phase_age = now - self._phase_started_at
        for obstacle in self._dynamic_obstacles:
            trigger_phase = str(obstacle.get("trigger_phase", "any"))
            if trigger_phase != "any" and trigger_phase != self._current_phase:
                continue
            start_after_sec = float(obstacle.get("start_after_sec", 0.0))
            if phase_age < start_after_sec:
                continue
            clear_after_sec = obstacle.get("clear_after_sec")
            if clear_after_sec is not None and phase_age > float(clear_after_sec):
                continue
            if point_in_rect(x, y, obstacle.get("rect", [0.0, 0.0, 0.0, 0.0])):
                return True
        return False


def main(args=None) -> None:
    if rclpy is None:
        raise RuntimeError("rclpy is required to run navigation_sim_world.")

    rclpy.init(args=args)
    node = NavigationSimWorld()
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
