import uuid
from collections.abc import Generator

import pytest
from langchain_core.vectorstores import VectorStore
from langchain_tests.integration_tests.vectorstores import VectorStoreIntegrationTests
from turbopuffer import Turbopuffer

from langchain_turbopuffer import TurbopufferVectorStore


class TestTurbopufferStandard(VectorStoreIntegrationTests):
    @pytest.fixture
    def vectorstore(self) -> Generator[VectorStore, None, None]:  # type: ignore[override]
        """Get an empty vectorstore for testing."""
        tpuf = Turbopuffer(region="gcp-us-central1")
        ns = tpuf.namespace(f"test_langchain_standard_{uuid.uuid4().hex[:8]}")

        store = TurbopufferVectorStore(
            namespace=ns,
            embedding=self.get_embeddings(),
        )

        # turbopuffer does not create the namespace until first write
        # need to write a dummy document to create the namespace and then delete it
        store.add_texts(["dummy_text"], ids=["dummy_document"])
        store.delete(["dummy_document"])

        try:
            yield store
        finally:
            store.delete()
