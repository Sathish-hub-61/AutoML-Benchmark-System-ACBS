# ACBS Independent Verification & Audit Report

**Date of Audit:** October 31, 2026  
**Auditor Role:** Independent QA & Release Auditor  
**Scope:** Verification of 27 Audit Defects (Phases 0–3) & 13 v3 Redesign Requirements (Phases 4–7)  
**Target Specifications:** `ACBS_Master_Fix_Prompt.md`, `ACBS_v3_Master_Design.md`, `docs/AUDIT_TRACKER.md`  

---

## 1. Executive Summary & Verification Counts

### Defect Verification Summary (27 Audit Items)
| Status | Count | Percentage |
|---|:---:|:---:|
| **PASS** | 0 | 0.0% |
| **PARTIAL** | 2 | 7.4% |
| **FAIL** | 25 | 92.6% |
| **NOT VERIFIED** | 0 | 0.0% |
| **TOTAL** | **27** | **100.0%** |

### Redesign Verification Summary (13 Architecture Items)
| Status | Count | Percentage |
|---|:---:|:---:|
| **PASS** | 1 | 7.7% |
| **PARTIAL** | 6 | 46.2% |
| **FAIL** | 6 | 46.2% |
| **NOT VERIFIED** | 0 | 0.0% |
| **TOTAL** | **13** | **100.0%** |

### Final Release Verdict
> **VERDICT: Not complete.**  
> *The repository is currently at Phase 0 baseline safety net; Phases 1 through 7 remediation claims have not been implemented in source code, all 27 regression tests are missing from the test suite, and the legacy classic tier remains active.*

---

## 2. Baseline Status (Step 0)

- **Git Commit / Head:** `2e7b3e7` (`chore(phase-0): baseline safety net, audit tracker, and smoke check`)
- **Git Branch:** `fix/phase-0-safety-net`
- **Git Tags:** `v1-classic-audit` (present at commit `923ce35`)
- **Git Working Tree:** Clean (`nothing to commit, working tree clean`)
- **Test Suite Execution:**
  - **Command:** `.venv\Scripts\python.exe -m pytest tests/ -v`
  - **Result:** **101 passed, 0 failed, 0 skipped, 0 xfail in 19.47s**
  - **Warnings (4):**
    1. `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.`
    2. `Pandas4Warning: For backward compatibility, 'str' dtypes are included by select_dtypes when 'object' dtype is specified.` in `src/acbs/automl/workers/gama_worker.py:30` (x2)
    3. `UndefinedMetricWarning: Only one class is present in y_true. ROC AUC score is not defined in that case.` in `tests/benchmark/test_metrics.py`
- **Linter Check:**
  - **Command:** `.venv\Scripts\python.exe -m ruff check src tests app scripts`
  - **Result:** **All checks passed!**
- **Audit Tracker Discrepancy:**
  - `docs/AUDIT_TRACKER.md` lists 27 planned regression test names (e.g. `test_encode_target_rejects_missing_values`, `test_upload_atomic_uuid_storage`).
  - **Verification:** Searched all files under `tests/`. **All 27 regression tests are MISSING** from the test suite.

---

## 3. Detailed Audit Findings: 27 Defects (Step 1)

