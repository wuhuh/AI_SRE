# Certificate Expired

## Symptoms
- TLS handshake failures
- mTLS denied
- logs "certificate expired"

## Checks
1. `query_logs` "certificate expired"
2. get secret expiration
3. `query_trace` TLS error span

## Recovery
- Rotate certificate
- Restart workloads to pick new secret
