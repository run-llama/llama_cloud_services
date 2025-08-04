import { LlamaCloudIndex } from "llama-cloud-services";
import { logger } from "./logger";
import pc from "picocolors";
import {
  consoleInput,
  retrievalAugmentedGeneration,
  renderLogo,
} from "./utils";
import dotenv from "dotenv";

dotenv.config();

export async function main(): Promise<number> {
  const index = new LlamaCloudIndex({
    name: process.env.PIPELINE_NAME as string,
    projectName: "Default",
    apiKey: process.env.LLAMA_CLOUD_API_KEY, // can provide API-key in the constructor or in the env
  });
  const retriever = index.asRetriever({
    similarityTopK: 5,
  });
  await renderLogo();
  logger.log(
    `Welcome to ${pc.bold(
      pc.magentaBright("✨LlamaChat✨"),
    )}, our demo for ${pc.bold(pc.green("Index🦙"))}, a ${pc.bold(
      pc.cyan("LlamaCloud☁️"),
    )}  (https://cloud.llamaindex.ai) product!.\nType a question below, and you will get an answer!👇\nIf you wish to exit, just type ${pc.bold(
      pc.gray("quit"),
    )}.\n`,
  );
  while (true) {
    const userInput = await consoleInput();
    if (userInput.toLowerCase() == "quit") {
      break;
    }
    try {
      const nodes = await retriever.retrieve(userInput);
      const summary = await retrievalAugmentedGeneration(nodes, userInput);
      logger.log(`${pc.bold(pc.magentaBright("LlamaChat✨:"))}\n${summary}`);
    } catch (error) {
      logger.error(`Error processing your request: ${error}`);
    }
  }
  return 0;
}

main().catch(console.error);
