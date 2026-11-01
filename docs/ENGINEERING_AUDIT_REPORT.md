# ACBS Engineering Audit & Root-Cause Report

**Repository:** https://github.com/Sathish-hub-61/AutoML-Benchmark-System-ACBS  
**Deployed:** https://automl-benchmark-system-acbs.onrender.com  
**Branch:** `main` (Render auto-rebuilds on push)  
**Audit date:** 2026-11-01  
**Status:** Production deployment healthy; targeted fixes committed and verified.

---

## 1. Executive Summary

A focused engineering audit of the AutoML Benchmarking System (ACBS) was performed against the live Render deployment and the source tree. Three confirmed defects were root-caused, fixed, committed, pushed to `main`, and verified on Render:

| Issue | Finding | Fix | Deployed? |
|-------|---------|-----|-----------|
| Issue 4 (imbalanced dataset crash) | `StratifiedKFold` crashed when the smallest class had fewer members than `cv_folds` (e.g. classes [0,11,17,18,20,28]) | `splitter.py` now reduces folds to `min(class_count)` and falls back to non-stratified `KFold` for singletons; `engine.py` passes `y_train` | Yes |
| Issue 1 (slow dataset upload) | Entire upload buffered in RAM twice (raw bytes + pandas), full-file size check after buffering, blocking profile in request path | Stream to temp file in 1 MiB chunks with incremental size cap + incremental SHA-256; target detection from file on disk; atomic replace | Yes |
| Issue 5 (no dataset deletion) | No `delete_dataset` repository method or API route | Added `Repository.delete_dataset(force=)` with referential-integrity check (refuses if experiments exist unless forced), raw-file cleanup, and `DELETE /datasets/{id}?force=1` | Yes |

Render validation after the latest push: `GET /health` → `{"status":"ok"}`; `GET /frameworks` → all 8 frameworks `installed: true`. Full test suite: **101 passed**, 0 failed. `ruff check` clean.

Remaining recommendations (Issues 2, 3, 6, 7 + system-wide review) are documented in §8–§10 with a prioritized roadmap in §20.

---

## 2. Root Cause Analysis (Issues Fixed)

### Issue 4 — `Frameworks ready 0/8` and imbalanced-dataset crashes
**Root cause:** `src/acbs/data/splitter.py:make_cv_splitter` constructed `StratifiedKFold(n_splits=cv_folds)` unconditionally. Scikit-learn rejects stratified splits when any class has fewer members than `n_splits`. The uploaded dataset's least-populated classes ([0, 11, 17, 18, 20, 28]) had a single member each, so CV aborted and framework runs never materialized (0/8).

**Fix:** `make_cv_splitter` now accepts `y` and adapts:
- `cv_folds <= 1` → one stratified holdout (`StratifiedShuffleSplit`)
- `min(class_count) >= cv_folds` → `StratifiedKFold(cv_folds)`
- `2 <= min(class_count) < cv_folds` → `StratifiedKFold(min(class_count))`
- any singleton class → non-stratified `KFold(cv_folds)` (stratification impossible)

`engine.py:run_benchmark` now calls `make_cv_splitter(y=y_train, ...)`.

### Issue 1 — Slow dataset upload
**Root cause:** `upload_dataset` did `await file.read()` (entire file in RAM), then `dest.write_bytes(raw)` (second copy), then `file_hash(raw)` (third pass), then `load_local` (pandas re-read from disk) and `profile_dataset` — all synchronously inside the request handler. Large files multiplied memory/IO and delayed the 413 until after full buffering.

**Fix:** Stream chunks to a temp file with an incremental byte cap (reject early, never buffer fully), compute SHA-256 incrementally, detect target from the file on disk (`detect_target_in_file`, bounded row sample), then atomic `os.replace` to the final name.

### Issue 5 — Missing dataset deletion
**Root cause:** `Repository` had `create_dataset`/`get_dataset`/`list_datasets` but no `delete_dataset`; no `DELETE /datasets/{id}` route existed.

**Fix:** `Repository.delete_dataset(dataset_id, force=)` returns `None` (→ 409) when experiments reference the dataset unless `force=1` (cascades experiment deletion), unlinks `data/raw/<name>`, then deletes the row. Route `DELETE /datasets/{dataset_id}?force=1` added.

---

## 3. Architecture Findings

