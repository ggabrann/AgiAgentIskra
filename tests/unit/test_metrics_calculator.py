from iskra_core.metrics_calculator import MetricsCalculator


def test_metrics_from_text_detects_pain():
    mc = MetricsCalculator()
    m = mc.from_text("мне очень больно ∆")
    assert m["pain"] >= 0.7
