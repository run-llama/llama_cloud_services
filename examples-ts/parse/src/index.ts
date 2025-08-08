import { LlamaParseReader } from "llama-cloud-services";
import { logger } from "./logger";
import pc from "picocolors";
import { consoleInput, generateSummary, renderLogo } from "./utils";

export async function main(): Promise<number> {
  const reader = new LlamaParseReader({ resultType: "markdown" });
  await renderLogo();
  logger.log(
    `Welcome to ${pc.bold(
      pc.magentaBright("✨LlamaParse Demo✨"),
    )}, our demo for ${pc.bold(pc.green("LlamaParse🦙"))}, a ${pc.bold(
      pc.cyan("LlamaCloud☁️"),
    )}  (https://cloud.llamaindex.ai) product!.\nType the path to the document you would like to process below👇\nIf you wish to exit, just type ${pc.bold(
      pc.gray("quit"),
    )}.\n`,
  );
  while (true) {
    const userInput = await consoleInput();
    if (userInput.toLowerCase() == "quit") {
      break;
    }
    try {
      const documents = await reader.loadData(userInput);
      const summary = await generateSummary(documents); // Added await here
      logger.log(`${pc.bold(pc.cyan("AI-generated summary✨"))}:\n${summary}`);
    } catch (error) {
      logger.error(`Error processing file: ${error}`);
    }
  }
  return 0;
}

main().catch(console.error);
