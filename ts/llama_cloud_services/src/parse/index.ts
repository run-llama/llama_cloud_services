import * as u from "./utils.js";
import { ParsingResult } from "./interfaces.js";

class LlamaParse {
  apiKey: string;

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  async parse(
    apiKey: string,
    filePath: string,
    fileName?: string,
    pollInterval: number = 2000,
    maxRetries: number = 5,
  ): Promise<ParsingResult> {
    const jobId = await u.uploadFile(apiKey, filePath, fileName);
    await u.pollForJobCompletion(this.apiKey, jobId, pollInterval, maxRetries);
    const result = await u.getAllResults(jobId, this.apiKey);
    return result;
  }
}

export { LlamaParse };
