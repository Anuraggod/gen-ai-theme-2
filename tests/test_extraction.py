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

    assert extracted is not None
    assert "Swipe Navigation" in extracted["goal"]
    assert extracted["title"] == "Swipe navigation settings"
    assert 0.0 <= extracted["score"] <= 1.0
    assert len(extracted["extractedActions"]) >= 1


def test_unsupported_query_returns_none_zero_hallucination():
    extractor = StructureExtractor()
    extracted = extractor.extract_structure(
        normalized_query="random completely unsupported feature problem without article",
        domain="Display"
    )

    # Zero hallucination: ungrounded queries return None
    assert extracted is None
