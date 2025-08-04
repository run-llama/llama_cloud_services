import { emitWarning } from "process";
import fs from "fs/promises";
import { Blob } from "buffer";
import type { ExtractResult } from "./type";
import {
  type Options,
  type ExtractAgentCreate,
  type ExtractConfig,
  type ExtractJobCreate,
  type ExtractAgent,
  type CreateExtractionAgentApiV1ExtractionExtractionAgentsPostData,
  type GetExtractionAgentByNameApiV1ExtractionExtractionAgentsByNameNameGetData,
  type GetExtractionAgentApiV1ExtractionExtractionAgentsExtractionAgentIdGetData,
  type RunJobApiV1ExtractionJobsPostData,
  type GetJobApiV1ExtractionJobsJobIdGetData,
  type GetJobResultApiV1ExtractionJobsJobIdResultGetData,
  StatusEnum,
  type UploadFileApiV1FilesPostData,
  createExtractionAgentApiV1ExtractionExtractionAgentsPost,
  getExtractionAgentByNameApiV1ExtractionExtractionAgentsByNameNameGet,
  getExtractionAgentApiV1ExtractionExtractionAgentsExtractionAgentIdGet,
  runJobApiV1ExtractionJobsPost,
  getJobApiV1ExtractionJobsJobIdGet,
  getJobResultApiV1ExtractionJobsJobIdResultGet,
  uploadFileApiV1FilesPost,
} from "./api";
import type { Client } from "@hey-api/client-fetch";
import { sleep } from "./utils";

type BodyUploadFileApiV1FilesPost = {
  upload_file: Blob | File;
};

export async function createAgent(
  name: string,
  dataSchema:
    | {
        [key: string]:
          | { [key: string]: unknown }
          | Array<unknown>
          | string
          | number
          | number
          | boolean
          | null;
      }
    | string,
  config: ExtractConfig | undefined = undefined,
  project_id: string | undefined = undefined,
  organization_id: string | undefined = undefined,
  client: Client | undefined = undefined,
): Promise<ExtractAgent | undefined> {
  const agentData = {
    name: name,
    data_schema: dataSchema,
    config: config,
  } as ExtractAgentCreate;
  const agentDataCreation = {
    body: agentData,
    query: { project_id: project_id, organization_id: organization_id },
  } as CreateExtractionAgentApiV1ExtractionExtractionAgentsPostData;
  const options =
    agentDataCreation as Options<CreateExtractionAgentApiV1ExtractionExtractionAgentsPostData>;
  if (typeof client != "undefined") {
    options.client = client;
  }
  const response =
    await createExtractionAgentApiV1ExtractionExtractionAgentsPost(options);
  if ("detail" in response) {
    throw new Error(
      `An error occurred while creating the extraction agent.\nDetails:\n\n${response.detail}\n\n`,
    );
  } else if (
    "id" in response &&
    "project_id" in response &&
    "config" in response &&
    "data_schema" in response &&
    "name" in response
  ) {
    return response as ExtractAgent;
  }
}

