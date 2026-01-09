// Emit deprecation warning once when package is imported
if (typeof console !== "undefined" && console.warn) {
  console.warn(
    "⚠️  DEPRECATION WARNING: This package (llama_cloud_services) is deprecated and will be maintained until May 1, 2026. " +
      "Please migrate to the new package: npm install @llamaindex/llama-cloud " +
      "(https://github.com/run-llama/llama-cloud-ts). " +
      "The new package provides the same functionality with improved performance and support.",
  );
}

export { LLamaCloudFileService } from "./LLamaCloudFileService.js";
export { LlamaCloudIndex } from "./LlamaCloudIndex.js";
export {
  LlamaCloudRetriever,
  type CloudRetrieveParams,
} from "./LlamaCloudRetriever.js";
export type { CloudConstructorParams } from "./type.js";
export { LlamaParseReader } from "./reader.js";
export { LlamaExtract, LlamaExtractAgent } from "./LlamaExtract.js";
export type { ExtractConfig } from "./extract.js";
export { LlamaClassify } from "./LlamaClassify.js";
export type {
  ClassifierRule,
  ClassifyJobResults,
  ClassifyParsingConfiguration,
} from "./classify.js";