| Defect ID | Phase | Severity | Status | Verifying Test Claimed | Actual Test in Suite | Evidence & Empirical Reproduction | Notes & Smallest Fix Needed |
|---|---|---|:---:|---|:---:|---|---|
| **BUG-CRIT-01** | Phase 3 | Critical | **FAIL** | `test_automl_model_export_roundtrip` | ❌ Missing | `src/acbs/models/export.py:251-285`<br>Calling export generates `load_snippet.py` with print comments (`# predictor = TabularPredictor.load(...)`). No model binaries saved in zip. | Persist fitted model folder from worker into export temp dir and bundle into zip with real `predict.py`. |
| **BUG-CRIT-02** | Phase 1 | Critical | **FAIL** | `test_encode_target_rejects_missing_values` | ❌ Missing | `src/acbs/data/loader.py:77`<br>Executed 60-row CSV with 1 NaN target. Generated classes: `['0.0', '1.0', 'nan']` and mapping: `{'0.0': 0, '1.0': 1, 'nan': 2}`. 5% missing target threshold not enforced. | Drop NaN target rows in `_clean_frame`/`_from_frame`, raise `DatasetError` if missing > 5%, reject if < 2 classes remain. |
| **BUG-CRIT-03** | Phase 2 | Critical | **FAIL** | `test_cors_origins_configured_from_env` | ❌ Missing | `src/acbs/api/main.py:11`<br>`allow_origins=["*"]`. Request from `https://malicious-site.com` returned `access-control-allow-origin: *`. `ACBS_CORS_ORIGINS` environment variable ignored. | Parse `ACBS_CORS_ORIGINS` env var into allowlist; default to frontend origin; reject foreign origins. |
| **BUG-CRIT-04** | Phase 2 | Critical | **FAIL** | `test_concurrent_experiments_queued` | ❌ Missing | `src/acbs/storage/models.py:100`<br>SQLite pragma check returned `journal_mode: delete`. Concurrency queue and restart recovery to `interrupted` status absent. | Set `PRAGMA journal_mode=WAL;` and `PRAGMA busy_timeout=10000;` on engine connect. Add queue semaphore. |
| **BUG-CRIT-05** | Phase 4 | Critical | **FAIL** | N/A (Architectural removal) | ❌ Missing | `src/acbs/models/export.py:84,91-194`<br>`_bundle_classic_model()` is still active and invoked when `not is_automl`. Classic export code was not deleted. | Remove classic model export logic when retiring classic ML tier. |
| **BUG-CRIT-06** | Phase 2 | Critical | **FAIL** | `test_api_token_auth_and_rate_limiting` | ❌ Missing | `src/acbs/api/main.py`<br>Zero occurrences of `ACBS_API_TOKEN` across repository. All API routes accept unauthenticated calls. No rate limiting middleware. | Implement FastAPI security dependency checking `Bearer` token against `ACBS_API_TOKEN`; add token-bucket rate limiter. |
| **BUG-HIGH-01** | Phase 2 | High | **FAIL** | `test_upload_atomic_uuid_storage` | ❌ Missing | `src/acbs/api/routes/datasets.py:76-78`<br>Direct file write: `dest = UPLOAD_DIR / name`. Two concurrent uploads of `data.csv` overwrite identical path on disk. | Save incoming stream as `data/raw/<uuid4>.<ext>`, storing original filename only in `meta.original_filename`. |
| **BUG-HIGH-02** | Phase 1 | High | **FAIL** | `test_target_detection_european_csv_semicolon` | ❌ Missing | `src/acbs/data/loader.py:137`<br>Loaded semicolon CSV `semi.csv`. Failed with `TargetNotFoundError: Target column 'target' not found. Columns: ['f1;f2;target']`. | Use `csv.Sniffer` with fallback delimiters `[',', ';', '\t', '\|']` in `load_local` and `detect_target`. |
| **BUG-HIGH-03** | Phase 1 | High | **FAIL** | `test_profiler_never_drops_last_remaining_feature` | ❌ Missing | `src/acbs/data/profiler.py:80-85`<br>Evaluated single-feature ID dataset: `suggested_drop_columns: ['id']` leaving 0 features. No safety check for last feature. | In `profile_dataset`, never suggest dropping a column if it leaves 0 remaining features; raise `DatasetError("no usable features")`. |
| **BUG-HIGH-04** | Phase 1 | High | **FAIL** | `test_loader_replaces_infinities_with_nan` | ❌ Missing | `src/acbs/data/loader.py:45-58`<br>Created dataset with `+inf` and `-inf`. `_from_frame()` preserved infinite values directly in `X` (`inf_count = 2`). | In `_clean_frame`, replace `np.inf` and `-np.inf` with `np.nan` and log replacement count. |
| **BUG-HIGH-05** | Phase 6 | High | **FAIL** | `test_advisor_prompt_injection_isolation` | ❌ Missing | `src/acbs/recommend/advisor.py:97`<br>Prompt built via raw concatenation: `f"User question: {ask}"`. Unsanitized injections pass directly to LLM. | Wrap user query in XML tags `<user_query>` with strict system instructions and refusal guards against instruction overrides. |
| **BUG-HIGH-06** | Phase 2 | High | **FAIL** | `test_upload_rejects_reserved_windows_names` | ❌ Missing | `src/acbs/api/routes/datasets.py:63`<br>Uploaded `con.csv` with explicit target. Server returned HTTP 200 and wrote `data/raw/con.csv`. | Add DOS device name check rejecting `CON, PRN, AUX, NUL, COM1-9, LPT1-9` regardless of case/extension. |
| **BUG-HIGH-07** | Phase 5 | High | **FAIL** | `test_results_view_renders_table_without_recommendation` | ❌ Missing | `app/views/results.py:27-30`<br>`try: rec = recommendation(exp_id) except ApiError: return`. Early return prevents `render_metrics_table(df)` from displaying. | In `results.py`, catch `ApiError` on recommendation and continue rendering `render_metrics_table(df)`. |
| **BUG-HIGH-08** | Phase 3 | High | **FAIL** | `test_ipc_parquet_file_based_memory_flat` | ❌ Missing | `src/acbs/automl/contracts.py:81-83`<br>`TrainSpec` serializes `X_train.values.tolist()` and passes JSON over stdin. Peak memory spikes on large tables. | Write split partitions to temporary Parquet files and pass file paths in `TrainSpec`. |
| **BUG-MED-01** | Phase 2 | Medium | **FAIL** | `test_export_temp_dir_cleaned_after_response` | ❌ Missing | `src/acbs/models/export.py:74`<br>`tempfile.mkdtemp(prefix=f"acbs_export_exp{...}")`. Returned via `FileResponse` in `experiments.py:353` with no background cleanup task. | Add `background_tasks.add_task(shutil.rmtree, target_dir)` to `FileResponse`. |
| **BUG-MED-02** | Phase 1 | Medium | **FAIL** | `test_encode_target_preserves_numeric_order` | ❌ Missing | `src/acbs/data/loader.py:77`<br>Labels `[1, 2, 10]` encoded via string conversion into `{'1': 0, '10': 1, '2': 2}` ('10' precedes '2'). | Sort classes numerically if all values are numeric prior to label encoding. |
| **BUG-MED-03** | Phase 2 | Medium | **FAIL** | `test_cancellation_persisted_in_db` | ❌ Missing | `src/acbs/api/routes/experiments.py:30`<br>`_CANCELLED: set[int] = set()`. Set is lost on process restart; not persisted in database. | Store cancellation state in `experiments.status = 'cancelled'` or cancellation table in DB. |
| **BUG-MED-04** | Phase 3 | Medium | **FAIL** | `test_amlb_inference_benchmark_protocol` | ❌ Missing | `src/acbs/benchmark/timing.py:19`<br>Calculates latency via `elapsed * per / n` with 5 repeats instead of median rows/sec for 1 and 10,000 rows. | Implement benchmark protocol measuring median rows/sec over 10 repeats for batch sizes 1 and 10,000. |
| **BUG-MED-05** | Phase 1 | Medium | **FAIL** | `test_load_local_sniffs_delimiter_and_decimals` | ❌ Missing | `src/acbs/data/loader.py:137`<br>Hardcoded `pd.read_csv(path, sep=",")`. Does not handle European decimal comma (`1,5` instead of `1.5`). | Pass `decimal=","` when comma-separated decimals detected or use sniffed separator/decimal parameters. |
| **BUG-MED-06** | Phase 1 | Medium | **FAIL** | `test_rerank_unsatisfiable_constraints_returns_422` | ❌ Missing | `src/acbs/api/routes/experiments.py:66,307`<br>`_recommend()` raises `ValueError("No models satisfied the constraints")` causing an unhandled HTTP 500 error. | Wrap `_recommend` in `rerank` route: catch `ValueError` and return `HTTPException(422, detail=...)` with closest feasible values. |
| **BUG-MED-07** | Phase 6 | Medium | **FAIL** | `test_advisor_async_nonblocking_execution` | ❌ Missing | `src/acbs/recommend/advisor.py:140`<br>Synchronous `httpx.post()` called directly in synchronous route `ask_advisor()`, blocking the event loop worker thread. | Convert `narrate()` to `async def narrate()` using `httpx.AsyncClient` or offload via `run_in_threadpool`. |
| **BUG-MED-08** | Phase 3 | Medium | **FAIL** | `test_gama_worker_no_pandas_deprecations` | ❌ Missing | `src/acbs/automl/workers/gama_worker.py:30`<br>`Pandas4Warning: For backward compatibility, 'str' dtypes are included by select_dtypes when 'object' dtype is specified.` | Update `select_dtypes(include=['category', 'object', 'str'])` or convert explicitly to string dtypes. |
| **BUG-MED-09** | Phase 1 | Medium | **PARTIAL** | `test_profiler_outlier_share_nan_safe` | ❌ Missing | `src/acbs/data/profiler.py:124`<br>`mask.stack().mean()`. Computed 0.0 with NaNs present, but does not use `future_stack=True` or column-wise safe mean. | Add `future_stack=True` or compute column-wise outlier ratio to prevent deprecation and indexing ambiguities. |
| **BUG-LOW-01** | Phase 2 | Low | **FAIL** | Pytest suite hygiene | ❌ Missing | `fastapi/testclient.py:1`<br>`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` | Upgrade `httpx2` or configure pytest warning filter in `pyproject.toml`. |
| **BUG-LOW-02** | Phase 2 | Low | **FAIL** | `test_web_api_relative_urls` | ❌ Missing | `web/js/api.js:4`<br>`const API_BASE = "";` without environment or window override; API mounted at root `/` rather than `/api/`. | Set `const API_BASE = window.ACBS_API_BASE \|\| "/api";` and mount API routers under `/api`. |
| **BUG-LOW-03** | Phase 2 | Low | **PARTIAL** | `test_api_404_returns_json_not_html` | ❌ Missing | `http://127.0.0.1:8000/api/xyz` returned JSON 404 (`{"detail":"Not Found"}`), but `/api/health` also returned 404 because routes lack `/api` prefix. | Prefix all API routers with `/api` so routes match `/api/...` uniformly. |
| **BUG-LOW-04** | Phase 3 | Low | **FAIL** | `test_workers_report_exact_package_versions` | ❌ Missing | `src/acbs/automl/contracts.py:93-132`<br>`RunResult` contains `framework_version` but lacks `python_version` and system dependency metadata. | Include `python_version` and snapshot of installed environment packages in `RunResult.extra`. |

