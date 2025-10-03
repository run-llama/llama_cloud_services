import { describe, it, expect, beforeEach, vi } from "vitest";
import { AgentClient, createAgentDataClient } from "../src/beta/agent/index.js";
import * as sdk from "../src/client/index.js";

describe("AgentClient", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("createItem sends correct payload and returns typed data", async () => {
    const spy = vi
      .spyOn(sdk, "createAgentDataApiV1BetaAgentDataPost")
      .mockResolvedValue({
        data: {
          id: "1",
          deployment_name: "dep",
          collection: "col",
          data: { foo: "bar" },
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
        },
      } as any);

    const client = new AgentClient<{ foo: string }>({
      deploymentName: "dep",
      collection: "col",
    });
    const result = await client.createItem({ foo: "bar" });

    expect(spy).toHaveBeenCalledOnce();
    const call = spy.mock.calls[0][0];
    expect(call.body.deployment_name).toBe("dep");
    expect(call.body.collection).toBe("col");
    expect(call.body.data).toEqual({ foo: "bar" });

    expect(result.id).toBe("1");
    expect(result.deploymentName).toBe("dep");
    expect(result.collection).toBe("col");
    expect(result.data).toEqual({ foo: "bar" });
    expect(result.createdAt).toEqual(new Date("2024-01-01T00:00:00Z"));
    expect(result.updatedAt).toEqual(new Date("2024-01-01T00:00:00Z"));
  });

  it("getItem returns null for 404 errors", async () => {
    const spy = vi
      .spyOn(sdk, "getAgentDataApiV1BetaAgentDataItemIdGet")
      .mockImplementation(async () => {
        const err: any = new Error("Not found");
        err.response = { status: 404 };
        throw err;
      });

    const client = new AgentClient({ deploymentName: "dep" });
    const res = await client.getItem("missing-id");

    expect(spy).toHaveBeenCalledOnce();
    expect(res).toBeNull();
  });

  it("updateItem updates and returns typed data", async () => {
    const spy = vi
      .spyOn(sdk, "updateAgentDataApiV1BetaAgentDataItemIdPut")
      .mockResolvedValue({
        data: {
          id: "123",
          deployment_name: "dep",
          collection: "col",
          data: { foo: "baz" },
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-02T00:00:00Z",
        },
      } as any);

    const client = new AgentClient<{ foo: string }>({
      deploymentName: "dep",
      collection: "col",
    });
    const res = await client.updateItem("123", { foo: "baz" });

    expect(spy).toHaveBeenCalledOnce();
    const call = spy.mock.calls[0][0];
    expect(call.path.item_id).toBe("123");
    expect(call.body.data).toEqual({ foo: "baz" });

    expect(res.id).toBe("123");
    expect(res.updatedAt).toEqual(new Date("2024-01-02T00:00:00Z"));
  });

  it("deleteItem calls delete endpoint with correct path", async () => {
    const spy = vi
      .spyOn(sdk, "deleteAgentDataApiV1BetaAgentDataItemIdDelete")
      .mockResolvedValue({} as any);

    const client = new AgentClient({ deploymentName: "dep" });
    await client.deleteItem("abc");

    expect(spy).toHaveBeenCalledOnce();
    expect(spy.mock.calls[0][0].path.item_id).toBe("abc");
  });

  it("delete by query returns deleted count", async () => {
    const spy = vi
      .spyOn(sdk, "deleteAgentDataByQueryApiV1BetaAgentDataDeletePost")
      .mockResolvedValue({ data: { deleted_count: 7 } } as any);

    const client = new AgentClient({
      deploymentName: "dep",
      collection: "col",
    });
    const count = await client.delete({
      filter: { status: { op: "eq", value: "accepted" } as any },
    });

    expect(spy).toHaveBeenCalledOnce();
    const body = spy.mock.calls[0][0].body;
    expect(body.deployment_name).toBe("dep");
    expect(body.collection).toBe("col");
    expect(count).toBe(7);
  });

  it("search maps items and optional fields correctly", async () => {
    const now = "2024-01-01T00:00:00Z";
    const spy = vi
      .spyOn(sdk, "searchAgentDataApiV1BetaAgentDataSearchPost")
      .mockResolvedValue({
        data: {
          items: [
            {
              id: "1",
              deployment_name: "dep",
              collection: "col",
              data: { foo: "bar" },
              created_at: now,
              updated_at: now,
            },
          ],
          total_size: 1,
          next_page_token: "next",
        },
      } as any);

    const client = new AgentClient<{ foo: string }>({
      deploymentName: "dep",
      collection: "col",
    });
    const result = await client.search({
      includeTotal: true,
      orderBy: "created_at desc",
      pageSize: 1,
      offset: 0,
    });

    expect(spy).toHaveBeenCalledOnce();
    const body = spy.mock.calls[0][0].body;
    expect(body.deployment_name).toBe("dep");
    expect(body.collection).toBe("col");
    expect(body.include_total).toBe(true);
    expect(body.order_by).toBe("created_at desc");
    expect(body.page_size).toBe(1);
    expect(body.offset).toBe(0);

    expect(result.items).toHaveLength(1);
    expect(result.totalSize).toBe(1);
    expect(result.nextPageToken).toBe("next");
    expect(result.items[0].createdAt).toEqual(new Date(now));
  });

  it("aggregate maps groups and optional fields correctly", async () => {
    const spy = vi
      .spyOn(sdk, "aggregateAgentDataApiV1BetaAgentDataAggregatePost")
      .mockResolvedValue({
        data: {
          items: [
            {
              group_key: { status: "accepted" },
              count: 3,
              first_item: { foo: "bar" },
            },
          ],
          total_size: 1,
          next_page_token: "tok",
        },
      } as any);

    const client = new AgentClient<{ foo: string }>({
      deploymentName: "dep",
      collection: "col",
    });
    const result = await client.aggregate({
      groupBy: ["status"],
      count: true,
      first: true,
      pageSize: 1,
      offset: 0,
    });

    expect(spy).toHaveBeenCalledOnce();
    const body = spy.mock.calls[0][0].body;
    expect(body.deployment_name).toBe("dep");
    expect(body.collection).toBe("col");
    expect(body.group_by).toEqual(["status"]);
    expect(body.count).toBe(true);
    expect(body.first).toBe(true);
    expect(body.page_size).toBe(1);
    expect(body.offset).toBe(0);

    expect(result.items).toHaveLength(1);
    expect(result.totalSize).toBe(1);
    expect(result.nextPageToken).toBe("tok");
    expect(result.items[0].groupKey).toEqual({ status: "accepted" });
    expect(result.items[0].count).toBe(3);
    expect(result.items[0].firstItem).toEqual({ foo: "bar" });
  });

  it("createAgentDataClient infers deployment name from env", async () => {
    const spy = vi
      .spyOn(sdk, "searchAgentDataApiV1BetaAgentDataSearchPost")
      .mockResolvedValue({
        data: { items: [], total_size: 0 },
      } as any);

    const client = createAgentDataClient({
      env: { LLAMA_DEPLOY_DEPLOYMENT_NAME: "env-dep" },
    });
    await client.search({});

    const body = spy.mock.calls[0][0].body;
    expect(body.deployment_name).toBe("env-dep");
  });

  it("createAgentDataClient infers deployment name from windowUrl (non-local)", async () => {
    const spy = vi
      .spyOn(sdk, "deleteAgentDataByQueryApiV1BetaAgentDataDeletePost")
      .mockResolvedValue({
        data: { deleted_count: 0 },
      } as any);

    const client = createAgentDataClient({
      windowUrl: "https://app.llamaindex.ai/deployments/abc/ui/",
    });
    await client.delete({});

    const body = spy.mock.calls[0][0].body;
    expect(body.deployment_name).toBe("abc");
  });
});
