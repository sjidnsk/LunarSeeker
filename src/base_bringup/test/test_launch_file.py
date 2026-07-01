from pathlib import Path

import yaml


LAUNCH_FILE = Path(__file__).resolve().parents[1] / "launch" / "sim_bringup.launch.py"
NAV2_LAUNCH_FILE = (
    Path(__file__).resolve().parents[1] / "launch" / "nav2_bringup.launch.py"
)
NAV2_SIM_VALIDATION_LAUNCH_FILE = (
    Path(__file__).resolve().parents[1] / "launch" / "nav2_sim_validation.launch.py"
)
NAV2_PARAMS_FILE = Path(__file__).resolve().parents[1] / "config" / "nav2_params.yaml"
PACKAGE_XML = Path(__file__).resolve().parents[1] / "package.xml"


def test_sim_bringup_launch_contains_mock_argument():
    text = LAUNCH_FILE.read_text(encoding="utf-8")

    assert "use_mock_hardware" in text
    assert "mission_state_machine" in text
    assert "robot_state_publisher" in text


def test_nav2_bringup_launch_uses_standalone_navigation_stack():
    text = NAV2_LAUNCH_FILE.read_text(encoding="utf-8")

    assert "navigation_launch.py" in text
    assert "nav2_bringup" in text
    assert "nav2_params.yaml" in text
    assert '"use_composition": "False"' in text
    for forbidden in (
        "bringup_launch.py",
        "slam_launch.py",
        "localization_launch.py",
        "mock_frontier_map",
        "mission_state_machine",
        "robot_state_publisher",
    ):
        assert forbidden not in text


def test_nav2_sim_validation_launch_connects_p1_p2_and_sim_nodes():
    text = NAV2_SIM_VALIDATION_LAUNCH_FILE.read_text(encoding="utf-8")

    for expected in (
        "nav2_bringup.launch.py",
        "navigation_coordinator.launch.py",
        "navigation_sim_world",
        "navigation_scenario_driver",
        "robot_state_publisher",
        "navigation_sim_scenarios.yaml",
        "scenario",
        "cmd_vel_topic",
        "frontier_blacklist_radius_m",
        '"5.0"',
        "use_rviz",
        "rviz2",
        "nav2_sim_validation.rviz",
    ):
        assert expected in text

    for forbidden in (
        "mock_navigation",
        "mock_frontier_map",
        "mission_state_machine",
    ):
        assert forbidden not in text


def test_nav2_params_use_expected_plugins_and_topics():
    params = yaml.safe_load(NAV2_PARAMS_FILE.read_text(encoding="utf-8"))

    assert "amcl" not in params
    assert "map_server" not in params
    assert "slam_toolbox" not in params

    planner = params["planner_server"]["ros__parameters"]
    assert planner["GridBased"]["plugin"] == "nav2_navfn_planner/NavfnPlanner"
    assert planner["GridBased"]["allow_unknown"] is True
    assert planner["GridBased"]["tolerance"] == 0.5

    controller = params["controller_server"]["ros__parameters"]
    follow_path = controller["FollowPath"]
    assert (
        follow_path["plugin"]
        == "nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController"
    )
    assert follow_path["desired_linear_vel"] == 0.25
    assert follow_path["use_collision_detection"] is True
    assert follow_path["allow_reversing"] is False

    local_costmap = params["local_costmap"]["local_costmap"]["ros__parameters"]
    global_costmap = params["global_costmap"]["global_costmap"]["ros__parameters"]
    assert local_costmap["global_frame"] == "odom"
    assert global_costmap["global_frame"] == "map"
    assert local_costmap["obstacle_layer"]["scan"]["topic"] == "/scan"
    assert global_costmap["obstacle_layer"]["scan"]["topic"] == "/scan"
    assert "static_layer" in global_costmap["plugins"]
    assert "static_layer" not in local_costmap["plugins"]
    assert "velocity_smoother" in params


def test_nav2_runtime_dependencies_are_declared():
    text = PACKAGE_XML.read_text(encoding="utf-8")

    for dependency in (
        "algo_navigation",
        "nav2_bringup",
        "nav2_navfn_planner",
        "nav2_regulated_pure_pursuit_controller",
        "rviz2",
    ):
        assert f"<exec_depend>{dependency}</exec_depend>" in text
