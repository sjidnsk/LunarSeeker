from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    params_file = LaunchConfiguration("params_file")
    odom_topic = LaunchConfiguration("odom_topic")
    imu_topic = LaunchConfiguration("imu_topic")
    filtered_odom_topic = LaunchConfiguration("filtered_odom_topic")
    map_frame = LaunchConfiguration("map_frame")
    odom_frame = LaunchConfiguration("odom_frame")
    base_frame = LaunchConfiguration("base_frame")
    world_frame = LaunchConfiguration("world_frame")
    publish_tf = LaunchConfiguration("publish_tf")
    use_sim_time = LaunchConfiguration("use_sim_time")
    log_level = LaunchConfiguration("log_level")

    default_params_file = PathJoinSubstitution(
        [FindPackageShare("algo_localization"), "config", "ekf.yaml"]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "params_file",
                default_value=default_params_file,
                description="robot_localization EKF parameter file.",
            ),
            DeclareLaunchArgument(
                "odom_topic",
                default_value="/odom",
                description="Raw wheel odometry topic consumed by EKF.",
            ),
            DeclareLaunchArgument(
                "imu_topic",
                default_value="/imu/data",
                description="IMU topic consumed by EKF. Bridge Noetic /imu/data_raw before ROS2 use.",
            ),
            DeclareLaunchArgument(
                "filtered_odom_topic",
                default_value="/odometry/filtered",
                description="Filtered odometry topic published by EKF.",
            ),
            DeclareLaunchArgument(
                "map_frame",
                default_value="map",
                description="Global map frame reserved for SLAM.",
            ),
            DeclareLaunchArgument(
                "odom_frame",
                default_value="odom",
                description="Continuous odometry frame.",
            ),
            DeclareLaunchArgument(
                "base_frame",
                default_value="base_footprint",
                description="Robot base frame used by Nav2 and localization.",
            ),
            DeclareLaunchArgument(
                "world_frame",
                default_value="odom",
                description="World frame for the single EKF instance.",
            ),
            DeclareLaunchArgument(
                "publish_tf",
                default_value="false",
                description="Set true only after shadow-mode EKF validation passes.",
            ),
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use simulation clock when replaying bags with /clock.",
            ),
            DeclareLaunchArgument(
                "log_level",
                default_value="info",
                description="Log level for robot_localization.",
            ),
            Node(
                package="robot_localization",
                executable="ekf_node",
                name="ekf_filter_node",
                output="screen",
                parameters=[
                    params_file,
                    {
                        "odom0": ParameterValue(odom_topic, value_type=str),
                        "imu0": ParameterValue(imu_topic, value_type=str),
                        "map_frame": ParameterValue(map_frame, value_type=str),
                        "odom_frame": ParameterValue(odom_frame, value_type=str),
                        "base_link_frame": ParameterValue(base_frame, value_type=str),
                        "world_frame": ParameterValue(world_frame, value_type=str),
                        "publish_tf": ParameterValue(publish_tf, value_type=bool),
                        "use_sim_time": ParameterValue(use_sim_time, value_type=bool),
                    },
                ],
                remappings=[
                    ("odometry/filtered", filtered_odom_topic),
                ],
                arguments=["--ros-args", "--log-level", log_level],
            ),
        ]
    )
