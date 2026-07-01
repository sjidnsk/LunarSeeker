from __future__ import annotations

try:
    import rclpy
    from geometry_msgs.msg import Pose
    from nav_msgs.msg import OccupancyGrid
    from rclpy.node import Node
    from rclpy.executors import ExternalShutdownException
    from rclpy.qos import DurabilityPolicy, QoSProfile
except ImportError:  # Allows import checks without ROS.
    rclpy = None
    Node = object
    ExternalShutdownException = RuntimeError
    OccupancyGrid = None
    Pose = None
    DurabilityPolicy = None
    QoSProfile = None


UNKNOWN = -1
FREE = 0
OCCUPIED = 100


class MockFrontierMap(Node):
    """Publish a small OccupancyGrid with free, occupied, and unknown regions."""

    def __init__(self) -> None:
        super().__init__("mock_frontier_map")
        self.declare_parameter("frame_id", "odom")
        self.declare_parameter("publish_rate_hz", 1.0)
        self.declare_parameter("width", 70)
        self.declare_parameter("height", 50)
        self.declare_parameter("resolution", 0.1)
        self.declare_parameter("origin_x", -1.5)
        self.declare_parameter("origin_y", -2.0)

        qos = QoSProfile(depth=1)
        qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self._map_pub = self.create_publisher(OccupancyGrid, "/map", qos)
        self._map = self._build_map()

        rate_hz = float(self.get_parameter("publish_rate_hz").value)
        self.create_timer(1.0 / max(rate_hz, 0.1), self._publish_map)

    def _publish_map(self) -> None:
        self._map.header.stamp = self.get_clock().now().to_msg()
        self._map_pub.publish(self._map)

    def _build_map(self) -> OccupancyGrid:
        width = int(self.get_parameter("width").value)
        height = int(self.get_parameter("height").value)
        resolution = float(self.get_parameter("resolution").value)
        origin_x = float(self.get_parameter("origin_x").value)
        origin_y = float(self.get_parameter("origin_y").value)
        data = [UNKNOWN for _ in range(width * height)]

        def cell_range(minimum: float, maximum: float, origin: float, limit: int):
            start = max(0, int((minimum - origin) / resolution))
            end = min(limit, int((maximum - origin) / resolution) + 1)
            return range(start, end)

        def fill_rect(
            *,
            min_x: float,
            max_x: float,
            min_y: float,
            max_y: float,
            value: int,
        ) -> None:
            for cell_y in cell_range(min_y, max_y, origin_y, height):
                for cell_x in cell_range(min_x, max_x, origin_x, width):
                    data[cell_y * width + cell_x] = value

        # 已知自由区从基地延伸到任务区入口；范围为 mock 调试值，待实测。
        fill_rect(min_x=-0.8, max_x=1.55, min_y=-1.0, max_y=1.0, value=FREE)
        fill_rect(min_x=1.55, max_x=2.15, min_y=-0.45, max_y=0.45, value=FREE)
        # 简单障碍用于检查 frontier 策略不会把 occupied cell 当目标。
        fill_rect(min_x=0.45, max_x=0.75, min_y=-0.95, max_y=-0.15, value=OCCUPIED)
        fill_rect(min_x=1.0, max_x=1.25, min_y=0.25, max_y=0.9, value=OCCUPIED)

        grid = OccupancyGrid()
        grid.header.frame_id = str(self.get_parameter("frame_id").value)
        grid.info.width = width
        grid.info.height = height
        grid.info.resolution = resolution
        grid.info.origin = Pose()
        grid.info.origin.position.x = origin_x
        grid.info.origin.position.y = origin_y
        grid.info.origin.orientation.w = 1.0
        grid.data = data
        return grid


def main(args=None) -> None:
    if rclpy is None:
        raise RuntimeError("rclpy is required to run mock_frontier_map.")

    rclpy.init(args=args)
    node = MockFrontierMap()
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
