import { UploadResponse, JobStatusResponse } from "../generic_interfaces";

export interface ExtractionJobResponse {
  id: string;
  status: string;
  extraction_agent_id: string;
  file_id: string;
}

export interface ExtractionResult {
  // The actual structure will depend on your extraction agent configuration
  [key: string]: unknown;
}

export interface CreateAgentRequest {
  name: string;
  [key: string]: unknown; // for the JSON schema properties
}

export { UploadResponse, JobStatusResponse };
