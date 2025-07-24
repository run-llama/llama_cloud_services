import { FailPageMode, ParserLanguages, ParsingMode } from "./client";

import { z } from "zod";

type Language = ParserLanguages;
const VALUES: [Language, ...Language[]] = [
  ParserLanguages.EN,
  ...Object.values(ParserLanguages),
];
const languageSchema = z.enum(VALUES);

const PARSE_PRESETS = [
  "fast",
  "balanced",
  "premium",
  "structured",
  "auto",
  "scientific",
  "invoice",
  "slides",
  "_carlyle",
] as const;

export const parsePresetSchema = z.enum(PARSE_PRESETS);

export const parseFormSchema = z.object({
  adaptive_long_table: z.boolean().optional(),
  annotate_links: z.boolean().optional(),
  auto_mode: z.boolean().optional(),
  auto_mode_trigger_on_image_in_page: z.boolean().optional(),
  auto_mode_trigger_on_table_in_page: z.boolean().optional(),
  auto_mode_trigger_on_text_in_page: z.string().optional(),
  auto_mode_trigger_on_regexp_in_page: z.string().optional(),
  auto_mode_configuration_json: z.string().optional(),
  azure_openai_api_version: z.string().optional(),
  azure_openai_deployment_name: z.string().optional(),
  azure_openai_endpoint: z.string().optional(),
  azure_openai_key: z.string().optional(),
  bbox_bottom: z.number().min(0).max(1).optional(),
  bbox_left: z.number().min(0).max(1).optional(),
  bbox_right: z.number().min(0).max(1).optional(),
  bbox_top: z.number().min(0).max(1).optional(),
  disable_ocr: z.boolean().optional(),
  disable_reconstruction: z.boolean().optional(),
  disable_image_extraction: z.boolean().optional(),
  do_not_cache: z.coerce.boolean().optional(),
  do_not_unroll_columns: z.coerce.boolean().optional(),
  extract_charts: z.boolean().optional(),
  guess_xlsx_sheet_name: z.boolean().optional(),
  html_make_all_elements_visible: z.boolean().optional(),
  html_remove_fixed_elements: z.boolean().optional(),
  html_remove_navigation_elements: z.boolean().optional(),
  http_proxy: z
    .string()
    .url(
      'Set a valid URL for the HTTP proxy, e.g., "http://proxy.example.com:8080"',
    )
    .refine(
      (url) => {
        try {
          const parsedUrl = new URL(url);
          return (
            parsedUrl.protocol === "http:" || parsedUrl.protocol === "https:"
          );
        } catch {
          return false;
        }
      },
      {
        message: "Invalid HTTP proxy URL",
      },
    )
    .optional(),
  input_s3_path: z.string().optional(),
  input_s3_region: z.string().optional(),
  input_url: z.string().optional(),
  invalidate_cache: z.boolean().optional(),
  language: z.array(languageSchema).optional(),
  extract_layout: z.boolean().optional(),
  max_pages: z.number().nullable().optional(),
  output_pdf_of_document: z.boolean().optional(),
  output_s3_path_prefix: z.string().optional(),
  output_s3_region: z.string().optional(),
  page_prefix: z.string().optional(),
  page_separator: z.string().optional(),
  page_suffix: z.string().optional(),
  preserve_layout_alignment_across_pages: z.boolean().optional(),
  skip_diagonal_text: z.boolean().optional(),
  spreadsheet_extract_sub_tables: z.boolean().optional(),
  structured_output: z.boolean().optional(),
  structured_output_json_schema: z.string().optional(),
  structured_output_json_schema_name: z.string().optional(),
  take_screenshot: z.boolean().optional(),
  target_pages: z.string().optional(),
  vendor_multimodal_api_key: z.string().optional(),
  vendor_multimodal_model_name: z.string().optional(),
  model: z.string().optional(),
  webhook_url: z.string().url().optional(),
  parse_mode: z.nativeEnum(ParsingMode).nullable().optional(),
  system_prompt: z.string().optional(),
  system_prompt_append: z.string().optional(),
  user_prompt: z.string().optional(),
  job_timeout_in_seconds: z.number().optional(),
  job_timeout_extra_time_per_page_in_seconds: z.number().optional(),
  strict_mode_image_extraction: z.boolean().optional(),
  strict_mode_image_ocr: z.boolean().optional(),
  strict_mode_reconstruction: z.boolean().optional(),
  strict_mode_buggy_font: z.boolean().optional(),
  save_images: z.boolean().optional(),
  ignore_document_elements_for_layout_detection: z.boolean().optional(),
  output_tables_as_HTML: z.boolean().optional(),
  use_vendor_multimodal_model: z.boolean().optional(),
  bounding_box: z.string().optional(),
  gpt4o_mode: z.boolean().optional(),
  gpt4o_api_key: z.string().optional(),
  complemental_formatting_instruction: z.string().optional(),
  content_guideline_instruction: z.string().optional(),
  premium_mode: z.boolean().optional(),
  is_formatting_instruction: z.boolean().optional(),
  continuous_mode: z.boolean().optional(),
  parsing_instruction: z.string().optional(),
  fast_mode: z.boolean().optional(),
  formatting_instruction: z.string().optional(),
  preset: parsePresetSchema.optional(),
  compact_markdown_table: z.boolean().optional(),
  markdown_table_multiline_header_separator: z.string().optional(),
  page_error_tolerance: z.number().min(0).max(1).optional(),
  replace_failed_page_mode: z.nativeEnum(FailPageMode).nullable().optional(),
  replace_failed_page_with_error_message_prefix: z.string().optional(),
  replace_failed_page_with_error_message_suffix: z.string().optional(),
});
