import { access, readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = process.cwd();
const page = await readFile(resolve(root, "app/page.tsx"), "utf8");
const paths = [...page.matchAll(/(?:notebook|refs):\s*(?:"([^"]+)"|\[([\s\S]*?)\])/g)]
  .flatMap((match) => (match[1] ? [match[1]] : [...match[2].matchAll(/"([^"]+)"/g)].map((item) => item[1])));
const localPaths = [...page.matchAll(/curriculum\/[A-Za-z0-9_./-]+\.(?:md|ipynb)(?:#[A-Za-z0-9_-]+)?/g)]
  .map((match) => match[0].split("#")[0]);

for (const path of [...new Set([...paths, ...localPaths])]) {
  if (/^https?:\/\//.test(path)) continue;
  try {
    await access(resolve(root, path.split("#")[0]));
  } catch {
    throw new Error(`Learning Hub link does not exist: ${path}`);
  }
}

const uniquePaths = [...new Set([...paths, ...localPaths])];
console.log(`Validated ${uniquePaths.length} learning material links.`);
