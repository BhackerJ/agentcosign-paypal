# Current deployment status

Render deployment and clean-browser acceptance completed; the service was then
suspended at the owner’s request. Auto-deploy is off. No new PayPal payment,
video upload or formal submission occurred. See
[the hosted acceptance report](../submission/P0-HOSTED-ACCEPTANCE.md).

The following is the historical pre-deployment review; its approval blockers
were resolved by subsequent owner authorization and card setup.

# P0 deployment review

No image has been pushed, no service has been deployed, and no video uploaded.

Target: one Linux amd64 Docker web service with one persistent disk. A single
instance is required because the queue and store locks are process-local.
`render.template.yaml` is a review template, not an applied Blueprint.

Local build:

```sh
docker build --platform linux/amd64 -f deployment/Dockerfile -t agentcosign-p0:review .
```

Only app code, verified fixture catalogs and locked dependencies are copied into
the image. Runtime state, .env files, private artifacts and git metadata are
excluded. `PUBLIC_ORIGIN` must match the deployed HTTPS origin. Inject the model
key at runtime; never bake it into the image. Keep `PAYPAL_CONFIG` unset for this
acceptance deployment: no create/capture can be made. The existing $210.34 sandbox
payment remains separate, prior local evidence; a hosted run must not pretend to
have executed it.

Proposed Render compute: 1 CPU / 2 GB (`standard` legacy name), 1 GB persistent
disk. Listed compute is $25/month plus $0.25/month disk, excluding taxes, model
usage, workspace charges and overages. Verify the final dashboard amount before
creating the service. Keep it available through December 15 only after operating
budget and model spend limits are confirmed.

Sources checked 2026-11-04:
- https://render.com/pricing
- https://render.com/docs/compute-plans
- https://render.com/docs/deploying-an-image
- https://render.com/docs/disks

Render requires a Git-backed commit or a registry image. The P0 changes are
local, so deploying this exact version requires either a code push or uploading
a private image. Neither is covered by the current “do not push or upload”
boundary. Prefer an explicitly approved private image upload; do not push the
public repository or upload videos as a side effect.

Before external activation: owner verifies Render email/login; approves the
specific private registry destination and image upload, runtime model-secret
transfer to Render, and service budget. Do not create registry credentials or
broaden account access without review.

Acceptance after activation: fresh browser, original requests intact, buyer
confirmation, shopper queue, isolated API, blocked unsupported candidates and
payment-disabled state. Record hosted URL and image digest. This remains
separate from the prior local paid run. Verify restart persistence and HTTPS
cookie/Origin behavior on the actual host, not just localhost. Configure and
monitor model spend allowance and attempt limits through the judging period.

Render login and its existing GitHub connection are now verified. An unsubmitted Git-backed form is prepared. A reviewed P0 branch push (after explicit approval) is simpler than provisioning private registry access; the image route remains an alternative, not a requirement. No secret has been entered into Render. Local amd64 clean-browser shopping/API and restart tests passed; hosted checks remain pending.
