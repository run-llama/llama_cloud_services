import { fs } from "fs";
import { path } from "path";
import { API_BASE } from "../const.js";
import { getContentType } from "../generic_utils.js";
import { UploadResponse, JobStatusResponse } from "../generic_interfaces.js";
import { ParsingResult, Pages } from "./interfaces.js";

export async function uploadFile(
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
  const response = await fetch(`${API_BASE}/parsing/upload`, {
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
 * Polls for job completion
 */
export async function pollForJobCompletion(
  apiKey: string,
  jobId: string,
  pollInterval: number,
  maxRetries: number,
): Promise<void> {
  let retries = 0;

  while (retries < maxRetries) {
    const response = await fetch(`${API_BASE}/parsing/jobs/${jobId}`, {
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

export async function getMarkdownResult(
  jobId: string,
  apiKey: string,
): Promise<string | null> {
  try {
    const response = await fetch(
      `${API_BASE}/parsing/job/${jobId}/result/markdown`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          accept: "application/json",
        },
      },
    );

    if (!response.ok) {
      return null;
    }

    const data = await response.json();
    return data["markdown"];
  } catch (error) {
    console.error("Error fetching markdown result:", error);
    return null;
  }
}

export async function getJsonResult(
  jobId: string,
  apiKey: string,
): Promise<Pages | null> {
  try {
    const response = await fetch(
      `${API_BASE}/parsing/job/${jobId}/result/json`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          accept: "application/json",
        },
      },
    );

    if (!response.ok) {
      return null;
    }

    const data = await response.json();
    return data as Pages;
  } catch (error) {
    console.error("Error fetching JSON result:", error);
    return null;
  }
}

export async function getTextResult(
  jobId: string,
  apiKey: string,
): Promise<string | null> {
  try {
    const response = await fetch(
      `${API_BASE}/parsing/job/${jobId}/result/text`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          accept: "application/json",
        },
      },
    );

    if (!response.ok) {
      return null;
    }

    const data = await response.json();
    return data["text"];
  } catch (error) {
    console.error("Error fetching text result:", error);
    return null;
  }
}

// Convenience function to get all results at once
export async function getAllResults(
  jobId: string,
  apiKey: string,
): Promise<ParsingResult> {
  const [markdown, json, text] = await Promise.all([
    getMarkdownResult(jobId, apiKey),
    getJsonResult(jobId, apiKey),
    getTextResult(jobId, apiKey),
  ]);

  return {
    markdown: markdown || undefined,
    json: json || undefined,
    text: text || undefined,
  };
}
