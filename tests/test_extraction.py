"""
test_extraction.py - Tests for Grounded Structure Extractor and hallucination resistance.
"""

from app.engine.extractor import StructureExtractor


def test_grounded_article_matching():
    extractor = StructureExtractor()
    extracted = extractor.extract_structure(
        normalized_query="phone swipe navigation gesture moving vertically horizontally",
        domain="Display"
    )

    assert "Swipe Navigation" in extracted["goal"]
    assert extracted["title"] == "Swipe navigation settings"
    assert 0.0 <= extracted["score"] <= 1.0
    assert len(extracted["extractedActions"]) >= 1


def test_fallback_for_unknown_domain():
    extractor = StructureExtractor()
    extracted = extractor.extract_structure(
        normalized_query="random unsupported feature problem",
        domain="Display"
    )

    assert extracted["goal"].startswith("Follow these steps")
    assert 2 <= len(extracted["title"].split()) <= 3
    assert len(extracted["extractedActions"]) >= 1
