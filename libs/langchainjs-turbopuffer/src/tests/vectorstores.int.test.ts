import { describe, test, expect, beforeEach, afterEach } from "vitest";
import { Turbopuffer } from "@turbopuffer/turbopuffer";
import { Document } from "@langchain/core/documents";
import { SyntheticEmbeddings } from "@langchain/core/utils/testing";
import { v4 as uuid } from "uuid";
import { TurbopufferVectorStore } from "../vectorstores.js";

const embeddings = new SyntheticEmbeddings({ vectorSize: 6 });

function createClient(): Turbopuffer {
  return new Turbopuffer({
    apiKey: process.env.TURBOPUFFER_API_KEY!,
    region: process.env.TURBOPUFFER_REGION ?? "gcp-us-central1",
  });
}

function createStore(): TurbopufferVectorStore {
  const client = createClient();
  return new TurbopufferVectorStore(embeddings, {
    namespace: client.namespace(`test-integration-${uuid()}`),
  });
}

describe("TurbopufferVectorStore", () => {
  let store: TurbopufferVectorStore;

  beforeEach(() => {
    store = createStore();
  });

  afterEach(async () => {
    try {
      await store.delete({ deleteAll: true });
    } catch {
      // Namespace may not exist if the test never wrote to it
    }
  });

  test("add and search", async () => {
    await store.addDocuments([
      { pageContent: "apple", metadata: { fruit: "apple" } },
      { pageContent: "banana", metadata: { fruit: "banana" } },
      { pageContent: "cherry", metadata: { fruit: "cherry" } },
    ]);

    const results = await store.similaritySearch("apple", 1);
    expect(results).toHaveLength(1);
    expect(results[0].pageContent).toBe("apple");
  });

  test("add and delete", async () => {
    const ids = await store.addDocuments([
      { pageContent: "hello", metadata: {} },
      { pageContent: "world", metadata: {} },
    ]);
    expect(ids).toHaveLength(2);

    await store.delete({ ids: [ids[0]] });
    const results = await store.similaritySearch("hello", 10);
    expect(results.every((r) => r.id !== ids[0])).toBe(true);
  });

  test("search with score", async () => {
    await store.addDocuments([
      { pageContent: "cat", metadata: {} },
      { pageContent: "dog", metadata: {} },
      { pageContent: "fish", metadata: {} },
    ]);

    const results = await store.similaritySearchWithScore("cat", 3);
    expect(results).toHaveLength(3);
    for (const r of results) {
      expect(r).toHaveLength(2);
      expect(typeof r[1]).toBe("number");
    }
  });

  test("metadata round trip", async () => {
    await store.addDocuments([
      { pageContent: "hello", metadata: { key_str: "value", key_int: 42 } },
    ]);

    const results = await store.similaritySearch("hello", 1);
    expect(results).toHaveLength(1);
    expect(results[0].metadata.key_str).toBe("value");
    expect(results[0].metadata.key_int).toBe(42);
  });

  test("upsert overwrite", async () => {
    await store.addDocuments(
      [{ pageContent: "original content", metadata: {} }],
      { ids: ["doc1"] }
    );
    await store.addDocuments(
      [{ pageContent: "updated content", metadata: {} }],
      { ids: ["doc1"] }
    );

    const results = await store.similaritySearch("updated content", 1);
    expect(results).toHaveLength(1);
    expect(results[0].pageContent).toBe("updated content");
  });

  test("filter query", async () => {
    await store.addDocuments([
      { pageContent: "red apple", metadata: { color: "red" } },
      { pageContent: "green apple", metadata: { color: "green" } },
      { pageContent: "blue berry", metadata: { color: "blue" } },
    ]);

    const results = await store.similaritySearch("apple", 10, [
      "color",
      "Eq",
      "red",
    ]);
    expect(results).toHaveLength(1);
    expect(results[0].metadata.color).toBe("red");
  });

  test("score ordering", async () => {
    await store.addDocuments([
      { pageContent: "aaa", metadata: {} },
      { pageContent: "bbb", metadata: {} },
      { pageContent: "ccc", metadata: {} },
      { pageContent: "ddd", metadata: {} },
    ]);

    const results = await store.similaritySearchWithScore("aaa", 4);
    expect(results).toHaveLength(4);
    const distances = results.map(([, score]) => score);
    const sorted = [...distances].sort((a, b) => a - b);
    expect(distances).toEqual(sorted);
  });

  test("delete nonexistent ids", async () => {
    await store.addDocuments(
      [{ pageContent: "placeholder", metadata: {} }],
      { ids: ["keep"] }
    );

    // Should not throw
    await store.delete({ ids: ["nonexistent_1", "nonexistent_2"] });

    const results = await store.similaritySearch("placeholder", 1);
    expect(results).toHaveLength(1);
  });

  test("delete all", async () => {
    await store.addDocuments([
      { pageContent: "one", metadata: {} },
      { pageContent: "two", metadata: {} },
    ]);
    await store.delete({ deleteAll: true });

    const results = await store.similaritySearch("one", 10);
    expect(results).toHaveLength(0);
  });

  test("large batch", async () => {
    const n = 100;
    const docs = Array.from({ length: n }, (_, i) => ({
      pageContent: `document number ${i}`,
      metadata: {},
    }));

    const ids = await store.addDocuments(docs);
    expect(ids).toHaveLength(n);

    const results = await store.similaritySearch("document number 0", 5);
    expect(results).toHaveLength(5);
  });

  test("fromTexts", async () => {
    const client = createClient();
    const newStore = await TurbopufferVectorStore.fromTexts(
      ["a", "b", "c"],
      [{}, {}, {}],
      embeddings,
      { namespace: client.namespace(`test-from-texts-${uuid()}`) }
    );

    try {
      const results = await newStore.similaritySearch("a", 1);
      expect(results).toHaveLength(1);
    } finally {
      await newStore.delete({ deleteAll: true });
    }
  });

  test("fromDocuments", async () => {
    const client = createClient();
    const newStore = await TurbopufferVectorStore.fromDocuments(
      [new Document({ pageContent: "doc one", metadata: { type: "test" } })],
      embeddings,
      { namespace: client.namespace(`test-from-docs-${uuid()}`) }
    );

    try {
      const results = await newStore.similaritySearch("doc", 1);
      expect(results[0].pageContent).toBe("doc one");
    } finally {
      await newStore.delete({ deleteAll: true });
    }
  });
});
