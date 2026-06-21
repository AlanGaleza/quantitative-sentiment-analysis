import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { Codex } from "@openai/codex-sdk";

import { ReviewSchema, type Review } from "./review-schema.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const packageRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(packageRoot, "..", "..");
const defaultDiffPath = path.join(packageRoot, "fixtures", "simulated-qsa.diff");
const promptPath = path.join(packageRoot, "prompts", "qsa-code-review.md");
const reviewScoreThreshold = 7;

type CliOptions = {
  diffFile: string;
  dryRun: boolean;
  outputFile: string | null;
  prBody: string;
  prBodyFile: string | null;
  prTitle: string;
};

function parseArgs(argv: string[]): CliOptions {
  const options: CliOptions = {
    diffFile: defaultDiffPath,
    dryRun: false,
    outputFile: null,
    prBody: "",
    prBodyFile: null,
    prTitle: "Local QSA diff review"
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--dry-run") {
      options.dryRun = true;
      continue;
    }
    if (arg === "--diff-file") {
      const value = argv[index + 1];
      if (!value) {
        throw new Error("--diff-file requires a path");
      }
      options.diffFile = path.resolve(process.cwd(), value);
      index += 1;
      continue;
    }
    if (arg === "--output-file") {
      const value = argv[index + 1];
      if (!value) {
        throw new Error("--output-file requires a path");
      }
      options.outputFile = path.resolve(process.cwd(), value);
      index += 1;
      continue;
    }
    if (arg === "--pr-title") {
      const value = argv[index + 1];
      if (!value) {
        throw new Error("--pr-title requires a value");
      }
      options.prTitle = value;
      index += 1;
      continue;
    }
    if (arg === "--pr-body") {
      const value = argv[index + 1];
      if (value === undefined) {
        throw new Error("--pr-body requires a value");
      }
      options.prBody = value;
      index += 1;
      continue;
    }
    if (arg === "--pr-body-file") {
      const value = argv[index + 1];
      if (!value) {
        throw new Error("--pr-body-file requires a path");
      }
      options.prBodyFile = path.resolve(process.cwd(), value);
      index += 1;
      continue;
    }
    throw new Error(`Unknown argument: ${arg}`);
  }

  return options;
}

function resultToText(result: unknown): string {
  if (typeof result === "string") {
    return result;
  }

  if (result && typeof result === "object") {
    const record = result as Record<string, unknown>;
    for (const key of ["finalResponse", "final_response", "output", "response", "text"]) {
      const value = record[key];
      if (typeof value === "string") {
        return value;
      }
    }
  }

  return JSON.stringify(result, null, 2);
}

function extractJsonObject(text: string): unknown {
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
  const candidate = fenced?.[1] ?? text;
  const start = candidate.indexOf("{");
  const end = candidate.lastIndexOf("}");

  if (start === -1 || end === -1 || end <= start) {
    throw new Error("Codex response did not contain a JSON object");
  }

  return JSON.parse(candidate.slice(start, end + 1));
}

async function readPrBody(options: CliOptions): Promise<string> {
  const bodyParts = [];
  if (options.prBody.trim()) {
    bodyParts.push(options.prBody.trim());
  }
  if (options.prBodyFile) {
    const fileBody = await readFile(options.prBodyFile, "utf8");
    if (fileBody.trim()) {
      bodyParts.push(fileBody.trim());
    }
  }

  return bodyParts.join("\n\n") || "(empty PR body)";
}

function replaceAllLiteral(input: string, search: string, value: string): string {
  return input.split(search).join(value);
}

async function buildPrompt(options: CliOptions): Promise<string> {
  const [template, diff, prBody] = await Promise.all([
    readFile(promptPath, "utf8"),
    readFile(options.diffFile, "utf8"),
    readPrBody(options)
  ]);

  return [
    ["{{PR_TITLE}}", options.prTitle.trim() || "Untitled PR"],
    ["{{PR_BODY}}", prBody],
    ["{{DIFF}}", diff.trim()]
  ].reduce(
    (prompt, [placeholder, value]) => replaceAllLiteral(prompt, placeholder, value),
    template
  );
}

function evaluateReviewGate(review: Review): string[] {
  const failures = [];

  if (review.verdict === "fail") {
    failures.push("verdict is fail");
  }

  if (review.findings.some((finding) => finding.severity === "blocker")) {
    failures.push("at least one finding is a blocker");
  }

  for (const [criterionName, criterion] of Object.entries(review.criteria)) {
    if (criterion.score < reviewScoreThreshold) {
      failures.push(`${criterionName} score ${criterion.score} is below ${reviewScoreThreshold}`);
    }
  }

  if (review.overall_score < reviewScoreThreshold) {
    failures.push(`overall_score ${review.overall_score} is below ${reviewScoreThreshold}`);
  }

  return failures;
}

async function writeReviewOutput(outputFile: string | null, reviewText: string): Promise<void> {
  if (!outputFile) {
    return;
  }

  await mkdir(path.dirname(outputFile), { recursive: true });
  await writeFile(outputFile, `${reviewText}\n`, "utf8");
}

async function main(): Promise<void> {
  const options = parseArgs(process.argv.slice(2));
  const prompt = await buildPrompt(options);

  if (options.dryRun) {
    console.log(prompt);
    return;
  }

  const codex = new Codex(
    process.env.OPENAI_API_KEY ? { apiKey: process.env.OPENAI_API_KEY } : {}
  );
  const thread = codex.startThread({
    approvalPolicy: "never",
    sandboxMode: "read-only",
    workingDirectory: repoRoot
  });
  const result = await thread.run(prompt);
  const text = resultToText(result);

  try {
    const parsed = ReviewSchema.safeParse(extractJsonObject(text));
    if (!parsed.success) {
      console.error("Codex returned JSON, but it did not match the review schema.");
      console.error(parsed.error.format());
      console.log(text);
      process.exitCode = 1;
      return;
    }

    const reviewText = JSON.stringify(parsed.data, null, 2);
    await writeReviewOutput(options.outputFile, reviewText);
    console.log(reviewText);

    const gateFailures = evaluateReviewGate(parsed.data);
    if (gateFailures.length > 0) {
      console.error("Review gate failed:");
      for (const failure of gateFailures) {
        console.error(`- ${failure}`);
      }
      process.exitCode = 1;
    }
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    console.log(text);
    process.exitCode = 1;
  }
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
