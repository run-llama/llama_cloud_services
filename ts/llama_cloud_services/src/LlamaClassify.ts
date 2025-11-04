import { createClient, createConfig, type Client } from "@hey-api/client-fetch";
import {
  classify,
  type ClassifyParsingConfiguration,
  type ClassifierRule,
  type ClassifyJobResults,
} from "./classify";
import { getUrl } from "./utils";
import { getEnv } from "@llamaindex/env";
import { File } from "buffer";

export class LlamaClassify {
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

  async classify(
    rules: ClassifierRule[],
    configuration: ClassifyParsingConfiguration,
    {
      fileContents,
      filePaths,
      projectId,
      pollingInterval = 1,
      maxPollingIterations = 1800,
      maxRetriesOnError = 10,
      retryInterval = 0.5,
    }: {
      fileContents?:
        | Buffer<ArrayBufferLike>[]
        | File[]
        | Uint8Array<ArrayBuffer>[]
        | string[]
        | undefined;
      filePaths?: string[] | undefined;
      projectId?: string;
      pollingInterval?: number;
      maxPollingIterations?: number;
      maxRetriesOnError?: number;
      retryInterval?: number;
    },
  ): Promise<ClassifyJobResults> {
    const result = await classify(rules, configuration, {
      fileContents,
      filePaths,
      projectId: projectId ?? undefined,
      client: this.client,
      pollingInterval,
      maxPollingIterations,
      maxRetriesOnError,
      retryInterval,
    });
    return result;
  }
}
