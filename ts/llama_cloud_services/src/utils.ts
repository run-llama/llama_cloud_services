import {
  client,
  listProjectsApiV1ProjectsGet,
  searchPipelinesApiV1PipelinesGet,
} from "./api";
import { DEFAULT_BASE_URL } from "@llamaindex/core/global";
import { getEnv } from "@llamaindex/env";
import type { ClientParams } from "./type.js";
import fs from "fs";
import path from "path";

function getBaseUrl(baseUrl?: string): string {
  return baseUrl ?? getEnv("LLAMA_CLOUD_BASE_URL") ?? DEFAULT_BASE_URL;
}

export function getAppBaseUrl(): string {
  return client.getConfig().baseUrl?.replace(/api\./, "") ?? "";
}

// fixme: refactor this to init at the top level or module level
let initOnce = false;
export function initService({ apiKey, baseUrl }: ClientParams = {}) {
  if (initOnce) {
    return;
  }
  initOnce = true;
  client.setConfig({
    baseUrl: getBaseUrl(baseUrl),
    throwOnError: true,
  });
  const token = apiKey ?? getEnv("LLAMA_CLOUD_API_KEY");
  client.interceptors.request.use((request) => {
    request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  });
  client.interceptors.error.use((error) => {
    throw new Error(
      `LlamaCloud API request failed. Error details: ${JSON.stringify(error)}`,
    );
  });
  if (!token) {
    throw new Error(
      "API Key is required for LlamaCloudIndex. Please pass the apiKey parameter",
    );
  }
}

export async function getProjectId(
  projectName: string,
  organizationId?: string,
): Promise<string> {
  const { data: projects } = await listProjectsApiV1ProjectsGet({
    query: {
      project_name: projectName,
      organization_id: organizationId ?? null,
    },
    throwOnError: true,
  });

  if (projects.length === 0) {
    throw new Error(
      `Unknown project name ${projectName}. Please confirm a managed project with this name exists.`,
    );
  } else if (projects.length > 1) {
    throw new Error(
      `Multiple projects found with name ${projectName}. Please specify organization_id.`,
    );
  }

  const project = projects[0]!;

  if (!project.id) {
    throw new Error(`No project found with name ${projectName}`);
  }

  return project.id;
}

export async function getPipelineId(
  name: string,
  projectName: string,
  organizationId?: string,
): Promise<string> {
  const { data: pipelines } = await searchPipelinesApiV1PipelinesGet({
    query: {
      project_id: await getProjectId(projectName, organizationId),
      pipeline_name: name,
    },
    throwOnError: true,
  });

  if (pipelines.length === 0 || !pipelines[0]!.id) {
    throw new Error(
      `No pipeline found with name ${name} in project ${projectName}`,
    );
  }

  return pipelines[0]!.id;
}

export async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function getSavePath(downloadPath: string, i: number): string {
  const now = new Date();
  const formatted =
    now.toISOString().replace(/[-:T]/g, "_").replace(/\..+/, "") +
    "_" +
    now.getMilliseconds().toString().padStart(3, "0");

  let savePath = path.join(downloadPath, `table_${formatted}.csv`);

  if (fs.existsSync(savePath)) {
    savePath = savePath.replace(".csv", "_") + i.toString() + ".csv";
  }

  return savePath;
}
