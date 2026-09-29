# General Troubleshooting and Incident Guide

## First response checklist

For any technical problem, collect the following before escalating:

- the environment affected (production, staging, development)
- exact error messages, HTTP status codes and the `X-Request-Id` header if available
- timestamp of the first occurrence with timezone
- whether the issue affects one user, one workspace or everyone
- any recent deployment or configuration change on the customer side

## Performance and slowness

Slow dashboards are usually caused by very large projects or browser extensions.

1. Ask the customer to test in a private/incognito window with extensions disabled.
2. Check the status page for ongoing incidents.
3. For API latency, ask for request timestamps and `X-Request-Id` values of slow calls so the
   engineering team can trace them.
4. Report timeouts: requests taking longer than 30 seconds are terminated with `504 Gateway Timeout`.
   Large report exports should use the asynchronous export endpoint instead.

## Outages and incident severity

- **SEV1**: production outage or data exposure affecting many customers. Page the on-call engineer
  immediately and link the ticket to the incident.
- **SEV2**: major feature unavailable for many customers, or production blocked for one large customer.
- **SEV3**: degraded functionality with a workaround.

Security issues (suspected account takeover, leaked credentials, data exposure) must always be
escalated to the security team, regardless of the number of affected users.

## Clearing cache and local data

Many display issues are resolved by a hard refresh (`Ctrl+Shift+R` / `Cmd+Shift+R`) or clearing
site data for `app.acme-cloud.dev`. The dashboard supports the latest two versions of Chrome,
Firefox, Safari and Edge.

## Webhook delivery problems

If webhooks are not received:

1. Confirm the endpoint returns a 2xx status within 10 seconds.
2. Check **Settings → Developers → Webhooks → Delivery log** for response codes.
3. Verify the receiving server accepts TLS 1.2 or newer.

## Data export and deletion

Workspace owners can export all data from **Settings → Workspace → Export**. Account deletion is
permanent after 30 days; within that window support can restore a deleted workspace.
