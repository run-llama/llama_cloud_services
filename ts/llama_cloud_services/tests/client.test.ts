import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { listProjectsApiV1ProjectsGet, client } from "../src/api.js";

describe("Global client configuration", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("adds X-SDK-Name header from global client config", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async (input, init) => {
        // Validate the header is present on the outgoing request
        let headers: Headers;
        if (input && typeof input === "object" && "headers" in (input as any)) {
          headers = (input as Request).headers;
        } else {
          headers = new Headers((init && init.headers) || {});
        }
        expect(headers.get("X-SDK-Name")).toBe("llamaindex-ts");

        return new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      });

    // Trigger any request via the generated SDK (imported through src/api.ts)
    await listProjectsApiV1ProjectsGet({ throwOnError: false });

    expect(fetchSpy).toHaveBeenCalledOnce();
  });

  it("respects additional custom headers set via setConfig", async () => {
    const prevConfig = client.getConfig();
    try {
      client.setConfig({
        ...prevConfig,
        headers: {
          ...(prevConfig.headers || {}),
          "X-Custom-Header": "custom-value",
        },
      });

      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockImplementation(async (input, init) => {
          let headers: Headers;
          if (
            input &&
            typeof input === "object" &&
            "headers" in (input as any)
          ) {
            headers = (input as Request).headers;
          } else {
            headers = new Headers((init && init.headers) || {});
          }
          expect(headers.get("X-SDK-Name")).toBe("llamaindex-ts");
          expect(headers.get("X-Custom-Header")).toBe("custom-value");

          return new Response(JSON.stringify([]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        });

      await listProjectsApiV1ProjectsGet({ throwOnError: false });
      expect(fetchSpy).toHaveBeenCalledOnce();
    } finally {
      // Restore original configuration to avoid test cross-talk
      client.setConfig(prevConfig);
    }
  });
});
