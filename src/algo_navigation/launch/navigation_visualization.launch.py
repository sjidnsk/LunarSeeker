from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    map_frame_id = LaunchConfiguration("map_frame_id")
    publish_rate_hz = LaunchConfiguration("publish_rate_hz")
    use_rviz = LaunchConfiguration("use_rviz")
    use_mock_map = LaunchConfiguration("use_mock_map")
    task_area_enabled = LaunchConfiguration("task_area.enabled")
    task_area_min_x = LaunchConfiguration("task_area.min_x")
    task_area_max_x = LaunchConfiguration("task_area.max_x")
    task_area_min_y = LaunchConfiguration("task_area.min_y")
    task_area_max_y = LaunchConfiguration("task_area.max_y")
    task_area_distance_weight = LaunchConfiguration("task_area.distance_weight")
    task_area_inside_bonus = LaunchConfiguration("task_area.inside_bonus")
    rviz_config = PathJoinSubstitution(
        [
            FindPackageShare("algo_navigation"),
            "rviz",
            "navigation_search.rviz",
        ]
    )

    shared_navigation_params = {
        "map_frame_id": map_frame_id,
        "publish_rate_hz": ParameterValue(publish_rate_hz, value_type=float),
        "task_area.enabled": ParameterValue(task_area_enabled, value_type=bool),
        "task_area.min_x": ParameterValue(task_area_min_x, value_type=float),
        "task_area.max_x": ParameterValue(task_area_max_x, value_type=float),
        "task_area.min_y": ParameterValue(task_area_min_y, value_type=float),
        "task_area.max_y": ParameterValue(task_area_max_y, value_type=float),
        "task_area.distance_weight": ParameterValue(
            task_area_distance_weight,
            value_type=float,
        ),
        "task_area.inside_bonus": ParameterValue(
            task_area_inside_bonus,
            value_type=float,
        ),
    }

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "map_frame_id",
                default_value="odom",
                description=(
                    "Visualization frame. Mock navigation defaults to odom; "
                    "switch to map when Nav2/localization provides map-frame goals."
                ),
            ),
            DeclareLaunchArgument(
                "publish_rate_hz",
                default_value="2.0",
                description="Publish rate for mock goals and visualization markers.",
            ),
            DeclareLaunchArgument(
                "use_rviz",
                default_value="true",
                description="Start RViz with the navigation search debug layout.",
            ),
            DeclareLaunchArgument(
                "use_mock_map",
                default_value="true",
                description="Publish a small OccupancyGrid for frontier visualization.",
            ),
            DeclareLaunchArgument(
                "task_area.enabled",
                default_value="true",
                description="Enable task-area-biased frontier selection and markers.",
            ),
            DeclareLaunchArgument(
                "task_area.min_x",
                default_value="1.6",
                description="Task area minimum x in the visualization frame.",
            ),
            DeclareLaunchArgument(
                "task_area.max_x",
                default_value="3.2",
                description="Task area maximum x in the visualization frame.",
            ),
            DeclareLaunchArgument(
                "task_area.min_y",
                default_value="-0.8",
                description="Task area minimum y in the visualization frame.",
            ),
            DeclareLaunchArgument(
                "task_area.max_y",
                default_value="0.8",
                description="Task area maximum y in the visualization frame.",
            ),
            DeclareLaunchArgument(
                "task_area.distance_weight",
                default_value="4.0",
                description="Frontier score weight for distance to the task area.",
            ),
            DeclareLaunchArgument(
                "task_area.inside_bonus",
                default_value="100.0",
                description="Frontier score bonus for candidates inside the task area.",
            ),
            Node(
                package="algo_navigation",
                executable="mock_frontier_map",
                name="mock_frontier_map",
                parameters=[
                    {
                        "frame_id": map_frame_id,
                    }
                ],
                condition=IfCondition(use_mock_map),
                output="screen",
            ),
            Node(
                package="algo_navigation",
                executable="mock_navigation",
                name="mock_navigation",
                parameters=[shared_navigation_params],
                output="screen",
            ),
            Node(
                package="algo_navigation",
                executable="navigation_visualizer",
                name="navigation_visualizer",
                parameters=[shared_navigation_params],
                output="screen",
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                name="rviz2_navigation_search",
                arguments=["-d", rviz_config],
                condition=IfCondition(use_rviz),
                output="screen",
            ),
        ]
    )
