import type { BaseSynthesizer } from "@llamaindex/core/response-synthesizers";
import type { BaseRetriever } from "@llamaindex/core/retriever";
import type { JSONValue } from "@llamaindex/core/global";
import type { BaseTool, ToolMetadata } from "@llamaindex/core/llms";
import type { BaseQueryEngine } from "@llamaindex/core/query-engine";
import type { JSONSchemaType } from "ajv";

export type QueryEngineParam = {
  query: string;
};

export type QueryToolParams = (
  | {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      options: any;
      retriever?: never;
    }
  | {
      options?: never;
      retriever?: BaseRetriever;
    }
) & {
  responseSynthesizer?: BaseSynthesizer;
  metadata?: ToolMetadata<JSONSchemaType<QueryEngineParam>> | undefined;
  includeSourceNodes?: boolean;
};

const DEFAULT_NAME = "query_engine_tool";
const DEFAULT_DESCRIPTION =
  "Useful for running a natural language query against a knowledge base and get back a natural language response.";

const DEFAULT_PARAMETERS: JSONSchemaType<QueryEngineParam> = {
  type: "object",
  properties: {
    query: {
      type: "string",
      description: "The query to search for",
    },
  },
  required: ["query"],
};

export type QueryEngineToolParams = {
  queryEngine: BaseQueryEngine;
  metadata?: ToolMetadata<JSONSchemaType<QueryEngineParam>> | undefined;
  includeSourceNodes?: boolean;
};

export class QueryEngineTool implements BaseTool<QueryEngineParam> {
  private queryEngine: BaseQueryEngine;
  metadata: ToolMetadata<JSONSchemaType<QueryEngineParam>>;
  includeSourceNodes: boolean;

  constructor({
    queryEngine,
    metadata,
    includeSourceNodes,
  }: QueryEngineToolParams) {
    this.queryEngine = queryEngine;
    this.metadata = {
      name: metadata?.name ?? DEFAULT_NAME,
      description: metadata?.description ?? DEFAULT_DESCRIPTION,
      parameters: metadata?.parameters ?? DEFAULT_PARAMETERS,
    };
    this.includeSourceNodes = includeSourceNodes ?? false;
  }

  async call({ query }: QueryEngineParam) {
    const response = await this.queryEngine.query({ query });

    if (!this.includeSourceNodes) {
      return { content: response.message.content } as unknown as JSONValue;
    }

    return {
      content: response.message.content,
      sourceNodes: response.sourceNodes,
    } as unknown as JSONValue;
  }
}
