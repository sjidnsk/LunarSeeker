from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    map_frame_id = LaunchConfiguration("map_frame_id")
    robot_base_frame_id = LaunchConfiguration("robot_base_frame_id")
    navigate_action_name = LaunchConfiguration("navigate_action_name")
    status_topic = LaunchConfiguration("status_topic")
    target_standoff_m = LaunchConfiguration("target_standoff_m")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "map_frame_id",
                default_value="map",
                description="Navigation frame used for Nav2 goals and status.",
            ),
            DeclareLaunchArgument(
                "robot_base_frame_id",
                default_value="base_link",
                description="Robot base frame used for TF pose lookup.",
            ),
            DeclareLaunchArgument(
                "navigate_action_name",
                default_value="/navigate_to_pose",
                description="Nav2 NavigateToPose action name.",
            ),
            DeclareLaunchArgument(
                "status_topic",
                default_value="/navigation/status",
                description="NavigationStatus output topic.",
            ),
            DeclareLaunchArgument(
                "target_standoff_m",
                default_value="0.45",
                description="Target approach standoff distance in meters; pending validation.",
            ),
            Node(
                package="algo_navigation",
                executable="navigation_coordinator",
                name="navigation_coordinator",
                parameters=[
                    {
                        "map_frame_id": map_frame_id,
                        "robot_base_frame_id": robot_base_frame_id,
                        "navigate_action_name": navigate_action_name,
                        "status_topic": status_topic,
                        "target_standoff_m": ParameterValue(
                            target_standoff_m,
                            value_type=float,
                        ),
                    }
                ],
                output="screen",
            ),
        ]
    )
