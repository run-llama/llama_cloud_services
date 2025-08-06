import { generateText } from "ai";
import { openai } from "@ai-sdk/openai";
import { NodeWithScore, MetadataMode } from "llamaindex";
import * as readline from "readline/promises";
import figlet from "figlet";
import pc from "picocolors";

export async function renderLogo(): Promise<void> {
  const logoText = figlet.textSync("LlamaChat", {
    font: "ANSI Shadow",
    horizontalLayout: "default",
    verticalLayout: "default",
    width: 100,
    whitespaceBreak: true,
  });

  // Add some styling with picocolors
  const styledLogo = pc.bold(pc.yellowBright(logoText));

  // Add some padding/margin
  console.log("\n");
  console.log(styledLogo);
  console.log(pc.gray("─".repeat(60)));
  console.log("\n");
}

export async function consoleInput(): Promise<string> {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  const answer = await rl.question(pc.cyanBright("You✨:"));
  rl.close();
  return answer;
}

export async function retrievalAugmentedGeneration(
  nodes: NodeWithScore[],
  prompt: string,
): Promise<string> {
  let mainText: string = "";

  for (const node of nodes) {
    mainText += `\t{information: '${node.node.getContent(
      MetadataMode.ALL,
    )}', relevanceScore: '${node.score ?? "no score"}'}\n`;
  }

  const { text } = await generateText({
    model: openai("gpt-4.1"),
    prompt: `[\n${mainText}\n]\n\nBased on the information you are given and on the relevance score of that (where -1 means no score available), answer to this user prompt: '${prompt}'`,
  });

  return text;
}
