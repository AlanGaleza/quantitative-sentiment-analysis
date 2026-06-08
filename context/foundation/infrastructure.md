---
project: quantitative-sentiment-analysis
researched_at: 2026-06-08T15:59:20Z
recommended_platform: Render
runner_up: Railway
context_type: mvp
tech_stack:
  language: Python 3.12
  framework: FastAPI
  runtime: uv + Uvicorn
---

## Recommendation

**Deploy on Render.**

Render is the best MVP platform for this project because it supports Python/FastAPI web services directly, detects `uv.lock` and adds uv to the runtime, and still offers free web services suitable for a solo, cost-sensitive MVP preview. Railway scored slightly stronger on agent workflow, and Fly.io remains technically strong for containerized Python, but the interview weighted lowest monthly cost above DX, did not require global edge routing, and allowed external managed services.

## Platform Comparison

Research sources checked on 2026-06-08: Render FastAPI, Free instances, Python version/uv, CLI, rollbacks, and MCP docs; Railway FastAPI and pricing docs; Fly.io pricing docs; Cloudflare Python Workers FastAPI docs; Vercel Functions limits; Netlify Functions overview.

| Platform | CLI-first | Managed/Serverless | Agent-readable docs | Stable deploy API | MCP / Integration | Total | Notes |
|---|---|---|---|---|---|---|---|
| Render | Pass | Pass | Partial | Pass | Pass | 4P / 1Partial | Best cost fit for FastAPI MVP; free web service limitations are acceptable for preview, not production. |
| Railway | Pass | Pass | Pass | Pass | Pass | 5P | Best agent workflow and DX; cost is less attractive than Render for a strict low-cost MVP. |
| Fly.io | Pass | Partial | Pass | Pass | Pass | 4P / 1Partial | Strong container platform and matches the original tech-stack hint, but no free account/free tier for new customers. |
| Cloudflare Workers | Pass | Pass | Pass | Pass | Partial | 4P / 1Partial | Excellent edge/free story, but Python Workers are not a native CPython + Uvicorn deployment target. |
| Vercel | Pass | Pass | Pass | Pass | Partial | 4P / 1Partial | FastAPI is supported, but function duration makes a 5-minute backtest requirement too tight for Hobby. |
| Netlify | Pass | Pass | Pass | Pass | Pass | 5P | Strong platform generally, but Netlify Functions are Node.js/TypeScript/Go, not a FastAPI/Python backend target. |

Render: Official docs cover Python/FastAPI web services and the required `uvicorn main:app --host 0.0.0.0 --port $PORT` shape. Render adds uv automatically when `uv.lock` is present, has a CLI for deploy/log operations, supports rollback through dashboard/API, and has a hosted MCP server for Codex/Cursor/Claude. The hard caveat is Free web services: they spin down after 15 minutes idle, lose local filesystem changes, have monthly limits, and roll back only to the two most recent previous deploys.

Railway: Railway has a first-class MCP server, CLI-driven deploy/log flows, and a public API for deployment operations including rollback and logs. It is the best runner-up when DX matters more than lowest cost. Pricing is still low, but the Free plan gives only a small monthly credit and Hobby is a paid plan, so it loses the cost tie-breaker.

Fly.io: Fly.io is the strongest container/runtime choice and has `flyctl`, logs, deploys, Machines, and a flyctl MCP server. It is less managed than Render/Railway and official docs state there is no free account/free tier for new customers, so it is not the first MVP choice under the cost constraint.

Cloudflare Workers: Workers has excellent free limits, agent-readable docs, and FastAPI support through Python Workers. It is not recommended for this repo because the project is a normal FastAPI/uv/Uvicorn backend and Cloudflare's Python runtime has package/runtime constraints that would shape implementation too early.

Vercel: Vercel supports FastAPI and has strong CLI/MCP/docs. It is not recommended because the Python Function runtime runs as serverless functions and the Hobby maximum duration is 300 seconds, which leaves no margin against the PRD's 5-minute backtest runtime.

Netlify: Netlify has strong CLI, previews, rollbacks, and an MCP server, but its Functions runtime is JavaScript/TypeScript/Go. That fails the Python FastAPI runtime constraint.

### Shortlisted Platforms

#### 1. Render (Recommended)

Render won because it is the cheapest viable path for a basic FastAPI web service, supports uv when `uv.lock` exists, and gives enough platform automation for preview deploys, logs, rollbacks, and agent-assisted operations.

#### 2. Railway

Railway scored second because it has excellent DX, MCP coverage, deployment APIs, and co-located services. It becomes the better choice if the project values speed and agent operations over the lowest possible monthly bill.

#### 3. Fly.io

Fly.io scored third because it is a robust container platform for Python APIs and already matches the original tech-stack hint. It loses for this MVP only because cost was weighted heavily and new users should not assume a free tier.

