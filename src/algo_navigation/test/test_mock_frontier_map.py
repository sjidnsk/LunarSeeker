import importlib.util
import sys
from pathlib import Path


MOCK_MAP_NODE = (
    Path(__file__).resolve().parents[1]
    / "algo_navigation"
    / "mock_frontier_map.py"
)
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

SPEC = importlib.util.spec_from_file_location("mock_frontier_map", MOCK_MAP_NODE)
MOCK_FRONTIER_MAP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOCK_FRONTIER_MAP)


def test_mock_frontier_map_declares_expected_topic_and_cell_values():
    text = MOCK_MAP_NODE.read_text(encoding="utf-8")

    assert "/map" in text
    assert "OccupancyGrid" in text
    assert "UNKNOWN = -1" in text
    assert "OCCUPIED = 100" in text
