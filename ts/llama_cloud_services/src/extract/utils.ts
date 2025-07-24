import fs from "fs";
import path from "path";
import { API_BASE } from "../const.js";
import type {
  ExtractionJobResponse,
  ExtractionResult,
  JobStatusResponse,
  UploadResponse,
} from "./interfaces.js";
import { getContentType } from "../generic_utils.js";

/**
 * Extracts data from a file using LlamaIndex Cloud
 * @param apiKey - Your LlamaIndex Cloud API key
 * @param agentId - The ID of your extraction agent
 * @param filePath - Path to the file to extract data from
 * @param fileName - Name of the file (optional, will be inferred from path if not provided)
 * @param pollInterval - How often to poll for job completion in milliseconds (default: 2000)
 * @param maxRetries - Maximum number of polling attempts (default: 150, ~5 minutes)
 * @param returnAsJson - Whether to return the result as a JSON string (default: false)
 * @returns Promise that resolves to the extracted data (object or JSON string)
 */
async function extractDataFromFile(
  apiKey: string,
  agentId: string,
  filePath: string,
  fileName?: string,
  pollInterval: number = 2000,
  maxRetries: number = 150,
): Promise<ExtractionResult> {
  // Step 1: Upload the file
  console.log("Uploading file...");
  const fileId = await uploadFile(apiKey, filePath, fileName);
  console.log(`File uploaded with ID: ${fileId}`);

  // Step 2: Run extraction job
  console.log("Starting extraction job...");
  const jobId = await runExtractionJob(apiKey, agentId, fileId);
  console.log(`Extraction job started with ID: ${jobId}`);

  // Step 3: Poll for job completion
  console.log("Polling for job completion...");
  await pollForJobCompletion(apiKey, jobId, pollInterval, maxRetries);
  console.log("Job completed successfully!");

  // Step 4: Get results
  console.log("Retrieving extraction results...");
  const results = await getExtractionResults(apiKey, jobId);
  console.log("Extraction completed successfully!");

  return results;
}

/**
 * Uploads a file to LlamaIndex Cloud
 */
async function uploadFile(
  apiKey: string,
  filePath: string,
  fileName?: string,
): Promise<string> {
  // Check if file exists
  if (!fs.existsSync(filePath)) {
    throw new Error(`File not found: ${filePath}`);
  }

  // Read the file
  const fileBuffer = fs.readFileSync(filePath);
  const finalFileName = fileName || path.basename(filePath);

  // Create FormData
  const formData = new FormData();

  // Convert Node.js Buffer to Uint8Array (Blob-compatible)
  const uint8Array = new Uint8Array(fileBuffer);

  // Create a Blob using Uint8Array
  const fileBlob = new Blob([uint8Array], {
    type: getContentType(finalFileName),
  });

  formData.append("upload_file", fileBlob, finalFileName);
  const response = await fetch(`${API_BASE}/files`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      accept: "application/json",
    },
    body: formData,
  });

  if (!response.ok) {
    throw new Error(
      `File upload failed: ${response.status} ${response.statusText}`,
    );
  }

  const result: UploadResponse = (await response.json()) as UploadResponse;
  return result.id;
}

/**
 * Starts an extraction job
 */
async function runExtractionJob(
  apiKey: string,
  agentId: string,
  fileId: string,
): Promise<string> {
  const response = await fetch(`${API_BASE}/extraction/jobs`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      extraction_agent_id: agentId,
      file_id: fileId,
    }),
  });

  if (!response.ok) {
    throw new Error(
      `Extraction job failed to start: ${response.status} ${response.statusText}`,
    );
  }

  const result: ExtractionJobResponse =
    (await response.json()) as ExtractionJobResponse;
  return result.id;
}

/**
 * Polls for job completion
 */
async function pollForJobCompletion(
  apiKey: string,
  jobId: string,
  pollInterval: number,
  maxRetries: number,
): Promise<void> {
  let retries = 0;

  while (retries < maxRetries) {
    const response = await fetch(`${API_BASE}/extraction/jobs/${jobId}`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        accept: "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(
        `Failed to get job status: ${response.status} ${response.statusText}`,
      );
    }

    const status: JobStatusResponse =
      (await response.json()) as JobStatusResponse;

    if (status.status === "SUCCESS") {
      return; // Job completed successfully
    }

    if (status.status === "FAILED") {
      throw new Error(`Extraction job failed`);
    }

    // Job is still PENDING or RUNNING, wait and retry
    await new Promise((resolve) => setTimeout(resolve, pollInterval));
    retries++;
  }

  throw new Error(`Job polling timed out after ${maxRetries} attempts`);
}

/**
 * Retrieves the results of a completed extraction job
 */
async function getExtractionResults(
  apiKey: string,
  jobId: string,
): Promise<ExtractionResult> {
  const response = await fetch(`${API_BASE}/extraction/jobs/${jobId}/result`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(
      `Failed to get extraction results: ${response.status} ${response.statusText}`,
    );
  }

  return (await response.json()) as ExtractionResult;
}

export { extractDataFromFile };