---

## 4. Detailed Redesign Verification (Step 2: 13 Requirements)

| # | Redesign Requirement | Status | Evidence & Verification Commands | Gaps / Missing Items |
|---|---|:---:|---|---|
| **1** | **Classic tier removed**<br>(no models/, tuning/, optuna, imbalanced-learn, streamlit) | **FAIL** | `src/acbs/models/registry.py` still implements 8 classic models.<br>`src/acbs/benchmark/tuner.py` still exists.<br>`pyproject.toml` lines 17, 18, 29 still require `imbalanced-learn`, `optuna`, and `streamlit`.<br>`app/streamlit_app.py` is still present. | Classic tier, tuning module, and dependencies were not removed. |
| **2** | **Constant predictor floor**<br>(baseline floor, scaled score formula) | **FAIL** | `src/acbs/models/registry.py:86` has `_dummy` as a regular model contender, not as a separate baseline floor.<br>`src/acbs/recommend/scoring.py` does not implement `(score - floor) / (best - floor)`. | Baseline scoring floor and normalized scoring formula are absent. |
| **3** | **9 frameworks in frameworks.yaml**<br>(Auto-sklearn present with OS reason, NaiveAutoML experimental) | **FAIL** | `envs/frameworks.yaml` lists only 8 frameworks. Auto-sklearn was completely deleted in commit `69de55b` instead of registered with an unsupported OS reason. Config file lives at `envs/` instead of `configs/`. | Auto-sklearn missing from registry; file location mismatch. |
| **4** | **AMLB protocol**<br>(identical outer folds, central scoring, timeouts) | **PARTIAL** | Host evaluates probabilities centrally via `evaluate_automl_result()` (`engine.py:343`). However, `engine.py:331-335` passes only a single train/test split to AutoML, not $k$-fold cross-validation. AMLB results.csv format missing. | Full outer stratified $k$-fold execution for AutoML contenders is missing. |
| **5** | **Failure handling & imputation**<br>(crash/timeout/skipped recorded, floor imputation in aggregates) | **PARTIAL** | `runner.py` records status `failed`, `timeout`, `skipped` without crashing the benchmark. Imputation with constant-predictor score in aggregation is not implemented. | Aggregate score imputation for failed runs is missing. |
| **6** | **Statistics & ranking**<br>(Wilcoxon, Friedman, Nemenyi, /rerank without retraining) | **PARTIAL** | `src/acbs/benchmark/aggregate.py:83,97` implements Friedman test and Wilcoxon signed-rank test. Nemenyi post-hoc test is missing. `rerank` route (`experiments.py:307`) does not retrain models (**PASS**). | Nemenyi test missing. |
| **7** | **Budgets & cost estimate**<br>(1/5/15/30 min budgets, cost estimate formula, AMLB results.csv) | **PARTIAL** | `POST /frameworks/estimate` exists, but calculates `len(fws) * budget_s * 1.25 * n_datasets` (does not multiply by folds). `export_csv` outputs internal dataframe, not AMLB-format CSV. | AMLB CSV schema (`id, task, fold, framework, constraint, result...`) missing; cost formula ignores folds. |
| **8** | **OpenML intake**<br>(task and suite ID, caching, limits) | **FAIL** | `src/acbs/data/loader.py:120-128` implements basic `_openml_dataset(identifier, target)` by dataset ID only. No OpenML suite or task intake logic exists. | OpenML task ID and suite ID fetching logic not implemented. |
| **9** | **Alembic migrations**<br>(alembic upgrade head on empty database) | **PASS** | Executed: `alembic upgrade head` on `.verify_tmp/test_empty.db`. Applied revisions `09d624075c51` -> `d6f3565d22a2` successfully without error. | None. Migrations fully functional. |
| **10** | **Frontend architecture**<br>(9 HTML pages, strict CSP, no innerHTML with data, no Streamlit) | **PARTIAL** | 9 HTML files exist in `web/`. However, 57 instances of `innerHTML` exist in `web/js/`. CSP headers are not enforced on static mounts. Streamlit app has not been removed. Playwright tests missing. | Streamlit removal, CSP headers, XSS-safe DOM manipulation, and E2E tests missing. |
| **11** | **Advisor Agent**<br>(LLMClient, 10 tools, approval gate, trace tables) | **FAIL** | `src/acbs/recommend/advisor.py` implements a basic single-shot text narration via Respan. No `LLMClient` interface, tool schemas, approval gates, or agent database tables exist. | Entire multi-tool Advisor Agent architecture is missing. |
| **12** | **Deployment readiness**<br>(Dockerfiles, compose, vercel.json, demo mode) | **PARTIAL** | `Dockerfile` and `docker-compose.yml` exist. However, `vercel.json` is missing at repo root. Local Docker daemon is inactive so images were not built. Pre-computed demo mode missing. | `vercel.json`, active container image builds, and demo dataset bundles missing. |
| **13** | **Documentation**<br>(README, architecture, methodology, ui_checklist) | **PARTIAL** | `architecture.md`, `protocol.md`, `ui_checklist.md` exist in `docs/`. `docs/methodology.md` is missing. `README.md` lines 49–53 have broken step formatting omitting the server startup command. | Add `docs/methodology.md` and fix quick start section in `README.md`. |

