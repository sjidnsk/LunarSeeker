from base_mission.mission_constants import (
    MAX_START_BOX_MM,
    MAX_TOTAL_MASS_KG,
    MISSION_TIME_LIMIT_SEC,
    RUN_COUNT_PER_ROUND,
    SCORE_RULES,
    MissionPhase,
)


def test_competition_constraints_are_encoded():
    assert MAX_TOTAL_MASS_KG == 30
    assert MAX_START_BOX_MM == (800, 800, 800)
    assert MISSION_TIME_LIMIT_SEC == 600
    assert RUN_COUNT_PER_ROUND == 2


def test_phase_values_match_interfaces():
    assert MissionPhase.IDLE == 0
    assert MissionPhase.READY == 1
    assert MissionPhase.COMPLETE == 8
    assert MissionPhase.FAULT == 255


def test_score_rules_match_mission_brief():
    assert SCORE_RULES["leave_base"] == 10
    assert SCORE_RULES["collect_target"] == 10
    assert SCORE_RULES["return_with_target"] == 10
    assert SCORE_RULES["unload_target"] == 20
