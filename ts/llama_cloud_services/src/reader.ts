/* eslint-disable @typescript-eslint/no-explicit-any */
import { type Client, createClient, createConfig } from "@hey-api/client-fetch";
import { Document, FileReader } from "@llamaindex/core/schema";
import { fs, getEnv, path } from "@llamaindex/env";
import {
  type BodyUploadFileApiParsingUploadPost,
  type FailPageMode,
  type ParserLanguages,
  type ParsingMode,
  getJobApiV1ParsingJobJobIdGet,
  getJobImageResultApiV1ParsingJobJobIdResultImageNameGet,
  getJobJsonResultApiV1ParsingJobJobIdResultJsonGet,
  getJobResultApiV1ParsingJobJobIdResultMarkdownGet,
  getJobTextResultApiV1ParsingJobJobIdResultTextGet,
  uploadFileApiV1ParsingUploadPost,
} from "./api";
import { sleep } from "./utils";

export type Language = ParserLanguages;
export type ResultType = "text" | "markdown" | "json";

// Export the backoff pattern type.
export type BackoffPattern = "constant" | "linear" | "exponential";

// TODO: should move into @llamaindex/env
type WriteStream = {
  write: (text: string) => void;
};

// Do not modify this variable or cause type errors
// eslint-disable-next-line no-var
var process: any;

/**
 * Represents a reader for parsing files using the LlamaParse API.
 * See https://github.com/run-llama/llama_parse
 */
export class LlamaParseReader extends FileReader {
  project_id?: string | undefined;
  organization_id?: string | undefined;
  // The API key for the LlamaParse API. Can be set as an environment variable: LLAMA_CLOUD_API_KEY
  apiKey: string;
  // The base URL of the Llama Cloud Platform.
  baseUrl: string = "https://api.cloud.llamaindex.ai";
  // The result type for the parser.
  resultType: ResultType = "text";
  // The interval in seconds to check if the parsing is done.
  checkInterval: number = 1;
  // The maximum timeout in seconds to wait for the parsing to finish.
  maxTimeout = 2000;
  // Whether to print the progress of the parsing.
  verbose = true;
  // The language to parse the file in.
  language: ParserLanguages[] = ["en"];

  // New polling options:
  // Controls the backoff mode: "constant", "linear", or "exponential".
  backoffPattern: BackoffPattern = "linear";
  // Maximum interval in seconds between polls.
  maxCheckInterval: number = 5;
  // Maximum number of retryable errors before giving up.
  maxErrorCount: number = 4;

  // The parsing instruction for the parser. Backend default is an empty string.
  parsingInstruction?: string | undefined;
  // Whether to ignore diagonal text (when the text rotation in degrees is not 0, 90, 180, or 270). Backend default is false.
  skipDiagonalText?: boolean | undefined;
  // Whether to ignore the cache and re-process the document. Documents are cached for 48 hours after job completion. Backend default is false.
  invalidateCache?: boolean | undefined;
  // Whether the document should not be cached. Backend default is false.
  doNotCache?: boolean | undefined;
  // Whether to use a faster mode to extract text (skipping OCR and table/heading reconstruction). Not compatible with gpt4oMode. Backend default is false.
  fastMode?: boolean | undefined;
  // Whether to keep columns in the text according to document layout. May reduce reconstruction accuracy and LLM/embedings performance.
  doNotUnrollColumns?: boolean | undefined;
  // A templated page separator for splitting text. If not set, default is "\n---\n".
  pageSeparator?: string | undefined;
  // A templated prefix to add at the beginning of each page.
  pagePrefix?: string | undefined;
  // A templated suffix to add at the end of each page.
  pageSuffix?: string | undefined;
  // Deprecated. Use vendorMultimodal params. Whether to use gpt-4o to extract text.
  gpt4oMode: boolean = false;
  // Deprecated. Use vendorMultimodal params. The API key for GPT-4o. Can be set via LLAMA_CLOUD_GPT4O_API_KEY.
  gpt4oApiKey?: string | undefined;
  // The bounding box margins as a string.
  boundingBox?: string | undefined;
  // The target pages (comma separated list, starting at 0).
  targetPages?: string | undefined;
  // Whether to ignore errors during parsing.
  ignoreErrors: boolean = true;
  // Whether to split by page using the pageSeparator (or "\n---\n" as default).
  splitByPage: boolean = true;
  // Whether to use the vendor multimodal API.
  useVendorMultimodalModel: boolean = false;
  // The model name for the vendor multimodal API.
  vendorMultimodalModelName?: string | undefined;
  // The API key for the multimodal API. Can be set via LLAMA_CLOUD_VENDOR_MULTIMODAL_API_KEY.
  vendorMultimodalApiKey?: string | undefined;