---

## 5. Associated Security & Verification Items (FT-08, FT-17, FT-18)

- **FT-08 (Class count < folds):** `FAIL`. `src/acbs/data/splitter.py` relies directly on `StratifiedKFold`. Passing a rare class with fewer samples than folds emits a warning or crashes during cross-validation rather than validating and adjusting folds cleanly beforehand.
- **FT-17 / FT-18 (DOS Device & Atomic Uploads):** `FAIL`. Uploading `con.csv` succeeded with HTTP 200. Upload writes directly to `dest.write_bytes(raw)` using the client-specified filename rather than streaming atomically to a UUID-named file.

---

## 6. Fresh-Clone Test (Step 3)

- **Clone Operation:** Executed `git clone . .verify_tmp/clone_test` (Succeeded).
- **README Execution Walkthrough:**
  - **Step 1 (Virtualenv & Dependencies):** Installs successfully (`pip install -e ".[dev]"`).
  - **Step 2 (AutoML Environments):** Requires python 3.10 and 3.11 runtimes on system.
  - **Step 3 (Starting the Server):** **DEFECT IN README.** Line 49 ends `smoke_test_envs.py`, and line 53 immediately says `"Open http://localhost:8000 in your browser"`. The command to launch the server (`uvicorn acbs.api.main:app --port 8000` or `acbs run`) is completely omitted from the Quick Start section.

