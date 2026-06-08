---
starter_id: fastapi
package_manager: uv
project_name: quantitative-sentiment-analysis
hints:
  language_family: python
  team_size: solo
  deployment_target: fly
  ci_provider: github-actions
  ci_default_flow: auto-deploy-on-merge
  bootstrapper_confidence: first-class
  path_taken: standard
  quality_override: false
  self_check_answers: null
  has_auth: true
  has_payments: false
  has_realtime: false
  has_ai: false
  has_background_jobs: false
---

## Why this stack

FastAPI is the recommended Python starter for an API/backend MVP with a 3-week after-hours timeline, small scale, login/workspace identity, deterministic backtest processing, and JSONL dataset export. It fits the PRD because the product needs explicit request/response contracts, validation-friendly data shapes, and a Python-native path for sentiment scoring and later model-training integration, without committing the PRD to implementation details. The selected path uses uv, deploys to Fly, and runs GitHub Actions with auto-deploy on merge so the bootstrapper can create a lean service foundation quickly.
