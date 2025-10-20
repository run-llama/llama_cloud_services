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
    parsingConfiguration: ClassifyParsingConfiguration,
    fileContents:
      | Buffer<ArrayBufferLike>[]
      | File[]
      | Uint8Array<ArrayBuffer>[]
      | string[]
      | undefined = undefined,
    filePaths: string[] | undefined = undefined,
    projectId: string | null = null,
    organizationId: string | null = null,
    pollingInterval: number = 1,
    maxPollingIterations: number = 1800,
    maxRetriesOnError: number = 10,
    retryInterval: number = 0.5,
  ): Promise<ClassifyJobResults> {
    const result = await classify(
      rules,
      parsingConfiguration,
      fileContents,
      filePaths,
      projectId,
      organizationId,
      this.client,
      pollingInterval,
      maxPollingIterations,
      maxRetriesOnError,
      retryInterval,
    );
    return result;
  }
}
