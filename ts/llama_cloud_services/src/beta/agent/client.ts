import { createClient, createConfig } from "@hey-api/client-fetch";
import { getEnv } from "@llamaindex/env";
import {
  aggregateAgentDataApiV1BetaAgentDataAggregatePost,
  createAgentDataApiV1BetaAgentDataPost,
  deleteAgentDataApiV1BetaAgentDataItemIdDelete,
  getAgentDataApiV1BetaAgentDataItemIdGet,
  searchAgentDataApiV1BetaAgentDataSearchPost,
  updateAgentDataApiV1BetaAgentDataItemIdPut,
  type AgentData,
  type AggregateGroup,
} from "../../client";
import type {
  AggregateAgentDataOptions,
  SearchAgentDataOptions,
  TypedAgentData,
  TypedAgentDataItems,
  TypedAggregateGroup,
  TypedAggregateGroupItems,
} from "./types";

/**
 * Async client for agent data operations
 */
export class AgentClient<T = unknown> {
  private client: ReturnType<typeof createClient>;
  private baseUrl: string;
  private headers: Record<string, string>;
  private collection: string;
  private agentUrlId: string;

  constructor({
    apiKey = getEnv("LLAMA_CLOUD_API_KEY"),
    baseUrl = "https://api.cloud.llamaindex.ai/",
    collection = "default",
    agentUrlId = "_public",
  }: {
    apiKey?: string;
    baseUrl?: string;
    collection?: string;
    agentUrlId?: string;
  }) {
    this.baseUrl = baseUrl;

    this.headers = {
      "X-SDK-Name": "llamaindex-ts",
      ...(apiKey && { Authorization: `Bearer ${apiKey}` }),
    };

    this.client = createClient(
      createConfig({
        baseUrl: this.baseUrl,
        headers: this.headers,
      }),
    );

    this.collection = collection;
    this.agentUrlId = agentUrlId;
  }

  /**
   * Create new agent data
   */
  async createItem(data: T): Promise<TypedAgentData<T>> {
    const response = await createAgentDataApiV1BetaAgentDataPost({
      throwOnError: true,
      body: {
        agent_slug: this.agentUrlId,
        collection: this.collection,
        data: data as Record<string, unknown>,
      },
      client: this.client,
    });

    return this.transformResponse(response.data);
  }

  /**
   * Get agent data by ID
   */
  async getItem(id: string): Promise<TypedAgentData<T> | null> {
    try {
      const response = await getAgentDataApiV1BetaAgentDataItemIdGet({
        throwOnError: true,
        path: { item_id: id },
        client: this.client,
      });

      return this.transformResponse(response.data);
    } catch (error) {
      if (
        error instanceof Error &&
        "response" in error &&
        (error as { response?: { status?: number } }).response?.status === 404
      ) {
        return null;
      }
      throw error;
    }
  }

  /**
   * Update agent data
   */
  async updateItem(id: string, data: T): Promise<TypedAgentData<T>> {
    const response = await updateAgentDataApiV1BetaAgentDataItemIdPut({
      throwOnError: true,
      path: { item_id: id },
      body: {
        data: data as Record<string, unknown>,
      },
      client: this.client,
    });

    return this.transformResponse(response.data);
  }

  /**
   * Delete agent data
   */
  async deleteItem(id: string): Promise<void> {
    await deleteAgentDataApiV1BetaAgentDataItemIdDelete({
      throwOnError: true,
      path: { item_id: id },
      client: this.client,
    });
  }

  /**
   * Search agent data
   */
  async search(
    options: SearchAgentDataOptions,
  ): Promise<TypedAgentDataItems<T>> {
    const response = await searchAgentDataApiV1BetaAgentDataSearchPost({
      throwOnError: true,
      body: {
        agent_slug: this.agentUrlId,
        ...(this.collection !== undefined && {
          collection: this.collection,
        }),
        ...(options.filter !== undefined && { filter: options.filter }),
        ...(options.orderBy !== undefined && { order_by: options.orderBy }),
        ...(options.pageSize !== undefined && { page_size: options.pageSize }),
        ...(options.offset !== undefined && { offset: options.offset }),
        ...(options.includeTotal !== undefined && {
          include_total: options.includeTotal,
        }),
      },
      client: this.client,
    });

    const result: TypedAgentDataItems<T> = {
      items: response.data.items.map((item: AgentData) =>
        this.transformResponse(item),
      ),
    };

    if (
      response.data.total_size !== null &&
      response.data.total_size !== undefined
    ) {
      result.totalSize = response.data.total_size;
    }

    if (
      response.data.next_page_token !== null &&
      response.data.next_page_token !== undefined
    ) {
      result.nextPageToken = response.data.next_page_token;
    }

    return result;
  }

