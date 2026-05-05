"""
RAG over the local knowledge base (markdown files).
Returns the most relevant snippets for the agent to ground its responses.
"""
import os
import glob
import re
from typing import List, Dict, Optional


class KnowledgeRetriever:
    """Lightweight TF-IDF retrieval over markdown FAQ/KB files."""

    def __init__(self, knowledge_dir: str = "./knowledge_base"):
        self.knowledge_dir = knowledge_dir
        self.documents = self._load()

    def _load(self) -> List[Dict]:
        docs = []
        for path in glob.glob(f"{self.knowledge_dir}/**/*.md", recursive=True):
            with open(path, encoding="utf-8") as f:
                content = f.read()
            for chunk in self._chunk(content):
                docs.append({
                    "source": os.path.basename(path),
                    "content": chunk,
                    "tokens": self._tokenize(chunk),
                })
        return docs

    @staticmethod
    def _chunk(text: str, max_chars: int = 800) -> List[str]:
        sections = re.split(r"\n##+ ", text)
        return [s for s in sections if len(s.strip()) > 20][:max_chars]

    @staticmethod
    def _tokenize(text: str) -> set:
        return set(re.findall(r"\b[a-z]{3,}\b", text.lower()))

    def search(self, query: str, k: int = 3, intent: Optional[str] = None) -> List[Dict]:
        query_tokens = self._tokenize(query)
        scored = [
            {**d, "score": len(query_tokens & d["tokens"]) / max(1, len(query_tokens))}
            for d in self.documents
        ]
        if intent:
            scored = [d for d in scored if intent in d["source"].lower() or d["score"] > 0]
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]
