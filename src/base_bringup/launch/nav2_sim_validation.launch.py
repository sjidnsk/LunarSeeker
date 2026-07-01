from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    scenario = LaunchConfiguration("scenario")
    scenario_config = LaunchConfiguration("scenario_config")
    mission_time_limit_sec = LaunchConfiguration("mission_time_limit_sec")
    cmd_vel_topic = LaunchConfiguration("cmd_vel_topic")
    use_sim_time = LaunchConfiguration("use_sim_time")
    nav2_log_level = LaunchConfiguration("nav2_log_level")
    use_rviz = LaunchConfiguration("use_rviz")
    rviz_config = LaunchConfiguration("rviz_config")

    default_scenario_config = PathJoinSubstitution(
        [
            FindPackageShare("algo_navigation"),
            "config",
            "navigation_sim_scenarios.yaml",
        ]
    )
    robot_description_file = PathJoinSubstitution(
        [
            FindPackageShare("base_description"),
            "urdf",
            "tzb_lunar_sampler.urdf.xacro",
        ]
    )
    default_rviz_config = PathJoinSubstitution(
        [
            FindPackageShare("algo_navigation"),
            "rviz",
            "nav2_sim_validation.rviz",
        ]
    )
    nav2_bringup_launch = PathJoinSubstitution(
        [
            FindPackageShare("base_bringup"),
            "launch",
            "nav2_bringup.launch.py",
        ]
    )
    coordinator_launch = PathJoinSubstitution(
        [
            FindPackageShare("algo_navigation"),
            "launch",
            "navigation_coordinator.launch.py",
        ]
    )
    robot_description = Command(
        [
            "xacro ",
            robot_description_file,
            " use_mock_hardware:=true",
        ]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "scenario",
                default_value="nominal",
                description=(
                    "P3 navigation simulation scenario: nominal, "
                    "frontier_unreachable, local_obstacle_blocked, "
                    "target_approach_failed."
                ),
            ),
            DeclareLaunchArgument(
                "scenario_config",
                default_value=default_scenario_config,
                description="YAML file containing P3 navigation simulation scenarios.",
            ),
            DeclareLaunchArgument(
                "mission_time_limit_sec",
                default_value="600",
                description="Mission time budget published by the scenario driver.",
            ),
            DeclareLaunchArgument(
                "cmd_vel_topic",
                default_value="/cmd_vel",
                description="Final Nav2 velocity command topic consumed by the 2D simulator.",
            ),
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="P3 lightweight simulator uses wall time unless /clock is added later.",
            ),
            DeclareLaunchArgument(
                "nav2_log_level",
                default_value="info",
                description="Nav2 log level for P3 simulation validation.",
            ),
            DeclareLaunchArgument(
                "use_rviz",
                default_value="false",
                description="Start RViz with the P3 Nav2 simulation validation layout.",
            ),
            DeclareLaunchArgument(
                "rviz_config",
                default_value=default_rviz_config,
                description="RViz config used when use_rviz is true.",
            ),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                name="robot_state_publisher",
                parameters=[
                    {
                        "robot_description": robot_description,
                        "use_sim_time": ParameterValue(use_sim_time, value_type=bool),
                    }
                ],
                output="screen",
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(nav2_bringup_launch),
                launch_arguments={
                    "use_sim_time": use_sim_time,
                    "autostart": "true",
                    "use_respawn": "false",
                    "log_level": nav2_log_level,
                }.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(coordinator_launch),
                launch_arguments={
                    "map_frame_id": "map",
                    "robot_base_frame_id": "base_link",
                    "navigate_action_name": "/navigate_to_pose",
                    "status_topic": "/navigation/status",
                    "frontier_blacklist_radius_m": "5.0",
                    "frontier_blacklist_ttl_sec": "30.0",
                    "nav_retry_limit": "1",
                }.items(),
            ),
            Node(
                package="algo_navigation",
                executable="navigation_sim_world",
                name="navigation_sim_world",
                parameters=[
                    {
                        "scenario": scenario,
                        "scenario_config": scenario_config,
                        "cmd_vel_topic": cmd_vel_topic,
                        "use_sim_time": ParameterValue(use_sim_time, value_type=bool),
                    }
                ],
                output="screen",
            ),
            Node(
                package="algo_navigation",
                executable="navigation_scenario_driver",
                name="navigation_scenario_driver",
                parameters=[
                    {
                        "scenario": scenario,
                        "scenario_config": scenario_config,
                        "mission_time_limit_sec": ParameterValue(
                            mission_time_limit_sec,
                            value_type=float,
                        ),
                        "use_sim_time": ParameterValue(use_sim_time, value_type=bool),
                    }
                ],
                output="screen",
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                name="rviz2_nav2_sim_validation",
                arguments=["-d", rviz_config],
                condition=IfCondition(use_rviz),
                output="screen",
            ),
        ]
    )
