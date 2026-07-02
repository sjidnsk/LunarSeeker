from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    params_file = LaunchConfiguration("params_file")
    use_sim_time = LaunchConfiguration("use_sim_time")
    autostart = LaunchConfiguration("autostart")
    use_respawn = LaunchConfiguration("use_respawn")
    log_level = LaunchConfiguration("log_level")
    nav2_params_file = PathJoinSubstitution(
        [
            FindPackageShare("base_bringup"),
            "config",
            "nav2_params.yaml",
        ]
    )
    nav2_navigation_launch = PathJoinSubstitution(
        [
            FindPackageShare("nav2_bringup"),
            "launch",
            "navigation_launch.py",
        ]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "params_file",
                default_value=nav2_params_file,
                description="Nav2 parameters for the standalone navigation stack.",
            ),
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use simulation clock if an external simulator provides /clock.",
            ),
            DeclareLaunchArgument(
                "autostart",
                default_value="true",
                description="Automatically configure and activate Nav2 lifecycle nodes.",
            ),
            DeclareLaunchArgument(
                "use_respawn",
                default_value="false",
                description="Respawn Nav2 nodes if they exit unexpectedly.",
            ),
            DeclareLaunchArgument(
                "log_level",
                default_value="info",
                description="Nav2 log level.",
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(nav2_navigation_launch),
                launch_arguments={
                    "namespace": "",
                    "use_sim_time": use_sim_time,
                    "autostart": autostart,
                    "params_file": params_file,
                    "use_composition": "False",
                    "container_name": "nav2_container",
                    "use_respawn": use_respawn,
                    "log_level": log_level,
                }.items(),
            ),
        ]
    )
