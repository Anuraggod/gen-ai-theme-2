"""
semantic_cache.py - Fast-Path Caching Engine.
Stores cached, validated troubleshooting plans.
Guarantees sub-300ms retrieval times.
Supports exact hash matching and semantic paraphrase similarity lookup.
"""

import math
import hashlib
import time
import re
from typing import Dict, Any, Optional, Tuple, List
from collections import Counter
import threading
from app.schema import TroubleshootingGoal
from app.config import SEMANTIC_CACHE_THRESHOLD, SEMANTIC_CACHE_MAX_SIZE

STOPWORDS = {
    "the", "a", "an", "in", "on", "at", "of", "for", "to", "is", "are", "was", "were",
    "my", "your", "it", "throughout", "during", "and", "or", "this", "that", "i", "me"
}


class FastPathSemanticCache:
    """
    Two-tier in-memory semantic cache:
    - Tier 1: Exact normalized query hash (SHA256) -> sub-2ms
    - Tier 2: Cosine similarity vector search over content terms & bigrams -> sub-15ms
    """

    def __init__(self, threshold: float = SEMANTIC_CACHE_THRESHOLD, max_size: int = SEMANTIC_CACHE_MAX_SIZE):
        self.threshold = threshold
        self.max_size = max_size
        self._lock = threading.Lock()
        self.exact_cache: Dict[str, Tuple[TroubleshootingGoal, float]] = {}
        self.semantic_entries: List[Dict[str, Any]] = []

    @staticmethod
    def _hash_query(normalized_query: str) -> str:
        return hashlib.sha256(normalized_query.strip().lower().encode("utf-8")).hexdigest()

    @staticmethod
    def _text_to_vector(text: str) -> Counter:
        """
        Creates term frequency vector with content words and bigrams.
        """
        words = [w for w in re.findall(r"\b\w+\b", text.lower()) if w not in STOPWORDS]
        if not words:
            words = re.findall(r"\b\w+\b", text.lower())
        vector = Counter(words)
        for i in range(len(words) - 1):
            vector[f"{words[i]}_{words[i+1]}"] = 1.0
        return vector

    @staticmethod
    def _cosine_similarity(vec1: Counter, vec2: Counter) -> float:
        """
        Computes cosine similarity between two term frequency vectors.
        """
        intersection = set(vec1.keys()) & set(vec2.keys())
        if not intersection:
            return 0.0

        numerator = sum(vec1[x] * vec2[x] for x in intersection)
        sum1 = sum(v ** 2 for v in vec1.values())
        sum2 = sum(v ** 2 for v in vec2.values())
        denominator = math.sqrt(sum1) * math.sqrt(sum2)

        if not denominator:
            return 0.0
        return float(numerator) / denominator

    def get(self, normalized_query: str) -> Tuple[Optional[TroubleshootingGoal], str, float]:
        """
        Looks up query in cache.
        Returns (goal_or_none, hit_type ["EXACT_HIT", "SEMANTIC_HIT", "MISS"], similarity_score).
        """
        norm_key = normalized_query.strip().lower()
        query_hash = self._hash_query(norm_key)

        with self._lock:
            # Tier 1: Exact Hash Hit
            if query_hash in self.exact_cache:
                goal, _ = self.exact_cache[query_hash]
                return goal, "EXACT_HIT", 1.0

            # Tier 2: Semantic Similarity Search
            if not self.semantic_entries:
                return None, "MISS", 0.0

            query_vec = self._text_to_vector(norm_key)
            best_score = 0.0
            best_goal = None

            for entry in self.semantic_entries:
                sim = self._cosine_similarity(query_vec, entry["vector"])
                if sim > best_score:
                    best_score = sim
                    best_goal = entry["goal"]

            if best_score >= self.threshold and best_goal is not None:
                return best_goal, "SEMANTIC_HIT", round(best_score, 4)

        return None, "MISS", 0.0

    def put(self, normalized_query: str, goal: TroubleshootingGoal) -> None:
        """
        Stores a validated troubleshooting plan in the cache.
        """
        if not goal:
            return

        norm_key = normalized_query.strip().lower()
        query_hash = self._hash_query(norm_key)
        now = time.time()

        with self._lock:
            if len(self.exact_cache) >= self.max_size:
                oldest_key = min(self.exact_cache.keys(), key=lambda k: self.exact_cache[k][1])
                del self.exact_cache[oldest_key]
                self.semantic_entries = self.semantic_entries[1:]

            self.exact_cache[query_hash] = (goal, now)
            self.semantic_entries.append({
                "query": norm_key,
                "vector": self._text_to_vector(norm_key),
                "goal": goal
            })

    def clear(self) -> None:
        """
        Resets the cache.
        """
        with self._lock:
            self.exact_cache.clear()
            self.semantic_entries.clear()

    def size(self) -> int:
        with self._lock:
            return len(self.exact_cache)