export async function getAgent(
  id: string | undefined = undefined,
  name: string | undefined = undefined,
  project_id: string | undefined = undefined,
  organization_id: string | undefined = undefined,
  client: Client | undefined = undefined,
): Promise<ExtractAgent | undefined> {
  if (typeof id === "undefined" && typeof name === "undefined") {
    throw new Error("One of `id` and `string` must be passed.");
  } else if (typeof id != "undefined" && typeof name != "undefined") {
    emitWarning("You passed both `id` and `name`, using only id...");
    const data = {
      path: { extraction_agent_id: id },
    } as GetExtractionAgentApiV1ExtractionExtractionAgentsExtractionAgentIdGetData;
    const options =
      data as Options<GetExtractionAgentApiV1ExtractionExtractionAgentsExtractionAgentIdGetData>;
    if (typeof client != "undefined") {
      options.client = client;
    }
    const response =
      await getExtractionAgentApiV1ExtractionExtractionAgentsExtractionAgentIdGet(
        options,
      );
    if ("detail" in response) {
      throw new Error(
        `An error occurred while creating the extraction agent.\nDetails:\n\n${response.detail}\n\n`,
      );
    } else if (
      "id" in response &&
      "project_id" in response &&
      "config" in response &&
      "data_schema" in response &&
      "name" in response
    ) {
      return response as ExtractAgent;
    }
  } else if (typeof name != "undefined" && typeof "id" === "undefined") {
    const data = {
      path: { name: name },
      query: { organization_id: organization_id, project_id: project_id },
    } as GetExtractionAgentByNameApiV1ExtractionExtractionAgentsByNameNameGetData;
    const options =
      data as Options<GetExtractionAgentByNameApiV1ExtractionExtractionAgentsByNameNameGetData>;
    if (typeof client != "undefined") {
      options.client = client;
    }
    const response =
      await getExtractionAgentByNameApiV1ExtractionExtractionAgentsByNameNameGet(
        options,
      );
    if ("detail" in response) {
      throw new Error(
        `An error occurred while creating the extraction agent.\nDetails:\n\n${response.detail}\n\n`,
      );
    } else if (
      "id" in response &&
      "project_id" in response &&
      "config" in response &&
      "data_schema" in response &&
      "name" in response
    ) {
      return response as ExtractAgent;
    }
  } else {
    const data = {
      path: { extraction_agent_id: id },
    } as GetExtractionAgentApiV1ExtractionExtractionAgentsExtractionAgentIdGetData;
    const options =
      data as Options<GetExtractionAgentApiV1ExtractionExtractionAgentsExtractionAgentIdGetData>;
    const response =
      await getExtractionAgentApiV1ExtractionExtractionAgentsExtractionAgentIdGet(
        options,
      );
    if ("detail" in response) {
      throw new Error(
        `An error occurred while creating the extraction agent.\nDetails:\n\n${response.detail}\n\n`,
      );
    } else if (
      "id" in response &&
      "project_id" in response &&
      "config" in response &&
      "data_schema" in response &&
      "name" in response
    ) {
      return response as ExtractAgent;
    }
  }
}

async function uploadFile(
  filePath: string,
  project_id: string | undefined = undefined,
  organization_id: string | undefined = undefined,
  client: Client | undefined = undefined,
): Promise<string | undefined> {
  const buffer = await fs.readFile(filePath);
  const fileBlob = new Blob([buffer]);
  const fileToUpload = {
    upload_file: fileBlob,
  } as BodyUploadFileApiV1FilesPost;
  const uploadData = {
    body: fileToUpload,
    query: { organization_id: organization_id, project_id: project_id },
  } as UploadFileApiV1FilesPostData;
  const uploadOptions = uploadData as Options<UploadFileApiV1FilesPostData>;
  if (typeof client != "undefined") {
    uploadOptions.client = client;
  }
  const uploadResponse = await uploadFileApiV1FilesPost(uploadOptions);
  let fileId: string | undefined = undefined;
  if ("detail" in uploadResponse) {
    throw new Error(
      `There was an error processing and uploading your file.\nDetail:\n\n${uploadResponse.detail}`,
    );
  }
  if ("id" in uploadResponse) {
    fileId = uploadResponse.id as string;
    return fileId;
  }
}

async function createExtractJob(
  options: Options<RunJobApiV1ExtractionJobsPostData>,
): Promise<string | undefined> {
  const response = await runJobApiV1ExtractionJobsPost(options);
  if ("detail" in response) {
    throw new Error(
      `An error occurred while creating your extraction job.\nDetails:\n\n${response.detail}\n\n`,
    );
  }
  if (
    "extraction_agent" in response &&
    "status" in response &&
    "id" in response
  ) {
    const jobStatus = response.status as StatusEnum;
    if (jobStatus == "CANCELLED") {
      throw new Error("Your extraction job has been cancelled");
    } else if (jobStatus == "ERROR") {
      throw new Error("Your extraction job has produced an error");
    } else {
      return response.id as string;
    }
  }
}

