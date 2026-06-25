import importlib.util
from pathlib import Path


MOCK_NODE = (
    Path(__file__).resolve().parents[1]
    / "algo_manipulation"
    / "mock_manipulation.py"
)

SPEC = importlib.util.spec_from_file_location("mock_manipulation", MOCK_NODE)
MOCK_MANIPULATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOCK_MANIPULATION)


def test_manipulation_state_for_phase():
    assert MOCK_MANIPULATION.manipulation_state_for_phase("approach") == "arm_ready"
    assert (
        MOCK_MANIPULATION.manipulation_state_for_phase("sample")
        == "pre_grasp_grasp_lift_stow_mock_success"
    )
    assert MOCK_MANIPULATION.manipulation_state_for_phase("unload") == (
        "place_release_mock_success"
    )


def test_mock_manipulation_declares_status_topic():
    text = MOCK_NODE.read_text(encoding="utf-8")

    assert "/mission/state" in text
    assert "/mock/manipulation_status" in text
