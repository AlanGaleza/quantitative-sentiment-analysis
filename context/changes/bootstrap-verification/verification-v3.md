---
bootstrapped_at: 2026-06-08T14:41:35Z
starter_id: fastapi
starter_name: FastAPI
project_name: quantitative-sentiment-analysis
language_family: python
package_manager: uv
cwd_strategy: native-cwd
bootstrapper_confidence: first-class
phase_3_status: ok
audit_command: pip-audit
---

## Hand-off

```yaml
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
```

FastAPI is the recommended Python starter for an API/backend MVP with a 3-week after-hours timeline, small scale, login/workspace identity, deterministic backtest processing, and JSONL dataset export. It fits the PRD because the product needs explicit request/response contracts, validation-friendly data shapes, and a Python-native path for sentiment scoring and later model-training integration, without committing the PRD to implementation details. The selected path uses uv, deploys to Fly, and runs GitHub Actions with auto-deploy on merge so the bootstrapper can create a lean service foundation quickly.

## Pre-scaffold verification

| Signal | Value | Severity | Notes |
| --- | --- | --- | --- |
| npm package | not run | n/a | non-JS starter |
| GitHub repo | not run | n/a | card docs_url is not a GitHub repository URL |

## Scaffold log

**Resolved invocation**: `uv init . && uv add fastapi uvicorn`
**Strategy**: native-cwd
**Exit code**: 0 after dependency repair and final confirmation
**Pre-flight files-to-touch**: pyproject.toml, .python-version, README.md, .venv, uv.lock, main.py or application entrypoint files
**Files written by CLI**: pyproject.toml, .python-version, README.md, .venv, uv.lock
**Pre-existing files preserved**: main.py, AGENTS.md, LICENSE, .gitignore, context/

The original starter command was completed across multiple attempts: `uv init .` created the project files, dependency installation initially failed on the `/mnt/e` virtualenv, the user requested sudo installation, and the environment was repaired by reinstalling the incomplete `annotated-doc` and `annotated-types` packages. Final confirmation command:

```text
UV_LINK_MODE=copy uv add fastapi uvicorn
```

Final confirmation output:

```text
Resolved 15 packages in 4ms
Checked 13 packages in 51ms
```

Import verification:

```text
fastapi 0.136.3
uvicorn 0.49.0
uv pip check: All installed packages are compatible
```

## Post-scaffold audit

**Tool**: `pip-audit --format json`
**Status**: failed to run
**Reason**: `pip-audit` is not installed in this shell.

Compatibility check did run successfully:

```text
uv pip check
Checked 13 packages in 122ms
All installed packages are compatible
```

## Hints recorded but not acted on

| Hint | Value |
| --- | --- |
| bootstrapper_confidence | first-class |
| quality_override | false |
| path_taken | standard |
| self_check_answers | null |
| team_size | solo |
| deployment_target | fly |
| ci_provider | github-actions |
| ci_default_flow | auto-deploy-on-merge |
| has_auth | true |
| has_payments | false |
| has_realtime | false |
| has_ai | false |
| has_background_jobs | false |

## Next steps

Next: a future skill will set up agent context (CLAUDE.md, AGENTS.md). For now, your project is scaffolded and verified.

Useful manual steps in the meantime:
- Review ownership on `.venv`, `pyproject.toml`, and `uv.lock` because dependency repair used sudo.
- Install `pip-audit` if you want the bootstrapper audit command to run later.
- Review `main.py`; it predates the scaffold and remains the current application entrypoint placeholder.
