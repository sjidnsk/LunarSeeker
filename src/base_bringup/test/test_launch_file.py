from pathlib import Path


LAUNCH_FILE = Path(__file__).resolve().parents[1] / "launch" / "sim_bringup.launch.py"


def test_sim_bringup_launch_contains_mock_argument():
    text = LAUNCH_FILE.read_text(encoding="utf-8")

    assert "use_mock_hardware" in text
    assert "mission_state_machine" in text
    assert "mock_base_sensors" in text
    assert "robot_state_publisher" in text
