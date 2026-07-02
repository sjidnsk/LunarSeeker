from __future__ import annotations

import math
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # Allows static tests to report the missing runtime dependency.
    yaml = None


def load_scenario(config_path: str, scenario_name: str) -> dict[str, Any]:
    """Load one P3 navigation simulation scenario from YAML."""

    if yaml is None:
        raise RuntimeError("python3-yaml is required for navigation simulation scenarios.")

    path = Path(config_path)
    with path.open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle) or {}

    scenarios = document.get("scenarios", {})
    if scenario_name not in scenarios:
        available = ", ".join(sorted(scenarios)) or "<none>"
        raise ValueError(f"unknown scenario '{scenario_name}', available: {available}")

    scenario = dict(scenarios[scenario_name])
    scenario.setdefault("name", scenario_name)
    scenario.setdefault("frames", document.get("frames", {}))
    scenario.setdefault("defaults", document.get("defaults", {}))
    return scenario


def normalize_angle(angle_rad: float) -> float:
    return (angle_rad + math.pi) % (2.0 * math.pi) - math.pi


def yaw_to_quaternion_values(yaw_rad: float) -> tuple[float, float, float, float]:
    half_yaw = yaw_rad * 0.5
    return (0.0, 0.0, math.sin(half_yaw), math.cos(half_yaw))


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def point_in_rect(x: float, y: float, rect: list[float] | tuple[float, ...]) -> bool:
    min_x, min_y, max_x, max_y = rect
    return min_x <= x <= max_x and min_y <= y <= max_y


def rect_cells(
    *,
    rect: list[float] | tuple[float, ...],
    origin_x: float,
    origin_y: float,
    resolution: float,
    width: int,
    height: int,
) -> tuple[range, range]:
    min_x, min_y, max_x, max_y = rect
    start_x = clamp(math.floor((min_x - origin_x) / resolution), 0, width - 1)
    end_x = clamp(math.ceil((max_x - origin_x) / resolution), 0, width - 1)
    start_y = clamp(math.floor((min_y - origin_y) / resolution), 0, height - 1)
    end_y = clamp(math.ceil((max_y - origin_y) / resolution), 0, height - 1)
    return range(int(start_x), int(end_x) + 1), range(int(start_y), int(end_y) + 1)
