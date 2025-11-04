import type {
  Options,
  CreateClassifyJobApiV1ClassifierJobsPostData,
  ClassifyJobCreate,
  ClassifierRule,
  ClassifyParsingConfiguration,
  GetClassifyJobApiV1ClassifierJobsClassifyJobIdGetData,
  GetClassificationJobResultsApiV1ClassifierJobsClassifyJobIdResultsGetData,
  ClassifyJobResults,
} from "./api";
import {
  StatusEnum,
  createClassifyJobApiV1ClassifierJobsPost,
  getClassifyJobApiV1ClassifierJobsClassifyJobIdGet,
  getClassificationJobResultsApiV1ClassifierJobsClassifyJobIdResultsGet,
} from "./api";
import type { Client } from "@hey-api/client-fetch";
import { sleep } from "./utils";
import { uploadFile } from "./fileUpload";
import { File } from "buffer";

async function createClassifyJob({
  fileIds,
  rules,
  parsingConfiguration,
  projectId,
  client,
  maxRetriesOnError = 10,
  retryInterval = 0.5,
}: {
  fileIds: string[];
  rules: ClassifierRule[];
  parsingConfiguration: ClassifyParsingConfiguration;
  projectId?: string | undefined;
  client?: Client | undefined;
  maxRetriesOnError?: number;
  retryInterval?: number;
}): Promise<string> {
  const rawData = {
    file_ids: fileIds,
    rules: rules,
    parsing_configuration: parsingConfiguration,
  } as ClassifyJobCreate;
  const data = {
    body: rawData,
    query: {
      project_id: projectId,
    },
  } as CreateClassifyJobApiV1ClassifierJobsPostData;
  const options = data as Options<CreateClassifyJobApiV1ClassifierJobsPostData>;
  if (typeof client != "undefined") {
    options.client = client;
  }
  let retries = 0;
  while (true) {
    if (retries > maxRetriesOnError) {
      throw new Error(
        "Error while creating the classify job: Exceeded maximum number of retries, the API keeps returning errors.",
      );
    }
    const response = await createClassifyJobApiV1ClassifierJobsPost(options);
    if (!response.response.ok) {
      if ("error" in response) {
        console.log(
          `An error occurred while creating the classification job.\nDetails:\n\n${JSON.stringify(
            response.error,
          )}\n\nRetrying...`,
        );
      }
      retries++;
      await sleep(retryInterval * 1000);
    } else {
      if (typeof response.data != "undefined") {
        return response.data.id;
      } else {
        throw new Error(
          "Error while creating the classify job: the job creation succeeded but no data where returned",
        );
      }
    }
  }
}

async function pollForJobCompletion({
  jobId,
  interval = 1,
  maxIterations = 1800,
  client,
}: {
  jobId: string;
  interval?: number;
  maxIterations?: number;
  client?: Client | undefined;
}): Promise<boolean> {
  let status: StatusEnum | undefined = undefined;
  const jobData = {
    path: { classify_job_id: jobId },
  } as GetClassifyJobApiV1ClassifierJobsClassifyJobIdGetData;
  const jobOptions =
    jobData as Options<GetClassifyJobApiV1ClassifierJobsClassifyJobIdGetData>;
  if (typeof client != "undefined") {
    jobOptions.client = client;
  }
  let numIterations: number = 0;
  while (true) {
    if (numIterations > maxIterations) {
      return false;
    }
    const response =
      await getClassifyJobApiV1ClassifierJobsClassifyJobIdGet(jobOptions);
    if (!response.response.ok) {
      numIterations++;
    }
    if (typeof response.data != "undefined") {
      status = response.data.status as StatusEnum;
      if (status == StatusEnum.CANCELLED || status == StatusEnum.ERROR) {
        throw new Error("There was an error during the classification job.");
      } else if (status == StatusEnum.SUCCESS) {
        return true;
      } else {
        numIterations++;
        await sleep(interval * 1000);
      }
    }
  }
}

