// Test setup and global configurations
import { beforeAll, afterAll } from "vitest";

// Global test setup
beforeAll(async () => {
  // Set up test environment
  if (!process.env.LLAMA_CLOUD_API_KEY) {
    console.warn(
      "⚠️  LLAMA_CLOUD_API_KEY not set. Integration tests will be skipped.",
    );
    console.warn(
      "   To run integration tests, set the LLAMA_CLOUD_API_KEY environment variable.",
    );
  }

  // Extend default timeout for integration tests
  // This is handled in vitest.config.ts but can be overridden here if needed
});

afterAll(async () => {
  // Clean up any global test artifacts
  console.log("✅ Test cleanup completed");
});

// Helper functions for tests
export const createTestDocument = (content: string, id?: string) => {
  return {
    text: content,
    id_:
      id || `test-doc-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
  };
};

export const createTestFileName = (extension: string = "txt") => {
  return `test-${Date.now()}-${Math.random()
    .toString(36)
    .substr(2, 9)}.${extension}`;
};

// Test data generators
export const generateTestContent = {
  simple: () => "This is a simple test document for parsing.",
  markdown: () =>
    "# Test Document\n\nThis is a **bold** test with *italic* text.\n\n- List item 1\n- List item 2",
  multiPage: () => "Page 1 content\n---\nPage 2 content\n---\nPage 3 content",
  multilingual: () => "English text. Texto en español. Texte en français.",
  structured: () =>
    JSON.stringify(
      {
        title: "Test Document",
        content: "This is structured test content",
        metadata: { type: "test", version: 1 },
      },
      null,
      2,
    ),
};

// Environment check utilities
export const hasApiKey = () => Boolean(process.env.LLAMA_CLOUD_API_KEY);

export const skipIfNoApiKey = (testName: string) => {
  if (!hasApiKey()) {
    console.warn(`Skipping ${testName} - no API key`);
    return true;
  }
  return false;
};

// Test timeout constants
export const TIMEOUTS = {
  short: 10000, // 10 seconds
  medium: 30000, // 30 seconds
  long: 60000, // 60 seconds
  veryLong: 120000, // 2 minutes
} as const;

// Common test configurations
export const TEST_CONFIGS = {
  reader: {
    basic: {
      resultType: "text" as const,
      verbose: false,
      checkInterval: 1,
      maxTimeout: 30,
    },
    markdown: {
      resultType: "markdown" as const,
      verbose: false,
      checkInterval: 1,
      maxTimeout: 30,
    },
    withInstruction: {
      resultType: "text" as const,
      parsingInstruction: "Extract main content only",
      verbose: false,
    },
    multiLanguage: {
      resultType: "text" as const,
      language: ["en", "es"],
      verbose: false,
    },
    withPages: {
      resultType: "text" as const,
      splitByPage: true,
      pageSeparator: "---",
      verbose: false,
    },
  },
  index: {
    basic: {
      projectName: "test-project",
      verbose: false,
    },
  },
} as const;
