import { createClient, createConfig, type Client } from "@hey-api/client-fetch";
import * as extract from "./extract";
import type { ExtractAgent, ExtractConfig } from "./extract";
import { getEnv } from "@llamaindex/env";
import type { ExtractResult } from "./type";

const URLS = {
  us: "https://api.cloud.llamaindex.ai",
  eu: "https://api.cloud.eu.llamaindex.ai",
  "us-staging": "https://api.staging.llamaindex.ai",
} as const;

function getUrl(baseUrl: string | undefined, region: string | undefined) {
  if (typeof baseUrl != "undefined") {
    return baseUrl;
  }
  if (typeof region === "undefined") {
    return URLS["us"];
  } else if (region === "us" || region === "eu" || region === "us-staging") {
    return URLS[region];
  } else {
    throw new Error(`Unsupported region: ${region}`);
  }
}

export class LlamaExtractAgent {
  private agent: ExtractAgent;
  private client: Client;

  constructor(agent: ExtractAgent, client: Client) {
    this.agent = agent;
    this.client = client;
  }

  async Extract(
    filePath: string,
    project_id: string | undefined = undefined,
    organization_id: string | undefined = undefined,
    fromUi: boolean | undefined = undefined,
    pollingInterval: number = 1000,
    maxPollingIterations: number = 600,
  ): Promise<ExtractResult | undefined> {
    return await extract.extract(
      this.agent.id,
      filePath,
      project_id,
      organization_id,
      this.client,
      fromUi,
      pollingInterval,
      maxPollingIterations,
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

  async CreateAgent(
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
    project_id: string | undefined = undefined,
    organization_id: string | undefined = undefined,
  ): Promise<LlamaExtractAgent | undefined> {
    const agent = await extract.createAgent(
      name,
      dataSchema,
      config,
      project_id,
      organization_id,
      this.client,
    );
    if (typeof agent != "undefined") {
      return new LlamaExtractAgent(agent, this.client);
    }
  }

  async GetAgent(
    name: string | undefined = undefined,
    id: string | undefined = undefined,
    project_id: string | undefined = undefined,
    organization_id: string | undefined = undefined,
  ): Promise<LlamaExtractAgent | undefined> {
    const agent = await extract.getAgent(
      id,
      name,
      project_id,
      organization_id,
      this.client,
    );
    if (typeof agent != "undefined") {
      return new LlamaExtractAgent(agent, this.client);
    }
  }
}
