from pathlib import Path

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = PACKAGE_ROOT / "config" / "navigation_sim_scenarios.yaml"
SIM_WORLD = PACKAGE_ROOT / "algo_navigation" / "navigation_sim_world.py"
SCENARIO_DRIVER = PACKAGE_ROOT / "algo_navigation" / "navigation_scenario_driver.py"
RVIZ_CONFIG = PACKAGE_ROOT / "rviz" / "nav2_sim_validation.rviz"
SETUP = PACKAGE_ROOT / "setup.py"
PACKAGE_XML = PACKAGE_ROOT / "package.xml"


def test_navigation_sim_scenarios_cover_success_and_required_failures():
    document = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8"))
    scenarios = document["scenarios"]

    assert {
        "nominal",
        "frontier_unreachable",
        "local_obstacle_blocked",
        "target_approach_failed",
    }.issubset(scenarios)
    assert scenarios["nominal"]["expected_failure"] == "none"
    assert scenarios["frontier_unreachable"]["expected_failure"] == "frontier_unreachable"
    assert scenarios["local_obstacle_blocked"]["expected_failure"] == "local_obstacle_blocked"
    assert (
        scenarios["target_approach_failed"]["expected_failure"]
        == "target_approach_failed"
    )


def test_navigation_sim_world_declares_required_runtime_contract():
    text = SIM_WORLD.read_text(encoding="utf-8")

    for expected in (
        '"/map"',
        '"/odom"',
        '"/scan"',
        '"/joint_states"',
        '"/cmd_vel"',
        '"/mission/state"',
        "TransformBroadcaster",
        "JointState",
        "LaserScan",
        "OccupancyGrid",
        "Odometry",
        "dynamic_obstacles",
        "base_footprint",
        "front_left_wheel_joint",
        "front_right_wheel_joint",
        "rear_left_wheel_joint",
        "rear_right_wheel_joint",
    ):
        assert expected in text


def test_navigation_scenario_driver_declares_required_runtime_contract():
    text = SCENARIO_DRIVER.read_text(encoding="utf-8")

    for expected in (
        '"/mission/state"',
        '"/target_detections"',
        '"/navigation/status"',
        "MissionState",
        "NavigationStatus",
        "ScienceTargetArray",
        "frontier_unreachable",
        "local_obstacle_blocked",
        "target_approach_failed",
    ):
        assert expected in text


def test_navigation_sim_entrypoints_config_and_dependencies_are_declared():
    setup_text = SETUP.read_text(encoding="utf-8")
    package_text = PACKAGE_XML.read_text(encoding="utf-8")

    assert "share/{package_name}/config" in setup_text
    assert "navigation_sim_world = algo_navigation.navigation_sim_world:main" in setup_text
    assert (
        "navigation_scenario_driver = "
        "algo_navigation.navigation_scenario_driver:main"
    ) in setup_text
    for dependency in ("sensor_msgs", "python3-yaml"):
        assert f"<exec_depend>{dependency}</exec_depend>" in package_text


def test_navigation_sim_rviz_config_uses_nav2_runtime_topics():
    text = RVIZ_CONFIG.read_text(encoding="utf-8")

    for expected in (
        "Fixed Frame: map",
        "/map",
        "/scan",
        "/odom",
        "/plan",
        "/plan_smoothed",
        "/global_costmap/costmap",
        "/local_costmap/costmap",
        "/robot_description",
    ):
        assert expected in text
    assert "/goal_pose" not in text
    assert "/mock/navigation_status" not in text
