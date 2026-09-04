# Postmortem: CrashLoopBackOff (2024-07-01)

## Impact
Inventory service unavailable for 12 minutes.

## Root Cause
ConfigMap typo in DB connection string.

## Detection
Pod restart count alert.

## Resolution
Fixed ConfigMap and rolled out.

## Action Items
- Validate ConfigMap in CI
- Add startup probe
