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
  type StatelessExtractionRequest,
  type ExtractStatelessApiV1ExtractionRunPostData,
  type ExtractStatelessApiV1ExtractionRunPostError,
  type RunJobApiV1ExtractionJobsPostResponse,
  type RunJobApiV1ExtractionJobsPostError,
  createExtractionAgentApiV1ExtractionExtractionAgentsPost,
  getExtractionAgentByNameApiV1ExtractionExtractionAgentsByNameNameGet,
  getExtractionAgentApiV1ExtractionExtractionAgentsExtractionAgentIdGet,
  runJobApiV1ExtractionJobsPost,
  getJobApiV1ExtractionJobsJobIdGet,
  getJobResultApiV1ExtractionJobsJobIdResultGet,
  uploadFileApiV1FilesPost,
  extractStatelessApiV1ExtractionRunPost,
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
  maxRetriesOnError: number = 10,
  retryInterval: number = 500,
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
  let retries: number = 0;
  while (true) {
    if (retries > maxRetriesOnError) {
      throw new Error(
        "Error while processing your file: Exceeded maximum number of retries, the API keeps returning errors.",
      );
    }
    const uploadResponse = await uploadFileApiV1FilesPost(uploadOptions);
    let fileId: string | undefined = undefined;
    if ("detail" in uploadResponse) {
      retries++;
      await sleep(retryInterval);
    }
    if ("id" in uploadResponse) {
      fileId = uploadResponse.id as string;
      return fileId;
    }
  }
}

async function createExtractJob(
  options:
    | Options<RunJobApiV1ExtractionJobsPostData>
    | Options<ExtractStatelessApiV1ExtractionRunPostData>,
  stateless: boolean = false,
  maxRetriesOnError: number = 10,
  retryInterval: number = 500,
): Promise<string | undefined> {
  let retries: number = 0;
  while (true) {
    if (retries > maxRetriesOnError) {
      throw new Error(
        "Error while creating the extraction job: Exceeded maximum number of retries, the API keeps returning errors.",
      );
    }
    let response:
      | ExtractStatelessApiV1ExtractionRunPostData
      | ExtractStatelessApiV1ExtractionRunPostError
      | RunJobApiV1ExtractionJobsPostResponse
      | RunJobApiV1ExtractionJobsPostError
      | undefined = undefined;
    if (!stateless) {
      response = (await runJobApiV1ExtractionJobsPost(
        options as Options<RunJobApiV1ExtractionJobsPostData>,
      )) as
        | RunJobApiV1ExtractionJobsPostResponse
        | RunJobApiV1ExtractionJobsPostError;
    } else {
      response = (await extractStatelessApiV1ExtractionRunPost(
        options as Options<ExtractStatelessApiV1ExtractionRunPostData>,
      )) as
        | ExtractStatelessApiV1ExtractionRunPostData
        | ExtractStatelessApiV1ExtractionRunPostError;
    }
    if ("detail" in response) {
      retries++;
      await sleep(retryInterval);
    }
    if (
      "extraction_agent" in response &&
      "status" in response &&
      "id" in response
    ) {
      const jobStatus = response.status as StatusEnum;
      if (jobStatus == "CANCELLED") {
        retries++;
        await sleep(retryInterval);
      } else if (jobStatus == "ERROR") {
        retries++;
        await sleep(retryInterval);
      } else {
        return response.id as string;
      }
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
      numIterations++;
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
  maxRetriesOnError: number = 10,
  retryInterval: number = 500,
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
  let retries: number = 0;
  while (true) {
    if (retries > maxRetriesOnError) {
      throw new Error(
        "Error while getting the result of the extraction job: Exceeded maximum number of retries, the API keeps returning errors.",
      );
    }
    const response =
      await getJobResultApiV1ExtractionJobsJobIdResultGet(jobOptions);
    if ("detail" in response) {
      retries++;
      await sleep(retryInterval);
    }
    if ("data" in response && "extraction_metadata" in response) {
      return {
        data: response.data,
        extractionMetadata: response.extraction_metadata,
      } as ExtractResult;
    }
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
  maxRetriesOnError: number = 10,
  retryInterval: number = 500,
): Promise<ExtractResult | undefined> {
  const fileId = (await uploadFile(
    filePath,
    project_id,
    organization_id,
    client,
    maxRetriesOnError,
    retryInterval,
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
  const jobId = (await createExtractJob(
    extractOptions,
    false,
    maxRetriesOnError,
    retryInterval,
  )) as string;
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
      maxRetriesOnError,
      retryInterval,
    )) as ExtractResult;
  }
}

export async function extractStateless(
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
  filePath: string,
  project_id: string | undefined = undefined,
  organization_id: string | undefined = undefined,
  client: Client | undefined = undefined,
  pollingInterval: number = 1000,
  maxPollingIterations: number = 600,
  maxRetriesOnError: number = 10,
  retryInterval: number = 500,
): Promise<ExtractResult | undefined> {
  const fileId = (await uploadFile(
    filePath,
    project_id,
    organization_id,
    client,
    maxRetriesOnError,
    retryInterval,
  )) as string;
  const extractStatetelessCreate = {
    data_schema: dataSchema,
    file_id: fileId,
    config: config,
  } as StatelessExtractionRequest;
  const extractStatetelessData = {
    body: extractStatetelessCreate,
  } as ExtractStatelessApiV1ExtractionRunPostData;
  const extractOptions =
    extractStatetelessData as Options<ExtractStatelessApiV1ExtractionRunPostData>;
  if (typeof client != "undefined") {
    extractOptions.client = client;
  }
  const jobId = (await createExtractJob(
    extractOptions,
    true,
    maxRetriesOnError,
    retryInterval,
  )) as string;
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
      maxRetriesOnError,
      retryInterval,
    )) as ExtractResult;
  }
}

export { type ExtractAgent, type ExtractConfig };
