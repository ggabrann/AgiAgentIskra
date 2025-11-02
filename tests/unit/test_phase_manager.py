from iskra_core.phase_manager import PhaseManager


def test_phase_transitions_by_metrics():
    pm = PhaseManager()
    assert pm.step({"chaos": 0.7}) == "Переход"
    assert pm.step({"clarity": 0.8}) == "Ясность"
    assert pm.step({"silence_mass": 0.7}) == "Молчание"
