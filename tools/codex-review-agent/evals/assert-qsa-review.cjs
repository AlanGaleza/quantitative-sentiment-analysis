const REQUIRED_CRITERIA = [
  "qsa_semantic_safety",
  "deterministic_data_contracts",
  "workspace_security_boundaries",
  "test_verification_discipline",
  "scope_maintainability_discipline"
];

const VALID_RISK_LEVELS = new Set(["low", "medium", "high"]);
const VALID_VERDICTS = new Set(["pass", "fail"]);
const VALID_STATUSES = new Set(["pass", "fail", "unknown"]);
const VALID_SEVERITIES = new Set(["blocker", "major", "minor"]);

function isRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isScore(value) {
  return Number.isInteger(value) && value >= 1 && value <= 10;
}

function stringifyOutput(output) {
  return typeof output === "string" ? output : JSON.stringify(output, null, 2);
}

function extractJsonObject(output) {
  const text = stringifyOutput(output).trim();
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
  const candidate = (fenced?.[1] ?? text).trim();

  try {
    return JSON.parse(candidate);
  } catch (_error) {
    const start = candidate.indexOf("{");
    const end = candidate.lastIndexOf("}");
    if (start === -1 || end === -1 || end <= start) {
      throw new Error("Output does not contain a JSON object");
    }
    return JSON.parse(candidate.slice(start, end + 1));
  }
}

function validateReviewShape(review) {
  const failures = [];

  if (!isRecord(review)) {
    return ["Review output must be a JSON object"];
  }

  if (typeof review.summary !== "string" || review.summary.length === 0) {
    failures.push("summary must be a non-empty string");
  }
  if (!VALID_RISK_LEVELS.has(review.risk_level)) {
    failures.push("risk_level must be low, medium, or high");
  }
  if (!VALID_VERDICTS.has(review.verdict)) {
    failures.push("verdict must be pass or fail");
  }
  if (!isScore(review.overall_score)) {
    failures.push("overall_score must be an integer from 1 to 10");
  }

  if (!isRecord(review.criteria)) {
    failures.push("criteria must be an object");
  } else {
    for (const criterionName of REQUIRED_CRITERIA) {
      const criterion = review.criteria[criterionName];
      if (!isRecord(criterion)) {
        failures.push(`${criterionName} criterion is missing`);
        continue;
      }
      if (!isScore(criterion.score)) {
        failures.push(`${criterionName}.score must be an integer from 1 to 10`);
      }
      if (!VALID_STATUSES.has(criterion.status)) {
        failures.push(`${criterionName}.status must be pass, fail, or unknown`);
      }
      if (typeof criterion.rationale !== "string" || criterion.rationale.length === 0) {
        failures.push(`${criterionName}.rationale must be a non-empty string`);
      }
    }
  }

  if (!Array.isArray(review.findings)) {
    failures.push("findings must be an array");
  } else {
    for (const [index, finding] of review.findings.entries()) {
      if (!isRecord(finding)) {
        failures.push(`findings[${index}] must be an object`);
        continue;
      }
      if (!VALID_SEVERITIES.has(finding.severity)) {
        failures.push(`findings[${index}].severity must be blocker, major, or minor`);
      }
      for (const key of ["file", "title", "details", "recommendation"]) {
        if (typeof finding[key] !== "string" || finding[key].length === 0) {
          failures.push(`findings[${index}].${key} must be a non-empty string`);
        }
      }
      if (finding.line !== null && !Number.isInteger(finding.line)) {
        failures.push(`findings[${index}].line must be an integer or null`);
      }
    }
  }

  if (!Array.isArray(review.tests_to_run) || review.tests_to_run.some((item) => typeof item !== "string")) {
    failures.push("tests_to_run must be a string array");
  }
  if (typeof review.cost_control_note !== "string" || review.cost_control_note.length === 0) {
    failures.push("cost_control_note must be a non-empty string");
  }

  return failures;
}

function validateExpectedBehavior(review, config = {}) {
  const failures = [];

  if (config.expectedVerdict && review.verdict !== config.expectedVerdict) {
    failures.push(`expected verdict ${config.expectedVerdict}, got ${review.verdict}`);
  }

  if (Number.isInteger(config.minFindings) && review.findings.length < config.minFindings) {
    failures.push(`expected at least ${config.minFindings} finding(s), got ${review.findings.length}`);
  }
  if (Number.isInteger(config.maxFindings) && review.findings.length > config.maxFindings) {
    failures.push(`expected at most ${config.maxFindings} finding(s), got ${review.findings.length}`);
  }

  if (Number.isInteger(config.minOverallScore) && review.overall_score < config.minOverallScore) {
    failures.push(`overall_score expected >= ${config.minOverallScore}, got ${review.overall_score}`);
  }

  for (const [criterionName, maxScore] of Object.entries(config.maxScores ?? {})) {
    const criterion = review.criteria?.[criterionName];
    if (!criterion) {
      failures.push(`missing score for ${criterionName}`);
      continue;
    }
    if (criterion.score > maxScore) {
      failures.push(`${criterionName}.score expected <= ${maxScore}, got ${criterion.score}`);
    }
  }
  for (const [criterionName, minScore] of Object.entries(config.minScores ?? {})) {
    const criterion = review.criteria?.[criterionName];
    if (!criterion) {
      failures.push(`missing score for ${criterionName}`);
      continue;
    }
    if (criterion.score < minScore) {
      failures.push(`${criterionName}.score expected >= ${minScore}, got ${criterion.score}`);
    }
  }

  const haystack = JSON.stringify(review).toLowerCase();
  for (const evidenceGroup of config.requiredEvidence ?? []) {
    const terms = Array.isArray(evidenceGroup) ? evidenceGroup : [evidenceGroup];
    const matched = terms.some((term) => haystack.includes(String(term).toLowerCase()));
    if (!matched) {
      failures.push(`missing expected evidence term from group: ${terms.join(" | ")}`);
    }
  }

  return failures;
}

function assertQsaReview(output, context = {}) {
  try {
    const review = extractJsonObject(output);
    const failures = [
      ...validateReviewShape(review),
      ...validateExpectedBehavior(review, context.config ?? {})
    ];

    return {
      pass: failures.length === 0,
      score: failures.length === 0 ? 1 : 0,
      reason: failures.length === 0 ? "QSA review contract matched expectations" : failures.join("; ")
    };
  } catch (error) {
    return {
      pass: false,
      score: 0,
      reason: error instanceof Error ? error.message : String(error)
    };
  }
}

module.exports = assertQsaReview;
module.exports._private = {
  extractJsonObject,
  validateExpectedBehavior,
  validateReviewShape
};
