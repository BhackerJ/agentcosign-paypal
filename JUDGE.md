# Session-isolated judge entry — local P0 implementation

This entry is under development; it is not the published judge deployment.
The existing single-task `app/server.py` workflow remains supported.

## Run locally

Use Python 3.12 and the installation steps in README.md. Install Chromium with
`python -m playwright install chromium`. Set `ANTHROPIC_API_KEY` in the service
process, never in the browser or repository. Then run:

```sh
python app/judge.py --state state/judges --port 64300
```

Open http://127.0.0.1:64300 in a fresh browser context. Submit a request for one
pair of shoes with exactly one USD maximum (for example, “Find black leather
shoes, size 11 wide, under $250, delivered within 14 days”). Review every
extracted property on the AgentCoSign page and confirm. Return to the example
personal agent, then start its browser shopper. That shopper uses visible
merchant controls and the authorization API; it cannot confirm, approve or pay.
Follow the approval link to review the exact quote.

For PayPal sandbox, append `--paypal-config /absolute/private/paypal.env` with
the existing sandbox config format documented in README.md. Without it, payment
is unavailable. PayPal login and final approval belong to the human buyer.
No payment is initiated automatically by extraction or shopping.

This version uses the two existing, fictional shoe catalogs. Product attributes
and fixed shipping/test tax are fixture data, not Channel3 data. Unsupported
requests may have no eligible product. Model extraction is a draft, not proof
that every requirement was understood: the original request and extracted
requirements are shown together for buyer confirmation.

## Isolation and limits

Each opaque HttpOnly judge cookie maps to a separate SQLite cart store, agent
key, intent confirmation, approval, PayPal record and receipt. API calls require
both `X-Agent-Session` and that session's bearer key. Buyer actions require
cookies, matching Origin and CSRF; supplying a bearer key does not grant buyer
authority. `/developer` and the legacy file-based entry are unavailable here.
A judge session expires after 24 hours. Expiry shows a refusal rather than
silently creating another purchase. Owner-assisted recovery is still needed
for expired judge sessions with pending orders; do not restart them as purchases.

One shopper executes at a time; other requests show queued status. An attempt
has 35 turns, a 180-second deadline checked between actions, an SDK request
bounded by remaining time, and an 80,000 cumulative model-token allowance.
Before each call, serialized input bytes plus a conservative overhead and
output allowance must fit the remaining budget. Browser action/cleanup time
can extend wall-clock duration. These are application limits, not a provider
billing guarantee. Set a provider spend cap before public deployment.
Extraction uses at most 900 output tokens and a 30-second SDK timeout.
There are 40 extraction and 40 shopper attempts total per state directory,
including failed attempts, and 200 sessions. These do not reset daily. Limits
must be sized and monitored through the judging period; this default is not a
claim of unlimited availability. New shopper runs do not record video.

## Local verification

```sh
PYTHONPATH=app:tests python -m unittest discover -s tests
```

`test_judge.py` uses injected extraction output and FakePayPal. It checks fresh
request mapping, budget preservation, cross-session key/cookie rejection,
restart persistence, neutral PayPal returns, and sequential duplicate capture.
It does **not** establish live Claude accuracy, real PayPal success, a new
shopping run, concurrency exactly-once guarantees, or production readiness.
Old payment evidence remains associated with its original run IDs.

## Hosting preparation (not deployed)

`deployment/Dockerfile` is a draft container build for a single service instance.
Configure an HTTPS `PUBLIC_ORIGIN`, persistent disk at `/var/data`, model secret
in the provider environment, and the sandbox config as secret file
`/etc/secrets/paypal.private.env`. `/health` is a liveness endpoint only.
Do not scale to multiple processes: queue and store locks are process-local.
The image build, reverse-proxy behavior, provider billing cap, non-sleeping plan,
credentials distribution, and service availability through December 15 remain
to be validated before publishing this entry.

Original walking-shoe and documented-resoling requests have now passed targeted live extraction and clean-browser confirmation tests. Strict “under $N” budgets exclude that amount by one cent. Local Linux amd64 container shopping/API and restart acceptance passed with PayPal disabled; hosted acceptance is still pending. Full regression count: 60.
