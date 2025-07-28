import type { BaseNodePostprocessor } from "@llamaindex/core/postprocessor";
import type { BaseQueryEngine } from "@llamaindex/core/query-engine";
import type { BaseSynthesizer } from "@llamaindex/core/response-synthesizers";
import type { Document } from "@llamaindex/core/schema";
import { RetrieverQueryEngine } from "../engines/query/RetrieverQueryEngine.js";
import type { CloudRetrieveParams } from "./LlamaCloudRetriever.js";
import { LlamaCloudRetriever } from "./LlamaCloudRetriever.js";
import type { CloudConstructorParams } from "./type.js";
import {
  getAppBaseUrl,
  getPipelineId,
  getProjectId,
  initService,
} from "./utils.js";

import {
  createBatchPipelineDocumentsApiV1PipelinesPipelineIdDocumentsPost,
  deletePipelineDocumentApiV1PipelinesPipelineIdDocumentsDocumentIdDelete,
  getPipelineDocumentStatusApiV1PipelinesPipelineIdDocumentsDocumentIdStatusGet,
  getPipelineStatusApiV1PipelinesPipelineIdStatusGet,
  type PipelineCreateReadable,
  searchPipelinesApiV1PipelinesGet,
  upsertBatchPipelineDocumentsApiV1PipelinesPipelineIdDocumentsPut,
  upsertPipelineApiV1PipelinesPut,
} from "@llamaindex/cloud/api";
import type { BaseRetriever } from "@llamaindex/core/retriever";
import { getEnv } from "@llamaindex/env";
import type { QueryToolParams } from "../indices/BaseIndex.js";
import { Settings } from "../Settings.js";
import { QueryEngineTool } from "../tools/QueryEngineTool.js";

export class LlamaCloudIndex {
  params: CloudConstructorParams;

  constructor(params: CloudConstructorParams) {
    this.params = params;
    initService(this.params);
  }

