# Requirements Document

## Introduction

This feature adds a GitHub Actions CI/CD pipeline to the retail-store-sample-app. The pipeline automates three responsibilities: detecting which service(s) changed on a push, building and pushing Docker images to Amazon ECR for only the changed services, and updating the `image.tag` value in each service's Helm chart `values.yaml` so that GitOps tooling (ArgoCD) picks up the new image automatically.

The application consists of five independently deployable microservices: **ui**, **cart**, **catalog**, **checkout**, and **orders**. Each service has its own source directory under `src/`, its own `Dockerfile`, and its own Helm chart under `src/<service>/chart/values.yaml`.

## Glossary

- **CI_CD_Pipeline**: The GitHub Actions workflow that orchestrates change detection, image build/push, and Helm values update.
- **Change_Detector**: The job or step within the CI_CD_Pipeline that identifies which services have changed in a given push.
- **Image_Builder**: The job or step within the CI_CD_Pipeline that builds a Docker image from a service's `Dockerfile` and pushes it to ECR.
- **Helm_Updater**: The job or step within the CI_CD_Pipeline that commits an updated `image.tag` value into the service's `values.yaml` file.
- **ECR**: Amazon Elastic Container Registry — the private Docker registry used to store built images.
- **Service**: One of the five microservice components — `ui`, `cart`, `catalog`, `checkout`, or `orders` — each located at `src/<service>/`.
- **Image_Tag**: A short Git SHA (7 characters) derived from `github.sha` that uniquely identifies the built image version.
- **Values_File**: The `src/<service>/chart/values.yaml` file that defines the `image.tag` field consumed by the Helm chart.
- **GitHub_Secrets**: Repository-level secrets `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, and `AWS_ACCOUNT_ID` that supply AWS credentials to the CI_CD_Pipeline.

---

## Requirements

### Requirement 1: Pipeline Trigger

**User Story:** As a developer, I want the CI/CD pipeline to run automatically on every push to the `main` branch, so that changes are built and deployed without manual intervention.

#### Acceptance Criteria

1. WHEN a push event occurs on the `main` branch, THE CI_CD_Pipeline SHALL start execution within 60 seconds of the push event being received by GitHub Actions.
2. WHEN a push event occurs on a branch other than `main`, THE CI_CD_Pipeline SHALL NOT start execution.
3. THE CI_CD_Pipeline SHALL support manual triggering via `workflow_dispatch` so that operators can run the pipeline on demand.
4. WHEN a new push event triggers the CI_CD_Pipeline while a previous pipeline run for the same branch is still in progress, THE CI_CD_Pipeline SHALL cancel the in-progress run and start a new one, so that only the latest commit is built.
5. WHEN the CI_CD_Pipeline starts, THE CI_CD_Pipeline SHALL record the triggering commit SHA, the trigger source (push or workflow_dispatch), and the UTC timestamp of the run start in the step summary.

---

### Requirement 2: Per-Service Change Detection

**User Story:** As a developer, I want only the services that have changed source files to be rebuilt, so that unchanged services are not rebuilt unnecessarily on every push.

#### Acceptance Criteria

1. WHEN a push event triggers the CI_CD_Pipeline, THE Change_Detector SHALL compare the files changed in the push against the path prefix `src/<service>/` for each of the five services (`ui`, `cart`, `catalog`, `checkout`, `orders`) and output a boolean changed flag per service.
2. WHEN one or more files under `src/ui/` have changed, THE Change_Detector SHALL mark the `ui` service as changed.
3. WHEN one or more files under `src/cart/` have changed, THE Change_Detector SHALL mark the `cart` service as changed.
4. WHEN one or more files under `src/catalog/` have changed, THE Change_Detector SHALL mark the `catalog` service as changed.
5. WHEN one or more files under `src/checkout/` have changed, THE Change_Detector SHALL mark the `checkout` service as changed.
6. WHEN one or more files under `src/orders/` have changed, THE Change_Detector SHALL mark the `orders` service as changed.
7. WHEN the CI_CD_Pipeline is triggered via `workflow_dispatch`, THE Change_Detector SHALL mark all five services (`ui`, `cart`, `catalog`, `checkout`, `orders`) as changed, regardless of which files were modified.
8. WHEN no files under `src/<service>/` have changed for a given service, THE Change_Detector SHALL mark that service as unchanged.
9. IF a service is marked as unchanged, THEN THE CI_CD_Pipeline SHALL skip the Image_Builder and Helm_Updater steps for that service and record that the service was skipped in the step summary.

---

### Requirement 3: AWS Authentication

**User Story:** As a pipeline operator, I want the pipeline to authenticate with AWS using repository secrets, so that it can push images to ECR without embedding credentials in code.

#### Acceptance Criteria

1. WHEN the Image_Builder job starts, THE CI_CD_Pipeline SHALL verify that `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, and `AWS_ACCOUNT_ID` are all present and non-empty in GitHub_Secrets; IF any required secret is absent or empty, THEN THE CI_CD_Pipeline SHALL fail the job immediately with an error message identifying the missing secret, before attempting any authentication.
2. WHEN all required secrets are present, THE CI_CD_Pipeline SHALL authenticate to AWS using `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_REGION`.
3. WHEN AWS authentication succeeds, THE CI_CD_Pipeline SHALL log in to ECR at the registry URL `<AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com` using the authenticated AWS identity, completing ECR login within 30 seconds.
4. IF AWS authentication fails, THEN THE CI_CD_Pipeline SHALL fail the job and report the authentication error without proceeding to ECR login or any image push.
5. IF ECR login fails after successful AWS authentication, THEN THE CI_CD_Pipeline SHALL fail the job and report the ECR login error without attempting to push any image.
6. THE CI_CD_Pipeline SHALL NOT expose the values of GitHub_Secrets in any log output, including authentication commands, error messages, and debug traces.

