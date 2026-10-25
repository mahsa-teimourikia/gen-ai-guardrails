import { access, readFile } from "node:fs/promises";

const html = await readFile("out/index.html", "utf8");
const quizHtml = await readFile("out/quiz/index.html", "utf8");
await access("out/assets/one-plus-i.png");
await access("out/favicon.svg");
const assets = [...html.matchAll(/(?:src|href)="(\/gen-ai-guardrails\/assets\/[^"?]+)"/g)].map(([, path]) => path);
if (!assets.length) throw new Error("No hashed Pages assets found");
for (const asset of assets) {
  await access(`out/${asset.replace(/^\/gen-ai-guardrails\//, "")}`);
}
const javascript = await Promise.all(
  assets
    .filter((asset) => asset.endsWith(".js"))
    .map((asset) => readFile(`out/${asset.replace(/^\/gen-ai-guardrails\//, "")}`, "utf8")),
);
const bundle = javascript.join("\n");
for (const expected of [
  "FIELD GUIDE",
  "What are GenAI guardrails?",
  "The guardrail lifecycle",
  "Best practices for production guardrails",
  "Scenario cookbook",
  "Evaluation and red teaming",
  "Security and privacy",
  "Agent and tool capstone",
  "State-of-the-art stack",
  "Inspect the reusable lab module",
  "One+i",
]) {
  if (!bundle.includes(expected)) throw new Error(`Pages bundle is missing ${expected}`);
}
if (!quizHtml.includes("question-list")) throw new Error("Quiz page artifact is missing the quiz shell");
console.log(`Pages smoke check passed (${assets.length} hashed assets, hub bundle, quiz page, and branding).`);