  webhookUrl?: string | undefined;
  premiumMode?: boolean | undefined;
  takeScreenshot?: boolean | undefined;
  disableOcr?: boolean | undefined;
  disableReconstruction?: boolean | undefined;
  inputS3Path?: string | undefined;
  outputS3PathPrefix?: string | undefined;
  continuousMode?: boolean | undefined;
  isFormattingInstruction?: boolean | undefined;
  annotateLinks?: boolean | undefined;
  azureOpenaiDeploymentName?: string | undefined;
  azureOpenaiEndpoint?: string | undefined;
  azureOpenaiApiVersion?: string | undefined;
  azureOpenaiKey?: string | undefined;
  auto_mode?: boolean | undefined;
  auto_mode_trigger_on_image_in_page?: boolean | undefined;
  auto_mode_trigger_on_table_in_page?: boolean | undefined;
  auto_mode_trigger_on_text_in_page?: string | undefined;
  auto_mode_trigger_on_regexp_in_page?: string | undefined;
  bbox_bottom?: number | undefined;
  bbox_left?: number | undefined;
  bbox_right?: number | undefined;
  bbox_top?: number | undefined;
  disable_image_extraction?: boolean | undefined;
  extract_charts?: boolean | undefined;
  guess_xlsx_sheet_name?: boolean | undefined;
  html_make_all_elements_visible?: boolean | undefined;
  html_remove_fixed_elements?: boolean | undefined;
  html_remove_navigation_elements?: boolean | undefined;
  http_proxy?: string | undefined;
  input_url?: string | undefined;
  max_pages?: number | undefined;
  output_pdf_of_document?: boolean | undefined;
  structured_output?: boolean | undefined;
  structured_output_json_schema?: string | undefined;
  structured_output_json_schema_name?: string | undefined;
  extract_layout?: boolean | undefined;

  // numWorkers is implemented in SimpleDirectoryReader
  stdout?: WriteStream | undefined;

  readonly #client: Client;

  output_tables_as_HTML: boolean = false;
  input_s3_region?: string | undefined;
  output_s3_region?: string | undefined;
  preserve_layout_alignment_across_pages?: boolean | undefined;
  spreadsheet_extract_sub_tables?: boolean | undefined;
  formatting_instruction?: string | undefined;
  parse_mode?: ParsingMode | undefined;
  system_prompt?: string | undefined;
  system_prompt_append?: string | undefined;
  user_prompt?: string | undefined;
  job_timeout_in_seconds?: number | undefined;
  job_timeout_extra_time_per_page_in_seconds?: number | undefined;
  strict_mode_image_extraction?: boolean | undefined;
  strict_mode_image_ocr?: boolean | undefined;
  strict_mode_reconstruction?: boolean | undefined;
  strict_mode_buggy_font?: boolean | undefined;
  ignore_document_elements_for_layout_detection?: boolean | undefined;
  complemental_formatting_instruction?: string | undefined;
  content_guideline_instruction?: string | undefined;
  adaptive_long_table?: boolean | undefined;
  model?: string | undefined;
  auto_mode_configuration_json?: string | undefined;
  compact_markdown_table?: boolean | undefined;
  markdown_table_multiline_header_separator?: string | undefined;
  page_error_tolerance?: number | undefined;
  replace_failed_page_mode?: FailPageMode | undefined;
  replace_failed_page_with_error_message_prefix?: string | undefined;
  replace_failed_page_with_error_message_suffix?: string | undefined;
  save_images?: boolean | undefined;
  preset?: string | undefined;
  high_res_ocr?: boolean | undefined;
  outlined_table_extraction?: boolean | undefined;
  hide_headers?: boolean | undefined;
  hide_footers?: boolean | undefined;
  page_header_prefix?: string | undefined;
  page_header_suffix?: string | undefined;
  page_footer_prefix?: string | undefined;
  page_footer_suffix?: string | undefined;
  merge_tables_across_pages_in_markdown?: boolean | undefined;

