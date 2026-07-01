import importlib.util
import sys
from pathlib import Path


MOCK_NODE = (
    Path(__file__).resolve().parents[1]
    / "algo_navigation"
    / "mock_navigation.py"
)
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

SPEC = importlib.util.spec_from_file_location("mock_navigation", MOCK_NODE)
MOCK_NAVIGATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOCK_NAVIGATION)


def test_goal_label_for_phase():
    assert MOCK_NAVIGATION.goal_label_for_phase("exploration") == "search_zone_a"
    assert MOCK_NAVIGATION.goal_label_for_phase("approach") == "selected_target"
    assert MOCK_NAVIGATION.goal_label_for_phase("return") == "base_return"


def test_mock_navigation_declares_expected_topics():
    text = MOCK_NODE.read_text(encoding="utf-8")

    assert "/mission/state" in text
    assert "/target_detections" in text
    assert "/goal_pose" in text
    assert "/mock/navigation_status" in text


def test_mock_navigation_uses_search_strategy():
    text = MOCK_NODE.read_text(encoding="utf-8")

    assert "generate_lawnmower_goals" in text
    assert "approach_goal_for_target" in text
    assert "target_standoff_m" in text
