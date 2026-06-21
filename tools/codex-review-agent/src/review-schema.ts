import { z } from "zod";

const ScoreSchema = z.number().int().min(1).max(10);

const CriterionSchema = z
  .object({
    score: ScoreSchema,
    status: z.enum(["pass", "fail", "unknown"]),
    rationale: z.string()
  })
  .strict();

const FindingSchema = z
  .object({
    severity: z.enum(["blocker", "major", "minor"]),
    file: z.string(),
    line: z.number().int().nullable(),
    title: z.string(),
    details: z.string(),
    recommendation: z.string()
  })
  .strict();

export const ReviewSchema = z
  .object({
    summary: z.string(),
    risk_level: z.enum(["low", "medium", "high"]),
    verdict: z.enum(["pass", "fail"]),
    overall_score: ScoreSchema,
    criteria: z
      .object({
        qsa_semantic_safety: CriterionSchema,
        deterministic_data_contracts: CriterionSchema,
        workspace_security_boundaries: CriterionSchema,
        test_verification_discipline: CriterionSchema,
        scope_maintainability_discipline: CriterionSchema
      })
      .strict(),
    findings: z.array(FindingSchema),
    tests_to_run: z.array(z.string()),
    cost_control_note: z.string()
  })
  .strict();

export type Review = z.infer<typeof ReviewSchema>;
