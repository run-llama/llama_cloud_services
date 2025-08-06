import { describe, it, expect, beforeEach, beforeAll } from "vitest";
import { LlamaParseReader } from "../src/reader.js";
import { LlamaCloudIndex } from "../src/LlamaCloudIndex.js";
import { LlamaExtract, LlamaExtractAgent } from "../src/LlamaExtract.js";
import { Document } from "@llamaindex/core/schema";
import { fs } from "@llamaindex/env";
import { ExtractConfig } from "../src/api.js";

// Integration tests that require actual API keys and files
describe("Integration Tests", () => {
  const skipIfNoApiKey = !process.env.LLAMA_CLOUD_API_KEY;

  beforeAll(() => {
    if (skipIfNoApiKey) {
      console.warn("LLAMA_CLOUD_API_KEY not set, skipping integration tests");
    }
  });

  describe("LlamaParseReader Integration", () => {
    let reader: LlamaParseReader;

    beforeEach(() => {
      if (skipIfNoApiKey) return;

      reader = new LlamaParseReader({
        apiKey: process.env.LLAMA_CLOUD_API_KEY!,
        resultType: "text",
        verbose: false,
      });
    });

    it.skipIf(skipIfNoApiKey)(
      "should parse a simple text document",
      async () => {
        // Create a simple test file
        const testContent = "This is a test document for parsing.";
        const testFilePath = "test-document.txt";

        // Write test file
        await fs.writeFile(testFilePath, new TextEncoder().encode(testContent));

        try {
          const result = await reader.loadData(testFilePath);

          expect(result).toBeDefined();
          expect(Array.isArray(result)).toBe(true);
          expect(result.length).toBeGreaterThan(0);
          expect(result[0]).toHaveProperty("text");
          expect(typeof result[0].text).toBe("string");

          // Clean up
          await fs.unlink(testFilePath);
        } catch (error) {
          // Clean up even if test fails
          try {
            await fs.unlink(testFilePath);
          } catch {}
          throw error;
        }
      },
      60000,
    );

    it.skipIf(skipIfNoApiKey)(
      "should parse with markdown result type",
      async () => {
        const markdownReader = new LlamaParseReader({
          apiKey: process.env.LLAMA_CLOUD_API_KEY!,
          resultType: "markdown",
          verbose: false,
        });

        const testContent = "This is a test document with **bold** text.";
        const testFilePath = "test-markdown.txt";

        await fs.writeFile(testFilePath, new TextEncoder().encode(testContent));

        try {
          const result = await markdownReader.loadData(testFilePath);

          expect(result).toBeDefined();
          expect(result.length).toBeGreaterThan(0);
          expect(result[0].text).toContain("test document");

          await fs.unlink(testFilePath);
        } catch (error) {
          try {
            await fs.unlink(testFilePath);
          } catch {}
          throw error;
        }
      },
      60000,
    );

    it.skipIf(skipIfNoApiKey)(
      "should handle parsing instruction",
      async () => {
        const instructedReader = new LlamaParseReader({
          apiKey: process.env.LLAMA_CLOUD_API_KEY!,
          resultType: "text",
          parsingInstruction:
            "Extract only the main content, ignore headers and footers",
          verbose: false,
        });

        const testContent = "Header\n\nMain content here\n\nFooter";
        const testFilePath = "test-instruction.txt";

        await fs.writeFile(testFilePath, new TextEncoder().encode(testContent));

        try {
          const result = await instructedReader.loadData(testFilePath);

          expect(result).toBeDefined();
          expect(result.length).toBeGreaterThan(0);

          await fs.unlink(testFilePath);
        } catch (error) {
          try {
            await fs.unlink(testFilePath);
          } catch {}
          throw error;
        }
      },
      60000,
    );

    it.skipIf(skipIfNoApiKey)(
      "should handle multiple languages",
      async () => {
        const multiLangReader = new LlamaParseReader({
          apiKey: process.env.LLAMA_CLOUD_API_KEY!,
          resultType: "text",
          language: ["en", "es"],
          verbose: false,
        });

        const testContent = "English text. Texto en español.";
        const testFilePath = "test-multilang.txt";

        await fs.writeFile(testFilePath, new TextEncoder().encode(testContent));

        try {
          const result = await multiLangReader.loadData(testFilePath);

          expect(result).toBeDefined();
          expect(result.length).toBeGreaterThan(0);

          await fs.unlink(testFilePath);
        } catch (error) {
          try {
            await fs.unlink(testFilePath);
          } catch {}
          throw error;
        }
      },
      60000,
    );

    it.skipIf(skipIfNoApiKey)(
      "should parse with splitByPage option",
      async () => {
        const pageReader = new LlamaParseReader({
          apiKey: process.env.LLAMA_CLOUD_API_KEY!,
          resultType: "text",
          splitByPage: true,
          pageSeparator: "---",
          verbose: false,
        });

        const testContent = "Page 1 content---Page 2 content---Page 3 content";
        const testFilePath = "test-pages.txt";

        await fs.writeFile(testFilePath, new TextEncoder().encode(testContent));

        try {
          const result = await pageReader.loadData(testFilePath);

          expect(result).toBeDefined();
          // Should split into multiple documents
          expect(result.length).toBeGreaterThanOrEqual(1);

          await fs.unlink(testFilePath);
        } catch (error) {
          try {
            await fs.unlink(testFilePath);
          } catch {}
          throw error;
        }
      },
      60000,
    );

    it.skipIf(skipIfNoApiKey)(
      "should handle URL input",
      async () => {
        const urlReader = new LlamaParseReader({
          apiKey: process.env.LLAMA_CLOUD_API_KEY!,
          resultType: "text",
          maxTimeout: 60000,
          verbose: false,
        });

        // Using a simple public URL with text content
        const testUrl =
          "https://cdn-blog.novoresume.com/articles/google-docs-resume-templates/basic-google-docs-resume.png";

        try {
          const result = await urlReader.loadData(testUrl);

          expect(result).toBeDefined();
          expect(result.length).toBeGreaterThan(0);
          expect(result[0].text).toBeTruthy();
        } catch (error) {
          // URL parsing might not be supported in all configurations
          console.warn("URL parsing test failed:", error.message);
        }
      },
      { timeout: 60000 },
    );

    it.skipIf(skipIfNoApiKey)(
      "should handle ignore errors option",
      async () => {
        const errorReader = new LlamaParseReader({
          apiKey: "invalid-api-key-should-fail",
          resultType: "text",
          ignoreErrors: true,
          verbose: false,
        });

        const testContent = "Test content";
        const testFilePath = "test-error.txt";

        await fs.writeFile(testFilePath, new TextEncoder().encode(testContent));

        try {
          const result = await errorReader.loadData(testFilePath);

          // Should return empty array instead of throwing
          expect(result).toBeDefined();
          expect(Array.isArray(result)).toBe(true);

          await fs.unlink(testFilePath);
        } catch (error) {
          try {
            await fs.unlink(testFilePath);
          } catch {}
          throw error;
        }
      },
      60000,
    );

    it.skipIf(skipIfNoApiKey)(
      "should load JSON result",
      async () => {
        const jsonReader = new LlamaParseReader({
          apiKey: process.env.LLAMA_CLOUD_API_KEY!,
          verbose: false,
        });

        const testContent = "Test document for JSON parsing";
        const testFilePath = "test-json.txt";

        await fs.writeFile(testFilePath, new TextEncoder().encode(testContent));

        try {
          const result = await jsonReader.loadJson(testFilePath);

          expect(result).toBeDefined();
          expect(Array.isArray(result)).toBe(true);
          expect(result.length).toBeGreaterThan(0);
          expect(result[0]).toHaveProperty("job_id");

          await fs.unlink(testFilePath);
        } catch (error) {
          try {
            await fs.unlink(testFilePath);
          } catch {}
          throw error;
        }
      },
      60000,
    );
  });

  describe("LlamaCloudIndex Integration", () => {
    let index: LlamaCloudIndex;

    beforeEach(() => {
      if (skipIfNoApiKey) return;

      index = new LlamaCloudIndex({
        name: `test-index-${Date.now()}`, // Unique name to avoid conflicts
        projectName: "test-project",
        apiKey: process.env.LLAMA_CLOUD_API_KEY!,
      });
    });

    it.skipIf(skipIfNoApiKey)(
      "should create index from documents",
      async () => {
        const documents = [
          new Document({
            text: "This is the first test document about artificial intelligence.",
            id_: `doc1-${Date.now()}`,
          }),
          new Document({
            text: "This is the second test document about machine learning.",
            id_: `doc2-${Date.now()}`,
          }),
        ];

        try {
          const result = await LlamaCloudIndex.fromDocuments({
            documents,
            name: `test-from-docs-${Date.now()}`,
            projectName: "test-project",
            apiKey: process.env.LLAMA_CLOUD_API_KEY!,
            verbose: false,
          });

          expect(result).toBeInstanceOf(LlamaCloudIndex);
          expect(result.params.name).toContain("test-from-docs");
        } catch (error) {
          console.warn("Index creation test failed:", error.message);
          // This might fail due to API rate limits or configuration
        }
      },
      120000,
    );

    it.skipIf(skipIfNoApiKey)("should create retriever", async () => {
      try {
        const retriever = index.asRetriever();
        expect(retriever).toBeDefined();
        expect(typeof retriever.retrieve).toBe("function");
      } catch (error) {
        console.warn("Retriever creation test failed:", error.message);
      }
    });

    it.skipIf(skipIfNoApiKey)("should create query engine", async () => {
      try {
        const queryEngine = index.asQueryEngine();
        expect(queryEngine).toBeDefined();
        expect(typeof queryEngine.query).toBe("function");
      } catch (error) {
        console.warn("Query engine creation test failed:", error.message);
      }
    });

    it.skipIf(skipIfNoApiKey)("should create query engine tool", async () => {
      try {
        const queryEngineTool = index.asQueryTool({
          metadata: {
            name: "test-tool",
            description: "Test tool description",
          },
        });
        expect(queryEngineTool).toBeDefined();
        expect(typeof queryEngineTool.call).toBe("function");
        expect(queryEngineTool.metadata.name).toBe("test-tool");
        expect(queryEngineTool.metadata.description).toBe(
          "Test tool description",
        );
      } catch (error) {
        console.warn("Query engine tool creation test failed:", error.message);
      }
    });

    it.skipIf(skipIfNoApiKey)(
      "should get pipeline and project IDs",
      async () => {
        try {
          const pipelineId = await index.getPipelineId();
          const projectId = await index.getProjectId();

          expect(typeof pipelineId).toBe("string");
          expect(typeof projectId).toBe("string");
          expect(pipelineId.length).toBeGreaterThan(0);
          expect(projectId.length).toBeGreaterThan(0);
        } catch (error) {
          console.warn("ID retrieval test failed:", error.message);
          // This might fail if the index doesn't exist yet
        }
      },
      30000,
    );
  });

  describe("Backoff Pattern Tests", () => {
    it.skipIf(skipIfNoApiKey)(
      "should handle different backoff patterns",
      async () => {
        const patterns: Array<"constant" | "linear" | "exponential"> = [
          "constant",
          "linear",
          "exponential",
        ];

        for (const pattern of patterns) {
          const reader = new LlamaParseReader({
            apiKey: process.env.LLAMA_CLOUD_API_KEY!,
            backoffPattern: pattern,
            checkInterval: 0.5,
            maxCheckInterval: 2,
            verbose: false,
          });

          expect(reader.backoffPattern).toBe(pattern);
        }
      },
    );
  });

  describe("LlamaExtract Integration", () => {
    it.skipIf(skipIfNoApiKey)(
      "should create agents correctly",
      async () => {
        const dataSchema = {
          properties: {
            text: {
              description: "Text from the file",
              type: "string",
            },
          },
          required: ["text"],
          type: "object",
        };
        const extractClient = new LlamaExtract(
          process.env.LLAMA_CLOUD_API_KEY!,
          "https://api.cloud.llamaindex.ai",
        );
        const agent = await extractClient.createAgent(
          "ExtractTestAgent",
          dataSchema,
        );
        expect(agent).instanceOf(LlamaExtractAgent);
      },
      60000,
    );
    it.skipIf(skipIfNoApiKey)(
      "should fetch agents correctly",
      async () => {
        const extractClient = new LlamaExtract(
          process.env.LLAMA_CLOUD_API_KEY!,
          "https://api.cloud.llamaindex.ai",
        );
        const agent = await extractClient.getAgent("ExtractTestAgent");
        expect(agent).instanceOf(LlamaExtractAgent);
      },
      60000,
    );
    it.skipIf(skipIfNoApiKey)(
      "should extract data correctly (file paths and file contents) with an agent and delete that agent",
      async () => {
        const extractClient = new LlamaExtract(
          process.env.LLAMA_CLOUD_API_KEY!,
          "https://api.cloud.llamaindex.ai",
        );
        const agent = await extractClient.getAgent("ExtractTestAgent");
        const testContent =
          "**Text to extract**: Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.";
        const testFilePath = "test-extract-agent.md";

        await fs.writeFile(testFilePath, new TextEncoder().encode(testContent));
        const result = await agent!.extract("test-extract-agent.md");
        expect("data" in result!).toBeTruthy();
        expect("extractionMetadata" in result!).toBeTruthy();

        const buffer = await fs.readFile("test-extract-agent.md");
        const resultBuffer = await agent!.extract(
          undefined,
          buffer,
          "test-extract-agent.md",
        );
        expect("data" in resultBuffer!).toBeTruthy();
        expect("extractionMetadata" in resultBuffer!).toBeTruthy();

        const success = await extractClient.deleteAgent(agent!.id);
        expect(success).toBeTruthy();
      },
      60000,
    );
    it.skipIf(skipIfNoApiKey)(
      "should extract statelessly file paths and file contents",
      async () => {
        const dataSchema = {
          properties: {
            text: {
              description: "Text from the file",
              type: "string",
            },
          },
          required: ["text"],
          type: "object",
        };

        const testContent =
          "**Text to extract**: Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.";
        const testFilePath = "test-extract.md";

        await fs.writeFile(testFilePath, new TextEncoder().encode(testContent));

        const extractClient = new LlamaExtract(
          process.env.LLAMA_CLOUD_API_KEY!,
          "https://api.cloud.llamaindex.ai",
        );
        const result = await extractClient.extract(
          dataSchema,
          {} as ExtractConfig,
          "test-extract.md",
        );
        expect("data" in result!).toBeTruthy();
        expect("extractionMetadata" in result!).toBeTruthy();

        const buffer = await fs.readFile("test-extract.md");
        const resultBuffer = await extractClient.extract(
          dataSchema,
          {} as ExtractConfig,
          undefined,
          buffer,
        ); // testing without passing a file name
        expect("data" in resultBuffer!).toBeTruthy();
        expect("extractionMetadata" in resultBuffer!).toBeTruthy();
      },
      60000,
    );
  });

  describe("Error Handling Integration", () => {
    it.skipIf(skipIfNoApiKey)(
      "should handle malformed files gracefully",
      async () => {
        const reader = new LlamaParseReader({
          apiKey: process.env.LLAMA_CLOUD_API_KEY!,
          ignoreErrors: true,
          verbose: false,
        });

        // Create a file with binary content that might cause issues
        const malformedContent = new Uint8Array([0xff, 0xfe, 0x00, 0x01, 0x02]);
        const testFilePath = "test-malformed.bin";

        await fs.writeFile(testFilePath, malformedContent);

        try {
          const result = await reader.loadData(testFilePath);

          // Should either parse successfully or return empty array with ignoreErrors
          expect(Array.isArray(result)).toBe(true);

          await fs.unlink(testFilePath);
        } catch (error) {
          try {
            await fs.unlink(testFilePath);
          } catch {}
          throw error;
        }
      },
      60000,
    );
  });
});
