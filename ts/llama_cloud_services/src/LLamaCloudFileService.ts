import {
  addFilesToPipelineApiApiV1PipelinesPipelineIdFilesPut,
  getPipelineFileStatusApiV1PipelinesPipelineIdFilesFileIdStatusGet,
  listPipelineFiles2ApiV1PipelinesPipelineIdFiles2Get,
  listProjectsApiV1ProjectsGet,
  readFileContentApiV1FilesIdContentGet,
  searchPipelinesApiV1PipelinesGet,
  uploadFileApiV1FilesPost,
} from "./api";
import { initService } from "./utils.js";

export class LLamaCloudFileService {
  /**
   * Get list of projects, each project contains a list of pipelines
   */
  public static async getAllProjectsWithPipelines() {
    initService();
    try {
      const { data: projects } = await listProjectsApiV1ProjectsGet({
        throwOnError: true,
      });
      const { data: pipelines } = await searchPipelinesApiV1PipelinesGet({
        throwOnError: true,
      });
      return projects.map((project) => ({
        ...project,
        pipelines: pipelines.filter((p) => p.project_id === project.id),
      }));
    } catch (error) {
      console.error("Error listing projects and pipelines:", error);
      return [];
    }
  }

  /**
   * Upload a file to a pipeline in LlamaCloud
   */
  public static async addFileToPipeline(
    projectId: string,
    pipelineId: string,
    uploadFile: File | Blob,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    customMetadata: Record<string, any> = {},
  ) {
    initService();
    const { data: file } = await uploadFileApiV1FilesPost({
      query: { project_id: projectId },
      body: {
        upload_file: uploadFile,
      },
      throwOnError: true,
    });
    const files = [
      {
        file_id: file.id,
        custom_metadata: { file_id: file.id, ...customMetadata },
      },
    ];
    await addFilesToPipelineApiApiV1PipelinesPipelineIdFilesPut({
      path: {
        pipeline_id: pipelineId,
      },
      body: files,
    });

    // Wait 2s for the file to be processed
    const maxAttempts = 20;
    let attempt = 0;
    while (attempt < maxAttempts) {
      const { data: result } =
        await getPipelineFileStatusApiV1PipelinesPipelineIdFilesFileIdStatusGet(
          {
            path: {
              pipeline_id: pipelineId,
              file_id: file.id,
            },
            throwOnError: true,
          },
        );
      if (result.status === "ERROR") {
        throw new Error(`File processing failed: ${JSON.stringify(result)}`);
      }
      if (result.status === "SUCCESS") {
        // File is ingested - return the file id
        return file.id;
      }
      attempt += 1;
      await new Promise((resolve) => setTimeout(resolve, 100)); // Sleep for 100ms
    }
    throw new Error(
      `File processing did not complete after ${maxAttempts} attempts. Check your LlamaCloud index at https://cloud.llamaindex.ai/project/${projectId}/deploy/${pipelineId} for more details.`,
    );
  }

  /**
   * Get download URL for a file in LlamaCloud
   */
  public static async getFileUrl(pipelineId: string, filename: string) {
    initService();
    const response = await listPipelineFiles2ApiV1PipelinesPipelineIdFiles2Get({
      path: {
        pipeline_id: pipelineId,
      },
      throwOnError: true,
    });
    const file = response.data.files.find((file) => file.name === filename);
    if (!file?.file_id) return null;
    const { data: fileContent } = await readFileContentApiV1FilesIdContentGet({
      path: {
        id: file.file_id,
      },
      query: {
        project_id: file.project_id || null,
      },
      throwOnError: true,
    });
    return fileContent.url;
  }
}
