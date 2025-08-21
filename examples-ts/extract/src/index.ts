import { LlamaExtract, ExtractConfig } from "llama-cloud-services";
import cliMarkdown from "cli-markdown";
import { logger } from "./logger";
import pc from "picocolors";
import { consoleInput, renderLogo } from "./utils";
import { dataSchema } from "./schema";
import { renderMarkdown, ResearchData } from "./markdown";

export async function main(): Promise<number> {
  const extractClient = new LlamaExtract(
    process.env.LLAMA_CLOUD_API_KEY!,
    "https://api.cloud.llamaindex.ai",
  );
  await renderLogo();
  logger.log(
    `Welcome to ${pc.bold(
      pc.magentaBright("LlamaExtract Demo✨"),
    )}, our demo for ${pc.bold(pc.green("LlamaExtract"))}, a ${pc.bold(
      pc.cyan("LlamaCloud☁️"),
    )}  (https://cloud.llamaindex.ai) product!.\nIn this demo we are going to try extracting relevant information  ${pc.bold(
      pc.yellowBright("from scientific papers"),
    )}. Type the path to the paper you would like to process below👇\nIf you wish to exit, just type ${pc.bold(
      pc.gray("quit"),
    )}.\n`,
  );
  while (true) {
    const userInput = await consoleInput();
    if (userInput.toLowerCase() == "quit") {
      break;
    }
    try {
      const generatedData = await extractClient.extract(
        dataSchema,
        {} as ExtractConfig,
        userInput,
      );
      const research = renderMarkdown(generatedData?.data as ResearchData); // Added await here
      logger.log(`${pc.bold(pc.cyan("Extracted information:✨"))}:\n`);
      logger.log(cliMarkdown(research));
    } catch (error) {
      logger.error(`Error processing file: ${error}`);
    }
  }
  return 0;
}

main().catch(console.error);
