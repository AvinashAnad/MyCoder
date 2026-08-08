"""FAISS vector store with nomic-embed-text embeddings via Ollama.

Stores all query/result pairs as embeddings for semantic retrieval.
"""

import json
import os
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

import numpy as np

try:
    import faiss
except ImportError:
    faiss = None

logger = logging.getLogger(__name__)

NOMIC_DIMENSION = 768


@dataclass
class MemoryEntry:
    query: str
    result: str
    timestamp: str
    model: str = ""
    metadata: dict | None = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class VectorStore:
    def __init__(self, client, persist_dir: str, embed_model: str = "nomic-embed-text"):
        self.client = client
        self.embed_model = embed_model
        self.persist_dir = Path(persist_dir)
        self.dimension = NOMIC_DIMENSION
        self.index = None
        self.entries: list[MemoryEntry] = []
        self._init_store()

    @property
    def available(self) -> bool:
        return faiss is not None and self.index is not None

    def _init_store(self):
        if faiss is None:
            logger.warning("faiss-cpu not installed — vector store disabled")
            return

        self.persist_dir.mkdir(parents=True, exist_ok=True)
        index_path = self.persist_dir / "index.faiss"
        meta_path = self.persist_dir / "entries.json"

        if index_path.exists() and meta_path.exists():
            try:
                self.index = faiss.read_index(str(index_path))
                with open(meta_path) as f:
                    raw = json.load(f)
                    self.entries = [MemoryEntry(**e) for e in raw]
                logger.info("Loaded %d entries from vector store", len(self.entries))
            except Exception as e:
                logger.warning("Failed to load vector store: %s", e)
                self.index = faiss.IndexFlatIP(self.dimension)
                self.entries = []
        else:
            self.index = faiss.IndexFlatIP(self.dimension)

    def embed(self, text: str) -> np.ndarray:
        resp = self.client.session.post(
            f"{self.client.base_url}/api/embed",
            json={"model": self.embed_model, "input": text},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        vec = np.array(data["embeddings"][0], dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def add(self, query: str, result: str, model: str = "", metadata: dict | None = None):
        if not self.available:
            return

        entry = MemoryEntry(
            query=query,
            result=result[:2000],
            timestamp=datetime.now().isoformat(),
            model=model,
            metadata=metadata or {},
        )

        combined = f"Query: {query}\nResult: {result[:500]}"
        try:
            vec = self.embed(combined)
        except Exception as e:
            logger.warning("Embedding failed: %s", e)
            return

        self.index.add(vec.reshape(1, -1))
        self.entries.append(entry)
        self._persist()

    def search(self, query: str, k: int = 5) -> list[tuple[MemoryEntry, float]]:
        if not self.available or self.index.ntotal == 0:
            return []

        try:
            vec = self.embed(query)
        except Exception as e:
            logger.warning("Search embedding failed: %s", e)
            return []

        k = min(k, self.index.ntotal)
        scores, indices = self.index.search(vec.reshape(1, -1), k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if 0 <= idx < len(self.entries):
                results.append((self.entries[idx], float(score)))
        return results

    def _persist(self):
        if not self.available:
            return
        try:
            faiss.write_index(self.index, str(self.persist_dir / "index.faiss"))
            with open(self.persist_dir / "entries.json", "w") as f:
                json.dump([asdict(e) for e in self.entries], f)
        except Exception as e:
            logger.warning("Failed to persist vector store: %s", e)

    @property
    def count(self) -> int:
        if not self.available:
            return 0
        return self.index.ntotal
