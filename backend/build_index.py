"""Build ChromaDB index from schemes.json for RAG search."""
import json
import os
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


SCHEMES_FILE = Path(__file__).parent.parent / "data" / "schemes.json"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
COLLECTION_NAME = "schemes"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE = 200  # words per raw_text chunk


def load_schemes() -> list:
    """Load schemes from JSON file."""
    with open(SCHEMES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def create_summary_chunk(scheme: dict) -> str:
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


def chunk_text(text: str, max_words: int) -> list:
    """Split text into chunks of approximately max_words."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i + max_words])
        if chunk.strip():
            chunks.append(chunk.strip())
    return chunks


def build_index():
    """Build ChromaDB index from schemes data."""
    print(f"Loading schemes from {SCHEMES_FILE}...")
    schemes = load_schemes()
    print(f"Loaded {len(schemes)} schemes")

    print(f"Loading embedding model: {EMBEDDING_MODEL}...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    print(f"Initializing ChromaDB at {CHROMA_DIR}...")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Delete existing collection if it exists
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Deleted existing collection: {COLLECTION_NAME}")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

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

    print(f"Embedding {len(all_documents)} chunks...")
    embeddings = model.encode(all_documents, show_progress_bar=True, batch_size=32)

    print("Adding to ChromaDB...")
    collection.add(
        documents=all_documents,
        embeddings=embeddings.tolist(),
        metadatas=all_metadatas,
        ids=all_ids
    )

    print(f"Index built successfully! Total chunks: {len(all_documents)}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Persisted at: {CHROMA_DIR}")


if __name__ == "__main__":
    build_index()