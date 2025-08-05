import { emitWarning } from "process";
import fs from "fs/promises";
import { Blob } from "buffer";
import * as path from "path";
import { fileTypeFromBuffer } from "file-type";
import type { ExtractResult } from "./type";
import { File } from "buffer";
import {
  type Options,
  type ExtractAgentCreate,
  type ExtractConfig,
  type ExtractJobCreate,
  type ExtractAgent,
  type ExtractJob,
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
  config: ExtractConfig = {} as ExtractConfig,
  project_id: string | null = null,
  organization_id: string | null = null,
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
  if (!response.response.ok) {
    if ("error" in response) {
      throw new Error(
        `An error occurred while creating the extraction agent.\nDetails:\n\n${JSON.stringify(
          response.error,
        )}\n\n`,
      );
    }
  } else {
    return response.data as ExtractAgent;
  }
}

export async function getAgent(
  id: string | undefined = undefined,
  name: string | undefined = undefined,
  project_id: string | null = null,
  organization_id: string | null = null,
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
    if (!response.response.ok) {
      if ("error" in response) {
        throw new Error(
          `An error occurred while getting the extraction agent by ID.\nDetails:\n\n${JSON.stringify(
            response.error,
          )}\n\n`,
        );
      }
    } else {
      return response.data as ExtractAgent;
    }
  } else if (typeof name != "undefined" && typeof id === "undefined") {
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
    if (!response.response.ok) {
      if ("error" in response) {
        throw new Error(
          `An error occurred while getting the extraction agent by name.\nDetails:\n\n${JSON.stringify(
            response.error,
          )}\n\n`,
        );
      }
    } else {
      return response.data as ExtractAgent;
    }
  } else {
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
    if (!response.response.ok) {
      if ("error" in response) {
        throw new Error(
          `An error occurred while getting the extraction agent by ID.\nDetails:\n\n${JSON.stringify(
            response.error,
          )}\n\n`,
        );
      }
    } else {
      return response.data as ExtractAgent;
    }
  }
}

async function uploadFile(
  filePath: string,
  project_id: string | null = null,
  organization_id: string | null = null,
  client: Client | undefined = undefined,
  maxRetriesOnError: number = 10,
  retryInterval: number = 500,
): Promise<string | undefined> {
  const buffer = await fs.readFile(filePath);
  const fileType = await fileTypeFromBuffer(buffer);
  const mimeType = fileType?.mime ?? "application/pdf";
  const fileName = path.basename(filePath);
  const uint8Array = new Uint8Array(buffer);
  const fileBlob = new File([uint8Array], fileName, { type: mimeType });
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
    if (!uploadResponse.response.ok) {
      retries++;
      await sleep(retryInterval);
    }
    if (typeof uploadResponse.data != "undefined") {
      fileId = uploadResponse.data.id as string;
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
      | {
          data: ExtractJob | undefined;
          request: Request;
          response: Response;
        }
      | undefined = undefined;
    if (!stateless) {
      response = (await runJobApiV1ExtractionJobsPost(
        options as Options<RunJobApiV1ExtractionJobsPostData>,
      )) as {
        data: ExtractJob | undefined;
        request: Request;
        response: Response;
      };
    } else {
      response = (await extractStatelessApiV1ExtractionRunPost(
        options as Options<ExtractStatelessApiV1ExtractionRunPostData>,
      )) as {
        data: ExtractJob | undefined;
        request: Request;
        response: Response;
      };
    }
    if (!response.response.ok) {
      if ("error" in response) {
        console.log(
          "An error occurred: ",
          JSON.stringify(response.error),
          "\nRetrying...",
        );
      }
      retries++;
      await sleep(retryInterval);
    }
    if (typeof response.data != "undefined") {
      const jobStatus = response.data.status as StatusEnum;
      if (jobStatus == "CANCELLED") {
        retries++;
        await sleep(retryInterval);
      } else if (jobStatus == "ERROR") {
        retries++;
        await sleep(retryInterval);
      } else {
        return response.data.id as string;
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
    if (!response.response.ok) {
      numIterations++;
    }
    if (typeof response.data != "undefined") {
      status = response.data.status as StatusEnum;
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
  project_id: string | null = null,
  organization_id: string | null = null,
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
    if (!response.response.ok) {
      if ("error" in response) {
        console.log(
          "An error occurred: ",
          JSON.stringify(response.error),
          "\nRetrying...",
        );
      }
      retries++;
      await sleep(retryInterval);
    }
    if (typeof response.data != "undefined") {
      return {
        data: response.data.data,
        extractionMetadata: response.data.extraction_metadata,
      } as ExtractResult;
    }
  }
}

export async function extract(
  agentId: string,
  filePath: string,
  project_id: string | null = null,
  organization_id: string | null = null,
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
  config: ExtractConfig = {} as ExtractConfig,
  filePath: string,
  project_id: string | null = null,
  organization_id: string | null = null,
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
