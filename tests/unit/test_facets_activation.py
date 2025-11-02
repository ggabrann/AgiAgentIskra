from iskra_core.facet_activation_engine import FacetActivationEngine


def test_kain_activates_on_high_pain():
    eng = FacetActivationEngine()
    m = {"pain": 0.9}
    active = eng.select_facets(m, {})
    assert "Kain" in active
    assert active[0] in ("Anhantra", "Kain")
