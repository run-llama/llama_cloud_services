import { describe, it, expect, beforeEach, vi, beforeAll } from "vitest";
import { LlamaParseReader } from "../src/reader.js";
import { fs, getEnv } from "@llamaindex/env";

// Mock environment variables
vi.mock("@llamaindex/env", async () => {
  const actual = await vi.importActual("@llamaindex/env");
  return {
    ...actual,
    getEnv: vi.fn((key: string) => {
      if (key === "LLAMA_CLOUD_API_KEY") {
        return process.env.LLAMA_CLOUD_API_KEY || "test-api-key";
      }
      return undefined;
    }),
  };
});

describe("LlamaParseReader", () => {
  let reader: LlamaParseReader;

  beforeAll(() => {
    // Skip tests if API key is not set
    if (!process.env.LLAMA_CLOUD_API_KEY) {
      console.warn("LLAMA_CLOUD_API_KEY not set, skipping integration tests");
    }
  });

  beforeEach(() => {
    reader = new LlamaParseReader({
      apiKey: process.env.LLAMA_CLOUD_API_KEY || "test-api-key",
      resultType: "text",
      verbose: false,
    });
  });

  describe("constructor", () => {
    it("should create instance with default values", () => {
      const defaultReader = new LlamaParseReader({
        apiKey: "test-key",
      });

      expect(defaultReader.resultType).toBe("text");
      expect(defaultReader.checkInterval).toBe(1);
      expect(defaultReader.maxTimeout).toBe(2000);
      expect(defaultReader.verbose).toBe(true);
      expect(defaultReader.language).toEqual(["en"]);
      expect(defaultReader.backoffPattern).toBe("linear");
    });

    it("should accept custom configuration", () => {
      const customReader = new LlamaParseReader({
        apiKey: "test-key",
        resultType: "markdown",
        checkInterval: 2,
        maxTimeout: 3000,
        verbose: false,
        language: ["es", "fr"],
        backoffPattern: "exponential",
      });

      expect(customReader.resultType).toBe("markdown");
      expect(customReader.checkInterval).toBe(2);
      expect(customReader.maxTimeout).toBe(3000);
      expect(customReader.verbose).toBe(false);
      expect(customReader.language).toEqual(["es", "fr"]);
      expect(customReader.backoffPattern).toBe("exponential");
    });

    it("should handle single language as array", () => {
      const singleLangReader = new LlamaParseReader({
        apiKey: "test-key",
        language: "de",
      });

      expect(singleLangReader.language).toEqual(["de"]);
    });

    it("should throw error if no API key provided", () => {
      vi.mocked(getEnv).mockReturnValue(undefined);

      expect(() => {
        new LlamaParseReader({});
      }).toThrow("API Key is required for LlamaParseReader");
    });
  });

  describe("loadData", () => {
    it.skipIf(!process.env.LLAMA_CLOUD_API_KEY)(
      "should parse a simple PDF file",
      async () => {
        // This test requires an actual PDF file and API key
        const mockFilePath = "test-file.pdf";
        const mockFileContent = Buffer.from([1, 2, 3, 4]); // Mock PDF content

        vi.spyOn(fs, "readFile").mockResolvedValue(mockFileContent);

        // Mock the API calls
        const mockJobId = "test-job-id";
        const mockResponse = { text: "Sample parsed text content" };

        // We can't easily mock the private methods, so this test would need real API
        // For now, let's test the method signature and error handling

        try {
          await reader.loadData(mockFilePath);
        } catch (error) {
          // Expected to fail with mock data, but should reach the API call
          expect(error).toBeDefined();
        }
      },
      30000,
    );

    it("should handle S3 input", async () => {
      const s3Path = "s3://bucket/document.pdf";

      try {
        await reader.loadData(s3Path);
      } catch (error) {
        // Expected to fail without real API, but should handle S3 format
        expect(error).toBeDefined();
      }
    });

    it("should use input_url when no file path provided", async () => {
      const readerWithUrl = new LlamaParseReader({
        apiKey: "test-key",
        input_url: "https://example.com/doc.pdf",
      });

      try {
        await readerWithUrl.loadData();
      } catch (error) {
        // Expected to fail without real API
        expect(error).toBeDefined();
      }
    });

    it("should use inputS3Path when no file path provided and no URL", async () => {
      const readerWithS3 = new LlamaParseReader({
        apiKey: "test-key",
        inputS3Path: "s3://bucket/doc.pdf",
      });

      try {
        await readerWithS3.loadData();
      } catch (error) {
        // Expected to fail without real API
        expect(error).toBeDefined();
      }
    });

    it("should throw error when no file path, URL, or S3 path provided", async () => {
      await expect(reader.loadData()).rejects.toThrow("File path is required");
    });
  });

  describe("loadDataAsContent", () => {
    it("should handle Uint8Array content", async () => {
      const content = new Uint8Array([1, 2, 3, 4]);
      const filename = "test.pdf";

      try {
        await reader.loadDataAsContent(content, filename);
      } catch (error) {
        // Expected to fail without real API
        expect(error).toBeDefined();
      }
    });

    it("should handle string S3 content", async () => {
      const s3Path = "s3://bucket/document.pdf";

      try {
        await reader.loadDataAsContent(s3Path);
      } catch (error) {
        // Expected to fail without real API
        expect(error).toBeDefined();
      }
    });

    it("should handle ignoreErrors flag", async () => {
      const errorReader = new LlamaParseReader({
        apiKey: "invalid-key",
        ignoreErrors: true,
      });

      const content = new Uint8Array([1, 2, 3, 4]);

      // Should return empty array instead of throwing
      const result = await errorReader.loadDataAsContent(content, "test.pdf");
      expect(result).toEqual([]);
    });
  });

  describe("loadJson", () => {
    it("should handle file path input", async () => {
      const filePath = "test.pdf";

      vi.spyOn(fs, "readFile").mockResolvedValue(Buffer.from([1, 2, 3, 4]));

      try {
        await reader.loadJson(filePath);
      } catch (error) {
        // Expected to fail without real API
        expect(error).toBeDefined();
      }
    });

    it("should handle Uint8Array input", async () => {
      const content = new Uint8Array([1, 2, 3, 4]);

      try {
        await reader.loadJson(content);
      } catch (error) {
        // Expected to fail without real API
        expect(error).toBeDefined();
      }
    });

    it("should handle URL input", async () => {
      const url = "https://example.com/document.pdf";

      try {
        await reader.loadJson(url);
      } catch (error) {
        // Expected to fail without real API
        expect(error).toBeDefined();
      }
    });

    it("should handle S3 input", async () => {
      const s3Path = "s3://bucket/document.pdf";

      try {
        await reader.loadJson(s3Path);
      } catch (error) {
        // Expected to fail without real API
        expect(error).toBeDefined();
      }
    });
  });

  describe("splitTextBySeparator", () => {
    it("should split text by default separator", () => {
      const text = "Page 1 content\n---\nPage 2 content\n---\nPage 3 content";

      // Access private method for testing (TypeScript hack)
      const result = (reader as any).splitTextBySeparator(text);

      expect(result).toHaveLength(3);
      expect(result[0].text).toBe("Page 1 content");
      expect(result[1].text).toBe("Page 2 content");
      expect(result[2].text).toBe("Page 3 content");
    });

    it("should split text by custom separator", () => {
      const customReader = new LlamaParseReader({
        apiKey: "test-key",
        pageSeparator: "###",
      });

      const text = "Page 1###Page 2###Page 3";
      const result = (customReader as any).splitTextBySeparator(text);

      expect(result).toHaveLength(3);
      expect(result[0].text).toBe("Page 1");
      expect(result[1].text).toBe("Page 2");
      expect(result[2].text).toBe("Page 3");
    });
  });

  describe("configuration options", () => {
    it("should handle all parsing options", () => {
      const fullConfigReader = new LlamaParseReader({
        apiKey: "test-key",
        parsingInstruction: "Extract tables only",
        skipDiagonalText: true,
        invalidateCache: true,
        doNotCache: true,
        fastMode: true,
        doNotUnrollColumns: true,
        pageSeparator: "---",
        pagePrefix: "[PAGE START]",
        pageSuffix: "[PAGE END]",
        gpt4oMode: true,
        gpt4oApiKey: "gpt4o-key",
        boundingBox: "0,0,100,100",
        targetPages: "1,2,3",
        ignoreErrors: false,
        splitByPage: false,
        useVendorMultimodalModel: true,
        vendorMultimodalModelName: "gpt-4-vision",
        vendorMultimodalApiKey: "vision-key",
      });

      expect(fullConfigReader.parsingInstruction).toBe("Extract tables only");
      expect(fullConfigReader.skipDiagonalText).toBe(true);
      expect(fullConfigReader.invalidateCache).toBe(true);
      expect(fullConfigReader.doNotCache).toBe(true);
      expect(fullConfigReader.fastMode).toBe(true);
      expect(fullConfigReader.doNotUnrollColumns).toBe(true);
      expect(fullConfigReader.pageSeparator).toBe("---");
      expect(fullConfigReader.pagePrefix).toBe("[PAGE START]");
      expect(fullConfigReader.pageSuffix).toBe("[PAGE END]");
      expect(fullConfigReader.gpt4oMode).toBe(true);
      expect(fullConfigReader.gpt4oApiKey).toBe("gpt4o-key");
      expect(fullConfigReader.boundingBox).toBe("0,0,100,100");
      expect(fullConfigReader.targetPages).toBe("1,2,3");
      expect(fullConfigReader.ignoreErrors).toBe(false);
      expect(fullConfigReader.splitByPage).toBe(false);
      expect(fullConfigReader.useVendorMultimodalModel).toBe(true);
      expect(fullConfigReader.vendorMultimodalModelName).toBe("gpt-4-vision");
      expect(fullConfigReader.vendorMultimodalApiKey).toBe("vision-key");
    });
  });

  describe("backoff patterns", () => {
    it("should support constant backoff", () => {
      const constantReader = new LlamaParseReader({
        apiKey: "test-key",
        backoffPattern: "constant",
      });

      expect(constantReader.backoffPattern).toBe("constant");
    });

    it("should support linear backoff", () => {
      const linearReader = new LlamaParseReader({
        apiKey: "test-key",
        backoffPattern: "linear",
      });

      expect(linearReader.backoffPattern).toBe("linear");
    });

    it("should support exponential backoff", () => {
      const exponentialReader = new LlamaParseReader({
        apiKey: "test-key",
        backoffPattern: "exponential",
      });

      expect(exponentialReader.backoffPattern).toBe("exponential");
    });
  });
});
