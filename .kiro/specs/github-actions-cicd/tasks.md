# Implementation Plan: GitHub Actions CI/CD Pipeline

## Overview

Implement a single GitHub Actions workflow file at `.github/workflows/ci.yml` that detects per-service changes, builds and pushes Docker images to ECR, and commits Helm values updates. Supporting shell scripts are extracted for testability, and a Python/Hypothesis property-based test harness validates the core invariants.

## Tasks

- [x] 1. Create workflow file scaffold
  - Create `.github/workflows/ci.yml` with the top-level `name`, `on` triggers (`push: branches: [main]`, `workflow_dispatch`), `concurrency` group (`ci-${{ github.ref }}`, `cancel-in-progress: true`), `permissions: contents: write`, and the workflow-level skip-ci condition (`if: "!contains(github.event.head_commit.message, '[skip ci]')"`)
  - Add empty job stubs for `detect-changes`, `build-and-push`, and `pipeline-summary` (with correct `needs`, `if: always()`, `runs-on: ubuntu-latest`) so the YAML is structurally valid from the start
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 8.1_

- [x] 2. Implement detect-changes job
  - [x] 2.1 Add `dorny/paths-filter@v3` step with per-service path filters for all five services (`src/ui/**`, `src/cart/**`, `src/catalog/**`, `src/checkout/**`, `src/orders/**`)
    - Expose per-service outputs (`ui`, `cart`, `catalog`, `checkout`, `orders`) from the job
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.8_
  - [x] 2.2 Add matrix-construction step that reads filter outputs and emits `matrix` job output as a JSON array string; handle `workflow_dispatch` override (all five services) and the empty-matrix case
    - Source logic from `scripts/build-matrix.sh` once that script is created (task 3)
    - _Requirements: 2.7, 2.9, 6.1_
  - [x] 2.3 Add step-summary output step that writes trigger event name, commit SHA, UTC timestamp, and the list of changed services (or "No services changed") to `$GITHUB_STEP_SUMMARY`
    - _Requirements: 1.5, 7.1_

- [x] 3. Extract and implement build-matrix shell script
  - [x] 3.1 Create `scripts/build-matrix.sh` that accepts five boolean arguments (one per service) and an `event_name` argument, and writes the JSON matrix array to stdout; must handle the `workflow_dispatch` override and zero-services case
    - Make the script executable (`chmod +x`)
    - _Requirements: 2.7, 2.9_
  - [x]* 3.2 Write property test for matrix construction (Property 2)
    - **Property 2: Matrix construction from change flags**
    - **Validates: Requirements 2.9, 6.1**
    - Create `tests/test_pipeline_properties.py`; use `hypothesis.given` with strategies that generate all combinations of five booleans and assert the output JSON array contains exactly the services whose flag is `True`; also test the `workflow_dispatch` override always returns all five services
    - Tag: `Feature: github-actions-cicd, Property 2: Matrix construction from change flags`

