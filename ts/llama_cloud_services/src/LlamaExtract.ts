import { createClient, createConfig, type Client } from "@hey-api/client-fetch";
import { File } from "buffer";
import * as extract from "./extract";
import type { ExtractAgent, ExtractConfig } from "./extract";
import { getEnv } from "@llamaindex/env";
import type { ExtractResult } from "./type";
import { getUrl } from "./utils";

export class LlamaExtractAgent {
  private agent: ExtractAgent;
  private client: Client;
  id: string;
  name: string;
  dataSchema: {
    [key: string]:
      | string
      | number
      | boolean
      | {
          [key: string]: unknown;
        }
      | unknown[]
      | null;
  };

  constructor(agent: ExtractAgent, client: Client) {
    this.agent = agent;
    this.client = client;
    this.id = agent.id;
    this.name = agent.name;
    this.dataSchema = agent.data_schema;
  }

  async extract(
    filePath: string | undefined = undefined,
    fileContent:
      | Buffer<ArrayBufferLike>
      | Uint8Array<ArrayBuffer>
      | string
      | File
      | undefined = undefined,
    fileName: string | undefined = undefined,
    project_id: string | null = null,
    organization_id: string | null = null,
    fromUi: boolean | undefined = undefined,
    pollingInterval: number = 1,
    maxPollingIterations: number = 1800,
    maxRetriesOnError: number = 10,
    retryInterval: number = 0.5,
  ): Promise<ExtractResult | undefined> {
    return await extract.extract(
      this.agent.id,
      filePath,
      fileContent,
      fileName,
      project_id,
      organization_id,
      this.client,
      fromUi,
      pollingInterval,
      maxPollingIterations,
      maxRetriesOnError,
      retryInterval,
    );
  }
}

export class LlamaExtract {
  private client: Client;

  constructor(
    apiKey: string | undefined = undefined,
    baseUrl: string | undefined = undefined,
    region: string | undefined = undefined,
  ) {
    const key = apiKey ?? getEnv("LLAMA_CLOUD_API_KEY");
    if (typeof key === "undefined") {
      throw new Error(
        "No API key provided and no API key found in environment. Please pass the API key or set `LLAMA_CLOUD_API_KEY` as an environment variable.",
      );
    }
    const url = getUrl(baseUrl, region);
    this.client = createClient(
      createConfig({
        baseUrl: url,
        headers: {
          Authorization: `Bearer ${key}`,
        },
      }),
    );
  }

  async createAgent(
    name: string,
    dataSchema:
      | {
          [key: string]:
            | { [key: string]: unknown }
            | Array<unknown>
            | string
            | number
            | number
            | boolean
            | null;
        }
      | string,
    config: ExtractConfig | undefined = undefined,
    project_id: string | null = null,
    organization_id: string | null = null,
    maxRetriesOnError: number = 10,
    retryInterval: number = 0.5,
  ): Promise<LlamaExtractAgent | undefined> {
    const agent = await extract.createAgent(
      name,
      dataSchema,
      config,
      project_id,
      organization_id,
      this.client,
      maxRetriesOnError,
      retryInterval,
    );
    if (typeof agent != "undefined") {
      return new LlamaExtractAgent(agent, this.client);
    }
  }

  async getAgent(
    name: string | undefined = undefined,
    id: string | undefined = undefined,
    project_id: string | null = null,
    organization_id: string | null = null,
    maxRetriesOnError: number = 10,
    retryInterval: number = 0.5,
  ): Promise<LlamaExtractAgent | undefined> {
    const agent = await extract.getAgent(
      id,
      name,
      project_id,
      organization_id,
      this.client,
      maxRetriesOnError,
      retryInterval,
    );
    if (typeof agent != "undefined") {
      return new LlamaExtractAgent(agent, this.client);
    }
  }

  async deleteAgent(
    id: string,
    maxRetriesOnError: number = 10,
    retryInterval: number = 500,
  ): Promise<boolean | undefined> {
    return await extract.deleteAgent(
      id,
      this.client,
      maxRetriesOnError,
      retryInterval,
    );
  }

  async extract(
    dataSchema:
      | {
          [key: string]:
            | { [key: string]: unknown }
            | Array<unknown>
            | string
            | number
            | number
            | boolean
            | null;
        }
      | string,
    config: ExtractConfig | undefined = undefined,
    filePath: string | undefined = undefined,
    fileContent:
      | Buffer<ArrayBufferLike>
      | Uint8Array<ArrayBuffer>
      | string
      | File
      | undefined = undefined,
    fileName: string | undefined = undefined,
    project_id: string | null = null,
    organization_id: string | null = null,
    pollingInterval: number = 1,
    maxPollingIterations: number = 1800,
    maxRetriesOnError: number = 10,
    retryInterval: number = 0.5,
  ): Promise<ExtractResult | undefined> {
    return await extract.extractStateless(
      dataSchema,
      config,
      filePath,
      fileContent,
      fileName,
      project_id,
      organization_id,
      this.client,
      pollingInterval,
      maxPollingIterations,
      maxRetriesOnError,
      retryInterval,
    );
  }
}