---

## 7. Action Plan & Priority Fixes

1. **Phase 1 (Data Integrity):**
   - Fix `src/acbs/data/loader.py`: drop NaN targets, preserve numeric class ordering, replace $\pm\infty$ with NaN, add `csv.Sniffer` for semicolon/European formats.
   - Fix `src/acbs/data/profiler.py`: guard against dropping all features.
   - Fix `src/acbs/api/routes/experiments.py`: return HTTP 422 for unsatisfiable rerank constraints.
2. **Phase 2 (Uploads & API Hardening):**
   - Store uploads as `data/raw/<uuid4>.<ext>`, enforce streaming size limit, block Windows reserved device names, restrict CORS from `ACBS_CORS_ORIGINS`, add `ACBS_API_TOKEN` auth.
   - Configure SQLite WAL mode (`PRAGMA journal_mode=WAL`) and busy timeout in `storage/models.py`.
3. **Phase 3 (Worker Contract & Model Export):**
   - Switch worker IPC from JSON-over-stdin to Parquet file paths.
   - Fix `src/acbs/models/export.py` to bundle real trained AutoML artifacts, dependencies, and `predict.py`.
4. **Phase 4 (v3 AutoML-Only Architecture):**
   - Retire classic ML tier (`src/acbs/models/registry.py`), remove `optuna`, `imbalanced-learn`, and `streamlit`.
   - Register all 9 frameworks including `auto-sklearn` with Windows-unsupported metadata.
5. **Phase 5–7 (Frontend, Advisor Agent & Deployment):**
   - Rebuild advisor with tool calling, approval gates, and async HTTP. Replace `innerHTML` with safe DOM manipulation.

