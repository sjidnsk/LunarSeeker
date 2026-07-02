from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
STATUS_MSG = PACKAGE_ROOT / "msg" / "NavigationStatus.msg"
CMAKELISTS = PACKAGE_ROOT / "CMakeLists.txt"


def test_navigation_status_message_is_registered():
    assert '"msg/NavigationStatus.msg"' in CMAKELISTS.read_text(encoding="utf-8")


def test_navigation_status_message_declares_expected_contract():
    text = STATUS_MSG.read_text(encoding="utf-8")

    for expected in (
        "uint8 STATUS_WAITING_FOR_NAV2=3",
        "uint8 STATUS_GOAL_ACTIVE=5",
        "uint8 STATUS_RETURN_RECOMMENDED=9",
        "uint8 GOAL_FRONTIER=2",
        "uint8 GOAL_TARGET_APPROACH=3",
        "geometry_msgs/PoseStamped goal_pose",
        "float32 distance_remaining_m",
        "uint16 recovery_count",
        "string last_result",
    ):
        assert expected in text
