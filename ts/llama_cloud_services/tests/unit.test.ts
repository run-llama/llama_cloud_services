import { describe, it, expect } from "vitest";
import { LlamaParseReader } from "../src/reader.js";

describe("Unit Tests", () => {
  describe("LlamaParseReader Configuration", () => {
    it("should create instance with minimal config", () => {
      const reader = new LlamaParseReader({
        apiKey: "test-key",
      });

      expect(reader.apiKey).toBe("test-key");
      expect(reader.resultType).toBe("text");
      expect(reader.verbose).toBe(true);
      expect(reader.language).toEqual(["en"]);
    });

    it("should handle custom configuration", () => {
      const reader = new LlamaParseReader({
        apiKey: "test-key",
        resultType: "markdown",
        checkInterval: 2,
        maxTimeout: 5000,
        verbose: false,
        language: ["es", "fr"],
        backoffPattern: "exponential",
        maxCheckInterval: 10,
        maxErrorCount: 5,
      });

      expect(reader.apiKey).toBe("test-key");
      expect(reader.resultType).toBe("markdown");
      expect(reader.checkInterval).toBe(2);
      expect(reader.maxTimeout).toBe(5000);
      expect(reader.verbose).toBe(false);
      expect(reader.language).toEqual(["es", "fr"]);
      expect(reader.backoffPattern).toBe("exponential");
      expect(reader.maxCheckInterval).toBe(10);
      expect(reader.maxErrorCount).toBe(5);
    });

    it("should convert single language to array", () => {
      const reader = new LlamaParseReader({
        apiKey: "test-key",
        language: "de",
      });

      expect(reader.language).toEqual(["de"]);
    });

    it("should clean trailing slash from baseUrl", () => {
      const reader = new LlamaParseReader({
        apiKey: "test-key",
        baseUrl: "https://api.example.com/",
      });

      expect(reader.baseUrl).toBe("https://api.example.com");
    });

    it("should clean parsing path from baseUrl", () => {
      const reader = new LlamaParseReader({
        apiKey: "test-key",
        baseUrl: "https://api.example.com/api/parsing",
      });

      expect(reader.baseUrl).toBe("https://api.example.com");
    });

    it("should handle all parsing options", () => {
      const reader = new LlamaParseReader({
        apiKey: "test-key",
        parsingInstruction: "Extract tables only",
        skipDiagonalText: true,
        invalidateCache: true,
        doNotCache: false,
        fastMode: true,
        doNotUnrollColumns: false,
        pageSeparator: "\\n---\\n",
        pagePrefix: "[START]",
        pageSuffix: "[END]",
        boundingBox: "0,0,100,100",
        targetPages: "1,2,3",
        ignoreErrors: false,
        splitByPage: true,
        gpt4oMode: false,
        useVendorMultimodalModel: true,
        vendorMultimodalModelName: "gpt-4-vision",
        premiumMode: true,
        takeScreenshot: false,
        disableOcr: true,
        disableReconstruction: false,
        continuousMode: true,
        isFormattingInstruction: false,
        annotateLinks: true,
      });

      expect(reader.parsingInstruction).toBe("Extract tables only");
      expect(reader.skipDiagonalText).toBe(true);
      expect(reader.invalidateCache).toBe(true);
      expect(reader.doNotCache).toBe(false);
      expect(reader.fastMode).toBe(true);
      expect(reader.doNotUnrollColumns).toBe(false);
      expect(reader.pageSeparator).toBe("\\n---\\n");
      expect(reader.pagePrefix).toBe("[START]");
      expect(reader.pageSuffix).toBe("[END]");
      expect(reader.boundingBox).toBe("0,0,100,100");
      expect(reader.targetPages).toBe("1,2,3");
      expect(reader.ignoreErrors).toBe(false);
      expect(reader.splitByPage).toBe(true);
      expect(reader.gpt4oMode).toBe(false);
      expect(reader.useVendorMultimodalModel).toBe(true);
      expect(reader.vendorMultimodalModelName).toBe("gpt-4-vision");
      expect(reader.premiumMode).toBe(true);
      expect(reader.takeScreenshot).toBe(false);
      expect(reader.disableOcr).toBe(true);
      expect(reader.disableReconstruction).toBe(false);
      expect(reader.continuousMode).toBe(true);
      expect(reader.isFormattingInstruction).toBe(false);
      expect(reader.annotateLinks).toBe(true);
    });

    it("should handle backoff patterns", () => {
      const constantReader = new LlamaParseReader({
        apiKey: "test-key",
        backoffPattern: "constant",
      });
      expect(constantReader.backoffPattern).toBe("constant");

      const linearReader = new LlamaParseReader({
        apiKey: "test-key",
        backoffPattern: "linear",
      });
      expect(linearReader.backoffPattern).toBe("linear");

      const exponentialReader = new LlamaParseReader({
        apiKey: "test-key",
        backoffPattern: "exponential",
      });
      expect(exponentialReader.backoffPattern).toBe("exponential");
    });

    it("should handle numeric configuration options", () => {
      const reader = new LlamaParseReader({
        apiKey: "test-key",
        bbox_bottom: 100,
        bbox_left: 0,
        bbox_right: 200,
        bbox_top: 50,
        max_pages: 10,
        job_timeout_in_seconds: 300,
        job_timeout_extra_time_per_page_in_seconds: 30,
        page_error_tolerance: 0.1,
      });

      expect(reader.bbox_bottom).toBe(100);
      expect(reader.bbox_left).toBe(0);
      expect(reader.bbox_right).toBe(200);
      expect(reader.bbox_top).toBe(50);
      expect(reader.max_pages).toBe(10);
      expect(reader.job_timeout_in_seconds).toBe(300);
      expect(reader.job_timeout_extra_time_per_page_in_seconds).toBe(30);
      expect(reader.page_error_tolerance).toBe(0.1);
    });

    it("should handle boolean configuration options", () => {
      const reader = new LlamaParseReader({
        apiKey: "test-key",
        output_tables_as_HTML: true,
        preserve_layout_alignment_across_pages: false,
        spreadsheet_extract_sub_tables: true,
        strict_mode_image_extraction: false,
        strict_mode_image_ocr: true,
        strict_mode_reconstruction: false,
        strict_mode_buggy_font: true,
        ignore_document_elements_for_layout_detection: false,
        adaptive_long_table: true,
        compact_markdown_table: false,
        save_images: true,
        high_res_ocr: false,
        outlined_table_extraction: true,
        hide_headers: false,
        hide_footers: true,
        merge_tables_across_pages_in_markdown: false,
      });

      expect(reader.output_tables_as_HTML).toBe(true);
      expect(reader.preserve_layout_alignment_across_pages).toBe(false);
      expect(reader.spreadsheet_extract_sub_tables).toBe(true);
      expect(reader.strict_mode_image_extraction).toBe(false);
      expect(reader.strict_mode_image_ocr).toBe(true);
      expect(reader.strict_mode_reconstruction).toBe(false);
      expect(reader.strict_mode_buggy_font).toBe(true);
      expect(reader.ignore_document_elements_for_layout_detection).toBe(false);
      expect(reader.adaptive_long_table).toBe(true);
      expect(reader.compact_markdown_table).toBe(false);
      expect(reader.save_images).toBe(true);
      expect(reader.high_res_ocr).toBe(false);
      expect(reader.outlined_table_extraction).toBe(true);
      expect(reader.hide_headers).toBe(false);
      expect(reader.hide_footers).toBe(true);
      expect(reader.merge_tables_across_pages_in_markdown).toBe(false);
    });

    it("should handle string configuration options", () => {
      const reader = new LlamaParseReader({
        apiKey: "test-key",
        input_s3_region: "us-west-2",
        output_s3_region: "eu-west-1",
        formatting_instruction: "Format as table",
        system_prompt: "You are a document parser",
        system_prompt_append: "Always be accurate",
        user_prompt: "Parse this document",
        complemental_formatting_instruction: "Additional formatting",
        content_guideline_instruction: "Follow guidelines",
        model: "gpt-4-turbo",
        auto_mode_configuration_json: '{"mode": "auto"}',
        markdown_table_multiline_header_separator: " | ",
        replace_failed_page_with_error_message_prefix: "[ERROR]",
        replace_failed_page_with_error_message_suffix: "[/ERROR]",
        preset: "high-quality",
        page_header_prefix: "[HEADER]",
        page_header_suffix: "[/HEADER]",
        page_footer_prefix: "[FOOTER]",
        page_footer_suffix: "[/FOOTER]",
      });

      expect(reader.input_s3_region).toBe("us-west-2");
      expect(reader.output_s3_region).toBe("eu-west-1");
      expect(reader.formatting_instruction).toBe("Format as table");
      expect(reader.system_prompt).toBe("You are a document parser");
      expect(reader.system_prompt_append).toBe("Always be accurate");
      expect(reader.user_prompt).toBe("Parse this document");
      expect(reader.complemental_formatting_instruction).toBe(
        "Additional formatting",
      );
      expect(reader.content_guideline_instruction).toBe("Follow guidelines");
      expect(reader.model).toBe("gpt-4-turbo");
      expect(reader.auto_mode_configuration_json).toBe('{"mode": "auto"}');
      expect(reader.markdown_table_multiline_header_separator).toBe(" | ");
      expect(reader.replace_failed_page_with_error_message_prefix).toBe(
        "[ERROR]",
      );
      expect(reader.replace_failed_page_with_error_message_suffix).toBe(
        "[/ERROR]",
      );
      expect(reader.preset).toBe("high-quality");
      expect(reader.page_header_prefix).toBe("[HEADER]");
      expect(reader.page_header_suffix).toBe("[/HEADER]");
      expect(reader.page_footer_prefix).toBe("[FOOTER]");
      expect(reader.page_footer_suffix).toBe("[/FOOTER]");
    });
  });

  describe("Result Type Validation", () => {
    it("should accept valid result types", () => {
      const textReader = new LlamaParseReader({
        apiKey: "test-key",
        resultType: "text",
      });
      expect(textReader.resultType).toBe("text");

      const markdownReader = new LlamaParseReader({
        apiKey: "test-key",
        resultType: "markdown",
      });
      expect(markdownReader.resultType).toBe("markdown");

      const jsonReader = new LlamaParseReader({
        apiKey: "test-key",
        resultType: "json",
      });
      expect(jsonReader.resultType).toBe("json");
    });
  });

  describe("Language Configuration", () => {
    it("should handle single language string", () => {
      const reader = new LlamaParseReader({
        apiKey: "test-key",
        language: "fr",
      });
      expect(reader.language).toEqual(["fr"]);
    });

    it("should handle multiple languages array", () => {
      const reader = new LlamaParseReader({
        apiKey: "test-key",
        language: ["en", "es", "fr", "de"],
      });
      expect(reader.language).toEqual(["en", "es", "fr", "de"]);
    });
  });
});
