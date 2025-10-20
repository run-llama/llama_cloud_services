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

async function createClassifyJob(
  file_ids: string[],
  rules: ClassifierRule[],
  parsing_configuration: ClassifyParsingConfiguration,
  organization_id: null | string,
  project_id: null | string,
  client: Client | undefined,
  maxRetriesOnError: number = 10,
  retryInterval: number = 0.5,
): Promise<string> {
  const rawData = {
    file_ids: file_ids,
    rules: rules,
    parsing_configuration: parsing_configuration,
  } as ClassifyJobCreate;
  const data = {
    body: rawData,
    query: {
      project_id: project_id,
      organization_id: organization_id,
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

async function pollForJobCompletion(
  jobId: string,
  interval: number = 1,
  maxIterations: number = 1800,
  client: Client | undefined = undefined,
): Promise<boolean> {
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

async function getJobResult(
  jobId: string,
  client: Client | undefined = undefined,
  project_id: string | null = null,
  organization_id: string | null = null,
  maxRetriesOnError: number = 10,
  retryInterval: number = 0.5,
): Promise<ClassifyJobResults> {
  const jobData = {
    path: { classify_job_id: jobId },
    query: { organization_id: organization_id, project_id: project_id },
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
  fileContents:
    | Buffer<ArrayBufferLike>[]
    | File[]
    | Uint8Array<ArrayBuffer>[]
    | string[]
    | undefined = undefined,
  filePaths: string[] | undefined = undefined,
  project_id: string | null = null,
  organization_id: string | null = null,
  client: Client | undefined = undefined,
  pollingInterval: number = 1,
  maxPollingIterations: number = 1800,
  maxRetriesOnError: number = 10,
  retryInterval: number = 0.5,
): Promise<ClassifyJobResults> {
  const fileIds: string[] = [];
  if (typeof fileContents == "undefined" && typeof filePaths == "undefined") {
    throw new Error(
      "At least one of fileContents and filePaths has to be provided",
    );
  } else if (
    typeof filePaths != "undefined" &&
    typeof fileContents != "undefined"
  ) {
    for (const name of filePaths) {
      const fileId = await uploadFile(
        name,
        undefined,
        undefined,
        project_id,
        organization_id,
        client,
        maxRetriesOnError,
        retryInterval,
      );
      if (typeof fileId != "undefined") {
        fileIds.push(fileId);
      } else {
        console.log(`Unable to upload ${name}, skipping...`);
      }
    }
    for (const content of fileContents) {
      const fileId = await uploadFile(
        undefined,
        content,
        undefined,
        project_id,
        organization_id,
        client,
        maxRetriesOnError,
        retryInterval,
      );
      if (typeof fileId != "undefined") {
        fileIds.push(fileId);
      } else {
        console.log(
          // TODO: improve error message
          `Unable to upload file, skipping...`,
        );
      }
    }
  } else if (
    typeof filePaths != "undefined" &&
    typeof fileContents == "undefined"
  ) {
    for (const name of filePaths) {
      const fileId = await uploadFile(
        name,
        undefined,
        undefined,
        project_id,
        organization_id,
        client,
        maxRetriesOnError,
        retryInterval,
      );
      if (typeof fileId != "undefined") {
        fileIds.push(fileId);
      } else {
        console.log(`Unable to upload ${name}, skipping...`);
      }
    }
  } else if (
    typeof filePaths == "undefined" &&
    typeof fileContents != "undefined"
  ) {
    for (const content of fileContents) {
      const fileId = await uploadFile(
        undefined,
        content,
        undefined,
        project_id,
        organization_id,
        client,
        maxRetriesOnError,
        retryInterval,
      );
      if (typeof fileId != "undefined") {
        fileIds.push(fileId);
      } else {
        console.log(
          // TODO: improve error message
          `Unable to upload file, skipping...`,
        );
      }
    }
  }
  const jobId = await createClassifyJob(
    fileIds,
    rules,
    parsingConfiguration,
    organization_id,
    project_id,
    client,
    maxRetriesOnError,
    retryInterval,
  );
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
    )) as ClassifyJobResults;
  }
}

export {
  type ClassifierRule,
  type ClassifyJobResults,
  type ClassifyParsingConfiguration,
};
