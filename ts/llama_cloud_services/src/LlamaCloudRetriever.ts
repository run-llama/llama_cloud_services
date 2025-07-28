import {
  type MetadataFilter,
  type MetadataFilters,
  type RetrievalParams,
  runSearchApiV1PipelinesPipelineIdRetrievePost,
  type TextNodeWithScore,
} from "./api";
import { DEFAULT_PROJECT_NAME } from "@llamaindex/core/global";
import type { QueryBundle } from "@llamaindex/core/query-engine";
import { BaseRetriever } from "@llamaindex/core/retriever";
import type { NodeWithScore } from "@llamaindex/core/schema";
import { jsonToNode, ObjectType } from "@llamaindex/core/schema";
import { extractText } from "@llamaindex/core/utils";
import type { ClientParams, CloudConstructorParams } from "./type.js";
import { getPipelineId, initService } from "./utils.js";

export type CloudRetrieveParams = Omit<
  RetrievalParams,
  "query" | "search_filters" | "dense_similarity_top_k"
> & { similarityTopK?: number; filters?: MetadataFilters };

export class LlamaCloudRetriever extends BaseRetriever {
  clientParams: ClientParams;
  retrieveParams: CloudRetrieveParams;
  organizationId?: string;
  projectName: string = DEFAULT_PROJECT_NAME;
  pipelineName: string;

  private resultNodesToNodeWithScore(
    nodes: TextNodeWithScore[],
  ): NodeWithScore[] {
    return nodes.map((node: TextNodeWithScore) => {
      const textNode = jsonToNode(node.node, ObjectType.TEXT);
      textNode.metadata = {
        ...textNode.metadata,
        ...node.node.extra_info, // append LlamaCloud extra_info to node metadata (file_name, pipeline_id, etc.)
      };
      return {
        // Currently LlamaCloud only supports text nodes
        node: textNode,
        score: node.score ?? undefined,
      };
    });
  }

  // LlamaCloud expects null values for filters, but LlamaIndexTS uses undefined for empty values
  // This function converts the undefined values to null
  private convertFilter(filters?: MetadataFilters): MetadataFilters | null {
    if (!filters) return null;

    const processFilter = (
      filter: MetadataFilter | MetadataFilters,
    ): MetadataFilter | MetadataFilters => {
      if ("filters" in filter) {
        // type MetadataFilters
        return { ...filter, filters: filter.filters.map(processFilter) };
      }
      return { ...filter, value: filter.value ?? null };
    };

    return { ...filters, filters: filters.filters.map(processFilter) };
  }

  constructor(params: CloudConstructorParams & CloudRetrieveParams) {
    super();
    this.clientParams = { apiKey: params.apiKey, baseUrl: params.baseUrl };
    initService(this.clientParams);
    this.retrieveParams = params;
    this.pipelineName = params.name;
    if (params.projectName) {
      this.projectName = params.projectName;
    }
    if (params.organizationId) {
      this.organizationId = params.organizationId;
    }
  }

  async _retrieve(query: QueryBundle): Promise<NodeWithScore[]> {
    const pipelineId = await getPipelineId(
      this.pipelineName,
      this.projectName,
      this.organizationId,
    );

    const filters = this.convertFilter(this.retrieveParams.filters);

    const { data: results } =
      await runSearchApiV1PipelinesPipelineIdRetrievePost({
        throwOnError: true,
        path: {
          pipeline_id: pipelineId,
        },
        body: {
          ...this.retrieveParams,
          query: extractText(query),
          search_filters: filters,
          dense_similarity_top_k: this.retrieveParams.similarityTopK!,
        },
      });

    return this.resultNodesToNodeWithScore(results.retrieval_nodes);
  }
}
