---
bootstrapped_at: 2026-06-08T14:31:34Z
starter_id: fastapi
starter_name: FastAPI
project_name: quantitative-sentiment-analysis
language_family: python
package_manager: uv
cwd_strategy: native-cwd
bootstrapper_confidence: first-class
phase_3_status: failed
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
**Exit code**: 2
**Pre-flight files-to-touch**: pyproject.toml, .python-version, README.md, .venv, main.py or application entrypoint files
**Files written by CLI**: 4 observed outputs before failure: pyproject.toml, .python-version, README.md, partial .venv
**Pre-existing files preserved**: main.py, AGENTS.md, LICENSE, .gitignore, context/

**Stdout/stderr (last 20 lines)**:

```text
Initialized project `quantitative-sentiment-analysis` at `/mnt/e/quantitative-sentiment-analysis`
Using CPython 3.12.3 interpreter at: /usr/bin/python3.12
Removed virtual environment at: .venv
Creating virtual environment at: .venv
Resolved 15 packages in 686ms
Downloading pydantic-core (2.0MiB)
 Downloaded pydantic-core
Prepared 13 packages in 259ms
warning: Failed to hardlink files; falling back to full copy. This may lead to degraded performance.
         If the cache and target directories are on different filesystems, hardlinking may not be supported.
         If this is intentional, set `export UV_LINK_MODE=copy` or use `--link-mode=copy` to suppress this warning.
error: Failed to install: annotated_types-0.7.0-py3-none-any.whl (annotated-types==0.7.0)
  Caused by: Failed to copy to `/mnt/e/quantitative-sentiment-analysis/.venv/lib/python3.12/site-packages/annotated_types-0.7.0.dist-info/licenses/.tmp6m4MOP/LICENSE`
  Caused by: failed to copy file from /home/alano/.cache/uv/archive-v0/tcH19hA5IOWrBDe_/annotated_types-0.7.0.dist-info/licenses/LICENSE to /mnt/e/quantitative-sentiment-analysis/.venv/lib/python3.12/site-packages/annotated_types-0.7.0.dist-info/licenses/.tmp6m4MOP/LICENSE: Operation not permitted (os error 1)
```

**.bootstrap-scaffold left in place at**: not created; native-cwd strategy wrote directly into cwd and failed during dependency installation

## Post-scaffold audit

**Audit not run**: scaffold halted during dependency installation; dependency tree was not fully installed.

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

Resolve the virtual environment install failure, then complete dependency installation.

Useful manual checks before retrying:
- `uv --version` now works, so the remaining failure is filesystem/virtualenv installation, not a missing uv binary.
- The project is partially initialized. `pyproject.toml` exists, so re-running the full bootstrap command may not be the best next action.
- Prefer completing the dependency add once the environment issue is resolved: `uv add fastapi uvicorn`.
- If you want a clean bootstrap retry instead, first inspect and intentionally remove or archive the partial scaffold files: `pyproject.toml`, `.python-version`, `README.md`, and `.venv`.
- Keep `context/` unchanged; it is the workflow record and should remain preserved.
