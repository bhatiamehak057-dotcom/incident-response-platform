# High Error Rate

## Symptoms
- Error rate increases significantly
- Requests begin failing
- Users experience failed operations

## Possible Causes
- Dependency failure
- Application bug
- Network failure
- Database problems
- Traffic spike

## Investigation
1. Check service health.
2. Review recent error logs.
3. Check latency and request volume.
4. Identify failing dependencies.
5. Compare metrics with normal operating levels.

## Remediation
1. Identify and isolate the failing dependency.
2. Enable circuit breaker or failover behavior.
3. Reduce retry traffic.
4. Roll back a problematic deployment if applicable.
5. Continue monitoring after remediation.