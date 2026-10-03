"""
test_audit_regressions.py - Comprehensive Suite of 14 Mandatory Regression Tests.
Verifies zero-hallucination, strict validator rejection, deeplink integrity,
parent-menu disambiguation, and uncontaminated semantic caching.
"""

import pytest
from app.schema import TroubleshootRequest
from app.engine.extractor import StructureExtractor
from app.engine.validator import OutputValidator
from app.engine.deeplink_mapper import DeeplinkMapper
from app.engine.pipeline import TroubleshootingPipeline
from app.cache.semantic_cache import FastPathSemanticCache


# 1. Unsupported query does not generate invented instructions
def test_unsupported_query_no_hallucinated_instructions():
    pipeline = TroubleshootingPipeline()
    req = TroubleshootRequest(query="unsupported completely random query about baking cakes")
    resp = pipeline.process_query(req)

    # Must return empty contexts rather than hallucinated device steps
    assert len(resp.contexts) == 0
    assert resp.metadata["status"] == "NO_GROUNDED_PLAN"


# 2. Invalid score is strictly rejected
def test_invalid_score_rejected():
    validator = OutputValidator()
    invalid_plan = {
        "goal": "Follow these steps to perform this Display Troubleshooting",
        "title": "Swipe navigation settings",
        "score": 1.5,  # Invalid: > 1.0
        "action": [
            {
                "actionName": "Display Settings",
                "description": "It will configure navigation preferences",
                "category": "auto",
                "stepGroups": [{"steps": ["Open Settings."]}]
            }
        ]
    }
    is_valid, goal, errors = validator.validate_plan(invalid_plan)
    assert is_valid is False
    assert goal is None
    assert any("Score out of bounds" in err for err in errors)


# 3. Invalid title length is rejected
def test_invalid_title_rejected():
    validator = OutputValidator()
    # 1-word title
    plan_1word = {
        "goal": "Follow these steps to perform this Display Troubleshooting",
        "title": "Navigation",
        "score": 0.9,
        "action": [
            {
                "actionName": "Display Settings",
                "description": "It will configure navigation preferences",
                "category": "auto",
                "stepGroups": [{"steps": ["Open Settings."]}]
            }
        ]
    }
    is_valid, _, errors = validator.validate_plan(plan_1word)
    assert is_valid is False
    assert any("strictly 2-3 words" in err for err in errors)

    # 4-word title
    plan_4word = dict(plan_1word)
    plan_4word["title"] = "Swipe navigation settings menu issue"
    is_valid4, _, errors4 = validator.validate_plan(plan_4word)
    assert is_valid4 is False
    assert any("strictly 2-3 words" in err for err in errors4)


# 4. Invalid description length is rejected
def test_invalid_description_length_rejected():
    validator = OutputValidator()
    # 4-word description (requires 5-7)
    plan_short_desc = {
        "goal": "Follow these steps to perform this Display Troubleshooting",
        "title": "Display settings issue",
        "score": 0.9,
        "action": [
            {
                "actionName": "Display Settings",
                "description": "It will fix issues",
                "category": "auto",
                "stepGroups": [{"steps": ["Open Settings."]}]
            }
        ]
    }
    is_valid, _, errors = validator.validate_plan(plan_short_desc)
    assert is_valid is False
    assert any("strictly 5-7 words" in err for err in errors)


# 5. Description not beginning with 'It will' is rejected
def test_description_prefix_rejected():
    validator = OutputValidator()
    plan = {
        "goal": "Follow these steps to perform this Display Troubleshooting",
        "title": "Display settings issue",
        "score": 0.9,
        "action": [
            {
                "actionName": "Display Settings",
                "description": "Configure your display settings preferences now",  # Missing 'It will'
                "category": "auto",
                "stepGroups": [{"steps": ["Open Settings."]}]
            }
        ]
    }
    is_valid, _, errors = validator.validate_plan(plan)
    assert is_valid is False
    assert any("start with 'It will'" in err for err in errors)


# 6. HTTP URL leak is rejected
def test_http_url_leak_rejected():
    validator = OutputValidator()
    plan = {
        "goal": "Follow these steps to perform this Display Troubleshooting",
        "title": "Display settings issue",
        "score": 0.9,
        "action": [
            {
                "actionName": "Display Settings",
                "description": "It will configure device preferences properly",
                "category": "auto",
                "stepGroups": [
                    {
                        "steps": [
                            "Open Settings.",
                            "Visit http://device.help.com/guide for details."  # HTTP leak
                        ]
                    }
                ]
            }
        ]
    }
    is_valid, _, errors = validator.validate_plan(plan)
    assert is_valid is False
    assert any("Prohibited URL leak" in err for err in errors)


# 7. HTTPS URL leak is rejected
def test_https_url_leak_rejected():
    validator = OutputValidator()
    plan = {
        "goal": "Follow these steps to perform this Display Troubleshooting",
        "title": "Display settings issue",
        "score": 0.9,
        "action": [
            {
                "actionName": "Display Settings",
                "description": "It will configure device preferences properly",
                "category": "auto",
                "stepGroups": [
                    {
                        "steps": [
                            "Open Settings.",
                            "Click https://samsung.com/support/touch to learn."  # HTTPS leak
                        ]
                    }
                ]
            }
        ]
    }
    is_valid, _, errors = validator.validate_plan(plan)
    assert is_valid is False
    assert any("Prohibited URL leak" in err for err in errors)


