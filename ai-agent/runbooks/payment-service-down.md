# Payment Service Down

## Symptoms
- Payment service reports DOWN
- Requests to the service fail
- Error rate approaches 100%

## Possible Causes
- Application crash
- Dependency failure
- Deployment failure
- Resource exhaustion
- Network connectivity issue

## Investigation
1. Check service health.
2. Review recent application logs.
3. Check latency and error rate.
4. Check recent deployments.
5. Check dependent services.

## Remediation
1. Restart the payment service if appropriate.
2. Roll back a failed deployment.
3. Restore unavailable dependencies.
4. Verify service health after remediation.