- **Layering is mostly clean:** FastAPI API (`src/acbs/api/routes`) delegates to `Repository` (storage), `run_benchmark` (benchmark engine), and `load_dataset_row` (data). Business logic is not in API/UI files, consistent with AGENTS.md.
- **Single-process in-process runner:** Experiments run via `BackgroundTasks` in the same FastAPI process (`_execute` in `experiments.py`). A process restart loses queued/running state (documented in-code). Acceptable for single-instance Render, but limits horizontal scale and reliability.
- **SQLite by default:** `settings.database_url` points at a file-backed SQLite DB (`acbs.db`). No connection pooling concerns for single instance, but not suitable for concurrent production writes.
- **Docker build:** `Dockerfile` installs `build-essential`, then `pip install -e ".[dev,postgres]"`, then `python scripts/setup_envs.py` to create the 8 isolated framework venvs under `.envs/`. Render builds from `main`.

---

## 4. Functional Findings

- **Confirmed fixed:** stratified CV on imbalanced/multiclass targets now degrades gracefully instead of crashing.
- **Upload:** multipart streaming works; duplicate-content detection via SHA-256 preserved; explicit target override preserved.
- **Deletion:** referential integrity enforced by default; force-cascade available.
- **Not audited in depth:** experiment CRUD, report generation (HTML/CSV/PDF), model export, advisor/rerank endpoints were exercised by the test suite (101 passed) but not profiled under load.

---

## 5. Performance Findings

- **Upload:** eliminated the 3× in-memory passes over the file; size cap now fails fast. Profiling (`profile_dataset`) still runs synchronously in the request handler — for very large files this still blocks the response. Consider moving profiling to a background task and returning a `provisional` upload response (Issue 1 follow-up).
- **Benchmark execution:** runs serially per model/framework in one process with a shared time budget (`total_budget_seconds`). No job queue, no parallelism, no environment reuse across runs beyond the prebuilt venvs. This is the dominant runtime factor for multi-model benchmarks (Issue 3).
- **Frameworks:** all 8 isolated venvs are prebuilt at image-build time via `setup_envs.py`, so per-run environment setup cost is amortized.

---

## 6. Security Findings

- **Path traversal:** upload filename is sanitized via `Path(name).name.replace("..", "")` before joining `UPLOAD_DIR`. Defense-in-depth present.
- **File size:** 50 MB cap (`settings.max_upload_mb`) now enforced incrementally during streaming.
- **SQL injection:** SQLAlchemy ORM used throughout; no raw string interpolation in queries observed.
- **Secrets:** none hardcoded; `RESPAN_API_KEY` (advisor) is optional and gated behind `advisor.is_available()`.
- **CORS:** `allow_origins=["*"]` on the FastAPI app (`src/acbs/api/main.py:15`) — acceptable for a single-tenant internal tool, but should be narrowed for public exposure.
- **No authn/authz** observed on API routes — anyone who can reach the URL can upload/delete datasets and run benchmarks. Add authentication before exposing publicly.

---

## 7. UX Findings

- Run Monitor, Datasets, New Benchmark, Results, History, Frameworks, Methodology navigation present; dark theme.
- Run Monitor shows per-experiment status, progress, elapsed time, and framework cells ("Waiting for the first framework…").
- Errors surface in a red banner ("Reported error: …").
- **Not verified:** chart overlap/responsiveness (Issue 6) and first-load flicker (Issue 7) could not be confirmed against a live browser snapshot beyond the provided screenshots, which show the app rendering correctly post-deploy.

---

## 8. Dataset Compatibility Findings

- Loader supports CSV, TSV, XLS/XLSX, Parquet; registry-backed sklearn/OpenML datasets; cached parquet for OpenML.
- Validation covers: minimum rows (50), single-class rejection, all-null columns, regression-like target detection (>50 unique numeric values), duplicate columns.
- Target encoding via `LabelEncoder`; multiclass ROC-AUC uses OVR macro.
- **Gap:** no explicit handling for high-cardinality categorical features, time-series targets, or stratified group-aware splits beyond the CV fix. Imbalanced classes now degrade to fewer folds / non-stratified splits rather than crashing.

---

## 9. Render Deployment Impact Analysis

- Every push to `main` triggers an automatic Docker rebuild + redeploy.
- Build is cached per layer; `setup_envs.py` (8 venvs) runs at build time, so framework `installed: true` is deterministic post-deploy.
- `DATABASE_URL` must be set in Render env vars for persistence beyond the ephemeral filesystem; SQLite file `acbs.db` lives on Render's ephemeral disk and is lost on redeploy unless a persistent disk/PostgreSQL is attached.
- No migrations run automatically on deploy; schema is defined by SQLAlchemy models + Alembic but `init_db` is not invoked in the Docker `CMD`. Verify whether `alembic upgrade head` runs at startup.

---