---

### Requirement 4: Docker Image Build and Push

**User Story:** As a developer, I want the pipeline to build a Docker image for each changed service and push it to a private ECR repository, so that deployable artifacts are versioned and stored centrally.

#### Acceptance Criteria

1. WHEN a service is marked as changed, THE Image_Builder SHALL build a Docker image using the `Dockerfile` located at `src/<service>/Dockerfile`.
2. WHEN building the image, THE Image_Builder SHALL set the Docker build context to `src/<service>/` so that all relative `COPY` instructions in the `Dockerfile` resolve correctly.
3. WHEN the image build succeeds, THE Image_Builder SHALL tag the image as `<AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/retail-store-sample-<service>:<IMAGE_TAG>` where `IMAGE_TAG` is the first 7 characters of `github.sha`.
4. WHEN the image is tagged, THE Image_Builder SHALL push the image to the ECR repository at the path described in criterion 3.
5. IF the ECR repository `retail-store-sample-<service>` does not exist, THEN THE Image_Builder SHALL fail the job with an error message identifying the missing repository name and halt any further push attempts for that service.
6. WHEN a service is marked as unchanged, THE Image_Builder SHALL skip the build and push for that service without failing the job.
7. IF the Docker image build fails for a service, THEN THE Image_Builder SHALL fail the job with an error message identifying the service name and the failed build step, and SHALL NOT attempt to tag or push the image for that service.
8. IF ECR authentication is not confirmed before a push, THEN THE Image_Builder SHALL fail the job before attempting the push and report the authentication error.

---

### Requirement 5: Helm Chart Values Update

**User Story:** As a platform engineer, I want the pipeline to update the `image.tag` value in each changed service's Helm chart, so that ArgoCD detects the new image and deploys it automatically.

#### Acceptance Criteria

