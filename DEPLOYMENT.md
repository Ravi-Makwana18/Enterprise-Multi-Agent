# Deployment and operations guide

## Quality gate

Before a release is promoted, ensure the following are true:

1. backend tests pass
2. frontend build succeeds
3. smoke tests validate `/health`, `/metrics`, and `/alerts`
4. no new critical alert rules are introduced
5. rollback script is tested on a staging environment

## CI pipeline

The repository includes a GitHub Actions workflow in `.github/workflows/ci.yml` that runs:
- backend unit and integration tests
- frontend build validation

## Deployment pipeline

The repository includes a deployment workflow in `.github/workflows/deploy.yml` for:
- staging deployment on branch push
- production deployment on tag or manual trigger

## Release process

1. create a release branch from `main`
2. validate the CI quality gate locally and in GitHub Actions
3. merge to `main` or trigger a tagged release
4. deploy to staging
5. validate app health and major user flows
6. promote to production
7. confirm metrics and alert baseline before closing the release

## Operational readiness summary

The application now includes:
- request tracing using `X-Trace-Id`
- runtime metrics at `/metrics`
- alert records at `/alerts`
- CI workflow for automated verification
- deployment and rollback scripts
- incident and rollback runbooks
