# Incident runbook

## Trigger

Use this playbook when one of the following is true:
- health checks fail for more than 2 minutes
- error rate crosses alert thresholds
- customer-visible request latency spikes above expected bounds
- workflow execution fails repeatedly for the same route

## Immediate response

1. Capture the current deployment SHA and environment.
2. Pull the latest `/metrics` and `/alerts` payloads.
3. Correlate the failing request with the matching trace ID from response headers.
4. Determine whether the issue is application, infrastructure, or dependency-related.
5. Keep the system stable by enacting the rollback procedure if the issue is release-induced.

## Triage checks

- Confirm backend health at `/health`.
- Review recent logs for validation, auth, or unhandled exceptions.
- Check the alert list for repeated 5xxs or latency spikes.
- Confirm database connectivity and Bedrock configuration if the failing workflow depends on them.

## Recovery

- If a recent deployment introduced the regression, run the rollback script.
- If the issue is due to external dependency failure, isolate the service and continue with manual controls.
- Notify stakeholders after recovery and capture the timeline of resolution.

## Follow-up

- Record the root cause, timeline, and affected users/routes.
- Open a backlog issue for permanent remediation.
- Update the release checklist and monitor thresholds if needed.
