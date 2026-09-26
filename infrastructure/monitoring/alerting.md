# Alerting and monitoring

## Core metrics

The application exposes operational telemetry at `/metrics` and `/alerts`.

Recommended thresholds:
- 5xx error rate > 2% for 5 minutes
- p95 API latency > 3000 ms for a sustained window
- workflow retry count > 3 in a single request cycle

## Dashboards

Monitor these panels in the operations dashboard:
- request throughput by endpoint
- error counts by status code
- p95 response latency per route
- workflow success and failure counts
- trace IDs for incident correlation

## Pager routing

- page the on-call engineer for 5xx spikes or repeated 429s above threshold
- notify product owner for workflow approval failures or data-quality issues
- route infrastructure events to platform channel when the app is degraded or unreachable

## Alert sources

The backend emits runtime alerts when:
- a route fails with HTTP 500+
- response latency exceeds 3s
- a workflow path is retried excessively

These alert records are surfaced through the `/alerts` endpoint for operational dashboards and incident review.
