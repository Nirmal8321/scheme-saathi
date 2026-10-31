"""RAG module - ChromaDB index building and scheme search."""
import json
from pathlib import Path
from typing import List, Dict, Optional

# Try to import heavy dependencies, fall back to mock if not available
try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False

SCHEMES_FILE = Path(__file__).parent.parent / "data" / "schemes.json"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
COLLECTION_NAME = "schemes"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


# Global model and client (lazy initialization)
_model = None
_client = None
_collection = None
_schemes_cache = None


def _load_schemes():
    """Load and cache schemes for mock search."""
    global _schemes_cache
    if _schemes_cache is None:
        with open(SCHEMES_FILE, "r", encoding="utf-8") as f:
            _schemes_cache = json.load(f)
    return _schemes_cache


def _mock_search(query: str, k: int = 6) -> List[Dict]:
    """
    Simple keyword-based mock search when chromadb is not available.
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
            # Also check for specific keywords
            score = overlap * 0.1
            # Boost for exact phrase matches
            for word in query_words:
                if word in searchable_text:
                    score += 0.05

            if score > 0:
                # Create a context chunk from raw_text
                raw_text = scheme.get("raw_text", "")
                # Take first 500 chars as context
                context = raw_text[:500]

                results.append({
                    "scheme_id": scheme["id"],
                    "scheme_name": scheme["name"],
                    "text": context,
                    "score": min(score, 1.0),
                    "chunk_type": "mock"
                })

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:k]


def _get_model():
    """Get or create the embedding model."""
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def _get_collection():
    """Get or create the ChromaDB collection."""
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = _client.get_collection(COLLECTION_NAME)
    return _collection


def search(query: str, k: int = 6) -> List[Dict]:
    """
    Search for relevant scheme chunks.

    Args:
        query: Search query in any language (Marathi, Hindi, English)
        k: Number of top results to return

    Returns:
        List of dicts with scheme_id, text, score
    """
    if HAS_CHROMA:
        try:
            model = _get_model()
            collection = _get_collection()

            query_embedding = model.encode([query])[0].tolist()

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )

            # Process results
            output = []
            if results["documents"] and results["documents"][0]:
                for doc, meta, dist in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0]
                ):
                    # Convert distance to similarity score (cosine: 1 - distance)
                    score = 1.0 - dist
                    output.append({
                        "scheme_id": meta["scheme_id"],
                        "scheme_name": meta["scheme_name"],
                        "text": doc,
                        "score": score,
                        "chunk_type": meta.get("chunk_type", "unknown")
                    })

            return output
        except Exception:
            # Fall back to mock if ChromaDB fails
            pass

    # Fallback to mock search
    return _mock_search(query, k)


def get_scheme(scheme_id: str) -> Optional[Dict]:
    """
    Get full scheme details from schemes.json by scheme_id.

    Args:
        scheme_id: The scheme identifier

    Returns:
        Full scheme dict or None if not found
    """
    with open(SCHEMES_FILE, "r", encoding="utf-8") as f:
        schemes = json.load(f)

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
    with open(SCHEMES_FILE, "r", encoding="utf-8") as f:
        schemes = json.load(f)

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