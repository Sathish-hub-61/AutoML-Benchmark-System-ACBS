# ACBS Defect & Audit Remediation Tracker

This document tracks all 27 defects identified during the comprehensive audit, mapped to remediation phases, fixing commits, and verifying regression tests.

| Defect ID | Severity | Phase | Description | Root Cause File | Status | Fix Commit | Verifying Test Name |
|---|---|---|---|---|---|---|---|
| **BUG-CRIT-01** | Critical | Phase 3 | AutoML model export returns stub without real model artifacts | `src/acbs/models/export.py` | PENDING | — | `test_automl_model_export_roundtrip` |
| **BUG-CRIT-02** | Critical | Phase 1 | Missing target values ($NaN$) cast to string `'nan'` and ingested as class | `src/acbs/data/loader.py` | PENDING | — | `test_encode_target_rejects_missing_values` |
| **BUG-CRIT-03** | Critical | Phase 2 | Permissive wildcard CORS (`allow_origins=["*"]`) | `src/acbs/api/main.py` | PENDING | — | `test_cors_origins_configured_from_env` |
| **BUG-CRIT-04** | Critical | Phase 2 | Unbounded concurrency crashes SQLite with lock errors | `src/acbs/api/routes/experiments.py` | PENDING | — | `test_concurrent_experiments_queued` |
| **BUG-CRIT-05** | Critical | Phase 4 | Classic export omitted class weighting and SMOTE/resampling | `src/acbs/models/export.py` | PENDING (Resolved by Phase 4 classic tier retirement) | — | Resolved by architectural removal |
| **BUG-CRIT-06** | Critical | Phase 2 | Complete absence of authentication or API access tokens | `src/acbs/api/` | PENDING | — | `test_api_token_auth_and_rate_limiting` |
| **BUG-HIGH-01** | High | Phase 2 | Upload overwrite race condition on identical filenames | `src/acbs/api/routes/datasets.py` | PENDING | — | `test_upload_atomic_uuid_storage` |
| **BUG-HIGH-02** | High | Phase 1 | Inability to detect targets in semicolon (`;`) or tab delimited CSVs | `src/acbs/data/target_detection.py` | PENDING | — | `test_target_detection_european_csv_semicolon` |
| **BUG-HIGH-03** | High | Phase 1 | Dropping ID column leaves 0 features when single feature is ID | `src/acbs/data/profiler.py` | PENDING | — | `test_profiler_never_drops_last_remaining_feature` |
| **BUG-HIGH-04** | High | Phase 1 | Infinite values ($\pm\infty$) crash preprocessing pipelines | `src/acbs/data/loader.py` | PENDING | — | `test_loader_replaces_infinities_with_nan` |
| **BUG-HIGH-05** | High | Phase 6 | Unsanitized prompt injection via advisor user question input | `src/acbs/recommend/advisor.py` | PENDING | — | `test_advisor_prompt_injection_isolation` |
| **BUG-HIGH-06** | High | Phase 2 | Windows reserved device names (`CON`, `PRN`, `AUX`, `NUL`) in uploads | `src/acbs/api/routes/datasets.py` | PENDING | — | `test_upload_rejects_reserved_windows_names` |
| **BUG-HIGH-07** | High | Phase 5 | Results view terminates early when recommendation is missing | `app/views/results.py`, `web/js/pages/results.js` | PENDING | — | `test_results_view_renders_table_without_recommendation` |
| **BUG-HIGH-08** | High | Phase 3 | IPC memory explosion from JSON-over-stdin list serialization | `src/acbs/automl/contracts.py` | PENDING | — | `test_ipc_parquet_file_based_memory_flat` |
| **BUG-MED-01** | Medium | Phase 2 | Disk leak: temporary export directories never cleaned up | `src/acbs/models/export.py` | PENDING | — | `test_export_temp_dir_cleaned_after_response` |
| **BUG-MED-02** | Medium | Phase 1 | Lexicographical string sorting reorders numeric class labels | `src/acbs/data/loader.py` | PENDING | — | `test_encode_target_preserves_numeric_order` |
| **BUG-MED-03** | Medium | Phase 2 | In-memory `_CANCELLED` set lost on multi-worker restarts | `src/acbs/api/routes/experiments.py` | PENDING | — | `test_cancellation_persisted_in_db` |
| **BUG-MED-04** | Medium | Phase 3 | ms/1k prediction metric skewed on small holdout slices | `src/acbs/benchmark/timing.py` | PENDING (Resolved by AMLB benchmark protocol) | — | `test_amlb_inference_benchmark_protocol` |
| **BUG-MED-05** | Medium | Phase 1 | Missing delimiter and decimal comma sniffing in `load_local` | `src/acbs/data/loader.py` | PENDING | — | `test_load_local_sniffs_delimiter_and_decimals` |
| **BUG-MED-06** | Medium | Phase 1 | Unsatisfiable rerank constraints return HTTP 500 error | `src/acbs/api/routes/experiments.py` | PENDING | — | `test_rerank_unsatisfiable_constraints_returns_422` |
| **BUG-MED-07** | Medium | Phase 6 | Synchronous external HTTP call blocks FastAPI event loop in advisor | `src/acbs/recommend/advisor.py` | PENDING | — | `test_advisor_async_nonblocking_execution` |
| **BUG-MED-08** | Medium | Phase 3 | Pandas 4.0 deprecation warnings in GAMA worker `select_dtypes` | `src/acbs/automl/workers/gama_worker.py` | PENDING | — | `test_gama_worker_no_pandas_deprecations` |
| **BUG-MED-09** | Medium | Phase 1 | Outlier share computation silently drops NaNs via `.stack()` | `src/acbs/data/profiler.py` | PENDING | — | `test_profiler_outlier_share_nan_safe` |
| **BUG-LOW-01** | Low | Phase 2 | Starlette TestClient httpx vs httpx2 deprecation warning | `tests/api/test_routes.py` | PENDING | — | Pytest suite hygiene |
| **BUG-LOW-02** | Low | Phase 2 | Hardcoded port assumptions in frontend api client | `web/js/api.js` | PENDING | — | `test_web_api_relative_urls` |
| **BUG-LOW-03** | Low | Phase 2 | Static file mount ordering intercepts API 404 responses | `src/acbs/api/main.py` | PENDING | — | `test_api_404_returns_json_not_html` |
| **BUG-LOW-04** | Low | Phase 3 | Unpinned framework versions in worker outputs | `src/acbs/automl/workers/` | PENDING | — | `test_workers_report_exact_package_versions` |

### Associated Verification Items
- **FT-08 (Phase 1):** Rare class smaller than $k$-splits verified and handled gracefully before CV execution (`test_splitter_checks_min_class_samples_per_fold`).
- **FT-17 / FT-18 (Phase 2):** Windows DOS device rejection and atomic streaming upload writes (`test_upload_security_and_atomicity`).