async function pollForJobCompletion(
  jobId: string,
  interval: number = 1000,
  maxIterations: number = 600,
  client: Client | undefined = undefined,
): Promise<boolean> {
  let status: StatusEnum | undefined = undefined;
  const jobData = {
    path: { job_id: jobId },
  } as GetJobApiV1ExtractionJobsJobIdGetData;
  const jobOptions = jobData as Options<GetJobApiV1ExtractionJobsJobIdGetData>;
  if (typeof client != "undefined") {
    jobOptions.client = client;
  }
  let numIterations: number = 0;
  while (true) {
    if (numIterations > maxIterations) {
      return false;
    }
    const response = await getJobApiV1ExtractionJobsJobIdGet(jobOptions);
    if ("detail" in response) {
      throw new Error(
        `There was an error extracting data from your file.\nDetail:\n\n${response.detail}`,
      );
    }
    if ("id" in response && "status" in response) {
      status = response.status as StatusEnum;
      if (status == StatusEnum.CANCELLED || status == StatusEnum.ERROR) {
        throw new Error("There was an error extracting data from your file.");
      } else if (status == StatusEnum.SUCCESS) {
        return true;
      } else {
        numIterations++;
        await sleep(interval);
      }
    }
  }
}

async function getJobResult(
  jobId: string,
  client: Client | undefined = undefined,
  project_id: string | undefined = undefined,
  organization_id: string | undefined = undefined,
): Promise<ExtractResult | undefined> {
  const jobData = {
    path: { job_id: jobId },
    query: { organization_id: organization_id, project_id: project_id },
  } as GetJobResultApiV1ExtractionJobsJobIdResultGetData;
  const jobOptions =
    jobData as Options<GetJobResultApiV1ExtractionJobsJobIdResultGetData>;
  if (typeof client != "undefined") {
    jobOptions.client = client;
  }
  const response =
    await getJobResultApiV1ExtractionJobsJobIdResultGet(jobOptions);
  if ("detail" in response) {
    throw new Error(
      `There was an error while retrieving the result of your data extraction job.\nDetail:\n\n${response.detail}`,
    );
  }
  if ("data" in response && "extraction_metadata" in response) {
    return {
      data: response.data,
      extractionMetadata: response.extraction_metadata,
    } as ExtractResult;
  }
}

export async function extract(
  agentId: string,
  filePath: string,
  project_id: string | undefined = undefined,
  organization_id: string | undefined = undefined,
  client: Client | undefined = undefined,
  fromUi: boolean | undefined = undefined,
  pollingInterval: number = 1000,
  maxPollingIterations: number = 600,
): Promise<ExtractResult | undefined> {
  const fileId = (await uploadFile(
    filePath,
    project_id,
    organization_id,
    client,
  )) as string;
  const extractJobCreate = {
    extraction_agent_id: agentId,
    file_id: fileId,
  } as ExtractJobCreate;
  const extractData = {
    body: extractJobCreate,
    query: { from_ui: fromUi },
  } as RunJobApiV1ExtractionJobsPostData;
  const extractOptions =
    extractData as Options<RunJobApiV1ExtractionJobsPostData>;
  if (typeof client != "undefined") {
    extractOptions.client = client;
  }
  const jobId = (await createExtractJob(extractOptions)) as string;
  const success = await pollForJobCompletion(
    jobId,
    pollingInterval,
    maxPollingIterations,
    client,
  );
  if (!success) {
    throw new Error("Your job is taking longer than 10 minutes, timing out...");
  } else {
    return (await getJobResult(
      jobId,
      client,
      project_id,
      organization_id,
    )) as ExtractResult;
  }
}

export { type ExtractAgent, type ExtractConfig };
