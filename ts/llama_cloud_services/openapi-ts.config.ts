import { defaultPlugins, defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  // you can download this file to get the latest version of the OpenAPI document
  // @link https://api.cloud.llamaindex.ai/api/openapi.json
  input: "./openapi.json",
  output: {
    path: "./src/client",
    format: "prettier",
    lint: "eslint",
  },
  plugins: [
    ...defaultPlugins,
    "@hey-api/client-fetch",
    "zod",
    "@hey-api/schemas",
    "@hey-api/sdk",
    {
      enums: "javascript",
      identifierCase: "PascalCase",
      name: "@hey-api/typescript",
    },
  ],
});
