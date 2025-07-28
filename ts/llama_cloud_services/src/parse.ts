import { createClient, createConfig } from "@hey-api/client-fetch";
import { createWorkflow, type InferWorkflowEventData } from "@llama-flow/core";
import { createStatefulMiddleware } from "@llama-flow/core/middleware/state";
import { withTraceEvents } from "@llama-flow/core/middleware/trace-events";
import { pRetryHandler } from "@llama-flow/core/util/p-retry";
import { fs, getEnv, path } from "@llamaindex/env";
import {
  type BodyUploadFileApiV1ParsingUploadPost,
  getJobApiV1ParsingJobJobIdGet,
  getJobJsonResultApiV1ParsingJobJobIdResultJsonGet,
  getJobResultApiV1ParsingJobJobIdResultMarkdownGet,
  getJobTextResultApiV1ParsingJobJobIdResultTextGet,
  type StatusEnum,
  uploadFileApiV1ParsingUploadPost,
} from "./client";
import {
  checkStatusEvent,
  checkStatusSuccessEvent,
  jsonResultEvent,
  markdownResultEvent,
  requestJsonEvent,
  requestMarkdownEvent,
  requestTextEvent,
  textResultEvent,
  uploadEvent,
} from "./events";

export type LlamaParseWorkflowParams = {
  region?: "us" | "eu" | "us-staging";
  apiKey?: string;
};

const URLS = {
  us: "https://api.cloud.llamaindex.ai",
  eu: "https://api.cloud.eu.llamaindex.ai",
  "us-staging": "https://api.staging.llamaindex.ai",
} as const;

const { withState, getContext } = createStatefulMiddleware(
  (params: LlamaParseWorkflowParams) => {
    const apiKey = params.apiKey ?? getEnv("LLAMA_CLOUD_API_KEY");
    const region = params.region ?? "us";
    if (!apiKey) {
      throw new Error("LLAMA_CLOUD_API_KEY is not set");
    }
    return {
      cache: {} as Record<string, StatusEnum>,
      client: createClient(
        createConfig({
          baseUrl: URLS[region],
          headers: {
            Authorization: `Bearer ${apiKey}`,
          },
        }),
      ),
    };
  },
);

const llamaParseWorkflow = withState(withTraceEvents(createWorkflow()));

llamaParseWorkflow.handle([uploadEvent], async ({ data: form }) => {
  const { state } = getContext();
  const finalForm = { ...form };
  if ("file" in form) {
    // support loads from the file system
    const file = form?.file;
    const isFilePath = typeof file === "string";
    const data = isFilePath ? await fs.readFile(file) : file;
    const filename: string | undefined = isFilePath
      ? path.basename(file)
      : undefined;
    finalForm.file = data
      ? globalThis.File && filename
        ? new File([data], filename)
        : new Blob([data])
      : undefined;
  }
  const {
    data: { id, status },
  } = await uploadFileApiV1ParsingUploadPost({
    throwOnError: true,
    body: {
      ...finalForm,
    } as BodyUploadFileApiV1ParsingUploadPost,
    client: state.client,
  });
  state.cache[id] = status;
  return checkStatusEvent.with(id);
});

llamaParseWorkflow.handle(
  [checkStatusEvent],
  pRetryHandler(
    async ({ data: uuid }) => {
      const { state } = getContext();
      if (state.cache[uuid] === "SUCCESS") {
        return checkStatusSuccessEvent.with(uuid);
      }
      const {
        data: { status },
      } = await getJobApiV1ParsingJobJobIdGet({
        throwOnError: true,
        path: {
          job_id: uuid,
        },
        client: state.client,
      });
      state.cache[uuid] = status;
      if (status === "SUCCESS") {
        return checkStatusSuccessEvent.with(uuid);
      }
      throw new Error(`LLamaParse status: ${status}`);
    },
    {
      retries: 100,
    },
  ),
);

//#region sub workflow
llamaParseWorkflow.handle([requestMarkdownEvent], async ({ data: job_id }) => {
  const { state } = getContext();
  const { data } = await getJobResultApiV1ParsingJobJobIdResultMarkdownGet({
    throwOnError: true,
    path: {
      job_id,
    },
    client: state.client,
  });
  return markdownResultEvent.with(data.markdown);
});

llamaParseWorkflow.handle([requestTextEvent], async ({ data: job_id }) => {
  const { state } = getContext();
  const { data } = await getJobTextResultApiV1ParsingJobJobIdResultTextGet({
    throwOnError: true,
    path: {
      job_id,
    },
    client: state.client,
  });
  return textResultEvent.with(data.text);
});

llamaParseWorkflow.handle([requestJsonEvent], async ({ data: job_id }) => {
  const { state } = getContext();
  const { data } = await getJobJsonResultApiV1ParsingJobJobIdResultJsonGet({
    throwOnError: true,
    path: {
      job_id,
    },
    client: state.client,
  });
  return jsonResultEvent.with(data.pages);
});
//#endregion

export type ParseJob = {
  get jobId(): string;
  get signal(): AbortSignal;
  get context(): ReturnType<typeof llamaParseWorkflow.createContext>;
  get form(): InferWorkflowEventData<typeof uploadEvent>;

  markdown(): Promise<string>;
  text(): Promise<string>;
  //eslint-disable-next-line @typescript-eslint/no-explicit-any
  json(): Promise<any[]>;
};

export const upload = async (
  params: InferWorkflowEventData<typeof uploadEvent> & LlamaParseWorkflowParams,
): Promise<ParseJob> => {
  //#region upload event
  const context = llamaParseWorkflow.createContext(params);
  const { stream, sendEvent } = context;
  const ev = uploadEvent.with(params);
  sendEvent(ev);

  const uploadThread = await llamaParseWorkflow
    .substream(ev, stream)
    .until((ev) => checkStatusSuccessEvent.include(ev))
    .toArray();
  //#region
  const jobId: string = uploadThread.at(-1)!.data;
  return {
    get signal() {
      // lazy load
      return context.signal;
    },
    get jobId() {
      return jobId;
    },
    get form() {
      return ev.data;
    },
    get context() {
      return context;
    },
    async markdown(): Promise<string> {
      const requestEv = requestMarkdownEvent.with(jobId);
      const { sendEvent, stream } = llamaParseWorkflow.createContext(params);
      sendEvent(requestEv);
      const markdownThread = await stream.until(markdownResultEvent).toArray();
      return markdownThread.at(-1)!.data;
    },
    async text(): Promise<string> {
      const requestEv = requestTextEvent.with(jobId);
      const { sendEvent, stream } = llamaParseWorkflow.createContext(params);
      sendEvent(requestEv);
      const textThread = await stream.until(textResultEvent).toArray();
      return textThread.at(-1)!.data;
    },
    //eslint-disable-next-line @typescript-eslint/no-explicit-any
    async json(): Promise<any[]> {
      const requestEv = requestJsonEvent.with(jobId);
      const { sendEvent, stream } = llamaParseWorkflow.createContext(params);
      sendEvent(requestEv);
      const jsonThread = await stream
        .until((ev) => jsonResultEvent.include(ev))
        .toArray();
      return jsonThread.at(-1)!.data;
    },
  };
};
