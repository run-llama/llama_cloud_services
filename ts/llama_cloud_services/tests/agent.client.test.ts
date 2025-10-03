import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { AgentClient } from "../src/beta/agent/index.js";

describe("AgentClient search-to-delete", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("searches items and deletes one by id", async () => {
    const itemId = "test-item-id-123";

    const searchResponseBody = {
      items: [
        {
          id: itemId,
          deployment_name: "_public",
          collection: "default",
          data: { foo: "bar" },
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      total_size: 1,
      next_page_token: null,
    };

    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async (input, init) => {
        const url = typeof input === "string" ? input : (input as Request).url;
        const method = (init?.method || (typeof input === "object" && "method" in (input as any) ? (input as any).method : "GET")) as string;

        if (url.includes("/api/v1/beta/agent-data/:search") && method === "POST") {
          return new Response(JSON.stringify(searchResponseBody), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }

        if (url.includes(`/api/v1/beta/agent-data/${itemId}`) && method === "DELETE") {
          return new Response(undefined, { status: 200 });
        }

        return new Response(JSON.stringify({ message: "unexpected" }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
        });
      });

    const client = new AgentClient({ deploymentName: "_public", collection: "default" });

    const searchResult = await client.search({});
    expect(searchResult.items.length).toBe(1);
    const first = searchResult.items[0];
    expect(first.id).toBe(itemId);

    await client.deleteItem(first.id);

    expect(fetchSpy).toHaveBeenCalled();
    const calls = fetchSpy.mock.calls.map((c) => (typeof c[0] === "string" ? c[0] : (c[0] as Request).url));
    expect(calls.some((u) => u.includes("/api/v1/beta/agent-data/:search"))).toBe(true);
    expect(calls.some((u) => u.includes(`/api/v1/beta/agent-data/${itemId}`))).toBe(true);
  });
});
