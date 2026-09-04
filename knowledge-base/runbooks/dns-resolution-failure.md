# DNS Resolution Failure

## Symptoms
- connection refused / unknown host
- random timeouts
- trace shows client error before span

## Checks
1. `query_logs` "UnknownHostException"
2. `get_pod` dnsPolicy
3. coredns metrics

## Recovery
- Fix service name / FQDN
- Check CoreDNS
