# langchain-turbopuffer

This repository contains the [langchain-turbopuffer](https://pypi.org/project/langchain-turbopuffer/) integration package for LangChain.

[turbopuffer](https://turbopuffer.com/) is a fast, cost-efficient vector database. This package provides a `TurbopufferVectorStore` class that integrates with LangChain's vector store interface.

## Installation

```bash
pip install langchain-turbopuffer
```

## Usage

```python
from langchain_turbopuffer import TurbopufferVectorStore
from langchain_openai import OpenAIEmbeddings
from turbopuffer import Turbopuffer

tpuf = Turbopuffer(
    # Pick the right region https://turbopuffer.com/docs/regions
    region="gcp-us-central1",
    # This is the default and can be omitted
    api_key=os.environ.get("TURBOPUFFER_API_KEY"),
)

ns = tpuf.namespace("example")

vector_store = TurbopufferVectorStore(
    namespace=ns,
    embedding=OpenAIEmbeddings(),
)
```

## Development

See [libs/langchain-turbopuffer/](libs/langchain-turbopuffer/) for the package source.
