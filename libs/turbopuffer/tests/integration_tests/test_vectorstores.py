"""Integration tests for Turbopuffer vector store.

These tests require a live Turbopuffer API key set via the
TURBOPUFFER_API_KEY environment variable.
"""

import uuid
from collections.abc import Generator

import pytest
from langchain_core.embeddings.fake import DeterministicFakeEmbedding
from turbopuffer import Turbopuffer

from langchain_turbopuffer import TurbopufferVectorStore


@pytest.fixture
def embedding() -> DeterministicFakeEmbedding:
    return DeterministicFakeEmbedding(size=6)


@pytest.fixture
def vectorstore(
    embedding: DeterministicFakeEmbedding,
) -> Generator[TurbopufferVectorStore, None, None]:
    tpuf = Turbopuffer(region="gcp-us-central1")
    ns = tpuf.namespace(f"test_integration_{uuid.uuid4().hex[:8]}")

    store = TurbopufferVectorStore(
        namespace=ns,
        embedding=embedding,
    )
    yield store
    store.delete()


def test_add_and_search(vectorstore: TurbopufferVectorStore) -> None:
    """Test adding texts and searching."""
    ids = vectorstore.add_texts(
        ["apple", "banana", "cherry"],
        metadatas=[{"fruit": "apple"}, {"fruit": "banana"}, {"fruit": "cherry"}],
    )
    assert len(ids) == 3

    results = vectorstore.similarity_search("apple", k=1)
    assert len(results) == 1
    assert results[0].page_content == "apple"


def test_add_and_delete(vectorstore: TurbopufferVectorStore) -> None:
    """Test adding and deleting documents."""
    ids = vectorstore.add_texts(["hello", "world"])
    assert len(ids) == 2

    vectorstore.delete(ids[:1])
    results = vectorstore.similarity_search("hello", k=10)
    assert all(r.id != ids[0] for r in results)


def test_search_with_score(vectorstore: TurbopufferVectorStore) -> None:
    """Test similarity search with scores."""
    vectorstore.add_texts(["cat", "dog", "fish"])
    results = vectorstore.similarity_search_with_score("cat", k=3)
    assert len(results) == 3
    assert all(isinstance(r, tuple) and len(r) == 2 for r in results)


def test_get_by_ids(vectorstore: TurbopufferVectorStore) -> None:
    """Test retrieving documents by IDs."""
    ids = vectorstore.add_texts(["one", "two", "three"])
    docs = vectorstore.get_by_ids(ids[:2])
    assert len(docs) == 2
    returned_ids = {d.id for d in docs}
    assert returned_ids == set(ids[:2])


def test_metadata_round_trip(vectorstore: TurbopufferVectorStore) -> None:
    """Test that metadata is preserved through add and retrieval."""
    ids = vectorstore.add_texts(
        ["hello"],
        metadatas=[{"key_str": "value", "key_int": 42}],
    )
    docs = vectorstore.get_by_ids(ids)
    assert len(docs) == 1
    assert docs[0].metadata["key_str"] == "value"
    assert docs[0].metadata["key_int"] == 42


def test_upsert_overwrite(vectorstore: TurbopufferVectorStore) -> None:
    """Test that adding with the same ID overwrites the document."""
    vectorstore.add_texts(["original content"], ids=["doc1"])
    vectorstore.add_texts(["updated content"], ids=["doc1"])

    docs = vectorstore.get_by_ids(["doc1"])
    assert len(docs) == 1
    assert docs[0].page_content == "updated content"


def test_filter_query(vectorstore: TurbopufferVectorStore) -> None:
    """Test similarity search with turbopuffer filter."""
    vectorstore.add_texts(
        ["red apple", "green apple", "blue berry"],
        metadatas=[{"color": "red"}, {"color": "green"}, {"color": "blue"}],
    )

    results = vectorstore.similarity_search(
        "apple",
        k=10,
        filters=("color", "Eq", "red"),
    )
    assert len(results) == 1
    assert results[0].metadata["color"] == "red"


def test_score_ordering(vectorstore: TurbopufferVectorStore) -> None:
    """Test that search with score returns results in ascending distance order."""
    vectorstore.add_texts(["aaa", "bbb", "ccc", "ddd"])
    results = vectorstore.similarity_search_with_score("aaa", k=4)

    assert len(results) == 4
    distances = [score for _, score in results]
    assert distances == sorted(distances), "Distances should be in ascending order"


def test_delete_nonexistent_ids(vectorstore: TurbopufferVectorStore) -> None:
    """Test that deleting non-existent IDs does not raise."""
    # Write something so the namespace exists
    vectorstore.add_texts(["placeholder"], ids=["keep"])
    # Should not raise
    vectorstore.delete(["nonexistent_1", "nonexistent_2"])
    # Original doc should still be there
    docs = vectorstore.get_by_ids(["keep"])
    assert len(docs) == 1


def test_large_batch(vectorstore: TurbopufferVectorStore) -> None:
    """Test adding a large batch of documents."""
    n = 100
    texts = [f"document number {i}" for i in range(n)]
    ids = vectorstore.add_texts(texts)

    assert len(ids) == n
    results = vectorstore.similarity_search("document number 0", k=5)
    assert len(results) == 5


def test_from_texts(embedding: DeterministicFakeEmbedding) -> None:
    """Test the from_texts factory method."""
    tpuf = Turbopuffer(region="gcp-us-central1")
    ns = tpuf.namespace(f"test_from_texts_{uuid.uuid4().hex[:8]}")

    store = TurbopufferVectorStore.from_texts(
        namespace=ns,
        texts=["a", "b", "c"],
        embedding=embedding,
    )

    try:
        results = store.similarity_search("a", k=1)
        assert len(results) == 1
    finally:
        store.delete()
