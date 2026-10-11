// Fails if UI source uses wording PRD v2 forbids: health/safety claims, "clean" as a
// status, or attributing readings to immersion. Usage: npm run check:wording

import { readdirSync, readFileSync, statSync } from "node:fs";
import { extname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(fileURLToPath(import.meta.url), "../..");
const SCAN_DIRS = ["app", "components", "lib"];
const SCAN_EXT = new Set([".ts", ".tsx", ".css", ".md", ".mdx"]);
// The generated backend export is data, not UI wording (and .json is not scanned).
const SKIP = [join("lib", "data", "generated")];

const RULES = [
  { name: "toxic", re: /\btoxic\w*/gi },
  { name: "safe / unsafe / safety", re: /\b(?:un)?safe(?:ty)?\b/gi },
  { name: "poison", re: /\bpoison\w*/gi },
  { name: "disease", re: /\bdisease\w*/gi },
  { name: '"clean" as a status (clean-up / cleaning are fine)', re: /\bclean\b(?![-\s]?up)/gi },
  { name: "causal claim about immersion", re: /(?:caused by|due to|because of)\s+(?:the\s+)?immersion|immersion\s+caused/gi },
  // Hindi equivalents
  { name: "सुरक्षित / असुरक्षित (safe / unsafe)", re: /सुरक्षित/g },
  { name: "विषैला / ज़हरीला (toxic)", re: /विषैल|ज़हरील|जहरील/g },
  { name: "स्वच्छ as a status (स्वच्छता is fine)", re: /स्वच्छ(?!ता)/g },
  { name: "बीमारी / रोग (disease)", re: /बीमारी|(?:^|[\s(“"'])रोग/g },
  { name: "विसर्जन के कारण (caused by immersion)", re: /विसर्जन\s+के\s+कारण/g },
];

function walk(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const rel = relative(root, full);
    if (SKIP.some((s) => rel.startsWith(s))) continue;
    if (statSync(full).isDirectory()) walk(full, out);
    else if (SCAN_EXT.has(extname(full))) out.push(full);
  }
  return out;
}

const files = SCAN_DIRS.flatMap((d) => walk(join(root, d)));
const problems = [];

for (const file of files) {
  const lines = readFileSync(file, "utf8").split(/\r?\n/);
  lines.forEach((line, i) => {
    for (const rule of RULES) {
      rule.re.lastIndex = 0;
      let m;
      while ((m = rule.re.exec(line)) !== null) {
        problems.push(`${relative(root, file)}:${i + 1}  [${rule.name}]  "${m[0].trim()}"`);
      }
    }
  });
}

if (problems.length > 0) {
  console.error(`Wording check failed (${problems.length}):\n  ` + problems.join("\n  "));
  process.exit(1);
}
console.log(`Wording check passed: ${files.length} files scanned, ${RULES.length} rules.`);
