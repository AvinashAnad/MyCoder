"""Tests for the FAISS vector store."""

import json
import os
import pytest
import numpy as np

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

from unittest.mock import MagicMock, patch


@pytest.mark.skipif(not HAS_FAISS, reason="faiss-cpu not installed")
class TestVectorStore:
    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.base_url = "http://localhost:11434"

        def fake_embed_post(url, json=None, timeout=None):
            resp = MagicMock()
            vec = np.random.randn(768).astype(np.float32)
            vec /= np.linalg.norm(vec)
            resp.json.return_value = {"embeddings": [vec.tolist()]}
            resp.raise_for_status = MagicMock()
            return resp

        client.session.post = fake_embed_post
        return client

    @pytest.fixture
    def store(self, mock_client, tmp_path):
        from mycoder.vector_store import VectorStore
        return VectorStore(mock_client, str(tmp_path), "nomic-embed-text")

    def test_available(self, store):
        assert store.available is True

    def test_initial_count_zero(self, store):
        assert store.count == 0

    def test_add_increments_count(self, store):
        store.add("how do I sort?", "Use sorted()", model="test")
        assert store.count == 1

    def test_search_returns_results(self, store):
        store.add("how do I sort a list?", "Use sorted()")
        store.add("how do I read a file?", "Use open()")
        results = store.search("sorting")
        assert len(results) > 0

    def test_persist_and_reload(self, store, mock_client, tmp_path):
        store.add("test query", "test result")
        assert store.count == 1

        from mycoder.vector_store import VectorStore
        store2 = VectorStore(mock_client, str(tmp_path))
        assert store2.count == 1
        assert store2.entries[0].query == "test query"

    def test_search_empty_store(self, store):
        results = store.search("anything")
        assert results == []

    def test_result_truncation(self, store):
        long_result = "x" * 5000
        store.add("q", long_result)
        assert len(store.entries[0].result) == 2000