  /**
   * Aggregate agent data into groups
   */
  async aggregate(
    options: AggregateAgentDataOptions,
  ): Promise<TypedAggregateGroupItems<T>> {
    const response = await aggregateAgentDataApiV1BetaAgentDataAggregatePost({
      throwOnError: true,
      body: {
        agent_slug: this.agentUrlId,
        ...(this.collection !== undefined && {
          collection: this.collection,
        }),
        ...(options.filter !== undefined && { filter: options.filter }),
        ...(options.groupBy !== undefined && { group_by: options.groupBy }),
        ...(options.count !== undefined && { count: options.count }),
        ...(options.first !== undefined && { first: options.first }),
        ...(options.orderBy !== undefined && { order_by: options.orderBy }),
        ...(options.offset !== undefined && { offset: options.offset }),
        ...(options.pageSize !== undefined && { page_size: options.pageSize }),
      },
      client: this.client,
    });

    const result: TypedAggregateGroupItems<T> = {
      items: response.data.items.map((item) =>
        this.transformAggregateResponse(item),
      ),
    };

    if (
      response.data.total_size !== null &&
      response.data.total_size !== undefined
    ) {
      result.totalSize = response.data.total_size;
    }

    if (
      response.data.next_page_token !== null &&
      response.data.next_page_token !== undefined
    ) {
      result.nextPageToken = response.data.next_page_token;
    }

    return result;
  }

  /**
   * Transform API response to typed data
   */
  private transformResponse(data: AgentData): TypedAgentData<T> {
    const result: TypedAgentData<T> = {
      id: data.id!,
      agentUrlId: data.agent_slug,
      data: data.data as T,
      createdAt: new Date(data.created_at!),
      updatedAt: new Date(data.updated_at!),
    };

    if (data.collection !== undefined) {
      result.collection = data.collection;
    }

    return result;
  }

  /**
   * Transform API aggregate response to typed data
   */
  private transformAggregateResponse(
    data: AggregateGroup,
  ): TypedAggregateGroup<T> {
    const result: TypedAggregateGroup<T> = {
      groupKey: data.group_key,
    };

    if (data.count !== null && data.count !== undefined) {
      result.count = data.count;
    }

    if (data.first_item !== null && data.first_item !== undefined) {
      result.firstItem = data.first_item as T;
    }

    return result;
  }
}

export interface AgentDataClientOptions<T = unknown> {
  /** API key for the client */
  apiKey?: string;
  /** Base URL for the client */
  /** Base URL of the llama cloud api */
  baseUrl?: string;
  /** If running in an agent runtime, optionally provide the window url to infer the agent url id */
  windowUrl?: string;
  /** Agent URL ID for the client, if not provided, it will be inferred from the window url, or fall back to "default" */
  agentUrlId?: string;
  /** Collection name for the client, defaults to "default" */
  collection?: string;
}
/**
 * Create a new AsyncAgentDataClient instance. Does it's best to infer an agent url id from environment.
 * Pass in the window url and/or env to infer the agent url id from them.
 * @param options - The options for the client
 * @returns A new AgentClient instance
 */
export function createAgentDataClient<T = unknown>({
  apiKey,
  baseUrl,
  windowUrl,
  env,
  agentUrlId,
  collection = "default",
}: {
  apiKey?: string;
  baseUrl?: string;
  windowUrl?: string;
  env?: Record<string, string>;
  agentUrlId?: string;
  collection?: string;
} = {}): AgentClient<T> {
  if (env && !agentUrlId) {
    agentUrlId =
      env.LLAMA_DEPLOY_DEPLOYMENT_NAME ||
      env.NEXT_PUBLIC_LLAMA_DEPLOY_DEPLOYMENT_NAME ||
      env.VITE_LLAMA_DEPLOY_DEPLOYMENT_NAME;
  }
  if (windowUrl && !agentUrlId) {
    try {
      const url = new URL(windowUrl);
      const path = url.pathname;
      const isLocalhost = // local agents should default to _public, otherwise a full deployment is required
        url.hostname.includes("localhost") ||
        url.hostname.includes("127.0.0.1");
      if (path.startsWith("/deployments/") && !isLocalhost) {
        // /deployments/<agent-url-id>/ui/ -> ["", "deployments", "<agent-url-id>", "ui"]
        agentUrlId = path.split("/")[2];
      }
    } catch (error) {
      console.warn(
        "Failed to infer agent url id from window url, falling back to default",
        error,
      );
    }
  }

  return new AgentClient({
    ...(apiKey && { apiKey }),
    ...(baseUrl && { baseUrl }),
    ...(agentUrlId && { agentUrlId }),
    collection,
  });
}
