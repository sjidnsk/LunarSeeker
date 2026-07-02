from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    params_file = LaunchConfiguration("params_file")
    scan_topic = LaunchConfiguration("scan_topic")
    map_frame = LaunchConfiguration("map_frame")
    odom_frame = LaunchConfiguration("odom_frame")
    base_frame = LaunchConfiguration("base_frame")
    use_sim_time = LaunchConfiguration("use_sim_time")
    log_level = LaunchConfiguration("log_level")

    default_params_file = PathJoinSubstitution(
        [FindPackageShare("algo_localization"), "config", "slam_toolbox_mapping.yaml"]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "params_file",
                default_value=default_params_file,
                description="slam_toolbox mapping parameter file.",
            ),
            DeclareLaunchArgument(
                "scan_topic",
                default_value="/scan",
                description="LaserScan topic consumed by slam_toolbox.",
            ),
            DeclareLaunchArgument(
                "map_frame",
                default_value="map",
                description="Map frame published by slam_toolbox.",
            ),
            DeclareLaunchArgument(
                "odom_frame",
                default_value="odom",
                description="Continuous odometry frame provided by EKF.",
            ),
            DeclareLaunchArgument(
                "base_frame",
                default_value="base_footprint",
                description="Robot base frame used by slam_toolbox scan matching.",
            ),
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use simulation clock when replaying bags with /clock.",
            ),
            DeclareLaunchArgument(
                "log_level",
                default_value="info",
                description="Log level for slam_toolbox.",
            ),
            Node(
                package="slam_toolbox",
                executable="async_slam_toolbox_node",
                name="slam_toolbox",
                output="screen",
                parameters=[
                    params_file,
                    {
                        "scan_topic": ParameterValue(scan_topic, value_type=str),
                        "map_frame": ParameterValue(map_frame, value_type=str),
                        "odom_frame": ParameterValue(odom_frame, value_type=str),
                        "base_frame": ParameterValue(base_frame, value_type=str),
                        "use_sim_time": ParameterValue(use_sim_time, value_type=bool),
                    },
                ],
                arguments=["--ros-args", "--log-level", log_level],
            ),
        ]
    )
