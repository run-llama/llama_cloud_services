export interface UploadResponse {
  id: string;
  name: string;
  status: string;
}

export interface JobStatusResponse {
  id: string;
  status: "PENDING" | "RUNNING" | "SUCCESS" | "FAILED";
  extraction_agent_id: string;
  file_id: string;
  created_at: string;
  updated_at: string;
}