  constructor(
    params: Partial<Omit<LlamaParseReader, "language" | "apiKey">> & {
      language?: ParserLanguages | ParserLanguages[] | undefined;
      apiKey?: string | undefined;
    } = {},
  ) {
    super();
    Object.assign(this, params);
    this.language = Array.isArray(this.language)
      ? this.language
      : [this.language];
    this.stdout =
      params.stdout ?? typeof process !== "undefined"
        ? process!.stdout
        : undefined;
    const apiKey = params.apiKey ?? getEnv("LLAMA_CLOUD_API_KEY");
    if (!apiKey) {
      throw new Error(
        "API Key is required for LlamaParseReader. Please pass the apiKey parameter or set the LLAMA_CLOUD_API_KEY environment variable.",
      );
    }
    this.apiKey = apiKey;
    if (this.baseUrl.endsWith("/")) {
      this.baseUrl = this.baseUrl.slice(0, -1);
    }
    if (this.baseUrl.endsWith("/api/parsing")) {
      this.baseUrl = this.baseUrl.slice(0, -"/api/parsing".length);
    }

    if (params.gpt4oMode) {
      params.gpt4oApiKey =
        params.gpt4oApiKey ?? getEnv("LLAMA_CLOUD_GPT4O_API_KEY");

      this.gpt4oApiKey = params.gpt4oApiKey;
    }
    if (params.useVendorMultimodalModel) {
      params.vendorMultimodalApiKey =
        params.vendorMultimodalApiKey ??
        getEnv("LLAMA_CLOUD_VENDOR_MULTIMODAL_API_KEY");

      this.vendorMultimodalApiKey = params.vendorMultimodalApiKey;
    }

    this.#client = createClient(
      createConfig({
        headers: {
          Authorization: `Bearer ${this.apiKey}`,
        },
        baseUrl: this.baseUrl,
      }),
    );
  }

  /**
   * Creates a job for the LlamaParse API.
   *
   * @param data - The file data as a Uint8Array.
   * @param filename - Optional filename for the file.
   * @returns A Promise resolving to the job ID as a string.
   */
  async #createJob(
    data: Uint8Array | string,
    filename?: string,
  ): Promise<string> {
    if (this.verbose) {
      console.log("Started uploading the file");
    }

    let file: File | Blob | null = null;
    let input_s3_path: string | undefined = this.inputS3Path;
    let input_url: string | undefined = this.input_url;
    if (typeof data !== "string") {
      // TODO: remove Blob usage when we drop Node.js 18 support
      file =
        globalThis.File && filename
          ? new File([data], filename)
          : new Blob([data]);
    } else if (data.startsWith("s3://")) {
      input_s3_path = data;
    } else if (data.startsWith("http://") || data.startsWith("https://")) {
      input_url = data;
    }

    const body = {
      file,
      input_s3_path,
      input_url,
      language: this.language,
      parsing_instruction: this.parsingInstruction,
      skip_diagonal_text: this.skipDiagonalText,
      invalidate_cache: this.invalidateCache,
      do_not_cache: this.doNotCache,
      fast_mode: this.fastMode,
      do_not_unroll_columns: this.doNotUnrollColumns,
      page_separator: this.pageSeparator,
      page_prefix: this.pagePrefix,
      page_suffix: this.pageSuffix,
      gpt4o_mode: this.gpt4oMode,
      gpt4o_api_key: this.gpt4oApiKey,
      bounding_box: this.boundingBox,
      target_pages: this.targetPages,
      use_vendor_multimodal_model: this.useVendorMultimodalModel,
      vendor_multimodal_model_name: this.vendorMultimodalModelName,
      vendor_multimodal_api_key: this.vendorMultimodalApiKey,
      premium_mode: this.premiumMode,
      webhook_url: this.webhookUrl,
      take_screenshot: this.takeScreenshot,
      disable_ocr: this.disableOcr,
      disable_reconstruction: this.disableReconstruction,
      output_s3_path_prefix: this.outputS3PathPrefix,
      continuous_mode: this.continuousMode,
      is_formatting_instruction: this.isFormattingInstruction,
      annotate_links: this.annotateLinks,
      azure_openai_deployment_name: this.azureOpenaiDeploymentName,
      azure_openai_endpoint: this.azureOpenaiEndpoint,
      azure_openai_api_version: this.azureOpenaiApiVersion,
      azure_openai_key: this.azureOpenaiKey,
      auto_mode: this.auto_mode,
      auto_mode_trigger_on_image_in_page:
        this.auto_mode_trigger_on_image_in_page,
      auto_mode_trigger_on_table_in_page:
        this.auto_mode_trigger_on_table_in_page,
      auto_mode_trigger_on_text_in_page: this.auto_mode_trigger_on_text_in_page,
      auto_mode_trigger_on_regexp_in_page:
        this.auto_mode_trigger_on_regexp_in_page,
      bbox_bottom: this.bbox_bottom,
      bbox_left: this.bbox_left,
      bbox_right: this.bbox_right,
      bbox_top: this.bbox_top,
      disable_image_extraction: this.disable_image_extraction,
      extract_charts: this.extract_charts,
      guess_xlsx_sheet_name: this.guess_xlsx_sheet_name,
      html_make_all_elements_visible: this.html_make_all_elements_visible,
      html_remove_fixed_elements: this.html_remove_fixed_elements,
      html_remove_navigation_elements: this.html_remove_navigation_elements,
      http_proxy: this.http_proxy,
      max_pages: this.max_pages,
      output_pdf_of_document: this.output_pdf_of_document,
      structured_output: this.structured_output,
      structured_output_json_schema: this.structured_output_json_schema,
      structured_output_json_schema_name:
        this.structured_output_json_schema_name,
      extract_layout: this.extract_layout,
      output_tables_as_HTML: this.output_tables_as_HTML,
      input_s3_region: this.input_s3_region,
      output_s3_region: this.output_s3_region,
      preserve_layout_alignment_across_pages:
        this.preserve_layout_alignment_across_pages,
      spreadsheet_extract_sub_tables: this.spreadsheet_extract_sub_tables,
      formatting_instruction: this.formatting_instruction,
      parse_mode: this.parse_mode,
      system_prompt: this.system_prompt,
      system_prompt_append: this.system_prompt_append,
      user_prompt: this.user_prompt,
      job_timeout_in_seconds: this.job_timeout_in_seconds,
      job_timeout_extra_time_per_page_in_seconds:
        this.job_timeout_extra_time_per_page_in_seconds,
      strict_mode_image_extraction: this.strict_mode_image_extraction,
      strict_mode_image_ocr: this.strict_mode_image_ocr,
      strict_mode_reconstruction: this.strict_mode_reconstruction,
      strict_mode_buggy_font: this.strict_mode_buggy_font,
      ignore_document_elements_for_layout_detection:
        this.ignore_document_elements_for_layout_detection,
      complemental_formatting_instruction:
        this.complemental_formatting_instruction,
      content_guideline_instruction: this.content_guideline_instruction,
      adaptive_long_table: this.adaptive_long_table,
      model: this.model,
      auto_mode_configuration_json: this.auto_mode_configuration_json,
      compact_markdown_table: this.compact_markdown_table,
      markdown_table_multiline_header_separator:
        this.markdown_table_multiline_header_separator,
      page_error_tolerance: this.page_error_tolerance,
      replace_failed_page_mode: this.replace_failed_page_mode,
      replace_failed_page_with_error_message_prefix:
        this.replace_failed_page_with_error_message_prefix,
      replace_failed_page_with_error_message_suffix:
        this.replace_failed_page_with_error_message_suffix,
      save_images: this.save_images,
      preset: this.preset,
      high_res_ocr: this.high_res_ocr,
      outlined_table_extraction: this.outlined_table_extraction,
      hide_headers: this.hide_headers,
      hide_footers: this.hide_footers,
      page_header_prefix: this.page_header_prefix,
      page_header_suffix: this.page_header_suffix,
      page_footer_prefix: this.page_footer_prefix,
      page_footer_suffix: this.page_footer_suffix,
      merge_tables_across_pages_in_markdown:
        this.merge_tables_across_pages_in_markdown,
    } satisfies {
      [Key in keyof BodyUploadFileApiParsingUploadPost]-?:
        | BodyUploadFileApiParsingUploadPost[Key]
        | undefined;
    } as unknown as BodyUploadFileApiParsingUploadPost;

    const response = await uploadFileApiV1ParsingUploadPost({
      client: this.#client,
      throwOnError: true,
      query: {
        project_id: this.project_id ?? null,
        organization_id: this.organization_id ?? null,
      },
      signal: AbortSignal.timeout(this.maxTimeout * 1000),
      body,
    });

    return response.data.id;
  }

  /**
   * Retrieves the result of a parsing job.
   *
   * Uses a polling loop with retry logic. Each API call is retried
   * up to maxErrorCount times if it fails with a 5XX or socket error.
   * The delay between polls increases according to the specified backoffPattern ("constant", "linear", or "exponential"),
   * capped by maxCheckInterval.
   *
   * @param jobId - The job ID.
   * @param resultType - The type of result to fetch ("text", "json", or "markdown").
   * @returns A Promise resolving to the job result.
   */
  private async getJobResult(
    jobId: string,
    resultType: "text" | "json" | "markdown",
  ): Promise<any> {
    let tries = 0;
    let currentInterval = this.checkInterval;
    const { default: pRetry } = await import("p-retry");

    while (true) {
      await sleep(currentInterval * 1000);

      // Wraps the API call in a retry
      let result;
      try {
        result = await pRetry(
          () =>
            getJobApiV1ParsingJobJobIdGet({
              client: this.#client,
              throwOnError: true,
              path: { job_id: jobId },
              signal: AbortSignal.timeout(this.maxTimeout * 1000),
            }),
          {
            retries: this.maxErrorCount,
            onFailedAttempt: (error) => {
              // Retry only on 5XX or socket errors.
              const status = (error.cause as any)?.response?.status;
              if (
                !(
                  (status && status >= 500 && status < 600) ||
                  ((error.cause as any)?.code &&
                    ((error.cause as any).code === "ECONNRESET" ||
                      (error.cause as any).code === "ETIMEDOUT" ||
                      (error.cause as any).code === "ECONNREFUSED"))
                )
              ) {
                throw error;
              }
              if (this.verbose) {
                console.warn(
                  `Attempting to get job ${jobId} result (attempt ${error.attemptNumber}) failed. Retrying...`,
                );
              }
            },
          },
        );
      } catch (e: any) {
        throw new Error(
          `Max error count reached for job ${jobId}: ${e.message}`,
        );
      }

      const { data } = result;
      const status = (data as Record<string, unknown>)["status"];

      if (status === "SUCCESS") {
        let resultData;
        switch (resultType) {
          case "json": {
            resultData =
              await getJobJsonResultApiV1ParsingJobJobIdResultJsonGet({
                client: this.#client,
                throwOnError: true,
                path: { job_id: jobId },
                query: {
                  organization_id: this.organization_id ?? null,
                },
                signal: AbortSignal.timeout(this.maxTimeout * 1000),
              });
            break;
          }
          case "markdown": {
            resultData =
              await getJobResultApiV1ParsingJobJobIdResultMarkdownGet({
                client: this.#client,
                throwOnError: true,
                path: { job_id: jobId },
                query: {
                  organization_id: this.organization_id ?? null,
                },
                signal: AbortSignal.timeout(this.maxTimeout * 1000),
              });
            break;
          }
          case "text": {
            resultData =
              await getJobTextResultApiV1ParsingJobJobIdResultTextGet({
                client: this.#client,
                throwOnError: true,
                path: { job_id: jobId },
                query: {
                  organization_id: this.organization_id ?? null,
                },
                signal: AbortSignal.timeout(this.maxTimeout * 1000),
              });
            break;
          }
        }
        return resultData.data;
      } else if (status === "PENDING") {
        if (this.verbose && tries % 10 === 0) {
          this.stdout?.write(".");
        }
        tries++;
      } else {
        if (this.verbose) {
          console.error(
            `Received error response ${status} for job ${jobId}. Got Error Code: ${data.error_code} and Error Message: ${data.error_message}`,
          );
        }
        throw new Error(
          `Failed to parse the file: ${jobId}, status: ${status}`,
        );
      }

      // Adjust the polling interval based on the backoff pattern.
      if (this.backoffPattern === "exponential") {
        currentInterval = Math.min(currentInterval * 2, this.maxCheckInterval);
      } else if (this.backoffPattern === "linear") {
        currentInterval = Math.min(
          currentInterval + this.checkInterval,
          this.maxCheckInterval,
        );
      } else if (this.backoffPattern === "constant") {
        currentInterval = this.checkInterval;
      }
    }
  }

  override async loadData(filePath?: string): Promise<Document[]> {
    if (!filePath) {
      if (this.input_url) {
        return this.loadDataAsContent(this.input_url, this.input_url);
      } else if (this.inputS3Path) {
        return this.loadDataAsContent(this.inputS3Path, this.inputS3Path);
      } else {
        throw new TypeError("File path is required");
      }
    } else {
      const data =
        filePath.startsWith("s3://") ||
        filePath.startsWith("http://") ||
        filePath.startsWith("https://")
          ? filePath
          : await fs.readFile(filePath);
      return this.loadDataAsContent(data, filePath);
    }
  }

  /**
   * Loads data from a file and returns an array of Document objects.
   * To be used with resultType "text" or "markdown".
   *
   * @param fileContent - The content of the file as a Uint8Array.
   * @param filename - Optional filename for the file.
   * @returns A Promise that resolves to an array of Document objects.
   */
  async loadDataAsContent(
    fileContent: Uint8Array | string,
    filename?: string,
  ): Promise<Document[]> {
    return this.#createJob(fileContent, filename)
      .then(async (jobId) => {
        if (this.verbose) {
          console.log(`Started parsing the file under job id ${jobId}`);
        }

        // Return results as Document objects.
        const jobResults = await this.getJobResult(jobId, this.resultType);
        const resultText = jobResults[this.resultType];

        // Split the text by separator if splitByPage is true.
        if (this.splitByPage) {
          return this.splitTextBySeparator(resultText);
        }

        return [new Document({ text: resultText })];
      })
      .catch((error) => {
        console.warn(
          `Error while parsing the file with: ${error.message ?? error.detail}`,
        );
        if (this.ignoreErrors) {
          return [];
        } else {
          throw error;
        }
      });
  }

  /**
   * Loads data from a file and returns an array of JSON objects.
   * To be used with resultType "json".
   *
   * @param filePathOrContent - The file path or the file content as a Uint8Array.
   * @returns A Promise that resolves to an array of JSON objects.
   */
  async loadJson(
    filePathOrContent: string | Uint8Array,
  ): Promise<Record<string, any>[]> {
    let jobId;
    const isFilePath =
      typeof filePathOrContent === "string" &&
      !(
        filePathOrContent.startsWith("s3://") ||
        filePathOrContent.startsWith("http://") ||
        filePathOrContent.startsWith("https://")
      );
    try {
      const data = isFilePath
        ? await fs.readFile(filePathOrContent)
        : filePathOrContent;
      // Create a job for the file.
      jobId = await this.#createJob(
        data,
        isFilePath ? path.basename(filePathOrContent) : undefined,
      );
      if (this.verbose) {
        console.log(`Started parsing the file under job id ${jobId}`);
      }

      // Return results as an array of JSON objects.
      const resultJson = await this.getJobResult(jobId, "json");
      resultJson.job_id = jobId;
      resultJson.file_path = isFilePath ? filePathOrContent : undefined;
      return [resultJson];
    } catch (e) {
      console.error(`Error while parsing the file under job id ${jobId}`, e);
      if (this.ignoreErrors) {
        return [];
      } else {
        throw e;
      }
    }
  }

  /**
   * Downloads and saves images from a given JSON result to a specified download path.
   * Currently only supports resultType "json".
   *
   * @param jsonResult - The JSON result containing image information.
   * @param downloadPath - The path where the downloaded images will be saved.
   * @returns A Promise that resolves to an array of image objects.
   */
  async getImages(
    jsonResult: Record<string, any>[],
    downloadPath: string,
  ): Promise<Record<string, any>[]> {
    try {
      // Create download directory if it doesn't exist (checks for write access).
      try {
        await fs.access(downloadPath);
      } catch {
        await fs.mkdir(downloadPath, { recursive: true });
      }

      const images: Record<string, any>[] = [];
      for (const result of jsonResult) {
        const jobId = result.job_id;
        for (const page of result.pages) {
          if (this.verbose) {
            console.log(`> Image for page ${page.page}: ${page.images}`);
          }
          for (const image of page.images) {
            const imageName = image.name;
            const imagePath = await this.getImagePath(
              downloadPath,
              jobId,
              imageName,
            );
            await this.fetchAndSaveImage(imageName, imagePath, jobId);
            // Assign metadata to the image.
            image.path = imagePath;
            image.job_id = jobId;
            image.original_pdf_path = result.file_path;
            image.page_number = page.page;
            images.push(image);
          }
        }
      }
      return images;
    } catch (e) {
      console.error(`Error while downloading images from the parsed result`, e);
      if (this.ignoreErrors) {
        return [];
      } else {
        throw e;
      }
    }
  }

  /**
   * Constructs the file path for an image.
   *
   * @param downloadPath - The base download directory.
   * @param jobId - The job ID.
   * @param imageName - The image name.
   * @returns A Promise that resolves to the full image path.
   */
  private async getImagePath(
    downloadPath: string,
    jobId: string,
    imageName: string,
  ): Promise<string> {
    return path.join(downloadPath, `${jobId}-${imageName}`);
  }

  /**
   * Fetches an image from the API and saves it to the specified path.
   *
   * @param imageName - The name of the image.
   * @param imagePath - The local path to save the image.
   * @param jobId - The associated job ID.
   */
  private async fetchAndSaveImage(
    imageName: string,
    imagePath: string,
    jobId: string,
  ): Promise<void> {
    const response =
      await getJobImageResultApiV1ParsingJobJobIdResultImageNameGet({
        client: this.#client,
        path: {
          job_id: jobId,
          name: imageName,
        },
      });
    if (response.error) {
      throw new Error(`Failed to download image: ${response.error.detail}`);
    }
    const blob = (await response.data) as Blob;
    // Write the image buffer to the specified imagePath.
    await fs.writeFile(imagePath, new Uint8Array(await blob.arrayBuffer()));
  }

  /**
   * Filters out invalid values (null, undefined, empty string) for specific parameters.
   *
   * @param params - The parameters object.
   * @param keysToCheck - The keys to check for valid values.
   * @returns A new object with filtered parameters.
   */
  private filterSpecificParams(
    params: Record<string, any>,
    keysToCheck: string[],
  ): Record<string, any> {
    const filteredParams: Record<string, any> = {};
    for (const [key, value] of Object.entries(params)) {
      if (keysToCheck.includes(key)) {
        if (value !== null && value !== undefined && value !== "") {
          filteredParams[key] = value;
        }
      } else {
        filteredParams[key] = value;
      }
    }
    return filteredParams;
  }

  /**
   * Splits text into Document objects using the page separator.
   *
   * @param text - The text to be split.
   * @returns An array of Document objects.
   */
  private splitTextBySeparator(text: string): Document[] {
    const separator = this.pageSeparator ?? "\n---\n";
    const textChunks = text.split(separator);
    return textChunks.map(
      (docChunk: string) =>
        new Document({
          text: docChunk,
        }),
    );
  }
}
