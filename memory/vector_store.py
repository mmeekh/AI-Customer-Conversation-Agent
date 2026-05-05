"""
Vector-based long-term memory using ChromaDB.
Stores embeddings of past conversations for semantic retrieval.
"""
import os
import chromadb
from chromadb.config import Settings
from datetime import datetime
from typing import List, Dict, Optional


class VectorMemory:
    """Semantic memory layer using sentence-transformer embeddings."""

    def __init__(self, persist_dir: str = "./data/chroma", collection: str = "conversations"):
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection,
            metadata={"hnsw:space": "cosine"},
        )

    def remember(self, thread_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> str:
        doc_id = f"{thread_id}-{datetime.utcnow().isoformat()}"
        meta = {
            "thread_id": thread_id,
            "role": role,
            "timestamp": datetime.utcnow().isoformat(),
            **(metadata or {}),
        }
        self.collection.add(documents=[content], metadatas=[meta], ids=[doc_id])
        return doc_id

    def recall(self, query: str, k: int = 5, thread_id: Optional[str] = None) -> List[Dict]:
        where = {"thread_id": thread_id} if thread_id else None
        results = self.collection.query(query_texts=[query], n_results=k, where=where)
        return [
            {"content": doc, "metadata": meta, "distance": dist}
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]

    def recall_similar_customers(self, query: str, k: int = 3) -> List[Dict]:
        """Find similar past tickets across all threads (cross-customer learning)."""
        return self.recall(query, k=k, thread_id=None)

    def forget_thread(self, thread_id: str) -> int:
        results = self.collection.get(where={"thread_id": thread_id})
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
        return len(results["ids"])
