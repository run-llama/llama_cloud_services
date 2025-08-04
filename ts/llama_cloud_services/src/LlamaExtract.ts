import { createClient, createConfig, type Client } from "@hey-api/client-fetch";
import * as extract from "./extract";
import { getEnv } from "@llamaindex/env";

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
}
