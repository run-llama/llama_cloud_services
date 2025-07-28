import { workflowEvent } from "@llama-flow/core";
import { zodEvent } from "@llama-flow/core/util/zod";
import { z } from "zod";
import { parseFormSchema } from "./schema";

export const uploadEvent = zodEvent(
  parseFormSchema.merge(
    z.object({
      file: z
        .string()
        .or(z.instanceof(File))
        .or(z.instanceof(Blob))
        .or(z.instanceof(Uint8Array))
        .optional()
        .describe("input"),
    }),
  ),
  {
    debugLabel: "upload",
    uniqueId: "52099967-34a8-419b-8950-c859eab60145",
  },
);
export const checkStatusEvent = workflowEvent<string>({
  debugLabel: "check-status",
  uniqueId: "462157fc-1ded-4ba7-9bc4-3e870395bd20",
});
export const checkStatusSuccessEvent = workflowEvent<string>({
  debugLabel: "check-status-success",
  uniqueId: "360b7641-30f7-456e-851d-104bb5e3f8d2",
});
export const requestMarkdownEvent = workflowEvent<string>({
  debugLabel: "markdown-request",
  uniqueId: "aa4c2e3c-0f09-4035-aab6-c72719c877cc",
});
export const requestTextEvent = workflowEvent<string>({
  debugLabel: "text-request",
  uniqueId: "6976536e-5399-4285-9455-0b70f1dfc92b",
});
export const requestJsonEvent = workflowEvent<string>({
  debugLabel: "json-request",
  uniqueId: "9fc4a330-52ad-4aac-8092-a650998b7f6f",
});

export const markdownResultEvent = workflowEvent<string>({
  debugLabel: "markdown-result",
  uniqueId: "2dfb57c8-73d1-4394-bea8-f05246d934d4",
});
export const textResultEvent = workflowEvent<string>({
  debugLabel: "text-result",
  uniqueId: "a27deec6-b24f-4eda-a5ac-ba2fb2bf37c8",
});
export const jsonResultEvent = workflowEvent<unknown>({
  debugLabel: "json-result",
  uniqueId: "e086e6bd-a612-4f25-ab41-9b31dcb8af86",
});
