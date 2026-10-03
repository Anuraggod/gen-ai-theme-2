"""
benchmark.py - Rigorous Latency and Semantic Hit-Rate Profiling Harness.
Ensures zero contamination in semantic cache evaluation:
1. Primes cache only with canonical reference queries.
2. Evaluates distinct unprimed paraphrases without inserting misses into the cache.
3. Separates cold-path, exact-hit, and genuine semantic-hit latencies.
"""

import time
import statistics
from typing import Dict, Any, List
from app.schema import TroubleshootRequest
from app.engine.pipeline import TroubleshootingPipeline


def run_benchmark(iterations: int = 100) -> Dict[str, Any]:
    print("=" * 65)
    print("SMART GUIDED TROUBLESHOOTING ENGINE — RIGOROUS BENCHMARK")
    print("=" * 65)

    pipeline = TroubleshootingPipeline()

    canonical_queries = [
        "phone swipe navigation moves up and down instead of left and right",
        "battery drains very fast throughout the day",
        "camera is blurry and out of focus",
        "phone is lagging and freezing during app usage"
    ]

    # Test Paraphrases (Never inserted into cache during semantic hit rate testing)
    test_paraphrases = [
        "swipe navigation moving vertically instead of horizontally",
        "phone swipe gesture direction wrong in display settings",
        "battery dying super fast after latest update",
        "excessive battery drain and short runtime",
        "photos look blurry and camera autofocus will not lock",
        "camera lens preview is fuzzy and out of focus",
        "device UI stuttering and apps freezing during multitasking",
        "phone lagging heavily and low available memory"
    ]

    # SECTION 1: Cold Path Measurements (Each query executed on empty cache)
    print(f"\n[1] Profiling Cold Path Pipeline ({len(canonical_queries)} queries)...")
    cold_latencies = []
    for q in canonical_queries:
        pipeline.cache.clear()
        start = time.perf_counter()
        req = TroubleshootRequest(query=q)
        resp = pipeline.process_query(req)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        cold_latencies.append(elapsed_ms)
        assert resp.metadata["cache_hit"] is False

    cold_p50 = statistics.median(cold_latencies)
    cold_p90 = statistics.quantiles(cold_latencies, n=10)[8] if len(cold_latencies) >= 10 else max(cold_latencies)
    cold_p95 = statistics.quantiles(cold_latencies, n=20)[18] if len(cold_latencies) >= 20 else max(cold_latencies)

    print(f"  Cold Requests Executed: {len(cold_latencies)}")
    print(f"  Cold Path Latency P50: {cold_p50:.3f} ms")
    print(f"  Cold Path Latency P90: {cold_p90:.3f} ms")
    print(f"  Cold Path Latency P95: {cold_p95:.3f} ms")

    # SECTION 2: Prime Cache ONLY with Canonical Queries
    pipeline.cache.clear()
    for q in canonical_queries:
        req = TroubleshootRequest(query=q)
        pipeline.process_query(req)

    # Verify cache contains exactly canonical entries
    assert pipeline.cache.size() == len(canonical_queries)

    # SECTION 3: Exact Cache Hit Latency (Targeted verification)
    print(f"\n[2] Profiling Exact Cache Hits ({iterations} iterations)...")
    exact_latencies = []
    for i in range(iterations):
        q = canonical_queries[i % len(canonical_queries)]
        start = time.perf_counter()
        # Direct lookup to avoid pipeline side-effects
        norm_q = pipeline.enricher.normalize_query(q)
        goal, hit_type, sim = pipeline.cache.get(norm_q)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        assert hit_type == "EXACT_HIT"
        exact_latencies.append(elapsed_ms)

    exact_p50 = statistics.median(exact_latencies)
    exact_p90 = statistics.quantiles(exact_latencies, n=10)[8]
    exact_p95 = statistics.quantiles(exact_latencies, n=20)[18]

    print(f"  Exact Cache Hits: {len(exact_latencies)}")
    print(f"  Exact Cache Latency P50: {exact_p50:.3f} ms")
    print(f"  Exact Cache Latency P90: {exact_p90:.3f} ms")
    print(f"  Exact Cache Latency P95: {exact_p95:.3f} ms")

    # SECTION 4: Uncontaminated Semantic Hit Rate & Latency
    print(f"\n[3] Profiling Genuine Semantic Paraphrase Retrieval ({len(test_paraphrases)} distinct paraphrases x 25 repetitions = {len(test_paraphrases)*25} tests)...")
    semantic_hit_count = 0
    semantic_miss_count = 0
    semantic_latencies = []

    # Ensure cache still only has canonical queries (uncontaminated)
    initial_cache_size = pipeline.cache.size()

    for i in range(25):
        for pq in test_paraphrases:
            norm_pq = pipeline.enricher.normalize_query(pq)
            start = time.perf_counter()
            # Test semantic lookup directly without calling cache.put()
            goal, hit_type, sim = pipeline.cache.get(norm_pq)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            semantic_latencies.append(elapsed_ms)

            if hit_type == "SEMANTIC_HIT":
                semantic_hit_count += 1
            else:
                semantic_miss_count += 1

    total_semantic_tests = semantic_hit_count + semantic_miss_count
    genuine_semantic_hit_rate = (semantic_hit_count / total_semantic_tests) * 100.0

    semantic_p50 = statistics.median(semantic_latencies)
    semantic_p90 = statistics.quantiles(semantic_latencies, n=10)[8]
    semantic_p95 = statistics.quantiles(semantic_latencies, n=20)[18]

    # Verify cache size never changed during measurement
    assert pipeline.cache.size() == initial_cache_size

    print(f"  Total Semantic Tests: {total_semantic_tests}")
    print(f"  Semantic Hits: {semantic_hit_count}")
    print(f"  Semantic Misses: {semantic_miss_count}")
    print(f"  Genuine Semantic Hit Rate: {genuine_semantic_hit_rate:.1f}%")
    print(f"  Semantic Retrieval Latency P50: {semantic_p50:.3f} ms")
    print(f"  Semantic Retrieval Latency P90: {semantic_p90:.3f} ms")
    print(f"  Semantic Retrieval Latency P95: {semantic_p95:.3f} ms")

    print("\n" + "=" * 65)
    print("BENCHMARK AUDIT SUMMARY (Target < 300 ms SLA under local environment):")
    print("=" * 65)
    print(f"  Fast-Path Exact Hit P95:       {exact_p95:.3f} ms  (Target < 300 ms) -> {'PASS' if exact_p95 < 300.0 else 'FAIL'}")
    print(f"  Fast-Path Semantic Hit P95:    {semantic_p95:.3f} ms  (Target < 300 ms) -> {'PASS' if semantic_p95 < 300.0 else 'FAIL'}")
    print(f"  Cold Pipeline P95:             {cold_p95:.3f} ms")
    print(f"  Uncontaminated Semantic Hit %: {genuine_semantic_hit_rate:.1f}%")
    print("=" * 65)

    return {
        "cold_p50_ms": round(cold_p50, 3),
        "cold_p95_ms": round(cold_p95, 3),
        "exact_p50_ms": round(exact_p50, 3),
        "exact_p95_ms": round(exact_p95, 3),
        "semantic_p50_ms": round(semantic_p50, 3),
        "semantic_p95_ms": round(semantic_p95, 3),
        "semantic_hit_count": semantic_hit_count,
        "semantic_miss_count": semantic_miss_count,
        "semantic_hit_rate_pct": round(genuine_semantic_hit_rate, 1)
    }


if __name__ == "__main__":
    run_benchmark(iterations=100)
