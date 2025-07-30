import { generateText } from "ai";
import { openai } from "@ai-sdk/openai";
import { Document } from "llamaindex";
import * as readline from "readline/promises";
import figlet from "figlet";
import pc from "picocolors";

export async function renderLogo(): Promise<void> {
  const logoText = figlet.textSync("LlamaParse Demo", {
    font: "ANSI Shadow",
    horizontalLayout: "default",
    verticalLayout: "default",
    width: 100,
    whitespaceBreak: true,
  });

  // Add some styling with picocolors
  const styledLogo = pc.bold(pc.magentaBright(logoText));

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

  const answer = await rl.question("Path to your file: ");
  rl.close();
  return answer;
}

export async function generateSummary(documents: Document[]): Promise<string> {
  let mainText: string = "";

  for (const document of documents) {
    mainText += `${document.text}\n\n---\n\n`;
  }

  const { text } = await generateText({
    model: openai("gpt-4.1"),
    prompt: `</chat>\n\t<text>${mainText}</text>\n\t<instructions>Could you please generate a summary of the given text?</instructions>\n</chat>`,
  });

  return text;
}