- [x] 4. Implement build-and-push matrix job — AWS auth and Docker build/push
  - [x] 4.1 Wire the matrix job in `ci.yml`: add `needs: detect-changes`, `strategy.fail-fast: false`, `matrix.service: ${{ fromJson(needs.detect-changes.outputs.matrix) }}`; skip the job cleanly when the matrix is empty
    - _Requirements: 6.1, 6.2_
  - [x] 4.2 Add checkout step (`actions/checkout@v4`, `fetch-depth: 0`) and validate-secrets step that checks all four required secrets (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_ACCOUNT_ID`) are non-empty and fails fast with an error message listing any missing ones
    - _Requirements: 3.1, 3.6_
  - [x] 4.3 Add `aws-actions/configure-aws-credentials@v4` step and `aws-actions/amazon-ecr-login@v2` step; set `IMAGE_TAG` job-level env to `${{ github.sha }}`
    - _Requirements: 3.2, 3.3, 3.4, 3.5_
  - [x] 4.4 Add Docker build-and-push step: build from `src/${SERVICE}/Dockerfile` with context `src/${SERVICE}/`, tag as full ECR URI `${REGISTRY}/retail-store-sample-${SERVICE}:${GITHUB_SHA::7}`, push, and write image URI and tag to step summary
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.7, 7.2_
  - [x]* 4.5 Write property test for image tag naming convention (Property 3)
    - **Property 3: Image tag naming convention**
    - **Validates: Requirements 4.3**
    - Add to `tests/test_pipeline_properties.py`; use `hypothesis.given` with strategies generating 40-char hex strings (SHA) and service names from the allowed set; assert the full URI matches `<ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/retail-store-sample-<service>:<sha[:7]>`
    - Tag: `Feature: github-actions-cicd, Property 3: Image tag naming convention`

- [x] 5. Implement Helm values update step and extract update script
  - [x] 5.1 Add values-file validation step in the build-and-push job: check that `src/${SERVICE}/chart/values.yaml` exists and contains a `tag:` field; emit `::error::` and exit 1 if either condition fails
    - _Requirements: 5.7_
  - [x] 5.2 Create `scripts/update-helm-tag.sh` that accepts `VALUES_FILE` and `TAG` arguments and applies `sed -i "s/^\(\s*tag:\s*\).*$/\1\"${TAG}\"/" "${VALUES_FILE}"`; make executable
    - _Requirements: 5.1, 5.2_
  - [x] 5.3 Add Helm update step in the build-and-push job that calls `scripts/update-helm-tag.sh` with the service values file and `${GITHUB_SHA::7}`; write the updated file path and new tag to step summary
    - _Requirements: 5.1, 5.2, 7.3_
  - [x]* 5.4 Write property test for Helm values idempotency (Property 4)
    - **Property 4: Helm values idempotency**
    - **Validates: Requirements 5.1, 5.2**
    - Add to `tests/test_pipeline_properties.py`; use `hypothesis.given` with strategies that generate random valid `values.yaml` content containing an `image:` block with `tag:` field and a random 7-char alphanumeric tag; run `scripts/update-helm-tag.sh` in a subprocess on a temp file; assert only the `tag:` value changed, all other lines are identical, and applying the operation twice gives the same result as once
    - Tag: `Feature: github-actions-cicd, Property 4: Helm values idempotency`

- [x] 6. Implement git commit and push steps with rebase
  - [x] 6.1 Add git-config, git-pull-rebase, git-add, git-commit, and git-push steps in the build-and-push job; commit message must be `ci: update ${SERVICE} image tag to ${GITHUB_SHA::7} [skip ci]`; use `git pull --rebase origin main` before committing to mitigate concurrent-push race conditions
    - _Requirements: 5.3, 5.4, 5.5, 5.8_
  - [x]* 6.2 Write property test for commit message format (Property 5)
    - **Property 5: Commit message format**
    - **Validates: Requirements 5.3, 8.2**
    - Add to `tests/test_pipeline_properties.py`; use `hypothesis.given` with strategies generating service names from the allowed set and 7-char alphanumeric tags; assert the produced commit message string matches `ci: update <service> image tag to <tag> [skip ci]` exactly and always contains `[skip ci]`
    - Tag: `Feature: github-actions-cicd, Property 5: Commit message format`
  - [x]* 6.3 Write property test for skip-CI detection (Property 6)
    - **Property 6: Skip-CI detection correctness**
    - **Validates: Requirements 8.1**
    - Add to `tests/test_pipeline_properties.py`; use `hypothesis.given` with strategies generating arbitrary text strings with and without `[skip ci]` inserted at random positions; assert the detection expression returns `True` if and only if `[skip ci]` is present
    - Tag: `Feature: github-actions-cicd, Property 6: Skip-CI detection correctness`

- [-] 7. Checkpoint — ensure scripts and tests are wired correctly
  - Verify `scripts/build-matrix.sh` and `scripts/update-helm-tag.sh` are present and executable
  - Run `python -m pytest tests/test_pipeline_properties.py -v` and confirm all property tests pass
  - Ensure all tests pass; ask the user if questions arise.

- [x] 8. Implement pipeline-summary job
  - [x] 8.1 Implement the `pipeline-summary` job body in `ci.yml`: add a single step that writes a Markdown table to `$GITHUB_STEP_SUMMARY` with the aggregate `needs.build-and-push.result` outcome; the job must run with `if: always()` and depend on `needs: [detect-changes, build-and-push]`
    - _Requirements: 6.3, 7.4_

- [ ] 9. Validate workflow YAML with actionlint
  - [-] 9.1 Create `tests/test_workflow_structure.py` that uses the `subprocess` module to run `actionlint .github/workflows/ci.yml` (or `actionlint -format '{{json .}}'` for structured output) and asserts exit code 0; also assert the following structural invariants by parsing the YAML directly with `PyYAML`:
    - `on.push.branches` contains only `main`
    - `workflow_dispatch` is present under `on`
    - `concurrency.cancel-in-progress` is `true`
    - `permissions.contents` is `write`
    - `jobs.build-and-push.strategy.fail-fast` is `false`
    - `jobs.pipeline-summary.if` contains `always()`
    - All `uses:` fields are pinned to a version tag
    - _Requirements: 1.1, 1.3, 1.4, 6.1_

- [~] 10. Final checkpoint — full pipeline review
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- The design specifies Python/Hypothesis for property-based tests; ensure `hypothesis` and `pytest` are available (`pip install hypothesis pytest pyyaml`)
- `scripts/build-matrix.sh` and `scripts/update-helm-tag.sh` are extracted from the inline YAML steps for testability; the workflow steps call these scripts directly
- `actionlint` must be installed on the runner or locally for task 9.1; if unavailable, the YAML structural assertions in `PyYAML` still validate the key invariants
- Each matrix job runs on its own runner; sequential Helm commits per service reduce (but do not eliminate) git push race conditions — `git pull --rebase` is the mitigation

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1", "3.1"] },
    { "id": 2, "tasks": ["2.2", "3.2", "4.1"] },
    { "id": 3, "tasks": ["2.3", "4.2", "4.3", "5.2"] },
    { "id": 4, "tasks": ["4.4", "5.1", "5.3", "4.5"] },
    { "id": 5, "tasks": ["5.4", "6.1"] },
    { "id": 6, "tasks": ["6.2", "6.3", "8.1"] },
    { "id": 7, "tasks": ["9.1"] }
  ]
}
```
