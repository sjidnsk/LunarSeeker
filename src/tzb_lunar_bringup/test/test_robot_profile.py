from pathlib import Path


PROFILE = Path(__file__).resolve().parents[1] / "config" / "robot_profile.yaml"


def test_mission_constraints_are_fixed():
    text = PROFILE.read_text(encoding="utf-8")

    assert "max_total_mass_kg: 30" in text
    assert "max_start_box_mm: [800, 800, 800]" in text
    assert "time_limit_sec: 600" in text
    assert "run_count_per_round: 2" in text
    assert "remote_intervention_allowed: false" in text


def test_required_topics_are_declared():
    text = PROFILE.read_text(encoding="utf-8")

    for topic in (
        "/cmd_vel",
        "/odom",
        "/joint_states",
        "/scan",
        "/camera/color/image_raw",
        "/camera/depth/image_rect_raw",
        "/tf",
        "/target_detections",
        "/mission/state",
        "can0",
        "can1",
    ):
        assert topic in text
