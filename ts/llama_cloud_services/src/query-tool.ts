import type { JSONValue } from "@llamaindex/core/global";
import type { ToolMetadata } from "@llamaindex/core/llms";
import type { BaseQueryEngine } from "@llamaindex/core/query-engine";
import { tool } from "@llamaindex/core/tools";
import { z } from "zod";

const DEFAULT_NAME = "llama_cloud_index_tool";
const DEFAULT_DESCRIPTION =
  "Useful for retrieving relevant information from document stored in a LlamaCloud Index";

export type QueryToolParams = {
  metadata?: Omit<ToolMetadata, "parameters"> | undefined;
  includeSourceNodes?: boolean;
};

export function createQueryEngineTool(
  options: { queryEngine: BaseQueryEngine } & QueryToolParams,
) {
  const { queryEngine, metadata, includeSourceNodes } = options;
  return tool({
    name: metadata?.name ?? DEFAULT_NAME,
    description: metadata?.description ?? DEFAULT_DESCRIPTION,
    parameters: z.object({
      query: z.string({
        description: "The query to search for",
      }),
    }),
    execute: async ({ query }) => {
      const response = await queryEngine.query({ query });
      if (!includeSourceNodes) {
        return { content: response.message.content } as unknown as JSONValue;
      }
      return {
        content: response.message.content,
        sourceNodes: response.sourceNodes,
      } as unknown as JSONValue;
    },
  });
}
