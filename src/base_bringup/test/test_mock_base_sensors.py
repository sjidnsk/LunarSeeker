import importlib.util
import math
from pathlib import Path


MOCK_NODE = (
    Path(__file__).resolve().parents[1]
    / "base_bringup"
    / "mock_base_sensors.py"
)

SPEC = importlib.util.spec_from_file_location("mock_base_sensors", MOCK_NODE)
MOCK_BASE_SENSORS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOCK_BASE_SENSORS)


def test_yaw_to_quaternion_identity():
    qx, qy, qz, qw = MOCK_BASE_SENSORS.yaw_to_quaternion(0.0)

    assert qx == 0.0
    assert qy == 0.0
    assert qz == 0.0
    assert qw == 1.0


def test_yaw_to_quaternion_half_turn():
    qx, qy, qz, qw = MOCK_BASE_SENSORS.yaw_to_quaternion(math.pi)

    assert qx == 0.0
    assert qy == 0.0
    assert math.isclose(qz, 1.0, rel_tol=1e-6)
    assert math.isclose(qw, 0.0, abs_tol=1e-6)


def test_mock_node_declares_required_topics():
    text = MOCK_NODE.read_text(encoding="utf-8")

    for topic in (
        "/odom",
        "/scan",
        "/imu/data",
        "/joint_states",
        "/target_detections",
    ):
        assert topic in text


def test_mock_node_declares_semantic_targets():
    text = MOCK_NODE.read_text(encoding="utf-8")

    assert "mock_target_01" in text
    assert "basalt_sample" in text
    assert "selected_for_sampling" in text


def test_mock_node_declares_map_to_odom_tf():
    text = MOCK_NODE.read_text(encoding="utf-8")

    assert "map_frame_id" in text
    assert "_publish_static_map_to_odom" in text
