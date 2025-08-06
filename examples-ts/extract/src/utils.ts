import * as readline from "readline/promises";
import figlet from "figlet";
import pc from "picocolors";

export async function renderLogo(): Promise<void> {
  const logoText = figlet.textSync("Extract Demo", {
    font: "ANSI Shadow",
    horizontalLayout: "default",
    verticalLayout: "default",
    width: 100,
    whitespaceBreak: true,
  });

  // Add some styling with picocolors
  const styledLogo = pc.bold(pc.redBright(logoText));

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