1. WHEN the image push for a service succeeds, THE Helm_Updater SHALL update the `image.tag` field in `src/<service>/chart/values.yaml` to the new `IMAGE_TAG` (the first 7 characters of `github.sha`).
2. THE Helm_Updater SHALL update only the `image.tag` field in-place, preserving the existing YAML structure, key order, and all other field values in `values.yaml` unchanged.
3. WHEN the `values.yaml` update is complete, THE Helm_Updater SHALL commit the change to the repository using a commit message in the format `ci: update <service> image tag to <IMAGE_TAG> [skip ci]`.
4. THE CI_CD_Pipeline SHALL use a GitHub token with `contents: write` permission to push the commit back to the `main` branch.
5. WHEN multiple services have changed in a single push, THE Helm_Updater SHALL update and push a separate commit for each service's `values.yaml` sequentially, so that each service's change is individually traceable and concurrent push conflicts are avoided.
6. WHEN a service is marked as unchanged, THE Helm_Updater SHALL make no modification to that service's `values.yaml`.
7. IF `src/<service>/chart/values.yaml` does not exist or does not contain an `image.tag` field, THEN THE Helm_Updater SHALL fail the job with an error message identifying the missing file or field, and SHALL NOT attempt a commit.
8. IF the `git push` to the `main` branch fails, THEN THE Helm_Updater SHALL fail the job with an error message reporting the push failure and the service name.

---

### Requirement 6: Pipeline Job Isolation

**User Story:** As a developer, I want each service's build and Helm update to be independent, so that a failure in one service does not block the pipeline for other services.

#### Acceptance Criteria

1. THE CI_CD_Pipeline SHALL run the Image_Builder and Helm_Updater steps for each changed service in a separate, independent job such that the failure or success of one service's job does not affect the execution of any other service's job.
2. WHEN the Image_Builder or Helm_Updater job for one service fails, THE CI_CD_Pipeline SHALL continue executing jobs for all other changed services that have not yet completed or started.
3. WHEN all service jobs complete, THE CI_CD_Pipeline SHALL write a final summary to the GitHub Actions step summary listing each service by name with its outcome: succeeded, failed, or skipped.

---

### Requirement 7: Pipeline Observability

**User Story:** As a developer, I want clear, structured output in the GitHub Actions UI, so that I can quickly identify which services were built and where failures occurred.

#### Acceptance Criteria

1. WHEN the Change_Detector completes, THE CI_CD_Pipeline SHALL log the list of changed services to the GitHub Actions step summary; IF no services have changed, THE CI_CD_Pipeline SHALL log "No services changed" to the step summary.
2. WHEN the Image_Builder completes for a service, THE CI_CD_Pipeline SHALL log to the step summary the registry host, repository name, and image tag of the pushed image.
3. WHEN the Helm_Updater completes for a service, THE CI_CD_Pipeline SHALL log to the step summary the repository-relative path of the updated `values.yaml` and the new image tag value.
4. IF any step produces an error, THEN THE CI_CD_Pipeline SHALL write the step name and cause of failure to the GitHub Actions step summary so the failure is visible without requiring access to raw runner logs.

---

### Requirement 8: Commit Loop Prevention

**User Story:** As a platform engineer, I want the pipeline to skip execution when it detects a CI-generated commit, so that the Helm values update commit does not re-trigger the pipeline in an infinite loop.

#### Acceptance Criteria

1. WHEN the CI_CD_Pipeline is triggered by a push event whose HEAD commit message contains the exact substring `[skip ci]`, THE CI_CD_Pipeline SHALL exit immediately without executing the Change_Detector, Image_Builder, or Helm_Updater.
2. THE Helm_Updater SHALL include `[skip ci]` in every commit message it generates, as specified in Requirement 5, criterion 3.
3. WHEN the CI_CD_Pipeline exits early due to a `[skip ci]` commit, THE CI_CD_Pipeline SHALL log a message to the GitHub Actions step summary stating that execution was skipped due to a CI-generated commit, so the skip is observable without inspecting raw logs.
