"""LangChain integration with Turbopuffer vector database."""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from turbopuffer import omit

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    from turbopuffer.resources import NamespacesResource
    from turbopuffer.types import DistanceMetric
    from turbopuffer.types.custom import Filter

logger = logging.getLogger(__name__)

CONTENT_KEY = "content"
DEFAULT_K = 10
_RESERVED_KEYS = frozenset({"id", "vector", CONTENT_KEY, "$dist"})
_METADATA_PREFIX = "_meta_"


class TurbopufferVectorStore(VectorStore):
    """Turbopuffer vector store integration.

    Setup:
        Install ``turbopuffer`` and ``langchain-turbopuffer`` packages:

        .. code-block:: bash

            pip install -qU turbopuffer langchain-turbopuffer
            export TURBOPUFFER_API_KEY="your-api-key"

    Key init args:
        embedding: Embedding function to use.
        namespace: Turbopuffer namespace to use.

    Example:
        .. code-block:: python

            from langchain_turbopuffer import TurbopufferVectorStore
            from langchain_openai import OpenAIEmbeddings

            from turbopuffer import TurbopufferClient

            tpuf = Turbopuffer(
                # Pick the right region https://turbopuffer.com/docs/regions
                region="gcp-us-central1",
                # This is the default and can be omitted
                api_key=os.environ.get("TURBOPUFFER_API_KEY"),
            )

            ns = tpuf.namespace("my-namespace")

            store = TurbopufferVectorStore(
                embedding=OpenAIEmbeddings(),
                namespace=ns,
            )
    """

    _ns: NamespacesResource
    _distance_metric: DistanceMetric

    def __init__(
        self,
        *,
        embedding: Embeddings,
        namespace: NamespacesResource,
        distance_metric: DistanceMetric = "cosine_distance",
    ) -> None:
        """Initialize TurbopufferVectorStore.

        Args:
            embedding: Embedding function to use.
            namespace: The turbopuffer namespace to use.
            distance_metric: The distance metric for similarity search.
            Default is ``cosine_distance``.
        """
        self._embedding = embedding
        self._ns = namespace
        self._distance_metric = distance_metric

    @property
    def embeddings(self) -> Embeddings | None:
        """Access the query embedding object."""
        return self._embedding

    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: list[dict] | None = None,
        *,
        ids: list[str] | None = None,
        **kwargs: Any,
    ) -> list[str]:
        """Add texts to the vector store.

        Args:
            texts: Texts to add.
            metadatas: Optional list of metadatas.
            ids: Optional list of IDs.
            kwargs: Additional keyword arguments.

        Returns:
            List of IDs of added texts.
        """
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]
        else:
            ids = [id_ if id_ is not None else str(uuid.uuid4()) for id_ in ids]

        texts_list = list(texts)
        embeddings = [
            [float(x) for x in emb]
            for emb in self._embedding.embed_documents(texts_list)
        ]

        if metadatas and len(metadatas) != len(texts_list):
            msg = (
                f"Number of metadatas ({len(metadatas)}) must match "
                f"number of texts ({len(texts_list)})."
            )
            raise ValueError(msg)

        upsert_rows: list[dict[str, Any]] = []
        for i, (text, emb, doc_id) in enumerate(
            zip(texts_list, embeddings, ids, strict=True)
        ):
            row: dict[str, Any] = {
                "id": doc_id,
                "vector": emb,
                CONTENT_KEY: text,
            }
            if metadatas:
                for key, value in metadatas[i].items():
                    if key in _RESERVED_KEYS:
                        logger.warning(
                            "Metadata key %r conflicts with a reserved "
                            "turbopuffer column. Storing as %r.",
                            key,
                            f"{_METADATA_PREFIX}{key}",
                        )
                        row[f"{_METADATA_PREFIX}{key}"] = value
                    else:
                        row[key] = value
            upsert_rows.append(row)

        self._ns.write(
            distance_metric=self._distance_metric,
            upsert_rows=upsert_rows,
        )

        return ids

    def delete(self, ids: list[str] | None = None, **kwargs: Any) -> bool | None:
        """Delete vectors by ID.

        Args:
            ids: List of IDs to delete. If `None`, deletes all documents.
            kwargs: Additional keyword arguments.

        Returns:
            `True` if successful.
        """
        if ids is None:
            self._ns.delete_all()
            return True

        if not ids:
            return True

        self._ns.write(deletes=ids)
        return True

    def get_by_ids(self, ids: Sequence[str], /) -> list[Document]:
        """Get documents by their IDs.

        Args:
            ids: List of IDs to retrieve.

        Returns:
            List of documents. May return fewer documents than requested
            if some IDs are not found.
        """
        if not ids:
            return []

        results = self._ns.query(
            filters=("id", "In", list(ids)),
            limit=len(ids),
            include_attributes=True,
        )

        return self._rows_to_documents(results.rows)

    def similarity_search(
        self,
        query: str,
        k: int = DEFAULT_K,
        filters: Filter | None = None,
        **kwargs: Any,
    ) -> list[Document]:
        """Return docs most similar to query.

        Args:
            query: Query text to search for.
            k: Number of results to return.
            filters: Filters to apply to the query.
            kwargs: Additional keyword arguments.

        Returns:
            List of documents most similar to the query.
        """
        query_embedding = [float(x) for x in self._embedding.embed_query(query)]
        return self.similarity_search_by_vector(query_embedding, k=k, filters=filters)

    def similarity_search_by_vector(
        self,
        embedding: list[float],
        k: int = DEFAULT_K,
        filters: Filter | None = None,
        **kwargs: Any,
    ) -> list[Document]:
        """Return docs most similar to embedding vector.

        Args:
            embedding: Embedding vector to search for.
            k: Number of results to return.
            filters: Filter to apply to the query.

        Returns:
            List of documents most similar to the embedding.
        """
        results = self._ns.query(
            rank_by=("vector", "ANN", embedding),
            top_k=k,
            filters=filters if filters is not None else omit,
            include_attributes=True,
        )

        return self._rows_to_documents(results.rows)

    def similarity_search_with_score(
        self,
        query: str,
        k: int = DEFAULT_K,
        filters: Filter | None = None,
        **kwargs: Any,
    ) -> list[tuple[Document, float]]:
        """Return docs and distance scores most similar to query.

        Args:
            query: Query text to search for.
            k: Number of results to return.
            filters: Filters to apply to the query.
            kwargs: Additional keyword arguments.

        Returns:
            List of ``(document, distance)`` tuples. Lower distance means
            more similar.
        """
        query_embedding = [float(x) for x in self._embedding.embed_query(query)]

        results = self._ns.query(
            rank_by=("vector", "ANN", query_embedding),
            top_k=k,
            filters=filters if filters is not None else omit,
            include_attributes=True,
        )

        docs_and_scores: list[tuple[Document, float]] = []
        for row in results.rows or []:
            doc = self._row_to_document(row)
            dist = getattr(row, "$dist", 0.0)
            docs_and_scores.append((doc, dist))

        return docs_and_scores

    def _select_relevance_score_fn(self) -> Callable[[float], float]:
        """Select the relevance score function based on distance metric.

        Returns:
            A function that converts a distance to a relevance score in [0, 1].
        """
        if self._distance_metric == "cosine_distance":
            return self._cosine_relevance_score_fn
        if self._distance_metric == "euclidean_squared":
            return self._euclidean_relevance_score_fn
        msg = (
            f"Unknown distance metric: {self._distance_metric}. "
            "Expected 'cosine_distance' or 'euclidean_squared'."
        )
        raise ValueError(msg)

    @classmethod
    def from_texts(
        cls,
        texts: list[str],
        embedding: Embeddings,
        metadatas: list[dict] | None = None,
        *,
        ids: list[str] | None = None,
        **kwargs: Any,
    ) -> TurbopufferVectorStore:
        """Create a TurbopufferVectorStore from texts.

        Args:
            texts: List of texts to add.
            embedding: Embedding function.
            metadatas: Optional list of metadatas.
            ids: Optional list of IDs.
            kwargs: Additional keyword arguments. Must include
                ``namespace`` (a turbopuffer ``NamespacesResource``).

        Returns:
            Initialized `TurbopufferVectorStore`.
        """
        store = cls(embedding=embedding, **kwargs)
        store.add_texts(texts, metadatas=metadatas, ids=ids)
        return store

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _rows_to_documents(self, rows: Any) -> list[Document]:
        """Convert turbopuffer result rows to LangChain Documents.

        Args:
            rows: Iterable of turbopuffer row objects.

        Returns:
            List of `Document` objects.
        """
        return [self._row_to_document(row) for row in rows]

    @staticmethod
    def _row_to_document(row: Any) -> Document:
        """Convert a single turbopuffer row to a LangChain Document.

        Args:
            row: A turbopuffer row object with `id` and attribute fields.

        Returns:
            A `Document` object.
        """
        row_dict: dict[str, Any] = (
            row.to_dict() if hasattr(row, "to_dict") else dict(row)
        )  # type: ignore[call-overload]

        doc_id = str(row_dict.get("id", ""))
        content = row_dict.get(CONTENT_KEY, "")

        metadata: dict[str, Any] = {}
        for key, value in row_dict.items():
            if key in _RESERVED_KEYS:
                continue
            if key.startswith(_METADATA_PREFIX):
                metadata[key[len(_METADATA_PREFIX) :]] = value
            else:
                metadata[key] = value

        return Document(
            id=doc_id,
            page_content=str(content),
            metadata=metadata,
        )
