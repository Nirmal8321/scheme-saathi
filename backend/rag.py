"""RAG module - Gemini embeddings index building and scheme search."""
import json
import os
from pathlib import Path
from typing import List, Dict, Optional

import numpy as np

SCHEMES_FILE = Path(__file__).parent.parent / "data" / "schemes.json"
INDEX_FILE = Path(__file__).parent.parent / "data" / "index.npz"

# Module-level cache
_schemes_cache = None
_embeddings = None
_documents = None
_metadatas = None
_ids = None
_index_loaded = False


def _load_schemes() -> List[Dict]:
    """Load and cache schemes."""
    global _schemes_cache
    if _schemes_cache is None:
        with open(SCHEMES_FILE, "r", encoding="utf-8") as f:
            _schemes_cache = json.load(f)
    return _schemes_cache


def _load_index():
    """Load the index from index.npz file."""
    global _embeddings, _documents, _metadatas, _ids, _index_loaded
    if _index_loaded:
        return

    if not INDEX_FILE.exists():
        print("Warning: index.npz not found. Run build_index.py first.")
        _index_loaded = True
        return

    try:
        data = np.load(INDEX_FILE, allow_pickle=True)
        _embeddings = data["embeddings"]
        _documents = data["documents"]
        _metadatas = data["metadatas"]
        _ids = data["ids"]
        _index_loaded = True
        print(f"Loaded index with {len(_embeddings)} chunks")
    except Exception as e:
        print(f"Warning: Failed to load index.npz: {e}")
        _index_loaded = True


def _keyword_search(query: str, k: int = 6) -> List[Dict]:
    """
    Simple keyword-based search as fallback.
    Scores based on keyword overlap with scheme raw_text and eligibility.
    """
    schemes = _load_schemes()
    query_lower = query.lower()
    query_words = set(query_lower.split())

    results = []
    for scheme in schemes:
        # Build searchable text
        searchable_text = " ".join([
            scheme.get("raw_text", ""),
            " ".join(scheme.get("eligibility", [])),
            scheme.get("category", ""),
            scheme.get("name", ""),
        ]).lower()

        # Score based on word overlap
        text_words = set(searchable_text.split())
        overlap = len(query_words & text_words)
        if overlap > 0:
            score = overlap * 0.1
            for word in query_words:
                if word in searchable_text:
                    score += 0.05

            if score > 0:
                raw_text = scheme.get("raw_text", "")
                context = raw_text[:500]

                results.append({
                    "scheme_id": scheme["id"],
                    "scheme_name": scheme["name"],
                    "text": context,
                    "score": min(score, 1.0),
                    "chunk_type": "keyword"
                })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:k]


def embed_query(query: str) -> Optional[np.ndarray]:
    """Embed a query using Gemini embedding model. Uses disk cache for repeats."""
    from backend.config import LLM_API_KEY
    from google import genai

    cache_dir = Path(__file__).parent.parent / "llm_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"embed_{hash(query)}.npy"

    # Check disk cache
    if cache_file.exists():
        try:
            return np.load(cache_file)
        except Exception:
            pass

    try:
        client = genai.Client(api_key=LLM_API_KEY)
        result = client.models.embed_content(
            model="models/gemini-embedding-001",
            contents=query
        )
        embedding = np.array(result.embeddings[0].values, dtype=np.float32)
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        # Save to cache
        try:
            np.save(cache_file, embedding)
        except Exception:
            pass

        return embedding
    except Exception as e:
        print(f"Warning: Failed to embed query: {e}")
        return None


def search(query: str, k: int = 6) -> List[Dict]:
    """
    Search for relevant scheme chunks.

    Args:
        query: Search query in any language (Marathi, Hindi, English)
        k: Number of top results to return

    Returns:
        List of dicts with scheme_id, scheme_name, text, score, chunk_type
    """
    _load_index()

    if _index_loaded and _embeddings is not None and len(_embeddings) > 0:
        # Try vector search
        try:
            query_emb = embed_query(query)
            if query_emb is not None:
                # Cosine similarity (embeddings are normalized)
                scores = np.dot(_embeddings, query_emb)
                top_indices = np.argsort(scores)[::-1][:k]

                output = []
                for idx in top_indices:
                    if scores[idx] > 0:
                        meta = _metadatas[idx]
                        output.append({
                            "scheme_id": meta["scheme_id"],
                            "scheme_name": meta["scheme_name"],
                            "text": str(_documents[idx]),
                            "score": float(scores[idx]),
                            "chunk_type": meta.get("chunk_type", "unknown")
                        })
                return output
        except Exception as e:
            print(f"Vector search failed, falling back to keyword: {e}")

    # Fallback to keyword search
    return _keyword_search(query, k)


def get_scheme(scheme_id: str) -> Optional[Dict]:
    """
    Get full scheme details from schemes.json by scheme_id.

    Args:
        scheme_id: The scheme identifier

    Returns:
        Full scheme dict or None if not found
    """
    schemes = _load_schemes()
    for scheme in schemes:
        if scheme["id"] == scheme_id:
            return scheme
    return None


def list_schemes() -> List[Dict]:
    """
    List all schemes with basic info.

    Returns:
        List of scheme dicts with id, name, category, benefit
    """
    schemes = _load_schemes()
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "category": s["category"],
            "benefit": s["benefit"],
            "level": s["level"],
            "state": s.get("state")
        }
        for s in schemes
    ]


def get_schemes_for_profile(profile: Dict, k: int = 6) -> List[Dict]:
    """
    Search schemes relevant to a user profile.

    Args:
        profile: User profile dict with occupation, income, etc.
        k: Number of results per query

    Returns:
        Combined and deduplicated search results
    """
    # Build query from profile
    query_parts = []
    if profile.get("occupation"):
        query_parts.append(profile["occupation"])
    if profile.get("annual_income"):
        query_parts.append(f"income {profile['annual_income']}")
    if profile.get("land_acres"):
        query_parts.append(f"{profile['land_acres']} acre land")
    if profile.get("state"):
        query_parts.append(profile["state"])
    if profile.get("caste_category"):
        query_parts.append(profile["caste_category"])
    if profile.get("gender"):
        query_parts.append(profile["gender"])

    query = " ".join(query_parts) if query_parts else "government scheme benefits"
    return search(query, k=k)


if __name__ == "__main__":
    # Quick test
    print("Testing RAG search...")
    results = search("farmer 2 acre income support", k=3)
    for r in results:
        print(f"  {r['scheme_name']} ({r['scheme_id']}): {r['score']:.3f} - {r['text'][:80]}...")

    print("\nListing all schemes:")
    for s in list_schemes():
        print(f"  {s['id']}: {s['name']} ({s['category']})")