## Anti-Bias Cross-Check: Render

### Devil's Advocate - Weaknesses

1. The Free web service can spin down after idle time, so first requests and automated smoke tests may observe cold-start delay rather than app behavior.
2. The PRD requires 30 days of backtest processing in <= 5 minutes on a standard developer machine; Render Free is not a reliable performance proxy for that requirement.
3. Free web services have ephemeral local files, so generated datasets must be exported to durable storage or returned immediately, not stored on local disk.
4. Rollback on Free is limited to recent deploy artifacts and does not roll back external state, disks, or database migrations.
5. Render API/MCP keys can be broadly scoped, so agent access must be limited and production-destructive actions need human approval.

### Pre-Mortem - How This Could Fail

The team deploys the FastAPI MVP on Render Free and treats a successful deploy as proof that the infrastructure decision is done. The first backtest endpoint is implemented synchronously and tested mostly on a local development machine. In production preview, the service often wakes from sleep, then spends too long processing 30 days of news on a small free instance. A generated dataset is briefly written to local disk, but later disappears after a redeploy or spin-down. The team then upgrades the instance to reduce runtime, but by then the application has already mixed HTTP request handling, export storage, and long-running processing into one path. The platform choice becomes blamed for a design issue: free web hosting was used as if it were a durable job runner and benchmark environment.

### Unknown Unknowns

- Render Free is good for previewing the platform, not for proving the backtest runtime NFR.
- Free Render Postgres expires after 30 days; do not put reproducibility-critical workspace state there without an upgrade plan.
- Service-initiated outbound traffic can suspend a Free web service if ingestion/export traffic is unusually high.
- `uv.lock` must stay committed at the repo root for Render's uv path to remain predictable.
- If MCP is enabled, the token should not be treated as a narrow read-only log token; Render API keys can expose broad workspace access.

## Operational Story

- **Preview deploys**: Use a Git-backed Render Web Service with service previews for branch/PR validation. Keep previews untrusted; do not expose real workspace datasets or production secrets to them.
- **Secrets**: Store `CRYPTOPANIC_API_KEY`, auth secrets, and export/storage credentials in Render environment variables or external provider secrets. Rotate secrets manually; agent access may read deployment status/logs but must not rotate primary secrets unattended.
- **Rollback**: Use Render's rollback from the service Events page or the Render API Roll back deploy endpoint. Disable or pause auto-deploys before rollback when the bad commit is still on the linked branch.
- **Approval**: A human approves production publish, plan upgrade, secret rotation, database deletion, persistent disk changes, and any operation that can expose workspace data. An agent may run preview deploys and read logs.
- **Logs**: Use `render logs --resources <service_id> --tail --output json` for runtime logs and Render deploy events for build failures. MCP can list services and inspect logs after workspace is selected.

## Risk Register

| Risk | Source | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Free service spin-down makes first requests slow | Research finding / Devil's advocate | High | Medium | Treat Render Free as preview only; run smoke checks after warm-up or upgrade before measuring latency. |
| Backtest exceeds 5 minutes on Free | Pre-mortem | Medium | High | Benchmark locally and on the target instance; move long processing to a job endpoint or paid instance before relying on runtime NFR. |
| Generated datasets lost from local filesystem | Devil's advocate / Research finding | Medium | High | Stream JSONL as response or write exports to durable external storage; never rely on local disk. |
| Free Postgres expiration breaks reproducibility | Unknown unknowns | Medium | High | Use external durable storage or paid database before storing workspace/run metadata. |
| Broad MCP/API token access exposes workspace operations | Unknown unknowns | Medium | High | Keep MCP off production by default; use least-privilege accounts where available and require human approval for destructive actions. |
| Rollback reintroduces bad commit through auto-deploy | Research finding | Low | Medium | Pause auto-deploys or revert the branch before rollback; document rollback runbook when CI is added. |
| Cloudflare/Vercel/Netlify temptation causes runtime mismatch | Devil's advocate | Medium | Medium | Keep this MVP on a normal Python web-service runtime unless implementation is intentionally redesigned for serverless/edge. |

## Getting Started

1. Keep the FastAPI app object importable as `quantitative_sentiment_analysis.main:app`.
2. Keep `pyproject.toml`, `uv.lock`, `.python-version`, and `render.yaml` committed at the repo root; Render detects uv from `uv.lock`.
3. Create the Render service from the GitHub repository Blueprint.
4. Use build command `uv sync --locked` and start command `uv run uvicorn quantitative_sentiment_analysis.main:app --host 0.0.0.0 --port $PORT`.
5. Add only non-production secrets for the first preview deploy; verify `/health` before adding backtest/export routes.

## Out of Scope

The following were not evaluated in this research:

- Docker image configuration
- CI/CD pipeline setup
- Production-scale architecture (multi-region, HA, DR)
