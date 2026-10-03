"""
benchmark.py - Automated latency profiling and benchmark harness for the Troubleshooting Engine.
Measures cold-path and fast-path cache latencies (P50, P90, P95).
"""

import time
import json
import statistics
from app.schema import TroubleshootRequest
from app.engine.pipeline import TroubleshootingPipeline


def run_benchmark(iterations: int = 100):
    print("=" * 60)
    print("SMART GUIDED TROUBLESHOOTING ENGINE BENCHMARK")
    print("=" * 60)

    pipeline = TroubleshootingPipeline()

    test_queries = [
        "phone swipe navigation moves up and down instead of left and right",
        "battery drains very fast throughout the day",
        "camera is blurry and out of focus",
        "phone is lagging and freezing during app usage",
        "swipe gestures moving vertically instead of horizontally",
        "battery dies super fast after update",
        "photos look all fuzzy and camera wont focus",
        "system sluggish and stuttering with high memory usage"
    ]

    # Warmup / Cold path measurement
    print(f"\n[1] Profiling Cold Path Pipeline ({len(test_queries)} unique queries)...")
    cold_latencies = []
    for q in test_queries:
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

    print(f"  Cold Requests: {len(cold_latencies)}")
    print(f"  Cold Latency P50: {cold_p50:.2f} ms")
    print(f"  Cold Latency P90: {cold_p90:.2f} ms")
    print(f"  Cold Latency P95: {cold_p95:.2f} ms")

    # Prime cache with test queries
    for q in test_queries:
        req = TroubleshootRequest(query=q)
        pipeline.process_query(req)

    # Fast-Path Exact Cache Hits Measurement
    print(f"\n[2] Profiling Fast-Path Exact Cache Hits ({iterations} iterations)...")
    exact_latencies = []
    for i in range(iterations):
        q = test_queries[i % len(test_queries)]
        start = time.perf_counter()
        req = TroubleshootRequest(query=q)
        resp = pipeline.process_query(req)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        exact_latencies.append(elapsed_ms)
        assert resp.metadata["cache_hit"] is True
        assert resp.metadata["cache_hit_type"] == "EXACT_HIT"

    exact_p50 = statistics.median(exact_latencies)
    exact_p90 = statistics.quantiles(exact_latencies, n=10)[8]
    exact_p95 = statistics.quantiles(exact_latencies, n=20)[18]

    print(f"  Exact Cache Hits: {len(exact_latencies)}")
    print(f"  Exact Cache Latency P50: {exact_p50:.2f} ms")
    print(f"  Exact Cache Latency P90: {exact_p90:.2f} ms")
    print(f"  Exact Cache Latency P95: {exact_p95:.2f} ms")

    # Fast-Path Semantic Cache Paraphrase Measurement
    print(f"\n[3] Profiling Fast-Path Semantic Paraphrase Hits ({iterations} iterations)...")
    paraphrases = [
        "swipe navigation moving vertically rather than horizontally",
        "phone battery drains rapidly during day",
        "camera photos look blurry and wont focus at all",
        "phone UI is lagging and freezing constantly"
    ]
    semantic_latencies = []
    semantic_hits = 0

    for i in range(iterations):
        pq = paraphrases[i % len(paraphrases)]
        start = time.perf_counter()
        req = TroubleshootRequest(query=pq)
        resp = pipeline.process_query(req)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        semantic_latencies.append(elapsed_ms)
        if resp.metadata["cache_hit"]:
            semantic_hits += 1

    semantic_p50 = statistics.median(semantic_latencies)
    semantic_p90 = statistics.quantiles(semantic_latencies, n=10)[8]
    semantic_p95 = statistics.quantiles(semantic_latencies, n=20)[18]
    hit_rate = (semantic_hits / iterations) * 100.0

    print(f"  Semantic Paraphrase Hits: {semantic_hits}/{iterations} ({hit_rate:.1f}%)")
    print(f"  Semantic Cache Latency P50: {semantic_p50:.2f} ms")
    print(f"  Semantic Cache Latency P90: {semantic_p90:.2f} ms")
    print(f"  Semantic Cache Latency P95: {semantic_p95:.2f} ms")

    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY (Sub-300ms SLA Target Verification):")
    print("=" * 60)
    print(f"Cached Response P95 (Exact):    {exact_p95:.2f} ms (Target < 300 ms) -> {'PASS' if exact_p95 < 300.0 else 'FAIL'}")
    print(f"Cached Response P95 (Semantic): {semantic_p95:.2f} ms (Target < 300 ms) -> {'PASS' if semantic_p95 < 300.0 else 'FAIL'}")
    print(f"Cold Pipeline P95:             {cold_p95:.2f} ms")
    print(f"Semantic Cache Hit Rate:       {hit_rate:.1f}%")
    print("=" * 60)

    return {
        "cold_p50": round(cold_p50, 2),
        "cold_p95": round(cold_p95, 2),
        "exact_cache_p50": round(exact_p50, 2),
        "exact_cache_p95": round(exact_p95, 2),
        "semantic_cache_p50": round(semantic_p50, 2),
        "semantic_cache_p95": round(semantic_p95, 2),
        "semantic_hit_rate": round(hit_rate, 1)
    }


if __name__ == "__main__":
    run_benchmark(iterations=100)
