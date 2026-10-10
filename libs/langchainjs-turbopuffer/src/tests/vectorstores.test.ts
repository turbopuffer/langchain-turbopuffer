import { describe, test, expect, vi } from "vitest";
import {
  Turbopuffer,
  APIError,
  BadRequestError,
  InternalServerError,
  NotFoundError,
  RateLimitError,
} from "@turbopuffer/turbopuffer";
import { SyntheticEmbeddings } from "@langchain/core/utils/testing";
import { TurbopufferVectorStore } from "../vectorstores.js";

// Unit tests: the namespace calls are stubbed, so nothing is sent over the network.
// The errors are the SDK's own classes, built the way the client builds them from a
// response, so their messages are "<status> <JSON body>".
function createStore(ns: string) {
  const client = new Turbopuffer({
    apiKey: "test-key",
    region: "gcp-us-central1",
    maxRetries: 0,
    fetch: () => {
      throw new Error("unit tests must not reach the network");
    },
  });
  const namespace = client.namespace(ns);
  const store = new TurbopufferVectorStore(
    new SyntheticEmbeddings({ vectorSize: 4 }),
    { namespace }
  );
  return { store, namespace };
}

function body(error: string) {
  return { status: "error", error };
}

const notFound = () =>
  new NotFoundError(
    404,
    body("namespace 'fresh' was not found"),
    undefined,
    new Headers()
  );

// Errors that are not 404s, but whose message contains "404".
const notFoundLookalikes: [string, () => APIError][] = [
  [
    "BadRequestError (400)",
    () =>
      new BadRequestError(
        400,
        body(
          'invalid input 404 for filter field "status_code", expecting string'
        ),
        undefined,
        new Headers()
      ),
  ],
  [
    "RateLimitError (429)",
    () =>
      new RateLimitError(
        429,
        body("query rate limit exceeded for namespace user-4047"),
        undefined,
        new Headers()
      ),
  ],
  [
    "InternalServerError (500)",
    () =>
      new InternalServerError(
        500,
        body("internal error while querying namespace project-14042"),
        undefined,
        new Headers()
      ),
  ],
];

describe("similaritySearchVectorWithScore", () => {
  test("a missing namespace (404) returns no results", async () => {
    const { store, namespace } = createStore("fresh");
    const query = vi
      .spyOn(namespace, "query")
      .mockRejectedValueOnce(notFound());

    await expect(store.similaritySearch("q", 3)).resolves.toEqual([]);
    expect(query).toHaveBeenCalledTimes(1);
  });

  test.each(notFoundLookalikes)("%s is raised", async (_name, makeError) => {
    const error = makeError();
    expect(error.message).toContain("404");
    const { store, namespace } = createStore("project-14042");
    const query = vi.spyOn(namespace, "query").mockRejectedValueOnce(error);

    await expect(store.similaritySearch("q", 3)).rejects.toBe(error);
    expect(query).toHaveBeenCalledTimes(1);
  });
});

describe("delete({ deleteAll: true })", () => {
  test("a missing namespace (404) is treated as already deleted", async () => {
    const { store, namespace } = createStore("fresh");
    const deleteAll = vi
      .spyOn(namespace, "deleteAll")
      .mockRejectedValueOnce(notFound());

    await expect(store.delete({ deleteAll: true })).resolves.toBeUndefined();
    expect(deleteAll).toHaveBeenCalledTimes(1);
  });

  test.each(notFoundLookalikes)("%s is raised", async (_name, makeError) => {
    const error = makeError();
    expect(error.message).toContain("404");
    const { store, namespace } = createStore("project-14042");
    const deleteAll = vi
      .spyOn(namespace, "deleteAll")
      .mockRejectedValueOnce(error);

    await expect(store.delete({ deleteAll: true })).rejects.toBe(error);
    expect(deleteAll).toHaveBeenCalledTimes(1);
  });
});
