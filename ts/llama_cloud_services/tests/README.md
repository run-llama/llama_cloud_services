# TypeScript Tests for LlamaCloud Services

This directory contains comprehensive tests for the TypeScript LlamaCloud Services package, including unit tests and integration tests.

## Setup

### 1. Install Dependencies

First, install the test dependencies:

```bash
cd ts/llama_cloud_services
pnpm install
```

This will install:

- `vitest` - Fast test runner with TypeScript support
- `@types/node` - Node.js type definitions
- `@vitest/coverage-v8` - Coverage reporting
- `@vitest/ui` - Web UI for tests

### 2. Environment Variables

For integration tests, you'll need to set up environment variables:

```bash
# Required for integration tests
export LLAMA_CLOUD_API_KEY="your-api-key-here"

# Optional for testing OpenAI embeddings
export OPENAI_API_KEY="your-openai-key"
export EMBEDDING_MODEL="text-embedding-ada-002"
```

You can also create a `.env` file:

```bash
# .env file
LLAMA_CLOUD_API_KEY=your-api-key-here
OPENAI_API_KEY=your-openai-key
EMBEDDING_MODEL=text-embedding-ada-002
```

## Running Tests

### Run All Tests

```bash
pnpm test
```

### Run Tests in Watch Mode

```bash
pnpm test:watch
```

### Run Tests with UI

```bash
pnpm test:ui
```

### Run Tests with Coverage

```bash
pnpm test:coverage
```

### Run Specific Test Files

```bash
# Unit tests only
pnpm test unit

# Integration tests only (requires API key)
pnpm test integration

# Specific test file
pnpm test reader.test.ts
```

## Test Structure

### Unit Tests (`unit.test.ts`)

- Test configuration and initialization
- Test parameter validation
- Test without external dependencies
- **No API key required**

### Integration Tests (`integration.test.ts`)

- Test real API interactions
- Test file parsing with actual files
- Test error handling with real services
- **Requires LLAMA_CLOUD_API_KEY**

### Reader Tests (`reader.test.ts`)

- Comprehensive tests for `LlamaParseReader` class
- Mock-based tests for API interactions
- Test all configuration options
- **Requires API key for some tests**

### Index Tests (`index.test.ts`)

- Tests for `LlamaCloudIndex` class
- Mock-based tests for pipeline operations
- Test document management
- **Mock-based, no API key required**

## Test Configuration

The test setup is configured in:

- `vitest.config.ts` - Main test configuration
- `tests/setup.ts` - Global test setup and utilities

### Key Configuration Options

- **Timeout**: 30 seconds for regular tests, 120 seconds for integration tests
- **Environment**: Node.js environment
- **Coverage**: V8 provider with text, JSON, and HTML reports
- **Globals**: Vitest globals enabled (describe, it, expect, etc.)

## Test Utilities

The `tests/setup.ts` file provides useful utilities:

```typescript
import {
  createTestDocument,
  createTestFileName,
  generateTestContent,
  hasApiKey,
  TIMEOUTS,
  TEST_CONFIGS,
} from "./setup.js";

// Create test document
const doc = createTestDocument("Test content", "custom-id");

// Generate test filename
const filename = createTestFileName("pdf");

// Check if API key is available
if (hasApiKey()) {
  // Run integration test
}

// Use predefined configurations
const reader = new LlamaParseReader({
  apiKey: "test-key",
  ...TEST_CONFIGS.reader.basic,
});
```

## Test Patterns

### Skipping Tests Without API Key

```typescript
it.skipIf(!process.env.LLAMA_CLOUD_API_KEY)(
  "should parse document",
  async () => {
    // Test that requires API key
  },
);
```

### Testing Error Handling

```typescript
it("should handle errors gracefully", async () => {
  const reader = new LlamaParseReader({
    apiKey: "invalid-key",
    ignoreErrors: true,
  });

  const result = await reader.loadData("test.txt");
  expect(result).toEqual([]); // Should return empty array, not throw
});
```

### Testing Configuration

```typescript
it("should accept custom configuration", () => {
  const reader = new LlamaParseReader({
    apiKey: "test-key",
    resultType: "markdown",
    language: ["en", "es"],
    backoffPattern: "exponential",
  });

  expect(reader.resultType).toBe("markdown");
  expect(reader.language).toEqual(["en", "es"]);
  expect(reader.backoffPattern).toBe("exponential");
});
```

## Coverage

To generate coverage reports:

```bash
pnpm test:coverage
```

This will generate:

- Terminal output with coverage summary
- `coverage/` directory with HTML report
- `coverage/coverage.json` with detailed coverage data

View the HTML report by opening `coverage/index.html` in your browser.

## Continuous Integration

For CI environments, use:

```bash
# Run tests without watch mode
pnpm test --run

# Run with coverage in CI
pnpm test:coverage --run
```

## Troubleshooting

### Common Issues

1. **"Cannot find module 'vitest'"**

   - Run `pnpm install` to install dependencies

2. **Tests timeout**

   - Increase timeout in `vitest.config.ts`
   - Check your internet connection for API tests

3. **Integration tests failing**

   - Verify `LLAMA_CLOUD_API_KEY` is set correctly
   - Check API key permissions

4. **TypeScript errors**
   - Ensure all peer dependencies are installed
   - Check that `@types/node` is installed

### Debug Mode

Run tests with debug output:

```bash
DEBUG=1 pnpm test
```

Or run specific tests with verbose output:

```bash
pnpm test --reporter=verbose
```

## Contributing

When adding new tests:

1. **Unit tests** for new functionality without external dependencies
2. **Integration tests** for features that require API calls
3. **Mock-based tests** for testing error conditions
4. Use the test utilities in `setup.ts` for consistency
5. Add appropriate timeouts for async operations
6. Clean up any test files created during testing

## Example Test Files

The Python tests (`py/tests/parse/test_llama_parse.py`) were used as reference for creating these TypeScript tests, ensuring feature parity and comprehensive coverage.