async function getJobResult({
  jobId,
  client,
  projectId,
  maxRetriesOnError = 10,
  retryInterval = 0.5,
}: {
  jobId: string;
  client?: Client | undefined;
  projectId?: string | undefined;
  maxRetriesOnError?: number;
  retryInterval?: number;
}): Promise<ClassifyJobResults> {
  const jobData = {
    path: { classify_job_id: jobId },
    query: { project_id: projectId },
  } as GetClassificationJobResultsApiV1ClassifierJobsClassifyJobIdResultsGetData;
  const jobOptions =
    jobData as Options<GetClassificationJobResultsApiV1ClassifierJobsClassifyJobIdResultsGetData>;
  if (typeof client != "undefined") {
    jobOptions.client = client;
  }
  let retries: number = 0;
  while (true) {
    if (retries > maxRetriesOnError) {
      throw new Error(
        "Error while getting the result of the classification job: Exceeded maximum number of retries, the API keeps returning errors.",
      );
    }
    const response =
      await getClassificationJobResultsApiV1ClassifierJobsClassifyJobIdResultsGet(
        jobOptions,
      );
    if (!response.response.ok) {
      if ("error" in response) {
        console.log(
          "An error occurred: ",
          JSON.stringify(response.error),
          "\nRetrying...",
        );
      }
      retries++;
      await sleep(retryInterval * 1000);
    }
    if (typeof response.data != "undefined") {
      return response.data as ClassifyJobResults;
    } else {
      throw new Error(
        "Error while retrieving results for the classify job: the result was successfully obtained but no data were returned",
      );
    }
  }
}

export async function classify(
  rules: ClassifierRule[],
  parsingConfiguration: ClassifyParsingConfiguration,
  {
    fileContents,
    filePaths,
    projectId,
    client,
    pollingInterval = 1,
    maxPollingIterations = 1800,
    maxRetriesOnError = 10,
    retryInterval = 0.5,
  }: {
    fileContents?:
      | Buffer<ArrayBufferLike>[]
      | File[]
      | Uint8Array<ArrayBuffer>[]
      | string[]
      | undefined;
    filePaths?: string[] | undefined;
    projectId?: string | undefined;
    client?: Client | undefined;
    pollingInterval?: number;
    maxPollingIterations?: number;
    maxRetriesOnError?: number;
    retryInterval?: number;
  },
): Promise<ClassifyJobResults> {
  const fileIds: string[] = [];
  if (!filePaths && !fileContents) {
    throw new Error(
      "One between filePath and fileContent needs to be provided",
    );
  }

  if (filePaths) {
    const uploadPromises = filePaths.map(async (name) => {
      try {
        const fileId = await uploadFile({
          filePath: name,
          maxRetriesOnError,
          retryInterval: retryInterval,
          project_id: projectId,
          client: client,
        });
        if (fileId) {
          return fileId;
        } else {
          console.error(`Unable to upload ${name}, skipping...`);
          return null;
        }
      } catch (error) {
        console.error(`Error uploading ${name}:`, error);
        return null;
      }
    });

    const results = await Promise.all(uploadPromises);
    fileIds.push(...results.filter((id) => id !== null));
  }

  if (fileContents) {
    const uploadPromises = fileContents.map(async (content) => {
      try {
        const fileId = await uploadFile({
          fileContent: content,
          ...(projectId ? { project_id: projectId } : {}),
          ...(client ? { client: client } : {}),
          maxRetriesOnError,
          retryInterval,
        });
        if (fileId) {
          return fileId;
        } else {
          console.error(`Unable to upload file (content), skipping...`);
          return null;
        }
      } catch (error) {
        console.error(`Error uploading file (content):`, error);
        return null;
      }
    });

    const results = await Promise.all(uploadPromises);
    fileIds.push(...results.filter((id) => id !== null));
  }

  if (fileIds.length == 0) {
    throw new Error(
      "None of the provided files was successfully uploaded, it is not possible to create a classification job.",
    );
  }

  const jobId = await createClassifyJob({
    fileIds,
    rules,
    parsingConfiguration,
    ...(projectId ? { projectId: projectId } : {}),
    ...(client ? { client: client } : {}),
    maxRetriesOnError,
    retryInterval,
  });
  const success = await pollForJobCompletion({
    jobId,
    interval: pollingInterval,
    maxIterations: maxPollingIterations,
    client,
  });
  if (!success) {
    throw new Error("Your job is taking longer than 10 minutes, timing out...");
  } else {
    return (await getJobResult({
      jobId,
      client,
      projectId,
      maxRetriesOnError,
      retryInterval,
    })) as ClassifyJobResults;
  }
}

export {
  type ClassifierRule,
  type ClassifyJobResults,
  type ClassifyParsingConfiguration,
};
