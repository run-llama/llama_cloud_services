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
import { jsonToNode, ObjectType, ImageNode } from "@llamaindex/core/schema";
import { extractText } from "@llamaindex/core/utils";
import type { ClientParams, CloudConstructorParams } from "./type.js";
import { getPipelineId, getProjectId, initService } from "./utils.js";
import {
  type PageScreenshotNodeWithScore,
  type PageFigureNodeWithScore,
  generateFilePageScreenshotPresignedUrlApiV1FilesIdPageScreenshotsPageIndexPresignedUrlPost,
  generateFilePageFigurePresignedUrlApiV1FilesIdPageFiguresPageIndexFigureNamePresignedUrlPost,
} from "./api";

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
    metadata: Record<string, string> | undefined,
  ): NodeWithScore[] {
    return nodes.map((node: TextNodeWithScore) => {
      const textNode = jsonToNode(node.node, ObjectType.TEXT);
      const extra_metadata = metadata || {};
      textNode.metadata = {
        ...textNode.metadata,
        ...node.node.extra_info, // append LlamaCloud extra_info to node metadata (file_name, pipeline_id, etc.)
        ...extra_metadata, // append retrieval-level metadata
      };
      return {
        // Currently LlamaCloud only supports text nodes
        node: textNode,
        score: node.score ?? undefined,
      };
    });
  }

  private async fetchBase64FromPresignedUrl(url: string): Promise<string> {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(
        `Failed to fetch media from presigned URL: ${response.status} ${response.statusText}`,
      );
    }
    const buffer = Buffer.from(await response.arrayBuffer());
    return buffer.toString("base64");
  }

  private async pageScreenshotNodesToNodeWithScore(
    nodes: PageScreenshotNodeWithScore[] | undefined,
    projectId: string,
    metadata: Record<string, string> | undefined,
  ): Promise<NodeWithScore[]> {
    if (!nodes || nodes.length === 0) return [];

    const results = await Promise.all(
      nodes.map(async (n) => {
        const { data: presigned } =
          await generateFilePageScreenshotPresignedUrlApiV1FilesIdPageScreenshotsPageIndexPresignedUrlPost(
            {
              throwOnError: true,
              path: {
                id: n.node.file_id,
                page_index: n.node.page_index,
              },
              query: {
                project_id: projectId,
                organization_id: this.organizationId ?? null,
              },
            },
          );
        const base64 = await this.fetchBase64FromPresignedUrl(presigned.url);
        const imageNode = new ImageNode({
          image: base64,
          metadata: {
            ...(n.node.metadata ?? {}),
            ...(metadata || {}),
            file_id: n.node.file_id,
            page_index: n.node.page_index,
          },
        });
        return { node: imageNode, score: n.score } satisfies NodeWithScore;
      }),
    );

    return results;
  }

  private async pageFigureNodesToNodeWithScore(
    nodes: PageFigureNodeWithScore[] | undefined,
    projectId: string,
    metadata: Record<string, string> | undefined,
  ): Promise<NodeWithScore[]> {
    if (!nodes || nodes.length === 0) return [];

    const results = await Promise.all(
      nodes.map(async (n) => {
        const { data: presigned } =
          await generateFilePageFigurePresignedUrlApiV1FilesIdPageFiguresPageIndexFigureNamePresignedUrlPost(
            {
              throwOnError: true,
              path: {
                id: n.node.file_id,
                page_index: n.node.page_index,
                figure_name: n.node.figure_name,
              },
              query: {
                project_id: projectId,
                organization_id: this.organizationId ?? null,
              },
            },
          );
        const base64 = await this.fetchBase64FromPresignedUrl(presigned.url);
        const imageNode = new ImageNode({
          image: base64,
          metadata: {
            ...(n.node.metadata ?? {}),
            ...(metadata || {}),
            file_id: n.node.file_id,
            page_index: n.node.page_index,
            figure_name: n.node.figure_name,
          },
        });
        return { node: imageNode, score: n.score } satisfies NodeWithScore;
      }),
    );

    return results;
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
    // Handle deprecated image retrieval flag
    const retrieveImageNodes = (this.retrieveParams as RetrievalParams)
      .retrieve_image_nodes;
    if (typeof retrieveImageNodes !== "undefined") {
      console.warn(
        "The `retrieve_image_nodes` parameter is deprecated. Use `retrieve_page_screenshot_nodes` and `retrieve_page_figure_nodes` instead.",
      );
    }

    const retrievePageScreenshotNodes = (this.retrieveParams as RetrievalParams)
      .retrieve_page_screenshot_nodes;
    const retrievePageFigureNodes = (this.retrieveParams as RetrievalParams)
      .retrieve_page_figure_nodes;

    if (retrieveImageNodes) {
      if (
        retrievePageScreenshotNodes === false ||
        retrievePageFigureNodes === false
      ) {
        throw new Error(
          "If `retrieve_image_nodes` is set to true, both `retrieve_page_screenshot_nodes` and `retrieve_page_figure_nodes` must also be set to true or omitted.",
        );
      }
      (this.retrieveParams as RetrievalParams).retrieve_page_screenshot_nodes =
        true;
      (this.retrieveParams as RetrievalParams).retrieve_page_figure_nodes =
        true;
    }

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

    const textNodes = this.resultNodesToNodeWithScore(
      results.retrieval_nodes,
      results.metadata,
    );

    const needScreenshots = (this.retrieveParams as RetrievalParams)
      .retrieve_page_screenshot_nodes;
    const needFigures = (this.retrieveParams as RetrievalParams)
      .retrieve_page_figure_nodes;

    if (!needScreenshots && !needFigures) {
      return textNodes;
    }

    const projectId = await getProjectId(this.projectName, this.organizationId);

    const [screenshotNodes, figureNodes] = await Promise.all([
      needScreenshots
        ? this.pageScreenshotNodesToNodeWithScore(
            results.image_nodes,
            projectId,
            results.metadata,
          )
        : Promise.resolve([] as NodeWithScore[]),
      needFigures
        ? this.pageFigureNodesToNodeWithScore(
            results.page_figure_nodes,
            projectId,
            results.metadata,
          )
        : Promise.resolve([] as NodeWithScore[]),
    ]);

    return [...textNodes, ...screenshotNodes, ...figureNodes];
  }
}
