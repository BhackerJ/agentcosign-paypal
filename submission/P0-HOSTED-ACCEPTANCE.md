# P0 hosted acceptance — 2026-11-04

## Deployment and current availability

Render successfully built and served commit `e0e220ea67fc2b1ed712768adc8163e2f7f6fb3e`
from `codex/p0-judge-entry` at https://agentcosign-paypal-p0.onrender.com.
After acceptance, the owner requested suspension. Render now shows **Suspended by you**.
The URL is not currently an available judge entry. Auto-deploy is off.

Docker service: one CPU, 2 GB RAM, one 1 GB disk mounted at `/var/data`.
Only the model credential was configured privately. No PayPal configuration was
installed; no hosted provider order or payment was created.

## New hosted run, separate from local payment evidence

Three fresh Chromium contexts submitted the three original natural-language
requests unchanged. All reached draft review and synthetic automated intent
confirmation. This is browser acceptance, not human buyer confirmation or a
held-out accuracy benchmark. The walking request retained walking type, 12-day
delivery and $130 maximum. The resoling request retained documented resoling,
10-day delivery and a strict-under-$220 cap of $219.99.

Only the first case ran the real model-driven browser shopper. It reached the
authorization API with `allow` in approximately 22.2 seconds and a $210.34 quote.
The other two cases validate intent extraction and confirmation only; they do
not establish catalog fulfillment. Catalogs remain fictional fixtures, not
Channel3 products.

All three contexts had Secure, HttpOnly, SameSite=Strict session cookies and
rejected unauthenticated agent API reads with HTTP 403. A valid-session capture
request returned HTTP 409, “PayPal sandbox is not configured”; this is a disabled
endpoint check, not a provider capture. After requesting a Render service restart,
the saved first session retained its confirmed intent and $210.34 quote without
another model or payment call. Local regression count remains 60; no code changed
in this acceptance report.

## Reused payment result — different local run

The prior local P0 acceptance used cart `f6ea4d95771dc9989c603b60`, order
`1KF77430V8495583E`, capture `4T557022JV912920G`, USD 210.34. It completed capture,
order/capture GET reconciliation and two sequential repeat checks, with one
capture POST and one merchant receipt. It is not a payment from the hosted run
and is not proof of concurrency exactly-once behavior. This work added zero
PayPal payments, recordings, video uploads or formal submissions.

## Cost and operating boundary

At the billing check: $50 credit balance, expiry October 31, 2027; month-to-date
unbilled charges displayed $0.00 (billing may lag), November projection $22.38.
Listed compute is $25/month and retained disk $0.25/month. Additional build
pipeline spend limit is $0, not a service-wide spending cap. Render confirms
suspended services are not billed for compute. Disk data is retained; do not
assume all storage charges stop. Model costs are separate from Render credits.
No recurring monitor was created: the owner selected suspension after acceptance.
Before resuming for judges, recheck credits, disk billing and model allowance,
and agree an operating window. Availability through December 15 is not yet met.

Sanitized acceptance data: [hosted acceptance JSON](p0-hosted-20261104.json).
Browser cookies, private state, API keys and raw private artifacts are excluded.
