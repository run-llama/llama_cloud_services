import * as z from "zod/v4";
import { API_BASE } from "../const.js";
import type { CreateAgentRequest, ExtractionResult } from "./interfaces.js";
import { extractDataFromFile } from "./utils.js";

class LlamaExtract {
  apiKey: string;

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  getAgent(agentId: string): LlamaExtractAgent {
    return new LlamaExtractAgent(this.apiKey, agentId);
  }

  async createAgent(
    agentName: string,
    dataSchema: z.ZodType,
    returnId: boolean = true,
  ): Promise<string | LlamaExtractAgent | null> {
    const jsonSchema = z.toJSONSchema(dataSchema) as CreateAgentRequest;
    jsonSchema.name = agentName;
    const response = await fetch(`${API_BASE}/extraction/extraction-agents`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.apiKey}`,
        accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(jsonSchema),
    });

    if (!response.ok) {
      console.log(
        `Failed to create agent: ${response.status} ${response.statusText}`,
      );
      return null;
    }

    const jsonResponse = await response.json();

    if (returnId) {
      return jsonResponse["id"] as string;
    } else {
      return new LlamaExtractAgent(this.apiKey, jsonResponse["id"] as string);
    }
  }
}

class LlamaExtractAgent {
  apiKey: string;
  agentId: string;

  constructor(apiKey: string, agentId: string) {
    this.apiKey = apiKey;
    this.agentId = agentId;
  }

  async extract(
    filePath: string,
    fileName?: string,
    pollInterval: number = 2000,
    maxRetries: number = 150,
  ): Promise<ExtractionResult | null> {
    try {
      return extractDataFromFile(
        this.apiKey,
        this.agentId,
        filePath,
        fileName,
        pollInterval,
        maxRetries,
      );
    } catch (error) {
      console.log(
        "An error has occurred while extracting data from your file",
        error,
      );
      return null;
    }
  }
}

export { LlamaExtract, LlamaExtractAgent };
