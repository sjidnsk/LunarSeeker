from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    mission_time_limit_sec = LaunchConfiguration("mission_time_limit_sec")
    use_mock_hardware = LaunchConfiguration("use_mock_hardware")
    robot_description_file = PathJoinSubstitution(
        [
            FindPackageShare("base_description"),
            "urdf",
            "tzb_lunar_sampler.urdf.xacro",
        ]
    )

    robot_description = Command(
        [
            "xacro ",
            robot_description_file,
            " use_mock_hardware:=",
            use_mock_hardware,
        ]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_mock_hardware",
                default_value="true",
                description="Start without real CAN devices or sensors.",
            ),
            DeclareLaunchArgument(
                "mission_time_limit_sec",
                default_value="600",
                description="Single-run mission time limit in seconds.",
            ),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                name="robot_state_publisher",
                parameters=[{"robot_description": robot_description}],
                output="screen",
            ),
            Node(
                package="base_mission",
                executable="mission_state_machine",
                name="mission_state_machine",
                parameters=[
                    {
                        "use_mock_hardware": ParameterValue(
                            use_mock_hardware, value_type=bool
                        ),
                        "mission.time_limit_sec": ParameterValue(
                            mission_time_limit_sec, value_type=int
                        ),
                    },
                ],
                output="screen",
            ),
            Node(
                package="base_bringup",
                executable="mock_base_sensors",
                name="mock_base_sensors",
                condition=IfCondition(use_mock_hardware),
                parameters=[
                    {
                        "publish_rate_hz": 10.0,
                        "map_frame_id": "map",
                        "odom_frame_id": "odom",
                        "base_frame_id": "base_link",
                        "lidar_frame_id": "lidar_link",
                        "imu_frame_id": "imu_link",
                        "target_frame_id": "base_link",
                    },
                ],
                output="screen",
            ),
            Node(
                package="algo_navigation",
                executable="mock_navigation",
                name="mock_navigation",
                condition=IfCondition(use_mock_hardware),
                parameters=[
                    {
                        "map_frame_id": "map",
                        "publish_rate_hz": 2.0,
                    },
                ],
                output="screen",
            ),
            Node(
                package="algo_manipulation",
                executable="mock_manipulation",
                name="mock_manipulation",
                condition=IfCondition(use_mock_hardware),
                parameters=[{"publish_rate_hz": 2.0}],
                output="screen",
            ),
        ]
    )