  private async waitForPipelineIngestion(
    verbose = Settings.debug,
    raiseOnError = false,
  ): Promise<void> {
    const pipelineId = await this.getPipelineId();

    if (verbose) {
      console.log("Waiting for pipeline ingestion: ");
    }

    while (true) {
      const { data: pipelineStatus } =
        await getPipelineStatusApiV1PipelinesPipelineIdStatusGet({
          path: {
            pipeline_id: pipelineId,
          },
          throwOnError: true,
        });

      if (pipelineStatus.status === "SUCCESS") {
        if (verbose) {
          console.log("Pipeline ingestion completed successfully");
        }
        break;
      }

      if (pipelineStatus.status === "ERROR") {
        if (verbose) {
          console.error("Pipeline ingestion failed");
        }

        if (raiseOnError) {
          throw new Error("Pipeline ingestion failed");
        }
      }

      if (verbose) {
        process.stdout.write(".");
      }

      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }

  private async waitForDocumentIngestion(
    docIds: string[],
    verbose = Settings.debug,
    raiseOnError = false,
  ): Promise<void> {
    const pipelineId = await this.getPipelineId();

    if (verbose) {
      console.log("Loading data: ");
    }

    const pendingDocs = new Set(docIds);

    while (pendingDocs.size) {
      const docsToRemove = new Set<string>();

      for (const doc of pendingDocs) {
        const {
          data: { status },
        } =
          await getPipelineDocumentStatusApiV1PipelinesPipelineIdDocumentsDocumentIdStatusGet(
            {
              path: { pipeline_id: pipelineId, document_id: doc },
              throwOnError: true,
            },
          );

        if (status === "NOT_STARTED" || status === "IN_PROGRESS") {
          continue;
        }

        if (status === "ERROR") {
          if (verbose) {
            console.error(`Document ingestion failed for ${doc}`);
          }

          if (raiseOnError) {
            throw new Error(`Document ingestion failed for ${doc}`);
          }
        }

        docsToRemove.add(doc);
      }

      for (const doc of docsToRemove) {
        pendingDocs.delete(doc);
      }

      if (pendingDocs.size) {
        if (verbose) {
          process.stdout.write(".");
        }

        await new Promise((resolve) => setTimeout(resolve, 500));
      }
    }

    if (verbose) {
      console.log("Done!");
    }

    await this.waitForPipelineIngestion(verbose, raiseOnError);
  }

  public async getPipelineId(
    name?: string,
    projectName?: string,
    organizationId?: string,
  ): Promise<string> {
    return await getPipelineId(
      name ?? this.params.name,
      projectName ?? this.params.projectName,
      organizationId ?? this.params.organizationId,
    );
  }

  public async getProjectId(
    projectName?: string,
    organizationId?: string,
  ): Promise<string> {
    return await getProjectId(
      projectName ?? this.params.projectName,
      organizationId ?? this.params.organizationId,
    );
  }

  /**
   * Adds documents to the given index parameters. If the index does not exist, it will be created.
   *
   * @param params - An object containing the following properties:
   *   - documents: An array of Document objects to be added to the index.
   *   - verbose: Optional boolean to enable verbose logging.
   *   - Additional properties from CloudConstructorParams.
   * @returns A Promise that resolves to a new LlamaCloudIndex instance.
   */
  static async fromDocuments(
    params: {
      documents: Document[];
      verbose?: boolean;
    } & CloudConstructorParams,
    config?: {
      embedding: PipelineCreateReadable["embedding_config"];
      transform: PipelineCreateReadable["transform_config"];
    },
  ): Promise<LlamaCloudIndex> {
    const index = new LlamaCloudIndex({ ...params });
    await index.ensureIndex({ ...config, verbose: params.verbose ?? false });
    await index.addDocuments(params.documents, params.verbose);
    return index;
  }

  async addDocuments(documents: Document[], verbose?: boolean): Promise<void> {
    const apiUrl = getAppBaseUrl();
    const projectId = await this.getProjectId();
    const pipelineId = await this.getPipelineId();

    await upsertBatchPipelineDocumentsApiV1PipelinesPipelineIdDocumentsPut({
      path: {
        pipeline_id: pipelineId,
      },
      body: documents.map((doc) => ({
        metadata: doc.metadata,
        text: doc.text,
        excluded_embed_metadata_keys: doc.excludedEmbedMetadataKeys,
        excluded_llm_metadata_keys: doc.excludedEmbedMetadataKeys,
        id: doc.id_,
      })),
    });

    while (true) {
      const { data: pipelineStatus } =
        await getPipelineStatusApiV1PipelinesPipelineIdStatusGet({
          path: { pipeline_id: pipelineId },
          throwOnError: true,
        });

      if (pipelineStatus.status === "SUCCESS") {
        console.info(
          "Documents ingested successfully, pipeline is ready to use",
        );
        break;
      }

      if (pipelineStatus.status === "ERROR") {
        console.error(
          `Some documents failed to ingest, check your pipeline logs at ${apiUrl}/project/${projectId}/deploy/${pipelineId}`,
        );
        throw new Error("Some documents failed to ingest");
      }

      if (pipelineStatus.status === "PARTIAL_SUCCESS") {
        console.info(
          `Documents ingestion partially succeeded, to check a more complete status check your pipeline at ${apiUrl}/project/${projectId}/deploy/${pipelineId}`,
        );
        break;
      }

      if (verbose) {
        process.stdout.write(".");
      }

      await new Promise((resolve) => setTimeout(resolve, 1000));
    }

    if (verbose) {
      console.info(
        `Ingestion completed, find your index at ${apiUrl}/project/${projectId}/deploy/${pipelineId}`,
      );
    }
  }

  asRetriever(params: CloudRetrieveParams = {}): BaseRetriever {
    return new LlamaCloudRetriever({ ...this.params, ...params });
  }

  asQueryEngine(
    params?: {
      responseSynthesizer?: BaseSynthesizer;
      preFilters?: unknown;
      nodePostprocessors?: BaseNodePostprocessor[];
    } & CloudRetrieveParams,
  ): BaseQueryEngine {
    const retriever = new LlamaCloudRetriever({
      ...this.params,
      ...params,
    });
    return new RetrieverQueryEngine(
      retriever,
      params?.responseSynthesizer,
      params?.nodePostprocessors,
    );
  }

  asQueryTool(params: QueryToolParams): QueryEngineTool {
    if (params.options) {
      params.retriever = this.asRetriever(params.options);
    }

    return new QueryEngineTool({
      queryEngine: this.asQueryEngine(params),
      metadata: params?.metadata,
      includeSourceNodes: params?.includeSourceNodes ?? false,
    });
  }

  queryTool(params: QueryToolParams): QueryEngineTool {
    return this.asQueryTool(params);
  }

  async insert(document: Document) {
    const pipelineId = await this.getPipelineId();

    await createBatchPipelineDocumentsApiV1PipelinesPipelineIdDocumentsPost({
      path: {
        pipeline_id: pipelineId,
      },
      body: [
        {
          metadata: document.metadata,
          text: document.text,
          excluded_embed_metadata_keys: document.excludedLlmMetadataKeys,
          excluded_llm_metadata_keys: document.excludedEmbedMetadataKeys,
          id: document.id_,
        },
      ],
    });

    await this.waitForDocumentIngestion([document.id_]);
  }

  async delete(document: Document) {
    const pipelineId = await this.getPipelineId();

    await deletePipelineDocumentApiV1PipelinesPipelineIdDocumentsDocumentIdDelete(
      {
        path: {
          pipeline_id: pipelineId,
          document_id: document.id_,
        },
      },
    );

    await this.waitForPipelineIngestion();
  }

  async refreshDoc(document: Document) {
    const pipelineId = await this.getPipelineId();

    await upsertBatchPipelineDocumentsApiV1PipelinesPipelineIdDocumentsPut({
      path: {
        pipeline_id: pipelineId,
      },
      body: [
        {
          metadata: document.metadata,
          text: document.text,
          excluded_embed_metadata_keys: document.excludedLlmMetadataKeys,
          excluded_llm_metadata_keys: document.excludedEmbedMetadataKeys,
          id: document.id_,
        },
      ],
    });

    await this.waitForDocumentIngestion([document.id_]);
  }

  public async ensureIndex(config?: {
    embedding?: PipelineCreateReadable["embedding_config"];
    transform?: PipelineCreateReadable["transform_config"];
    verbose?: boolean;
  }): Promise<void> {
    const projectId = await this.getProjectId();

    const { data: pipelines } = await searchPipelinesApiV1PipelinesGet({
      query: {
        project_id: projectId,
        pipeline_name: this.params.name,
      },
      throwOnError: true,
    });

    if (pipelines.length === 0) {
      // no pipeline found, create a new one
      let embeddingConfig = config?.embedding;
      if (!embeddingConfig) {
        // no embedding config provided, use OpenAI as default
        const openAIApiKey = getEnv("OPENAI_API_KEY");
        const embeddingModel = getEnv("EMBEDDING_MODEL");
        if (!openAIApiKey || !embeddingModel) {
          throw new Error(
            "No embedding configuration provided. Fallback to OpenAI embedding model. OPENAI_API_KEY and EMBEDDING_MODEL environment variables must be set.",
          );
        }
        embeddingConfig = {
          type: "OPENAI_EMBEDDING",
          component: {
            api_key: openAIApiKey,
            model_name: embeddingModel,
          },
        };
      }

      let transformConfig = config?.transform;
      if (!transformConfig) {
        transformConfig = {
          mode: "auto",
          chunk_size: 1024,
          chunk_overlap: 200,
        };
      }

      const { data: pipeline } = await upsertPipelineApiV1PipelinesPut({
        query: {
          project_id: projectId,
        },
        body: {
          name: this.params.name,
          embedding_config: embeddingConfig,
          transform_config: transformConfig,
        },
        throwOnError: true,
      });

      if (config?.verbose) {
        console.log(
          `Created pipeline ${pipeline.id} with name ${pipeline.name}`,
        );
      }
    }
  }
}
