"""
pipeline.py - Core Orchestrator for the Smart Guided Troubleshooting Engine.
Coordinates:
0. Fast-Path Caching (< 300ms)
1. Query Enrichment (8-10 variations)
2. Grounded Structure Extraction (refuses ungrounded fabrication)
3. Deeplink Mapping & Parent-Menu Disambiguation
4. Action Sequencing (auto -> manual -> critical last)
5. Strict Deterministic Validation Gate & Zero-URL Leak Gate
"""

import time
from typing import Dict, Any, Optional
from app.schema import TroubleshootRequest, TroubleshootResponse, TroubleshootingGoal
from app.engine.enrichment import QueryEnricher
from app.engine.extractor import StructureExtractor
from app.engine.deeplink_mapper import DeeplinkMapper
from app.engine.sequencer import ActionSequencer
from app.engine.validator import OutputValidator
from app.cache.semantic_cache import FastPathSemanticCache


class TroubleshootingPipeline:
    """
    End-to-end troubleshooting pipeline adhering strictly to Theme 2 specifications
    and zero-hallucination source grounding rules.
    """

    def __init__(self):
        self.enricher = QueryEnricher()
        self.extractor = StructureExtractor()
        self.deeplink_mapper = DeeplinkMapper()
        self.sequencer = ActionSequencer()
        self.validator = OutputValidator()
        self.cache = FastPathSemanticCache()

    def process_query(self, request: TroubleshootRequest) -> TroubleshootResponse:
        """
        Executes the troubleshooting pipeline.
        """
        start_time = time.perf_counter()
        raw_query = request.query.strip()

        # Step 0: Pre-normalization for cache
        normalized_q = self.enricher.normalize_query(raw_query)

        # Step 1: Fast-Path Cache Lookup
        cached_goal, hit_type, hit_score = self.cache.get(normalized_q)
        if cached_goal is not None and hit_type in ["EXACT_HIT", "SEMANTIC_HIT"]:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return TroubleshootResponse(
                contexts=[cached_goal],
                metadata={
                    "cache_hit": True,
                    "cache_hit_type": hit_type,
                    "cache_similarity": hit_score,
                    "latency_ms": round(elapsed_ms, 2),
                    "execution_path": "FAST_PATH_CACHE",
                    "domain": request.domain or self.enricher.detect_domain(raw_query)
                }
            )

        # Step 2: Query Enrichment (8-10 variations across registers)
        enrichment_result = self.enricher.enrich(raw_query, domain_hint=request.domain)
        domain = enrichment_result["domain"]
        variations = enrichment_result["variations"]

        # Step 3: Grounded Structure Extraction (Zero-Hallucination)
        extracted_data = self.extractor.extract_structure(
            normalized_query=normalized_q,
            domain=domain,
            custom_reference=request.referenceContext
        )

        if not extracted_data:
            # If no grounded reference exists, return empty contexts rather than hallucinating steps
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return TroubleshootResponse(
                contexts=[],
                metadata={
                    "status": "NO_GROUNDED_PLAN",
                    "message": "No grounded troubleshooting instructions available for this query.",
                    "cache_hit": False,
                    "cache_hit_type": "MISS",
                    "latency_ms": round(elapsed_ms, 2),
                    "execution_path": "COLD_PIPELINE",
                    "domain": domain,
                    "query_variations": variations,
                    "variation_count": len(variations)
                }
            )

        # Step 4: Deeplink Mapping with Parent-Menu Protection
        mapped_actions = []
        for raw_act in extracted_data.get("extractedActions", []):
            mapped_act = self.deeplink_mapper.map_action(
                action_dict=raw_act,
                domain=domain,
                query_text=raw_query
            )
            mapped_actions.append(mapped_act)

        # Step 5: Action Sequencing (auto -> manual -> critical last)
        sequenced_actions = self.sequencer.sequence_actions(mapped_actions)

        # Build raw candidate plan
        raw_plan = {
            "goal": extracted_data["goal"],
            "title": extracted_data["title"],
            "score": extracted_data["score"],
            "action": sequenced_actions
        }

        # Step 6: Strict Deterministic Validation & Zero-URL Leak Gate
        is_valid, validated_goal, errors = self.validator.validate_plan(raw_plan)

        if not is_valid or validated_goal is None:
            # Reject invalid output strictly
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return TroubleshootResponse(
                contexts=[],
                metadata={
                    "status": "VALIDATION_FAILED",
                    "validation_errors": errors,
                    "cache_hit": False,
                    "cache_hit_type": "MISS",
                    "latency_ms": round(elapsed_ms, 2),
                    "execution_path": "COLD_PIPELINE",
                    "domain": domain,
                    "query_variations": variations,
                    "variation_count": len(variations)
                }
            )

        # Step 7: Store Only Validated Plans in Semantic Cache
        self.cache.put(normalized_q, validated_goal)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return TroubleshootResponse(
            contexts=[validated_goal],
            metadata={
                "status": "SUCCESS",
                "cache_hit": False,
                "cache_hit_type": "MISS",
                "latency_ms": round(elapsed_ms, 2),
                "execution_path": "COLD_PIPELINE",
                "domain": domain,
                "query_variations": variations,
                "variation_count": len(variations)
            }
        )
