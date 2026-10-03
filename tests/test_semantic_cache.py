"""
test_semantic_cache.py - Tests for Fast-Path Semantic Cache.
"""

from app.cache.semantic_cache import FastPathSemanticCache
from app.schema import TroubleshootingGoal, Action, StepGroup


def create_sample_goal():
    return TroubleshootingGoal(
        goal="Follow these steps to perform this Battery Troubleshooting",
        title="Battery fast drain",
        score=0.95,
        action=[
            Action(
                actionName="Power Saving Mode",
                description="It will reduce background power consumption",
                category="auto",
                stepGroups=[
                    StepGroup(
                        steps=["Open Settings.", "Tap Power saving."],
                        actionableDeeplink="bixby://masked/settings/battery/power_saving",
                        validationDeeplink=None
                    )
                ]
            )
        ]
    )


def test_cache_miss_and_put():
    cache = FastPathSemanticCache()
    query = "battery drains very quickly"

    goal, hit_type, _ = cache.get(query)
    assert hit_type == "MISS"
    assert goal is None

    sample_goal = create_sample_goal()
    cache.put(query, sample_goal)

    # Exact Hit
    cached, hit_type, score = cache.get(query)
    assert hit_type == "EXACT_HIT"
    assert cached is not None
    assert cached.title == "Battery fast drain"


def test_semantic_paraphrase_cache_hit():
    cache = FastPathSemanticCache(threshold=0.75)
    canonical = "battery drains very quickly throughout the day"
    cache.put(canonical, create_sample_goal())

    # Paraphrased query with similar words
    paraphrase = "phone battery drains very quickly during day"
    cached, hit_type, score = cache.get(paraphrase)

    assert hit_type in ["EXACT_HIT", "SEMANTIC_HIT"]
    assert cached is not None
    assert cached.title == "Battery fast drain"


def test_cache_clear():
    cache = FastPathSemanticCache()
    cache.put("test query", create_sample_goal())
    assert cache.size() == 1

    cache.clear()
    assert cache.size() == 0
