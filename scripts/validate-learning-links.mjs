import { execFileSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const trackedFiles = new Set(
  execFileSync("git", ["ls-files"], { cwd: root, encoding: "utf8" })
    .split("\n")
    .filter(Boolean),
);
const failures = [];
const validatedLinks = new Set();

const read = (file) => readFile(path.resolve(root, file), "utf8");
const isExternal = (value) => /^(?:https?:|mailto:|tel:|data:)/i.test(value);
const stripQuery = (value) => value.split("?", 1)[0];

function targetExists(target) {
  const normalized = target.replace(/\/$/, "");
  return trackedFiles.has(normalized) || [...trackedFiles].some((file) => file.startsWith(`${normalized}/`));
}

function githubSlug(value) {
  return value
    .replace(/<[^>]+>/g, "")
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/[`*_~]/g, "")
    .toLowerCase()
    .trim()
    .replace(/[^\p{L}\p{N}\s-]/gu, "")
    .replace(/\s+/g, "-");
}

async function markdownAnchors(file) {
  const text = await read(file);
  const anchors = new Set();
  const seen = new Map();
  for (const match of text.matchAll(/^#{1,6}\s+(.+)$/gm)) {
    const base = githubSlug(match[1]);
    const count = seen.get(base) ?? 0;
    seen.set(base, count + 1);
    anchors.add(count === 0 ? base : `${base}-${count}`);
  }
  return anchors;
}

async function validateLocalLink(source, rawValue) {
  const value = rawValue.replace(/^<|>$/g, "");
  if (!value || isExternal(value)) return;

  const [rawTarget, anchor] = value.split("#", 2);
  const targetPart = decodeURIComponent(stripQuery(rawTarget));
  const target = targetPart
    ? path.posix.normalize(path.posix.join(path.posix.dirname(source), targetPart))
    : source;
  validatedLinks.add(`${source} -> ${value}`);

  if (!targetExists(target)) {
    failures.push(`${source} -> ${value} (missing target ${target})`);
    return;
  }
  if (anchor && target.endsWith(".md")) {
    const anchors = await markdownAnchors(target);
    if (!anchors.has(decodeURIComponent(anchor).toLowerCase())) {
      failures.push(`${source} -> ${value} (missing anchor)`);
    }
  }
}

for (const file of [...trackedFiles].filter((name) => name.endsWith(".md"))) {
  const text = await read(file);
  for (const match of text.matchAll(/!?\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g)) {
    await validateLocalLink(file, match[1]);
  }
}

const courseReadmes = [...trackedFiles]
  .filter((file) => /^curriculum\/(?:beginner|intermediate|advanced)\/\d{2}-[^/]+\/README\.md$/.test(file))
  .sort();
if (courseReadmes.length !== 8) {
  failures.push(`expected 8 course READMEs, found ${courseReadmes.length}`);
}

const courseArtifacts = courseReadmes.map((readme) => {
  const directory = path.posix.dirname(readme);
  const notebooks = [...trackedFiles].filter(
    (file) => path.posix.dirname(file) === directory && file.endsWith(".ipynb"),
  );
  const labs = [...trackedFiles].filter(
    (file) => path.posix.dirname(file) === directory && /(?:^|_)lab\.py$/.test(path.posix.basename(file)),
  );
  if (notebooks.length !== 1) failures.push(`${directory} should contain exactly one canonical notebook`);
  if (labs.length !== 1) failures.push(`${directory} should contain exactly one reusable lab module`);
  return { readme, notebooks, labs };
});

const hub = await read("app/page.tsx");
const lessonIds = [...hub.matchAll(/^\s+id:\s*"([bia]\d+)",/gm)].map((match) => match[1]);
const hubNotebooks = new Set([...hub.matchAll(/notebook:\s*"([^"]+)"/g)].map((match) => match[1]));
const hubLabs = new Set([...hub.matchAll(/lab:\s*"([^"]+)"/g)].map((match) => match[1]));
const hubPaths = new Set(
  [...hub.matchAll(/curriculum\/[A-Za-z0-9_./-]+\.(?:md|ipynb|py)(?:#[A-Za-z0-9_-]+)?/g)]
    .map((match) => match[0].split("#", 1)[0]),
);
const checkpointCount = [...hub.matchAll(/^\s+question:\s*"/gm)].length;

if (lessonIds.length !== 8 || new Set(lessonIds).size !== 8) {
  failures.push(`expected 8 unique Hub lessons, found ${lessonIds.length}`);
}
if (checkpointCount !== 24) {
  failures.push(`expected 24 Hub checkpoint questions, found ${checkpointCount}`);
}
for (const { readme, notebooks, labs } of courseArtifacts) {
  if (!hubPaths.has(readme)) failures.push(`Hub is missing lesson link ${readme}`);
  for (const notebook of notebooks) {
    if (!hubNotebooks.has(notebook)) failures.push(`Hub is missing notebook link ${notebook}`);
  }
  for (const lab of labs) {
    if (!hubLabs.has(lab)) failures.push(`Hub is missing lab link ${lab}`);
  }
}
for (const localPath of hubPaths) {
  await validateLocalLink("README.md", localPath);
}

const quiz = await read("quiz/questions.js");
const quizIds = [...quiz.matchAll(/\bid:\s*"([^"]+)"/g)].map((match) => match[1]);
const quizSources = [...quiz.matchAll(/\burl:\s*"([^"]+)"/g)].map((match) => match[1]);
if (quizIds.length !== 34 || new Set(quizIds).size !== 34) {
  failures.push(`expected 34 unique quiz questions, found ${quizIds.length}`);
}
for (const source of quizSources) {
  await validateLocalLink("quiz/questions.js", `../${source}`);
}

if (failures.length) {
  throw new Error(`Learning-material validation failed:\n- ${failures.join("\n- ")}`);
}

const notebookCount = courseArtifacts.reduce((count, item) => count + item.notebooks.length, 0);
const labCount = courseArtifacts.reduce((count, item) => count + item.labs.length, 0);
console.log(
  `Validated ${courseReadmes.length} courses, ${notebookCount} notebooks, ${labCount} labs, ` +
    `${checkpointCount} Hub checkpoints, ${quizIds.length} quiz questions, and ${validatedLinks.size} local links.`,
);
