from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
COORDINATOR = PACKAGE_ROOT / "algo_navigation" / "navigation_coordinator.py"
LAUNCH_FILE = PACKAGE_ROOT / "launch" / "navigation_coordinator.launch.py"
SETUP = PACKAGE_ROOT / "setup.py"
PACKAGE_XML = PACKAGE_ROOT / "package.xml"


def test_navigation_coordinator_declares_expected_ros_contract():
    text = COORDINATOR.read_text(encoding="utf-8")

    for expected in (
        "ActionClient",
        "NavigateToPose",
        "NavigationStatus",
        '"/mission/state"',
        '"/target_detections"',
        '"/map"',
        '"/navigation/status"',
        '"/navigate_to_pose"',
    ):
        assert expected in text


def test_navigation_coordinator_launch_starts_only_coordinator():
    text = LAUNCH_FILE.read_text(encoding="utf-8")

    assert "navigation_coordinator" in text
    for forbidden in (
        "mock_frontier_map",
        "mock_navigation",
        "nav2_bringup",
        "mission_state_machine",
        "robot_state_publisher",
    ):
        assert forbidden not in text


def test_navigation_coordinator_entrypoint_and_dependencies_are_declared():
    setup_text = SETUP.read_text(encoding="utf-8")
    package_text = PACKAGE_XML.read_text(encoding="utf-8")

    assert "navigation_coordinator = algo_navigation.navigation_coordinator:main" in setup_text
    for dependency in (
        "action_msgs",
        "tf2_geometry_msgs",
        "tf2_ros",
    ):
        assert f"<exec_depend>{dependency}</exec_depend>" in package_text
