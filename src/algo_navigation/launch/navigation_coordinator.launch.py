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
    frontier_blacklist_ttl_sec = LaunchConfiguration("frontier_blacklist_ttl_sec")
    frontier_blacklist_radius_m = LaunchConfiguration("frontier_blacklist_radius_m")
    nav_retry_limit = LaunchConfiguration("nav_retry_limit")

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
            DeclareLaunchArgument(
                "frontier_blacklist_ttl_sec",
                default_value="30.0",
                description="Failed frontier blacklist TTL in seconds; pending validation.",
            ),
            DeclareLaunchArgument(
                "frontier_blacklist_radius_m",
                default_value="0.5",
                description="Failed frontier blacklist radius in meters; pending validation.",
            ),
            DeclareLaunchArgument(
                "nav_retry_limit",
                default_value="1",
                description="Retry limit for non-frontier navigation goals.",
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
                        "frontier.blacklist_ttl_sec": ParameterValue(
                            frontier_blacklist_ttl_sec,
                            value_type=float,
                        ),
                        "frontier.blacklist_radius_m": ParameterValue(
                            frontier_blacklist_radius_m,
                            value_type=float,
                        ),
                        "nav.retry_limit": ParameterValue(
                            nav_retry_limit,
                            value_type=int,
                        ),
                    }
                ],
                output="screen",
            ),
        ]
    )
