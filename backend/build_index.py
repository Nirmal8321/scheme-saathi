"""Build search index from schemes.json using Gemini embeddings."""
import json
import os
import numpy as np
from pathlib import Path
from typing import List, Dict

from backend.config import LLM_API_KEY
from google import genai

SCHEMES_FILE = Path(__file__).parent.parent / "data" / "schemes.json"
INDEX_FILE = Path(__file__).parent.parent / "data" / "index.npz"
EMBEDDING_MODEL = "models/gemini-embedding-001"
CHUNK_SIZE = 200  # words per raw_text chunk


def load_schemes() -> List[Dict]:
    """Load schemes from JSON file."""
    with open(SCHEMES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def create_summary_chunk(scheme: Dict) -> str:
    """Create a summary chunk from structured scheme fields."""
    parts = [
        f"Scheme: {scheme['name']}",
        f"Benefit: {scheme['benefit']}",
        f"Category: {scheme['category']}",
        f"Level: {scheme['level']}",
        f"Eligibility: {'; '.join(scheme['eligibility'])}",
        f"Documents: {', '.join(scheme['documents'])}",
        f"How to apply: {scheme['how_to_apply']}",
    ]
    if scheme.get("state"):
        parts.append(f"State: {scheme['state']}")
    return "\n".join(parts)


def chunk_text(text: str, max_words: int) -> List[str]:
    """Split text into chunks of approximately max_words."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i + max_words])
        if chunk.strip():
            chunks.append(chunk.strip())
    return chunks


def build_index():
    """Build search index from schemes data using Gemini embeddings."""
    print(f"Loading schemes from {SCHEMES_FILE}...")
    schemes = load_schemes()
    print(f"Loaded {len(schemes)} schemes")

    print(f"Initializing Gemini client...")
    client = genai.Client(api_key=LLM_API_KEY)

    all_documents = []
    all_metadatas = []
    all_ids = []

    for scheme in schemes:
        scheme_id = scheme["id"]
        scheme_name = scheme["name"]

        # Chunk 1: Summary of structured fields
        summary = create_summary_chunk(scheme)
        all_documents.append(summary)
        all_metadatas.append({
            "scheme_id": scheme_id,
            "scheme_name": scheme_name,
            "chunk_type": "summary"
        })
        all_ids.append(f"{scheme_id}_summary")

        # Chunks from raw_text
        raw_text = scheme.get("raw_text", "")
        if raw_text:
            text_chunks = chunk_text(raw_text, CHUNK_SIZE)
            for idx, chunk in enumerate(text_chunks):
                all_documents.append(chunk)
                all_metadatas.append({
                    "scheme_id": scheme_id,
                    "scheme_name": scheme_name,
                    "chunk_type": "raw_text",
                    "chunk_index": idx
                })
                all_ids.append(f"{scheme_id}_raw_{idx}")

    print(f"Embedding {len(all_documents)} chunks with {EMBEDDING_MODEL}...")
    embeddings_list = []
    batch_size = 32

    for i in range(0, len(all_documents), batch_size):
        batch = all_documents[i:i + batch_size]
        print(f"  Processing batch {i//batch_size + 1}/{(len(all_documents) + batch_size - 1)//batch_size}...")
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=batch
        )
        for emb in result.embeddings:
            embeddings_list.append(emb.values)

    embeddings = np.array(embeddings_list, dtype=np.float32)
    print(f"Embeddings shape: {embeddings.shape}")

    # Normalize embeddings for cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / np.maximum(norms, 1e-10)

    # Save to index.npz
    print(f"Saving index to {INDEX_FILE}...")
    np.savez_compressed(
        INDEX_FILE,
        embeddings=embeddings,
        documents=np.array(all_documents, dtype=object),
        metadatas=np.array(all_metadatas, dtype=object),
        ids=np.array(all_ids, dtype=object)
    )

    print(f"Index built successfully! Total chunks: {len(all_documents)}")
    print(f"Saved to: {INDEX_FILE}")


if __name__ == "__main__":
    build_index()