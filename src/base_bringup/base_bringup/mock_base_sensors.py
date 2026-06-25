from __future__ import annotations

import math
from typing import List

try:
    import rclpy
    from geometry_msgs.msg import TransformStamped
    from nav_msgs.msg import Odometry
    from rclpy.node import Node
    from sensor_msgs.msg import Imu, JointState, LaserScan
    from tf2_ros import StaticTransformBroadcaster, TransformBroadcaster

    from base_interfaces.msg import ScienceTarget, ScienceTargetArray
except ImportError:  # Allows non-ROS unit tests to import this module.
    rclpy = None
    TransformStamped = None
    Odometry = None
    Node = object
    Imu = None
    JointState = None
    LaserScan = None
    StaticTransformBroadcaster = None
    TransformBroadcaster = None
    ScienceTarget = None
    ScienceTargetArray = None


def yaw_to_quaternion(yaw: float):
    quaternion_z = math.sin(yaw * 0.5)
    quaternion_w = math.cos(yaw * 0.5)
    return 0.0, 0.0, quaternion_z, quaternion_w


class MockBaseSensors(Node):
    """Publish deterministic mock base, sensor, joint, and target topics."""

    def __init__(self) -> None:
        super().__init__("mock_base_sensors")
        self.declare_parameter("publish_rate_hz", 10.0)
        self.declare_parameter("map_frame_id", "map")
        self.declare_parameter("odom_frame_id", "odom")
        self.declare_parameter("base_frame_id", "base_link")
        self.declare_parameter("lidar_frame_id", "lidar_link")
        self.declare_parameter("imu_frame_id", "imu_link")
        self.declare_parameter("target_frame_id", "base_link")
        self.declare_parameter("linear_speed_mps", 0.05)
        self.declare_parameter("yaw_rate_rps", 0.0)
        self.declare_parameter("selected_target_id", "mock_target_01")

        self._odom_pub = self.create_publisher(Odometry, "/odom", 10)
        self._scan_pub = self.create_publisher(LaserScan, "/scan", 10)
        self._imu_pub = self.create_publisher(Imu, "/imu/data", 10)
        self._joint_pub = self.create_publisher(JointState, "/joint_states", 10)
        self._target_pub = self.create_publisher(
            ScienceTargetArray, "/target_detections", 10
        )
        self._tf_broadcaster = TransformBroadcaster(self)
        self._static_tf_broadcaster = StaticTransformBroadcaster(self)
        self._started_at = self.get_clock().now()
        self._publish_static_map_to_odom()

        rate_hz = float(self.get_parameter("publish_rate_hz").value)
        period_sec = 1.0 / max(rate_hz, 0.1)
        self.create_timer(period_sec, self._publish_mock_state)

    def _elapsed_sec(self) -> float:
        return (self.get_clock().now() - self._started_at).nanoseconds / 1e9

    def _publish_mock_state(self) -> None:
        now = self.get_clock().now().to_msg()
        elapsed = self._elapsed_sec()
        linear_speed = float(self.get_parameter("linear_speed_mps").value)
        yaw_rate = float(self.get_parameter("yaw_rate_rps").value)
        yaw = yaw_rate * elapsed
        x = linear_speed * elapsed
        qx, qy, qz, qw = yaw_to_quaternion(yaw)

        odom_frame = str(self.get_parameter("odom_frame_id").value)
        base_frame = str(self.get_parameter("base_frame_id").value)
        lidar_frame = str(self.get_parameter("lidar_frame_id").value)
        imu_frame = str(self.get_parameter("imu_frame_id").value)
        target_frame = str(self.get_parameter("target_frame_id").value)

        self._publish_odom(now, odom_frame, base_frame, x, qx, qy, qz, qw)
        self._publish_tf(now, odom_frame, base_frame, x, qx, qy, qz, qw)
        self._publish_scan(now, lidar_frame)
        self._publish_imu(now, imu_frame, qx, qy, qz, qw, yaw_rate)
        self._publish_joint_states(now)
        self._publish_mock_targets(now, target_frame)

    def _publish_odom(
        self,
        stamp,
        odom_frame: str,
        base_frame: str,
        x: float,
        qx: float,
        qy: float,
        qz: float,
        qw: float,
    ) -> None:
        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = odom_frame
        odom.child_frame_id = base_frame
        odom.pose.pose.position.x = x
        odom.pose.pose.position.y = 0.0
        odom.pose.pose.position.z = 0.0
        odom.pose.pose.orientation.x = qx
        odom.pose.pose.orientation.y = qy
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        odom.twist.twist.linear.x = float(
            self.get_parameter("linear_speed_mps").value
        )
        odom.twist.twist.angular.z = float(self.get_parameter("yaw_rate_rps").value)
        odom.pose.covariance = self._pose_covariance()
        odom.twist.covariance = self._twist_covariance()
        self._odom_pub.publish(odom)

    def _publish_tf(
        self,
        stamp,
        odom_frame: str,
        base_frame: str,
        x: float,
        qx: float,
        qy: float,
        qz: float,
        qw: float,
    ) -> None:
        transform = TransformStamped()
        transform.header.stamp = stamp
        transform.header.frame_id = odom_frame
        transform.child_frame_id = base_frame
        transform.transform.translation.x = x
        transform.transform.translation.y = 0.0
        transform.transform.translation.z = 0.0
        transform.transform.rotation.x = qx
        transform.transform.rotation.y = qy
        transform.transform.rotation.z = qz
        transform.transform.rotation.w = qw
        self._tf_broadcaster.sendTransform(transform)

    def _publish_static_map_to_odom(self) -> None:
        transform = TransformStamped()
        transform.header.stamp = self.get_clock().now().to_msg()
        transform.header.frame_id = str(self.get_parameter("map_frame_id").value)
        transform.child_frame_id = str(self.get_parameter("odom_frame_id").value)
        transform.transform.translation.x = 0.0
        transform.transform.translation.y = 0.0
        transform.transform.translation.z = 0.0
        transform.transform.rotation.w = 1.0
        self._static_tf_broadcaster.sendTransform(transform)

    def _publish_scan(self, stamp, lidar_frame: str) -> None:
        sample_count = 181
        scan = LaserScan()
        scan.header.stamp = stamp
        scan.header.frame_id = lidar_frame
        scan.angle_min = -math.pi
        scan.angle_max = math.pi
        scan.angle_increment = (scan.angle_max - scan.angle_min) / (sample_count - 1)
        scan.time_increment = 0.0
        scan.scan_time = 0.1
        scan.range_min = 0.10
        scan.range_max = 10.0
        scan.ranges = self._mock_ranges(sample_count)
        self._scan_pub.publish(scan)

    def _publish_imu(
        self,
        stamp,
        imu_frame: str,
        qx: float,
        qy: float,
        qz: float,
        qw: float,
        yaw_rate: float,
    ) -> None:
        imu = Imu()
        imu.header.stamp = stamp
        imu.header.frame_id = imu_frame
        imu.orientation.x = qx
        imu.orientation.y = qy
        imu.orientation.z = qz
        imu.orientation.w = qw
        imu.angular_velocity.z = yaw_rate
        imu.linear_acceleration.x = 0.0
        imu.linear_acceleration.y = 0.0
        imu.linear_acceleration.z = 9.81
        self._imu_pub.publish(imu)

    def _publish_joint_states(self, stamp) -> None:
        joint_state = JointState()
        joint_state.header.stamp = stamp
        joint_state.name = [
            "front_left_wheel_joint",
            "front_right_wheel_joint",
            "rear_left_wheel_joint",
            "rear_right_wheel_joint",
        ]
        joint_state.position = [0.0, 0.0, 0.0, 0.0]
        joint_state.velocity = [0.0, 0.0, 0.0, 0.0]
        self._joint_pub.publish(joint_state)

    def _publish_mock_targets(self, stamp, target_frame: str) -> None:
        targets = ScienceTargetArray()
        targets.header.stamp = stamp
        targets.header.frame_id = target_frame
        targets.targets = [
            self._build_target(
                stamp=stamp,
                frame_id=target_frame,
                target_id="mock_target_01",
                target_type="basalt_sample",
                confidence=0.92,
                xyz=(1.20, 0.22, 0.16),
                selected=True,
            ),
            self._build_target(
                stamp=stamp,
                frame_id=target_frame,
                target_id="mock_target_02",
                target_type="anorthosite_sample",
                confidence=0.74,
                xyz=(1.65, -0.30, 0.18),
                selected=False,
            ),
        ]
        self._target_pub.publish(targets)

    def _build_target(
        self,
        stamp,
        frame_id: str,
        target_id: str,
        target_type: str,
        confidence: float,
        xyz: tuple[float, float, float],
        selected: bool,
    ):
        target = ScienceTarget()
        target.header.stamp = stamp
        target.header.frame_id = frame_id
        target.target_id = target_id
        target.target_type = target_type
        target.confidence = confidence
        target.pose.header.stamp = stamp
        target.pose.header.frame_id = frame_id
        target.pose.pose.position.x = xyz[0]
        target.pose.pose.position.y = xyz[1]
        target.pose.pose.position.z = xyz[2]
        target.pose.pose.orientation.w = 1.0
        target.status = (
            ScienceTarget.STATUS_CONFIRMED
            if selected
            else ScienceTarget.STATUS_CANDIDATE
        )
        target.selected_for_sampling = selected
        return target

    @staticmethod
    def _mock_ranges(sample_count: int) -> List[float]:
        ranges = [3.0] * sample_count
        front_index = sample_count // 2
        for offset in range(-6, 7):
            ranges[front_index + offset] = 2.0
        return ranges

    @staticmethod
    def _pose_covariance() -> List[float]:
        covariance = [0.0] * 36
        covariance[0] = 0.02
        covariance[7] = 0.02
        covariance[14] = 0.05
        covariance[21] = 0.1
        covariance[28] = 0.1
        covariance[35] = 0.05
        return covariance

    @staticmethod
    def _twist_covariance() -> List[float]:
        covariance = [0.0] * 36
        covariance[0] = 0.01
        covariance[7] = 0.01
        covariance[35] = 0.02
        return covariance


def main(args=None) -> None:
    if rclpy is None:
        raise RuntimeError("rclpy is required to run mock_base_sensors.")

    rclpy.init(args=args)
    node = MockBaseSensors()
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
