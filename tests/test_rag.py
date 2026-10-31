"""Test script for RAG search functionality."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.rag import search, list_schemes


def test_search():
    """Run test queries and print top 3 results each."""
    test_queries = [
        # English queries
        "farmer 2 acre income support",
        "woman entrepreneur loan business",
        "student SC scholarship education",
        # Marathi query
        "शेतकरी जमीन उत्पन्न सहाय्य",
        # Hindi query
        "महिला उद्यमी लोन व्यवसाय",
    ]

    print("=" * 60)
    print("RAG Search Test Results")
    print("=" * 60)

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 60)
        results = search(query, k=3)
        if results:
            for i, r in enumerate(results, 1):
                print(f"  {i}. {r['scheme_name']} ({r['scheme_id']}) - Score: {r['score']:.3f}")
                print(f"     Type: {r['chunk_type']}")
                print(f"     Text: {r['text'][:120]}...")
        else:
            print("  No results found")

    print("\n" + "=" * 60)
    print("All Schemes in Index:")
    print("=" * 60)
    schemes = list_schemes()
    for s in schemes:
        print(f"  {s['id']}: {s['name']} [{s['category']}] - {s['benefit']}")

    print("\nTest completed!")


if __name__ == "__main__":
    test_search()