# 8. Fabricated deeplink is rejected
def test_fabricated_deeplink_rejected():
    validator = OutputValidator()
    plan = {
        "goal": "Follow these steps to perform this Display Troubleshooting",
        "title": "Display settings issue",
        "score": 0.9,
        "action": [
            {
                "actionName": "Display Settings",
                "description": "It will configure device preferences properly",
                "category": "auto",
                "stepGroups": [
                    {
                        "steps": ["Open Settings."],
                        "actionableDeeplink": "bixby://masked/fabricated/nonexistent_screen/uri"
                    }
                ]
            }
        ]
    }
    is_valid, _, errors = validator.validate_plan(plan)
    assert is_valid is False
    assert any("does not exist in catalog" in err for err in errors)


# 9. Modified catalog deeplink is rejected
def test_modified_catalog_deeplink_rejected():
    validator = OutputValidator()
    plan = {
        "goal": "Follow these steps to perform this Display Troubleshooting",
        "title": "Display settings issue",
        "score": 0.9,
        "action": [
            {
                "actionName": "Display Settings",
                "description": "It will configure device preferences properly",
                "category": "auto",
                "stepGroups": [
                    {
                        "steps": ["Open Settings."],
                        "actionableDeeplink": "bixby://masked/settings/display/navigation_bar_MODIFIED_TYPO"
                    }
                ]
            }
        ]
    }
    is_valid, _, errors = validator.validate_plan(plan)
    assert is_valid is False
    assert any("does not exist in catalog" in err for err in errors)


# 10. Manual action cannot contain actionable deeplink
def test_manual_action_cannot_contain_deeplink():
    validator = OutputValidator()
    plan = {
        "goal": "Follow these steps to perform this Battery Troubleshooting",
        "title": "Battery charging issue",
        "score": 0.9,
        "action": [
            {
                "actionName": "Clean Port",
                "description": "It will remove port lint buildup",
                "category": "manual",
                "stepGroups": [
                    {
                        "steps": ["Clean port with brush."],
                        "actionableDeeplink": "bixby://masked/settings/battery"  # Prohibited on manual
                    }
                ]
            }
        ]
    }
    is_valid, _, errors = validator.validate_plan(plan)
    assert is_valid is False
    assert any("Manual action" in err and "must not contain an actionable deeplink" in err for err in errors)


# 11. Critical action cannot be followed by auto/manual action
def test_critical_ordering_violation_rejected():
    validator = OutputValidator()
    plan = {
        "goal": "Follow these steps to perform this Device Troubleshooting",
        "title": "Device lag issue",
        "score": 0.9,
        "action": [
            {
                "actionName": "Factory Data Reset",
                "description": "It will restore original factory system",
                "category": "critical",
                "stepGroups": [
                    {
                        "steps": ["Perform factory reset."],
                        "actionableDeeplink": "bixby://masked/settings/general/factory_reset"
                    }
                ]
            },
            {
                "actionName": "Memory Cleaner",
                "description": "It will terminate idle background tasks",
                "category": "auto",  # Invalid: auto action placed after critical
                "stepGroups": [
                    {
                        "steps": ["Clean RAM."],
                        "actionableDeeplink": "bixby://masked/settings/device_care/memory"
                    }
                ]
            }
        ]
    }
    is_valid, _, errors = validator.validate_plan(plan)
    assert is_valid is False
    assert any("Sequencing violation" in err for err in errors)


# 12. Parent screen loses to more specific child screen
def test_parent_screen_loses_to_specific_child():
    mapper = DeeplinkMapper()
    best_match = mapper.find_best_deeplink(
        action_name="Navigation Bar Settings",
        target_keyword="navigation_bar",
        domain="Display",
        query_text="phone swipe navigation gestures inverted"
    )
    assert best_match is not None
    assert best_match["uri"] == "bixby://masked/settings/display/navigation_bar"
    assert best_match["uri"] != "bixby://masked/settings/display"


# 13. Semantic cache hit is genuinely semantic rather than an exact hit
def test_semantic_cache_hit_is_genuinely_semantic():
    cache = FastPathSemanticCache(threshold=0.55)
    pipeline = TroubleshootingPipeline()

    canonical = "battery drains very fast throughout the day"
    req_canonical = TroubleshootRequest(query=canonical)
    resp_canonical = pipeline.process_query(req_canonical)
    assert len(resp_canonical.contexts) > 0
    goal = resp_canonical.contexts[0]

    # Insert only normalized canonical into cache
    norm_canonical = pipeline.enricher.normalize_query(canonical)
    cache.clear()
    cache.put(norm_canonical, goal)

    # Query with a genuine unprimed paraphrase
    paraphrase = "phone battery dying super fast after update"
    norm_paraphrase = pipeline.enricher.normalize_query(paraphrase)
    cached_goal, hit_type, sim_score = cache.get(norm_paraphrase)

    assert hit_type == "SEMANTIC_HIT"
    assert hit_type != "EXACT_HIT"
    assert cached_goal is not None
    assert cached_goal.title == "Battery fast drain"


# 14. Semantic benchmark does not contaminate its own hit rate
def test_semantic_benchmark_no_self_contamination():
    cache = FastPathSemanticCache(threshold=0.55)
    canonical = "battery drains very fast throughout the day"
    pipeline = TroubleshootingPipeline()
    req = TroubleshootRequest(query=canonical)
    resp = pipeline.process_query(req)
    goal = resp.contexts[0]

    norm_canonical = pipeline.enricher.normalize_query(canonical)
    cache.clear()
    cache.put(norm_canonical, goal)
    initial_size = cache.size()
    assert initial_size == 1

    # Simulate 5 consecutive paraphrase queries using get() without put()
    paraphrase = "phone battery dying super fast after update"
    norm_paraphrase = pipeline.enricher.normalize_query(paraphrase)
    for _ in range(5):
        _, hit_type, _ = cache.get(norm_paraphrase)

    # Cache size must remain strictly uncontaminated
    assert cache.size() == initial_size
