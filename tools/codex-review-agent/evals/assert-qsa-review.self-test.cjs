const assert = require("node:assert/strict");

const assertQsaReview = require("./assert-qsa-review.cjs");

const config = {
  expectedVerdict: "fail",
  minFindings: 1,
  maxScores: {
    qsa_semantic_safety: 6,
    deterministic_data_contracts: 6
  },
  requiredEvidence: [
    ["live-ready trading signals", "trading signals"],
    ["datetime.now", "generated_at", "wall-clock"],
    ["stable sorting", "nondeterministic", "input order"]
  ]
};

const matchingReview = {
  summary: "The diff removes stable sorting, adds generated_at from datetime.now, and introduces live-ready trading signals wording.",
  risk_level: "high",
  verdict: "fail",
  overall_score: 5,
  criteria: {
    qsa_semantic_safety: {
      score: 4,
      status: "fail",
      rationale: "The copy now says live-ready trading signals instead of BACKTEST directional bias."
    },
    deterministic_data_contracts: {
      score: 4,
      status: "fail",
      rationale: "Removing stable sorting and adding wall-clock generated_at breaks deterministic JSONL."
    },
    workspace_security_boundaries: {
      score: 8,
      status: "pass",
      rationale: "No workspace boundary change is visible."
    },
    test_verification_discipline: {
      score: 6,
      status: "fail",
      rationale: "The risky diff does not include targeted tests."
    },
    scope_maintainability_discipline: {
      score: 7,
      status: "pass",
      rationale: "The scope is small, but the behavior is unsafe."
    }
  },
  findings: [
    {
      severity: "major",
      file: "src/quantitative_sentiment_analysis/backtest_dataset/export.py",
      line: 12,
      title: "Generated timestamp breaks deterministic JSONL",
      details: "datetime.now is serialized into generated_at for every export.",
      recommendation: "Remove wall-clock metadata from deterministic exports."
    }
  ],
  tests_to_run: ["npm --prefix tools/codex-review-agent run review:dry"],
  cost_control_note: "The review is bounded to the provided diff."
};

const falsePassReview = {
  ...matchingReview,
  summary: "Looks fine.",
  verdict: "pass",
  overall_score: 9,
  criteria: {
    ...matchingReview.criteria,
    qsa_semantic_safety: {
      score: 9,
      status: "pass",
      rationale: "No issue."
    },
    deterministic_data_contracts: {
      score: 9,
      status: "pass",
      rationale: "No issue."
    }
  },
  findings: []
};

const fencedResult = assertQsaReview(`\`\`\`json\n${JSON.stringify(matchingReview)}\n\`\`\``, { config });
assert.equal(fencedResult.pass, true, fencedResult.reason);

const failedResult = assertQsaReview(JSON.stringify(falsePassReview), { config });
assert.equal(failedResult.pass, false, "false-pass review should fail assertions");
assert.match(failedResult.reason, /expected verdict fail|qsa_semantic_safety\.score|expected at least/);

const invalidJsonResult = assertQsaReview("not json", { config });
assert.equal(invalidJsonResult.pass, false, "non-JSON output should fail assertions");

const expectedPassReview = {
  ...matchingReview,
  summary: "The workflow-only diff is scoped and keeps QSA domain contracts unchanged.",
  risk_level: "low",
  verdict: "pass",
  overall_score: 8,
  criteria: {
    qsa_semantic_safety: {
      score: 10,
      status: "pass",
      rationale: "No live trading, broker, order, or investment recommendation behavior is added."
    },
    deterministic_data_contracts: {
      score: 10,
      status: "pass",
      rationale: "No JSONL export or deterministic dataset behavior changes."
    },
    workspace_security_boundaries: {
      score: 8,
      status: "pass",
      rationale: "GitHub comment permissions are scoped to the review workflow."
    },
    test_verification_discipline: {
      score: 7,
      status: "pass",
      rationale: "The change can be verified through a PR workflow run."
    },
    scope_maintainability_discipline: {
      score: 8,
      status: "pass",
      rationale: "The change stays focused on review workflow output."
    }
  },
  findings: []
};

const expectedPassResult = assertQsaReview(JSON.stringify(expectedPassReview), {
  config: {
    expectedVerdict: "pass",
    minOverallScore: 7,
    minScores: {
      qsa_semantic_safety: 7,
      deterministic_data_contracts: 7,
      workspace_security_boundaries: 7,
      scope_maintainability_discipline: 7
    }
  }
});
assert.equal(expectedPassResult.pass, true, expectedPassResult.reason);

const lowScorePassResult = assertQsaReview(
  JSON.stringify({
    ...expectedPassReview,
    overall_score: 6,
    criteria: {
      ...expectedPassReview.criteria,
      scope_maintainability_discipline: {
        ...expectedPassReview.criteria.scope_maintainability_discipline,
        score: 6
      }
    }
  }),
  {
    config: {
      expectedVerdict: "pass",
      minOverallScore: 7,
      minScores: {
        scope_maintainability_discipline: 7
      }
    }
  }
);
assert.equal(lowScorePassResult.pass, false, "expected-pass review with low score should fail assertions");

console.log("QSA promptfoo assertion self-test passed.");
