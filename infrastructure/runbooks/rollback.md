# Rollback procedure

## When to use

- deployment introduces regressions in API behavior
- availability or error budget is breached
- latency or workflow failures are caused by the latest release

## Steps

1. Stop any new deploy activity and announce an incident.
2. Identify the last known-good deployment SHA.
3. Run the rollback script:

```bash
./infrastructure/deploy/rollback.sh staging
```

or

```bash
./infrastructure/deploy/rollback.sh production
```

4. Confirm the app is healthy with `/health` and check `/metrics` for a return to baseline.
5. Notify stakeholders that the rollback is complete and capture the incident details.

## Post-rollback checks

- validate chat, ticket, review, and approval flows
- confirm alert volume returns to normal
- review whether the bug should be patched before the next release