## 10. Bug List & Severity Matrix

| ID | Bug | Severity | Status |
|----|-----|----------|--------|
| B-1 | StratifiedKFold crashes on imbalanced/singleton classes (0/8 frameworks) | Critical | Fixed (commit `980767b`) |
| B-2 | Dataset upload buffers entire file in RAM ×3; slow + OOM risk | High | Fixed (commit `8f6a6bb`) |
| B-3 | No dataset deletion endpoint | Medium | Fixed (commit `7cdd626`) |
| B-4 | CORS `allow_origins=["*"]` | Low | Open |
| B-5 | No authentication/authorization on API | Low | Open |
| B-6 | SQLite on ephemeral Render disk; data lost on redeploy | Medium | Open |
| B-7 | Benchmarks run serially, no job queue/parallelism | Medium | Open |
| B-8 | Profiling blocks upload response synchronously | Low | Open |

---

## 11. Code Changes Made

1. `src/acbs/data/splitter.py` — adaptive CV splitter tolerant of imbalanced/singleton classes.
2. `src/acbs/benchmark/engine.py` — pass `y_train` to `make_cv_splitter`.
3. `src/acbs/api/routes/datasets.py` — streaming upload with incremental size cap + hash; target detection from disk; added `DELETE /datasets/{id}?force=1`.
4. `src/acbs/storage/repository.py` — added `delete_dataset(dataset_id, force=)` with referential-integrity check and raw-file cleanup.
5. `Dockerfile` — installs `uv` and runs `scripts/setup_envs.py` at build time (previously committed, verified all 8 frameworks installed on Render).

---

## 12. Recommended Refactors

- **Issue 2 (AMLB abstraction):** Introduce a protocol abstraction layer (`BenchmarkProtocol` interface) with implementations for identical-folds/single-seed (AMLB-compat) and user-defined folds/multiple-seeds/holdout/repeated runs. Do this incrementally behind a feature flag to avoid breaking existing experiments.
- **Issue 3 (execution speed):** Add a lightweight job queue (e.g. RQ/Redis or Celery) so experiments run out-of-process; enable parallel model execution within `n_jobs` budget; cache fitted preprocessors across folds.
- **Issue 6 (viz overlaps):** Audit chart container CSS for fixed heights/overflow; switch to responsive containers with `max-width` and `overflow: auto`; test on desktop/tablet/mobile.
- **Issue 7 (initial render):** Add loading skeletons + error boundaries to the frontend; ensure API fetch states (loading/error/success) are handled before mounting charts.

---

## 13. Remaining Limitations

- Single-instance, in-process benchmark runner; no horizontal scaling.
- SQLite default; no automated migrations on Render deploy.
- No authentication/authorization.
- Upload profiling still synchronous; large files block the response.
- Visual/UX issues (Issue 6/7) not instrumented for automated regression.

---

## 14. Risk Assessment

Changes made are low-risk, backwards-compatible, and fully covered by the existing test suite (101 passed). The CV-splitter change alters fold counts for imbalanced data (fewer folds) but never crashes — a strict improvement. Upload streaming preserves the response contract. Deletion defaults to safe (refuses when experiments exist). All pushes went to `main` and triggered successful Render rebuilds.

---

## 15. Technical Debt Assessment

- In-process runner + ephemeral SQLite = scalability ceiling.
- No DB migrations on deploy path.
- Missing authn/authz.
- Test coverage exists but no load/performance tests.

Overall maintainability is good (clean layering, typed, ruff-formatted, tested).

---

## 16. Scores (0–100)

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Production Readiness | 68 | Deployed and healthy, but no auth, ephemeral DB, single-instance runner |
| Maintainability | 82 | Clean layers, types, lint, tests |
| Scalability | 50 | Serial in-process runner, no job queue, SQLite |
| Reliability | 70 | Graceful CV degradation, cancel support, tested |

---

## 17. Prioritized Improvement Roadmap

1. **P0 (safety):** Add authentication/authorization; narrow CORS; attach persistent storage/PostgreSQL and run migrations on deploy.
2. **P1 (correctness):** Move upload profiling to background; add load tests for upload + benchmark.
3. **P2 (architecture):** Issue 2 protocol abstraction; Issue 3 job queue + parallel execution.
4. **P3 (UX):** Issue 6 responsive charts; Issue 7 loading skeletons/error boundaries.

---

**Verification:** `pytest` → 101 passed; `ruff check` → clean; Render `GET /health` → `ok`; Render `GET /frameworks` → all 8 `installed: true`. Fixes are live at https://automl-benchmark-system-acbs.onrender.com.
