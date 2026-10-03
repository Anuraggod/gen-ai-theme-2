"""
test_enrichment.py - Tests for Query Enrichment engine and variation generation.
"""

from app.engine.enrichment import QueryEnricher


def test_colloquial_normalization():
    enricher = QueryEnricher()
    raw = "My phone swipe thing is going up and down instead of left and right"
    normalized = enricher.normalize_query(raw)
    assert "swipe navigation gesture" in normalized
    assert "moving vertically" in normalized
    assert "horizontally" in normalized


def test_domain_detection():
    enricher = QueryEnricher()
    assert enricher.detect_domain("phone swipe navigation gestures inverted") == "Display"
    assert enricher.detect_domain("battery drains very quickly and power saver") == "Battery"
    assert enricher.detect_domain("camera blurry out of focus photos") == "Camera"
    assert enricher.detect_domain("phone is lagging and UI freezing") == "Performance"


def test_variation_generation_registers_and_count():
    enricher = QueryEnricher()
    res = enricher.enrich("My phone swipe thing is going up and down instead of left and right")

    assert res["domain"] == "Display"
    assert 8 <= res["variationCount"] <= 10

    registers = [v["register"] for v in res["variations"]]
    assert "formal" in registers
    assert "casual" in registers
    assert "keyword" in registers
    assert "frustrated" in registers
    assert "typo" in registers
    assert "intent" in registers
