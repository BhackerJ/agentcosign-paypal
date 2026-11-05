# Published v5 hosted acceptance

The approved bundle and source have been published. Render built commit 5137330
and actual clean-browser HTTPS/live recovery and automated test-buyer approval
passed. It is now suspended again. See
[HOSTED-V5-ACCEPTANCE](../submission/HOSTED-V5-ACCEPTANCE.md).
Prior pending-publication/hosted-acceptance notes below are historical.

---

# Current follow-up: same-cart return and offline positive acceptance

The live return fix and no-external-service positive container test are complete.
See [OFFLINE-POSITIVE.md](OFFLINE-POSITIVE.md) for the new, separate test run,
current return-review image ID and reproducible restart verification. 83 full
regression tests passed. Prior image results below retain their original image ID.
Real Render HTTPS and real-model/Channel3 acceptance are still pending. Render
remains suspended; no source/image/video published or payment added.

---

# One-link experience deployment review — November 4, 2026

**Local image acceptance complete. Render remains suspended. Nothing pushed or uploaded.**
Target remains the existing Render service `agentcosign-paypal-p0`; this template
must not be applied as a new paid service. No new PayPal payment is required.

## What is ready

- Docker starts `app/experience.py`, includes the recovery tool, minimized recorded
  evidence and the prepared original report/replay resources.
- `PORT`, `PUBLIC_ORIGIN`, `STATE_DIR`, `REPLAY_DIR`, `MAX_LIVE_RUNS` and
  `MAX_ACTIVE_SESSIONS` are supported. Non-loopback listening requires an explicit
  public origin; public origins require HTTPS. Agent review uses container-local
  `127.0.0.1:PORT`, not an external round trip. Secure buyer-session cookie flags
  derive from the public origin.
- A full live-session pool returns HTTP 429 with recorded/existing-session links.
  Only unexpired sessions occupy active capacity; expired rows and purchase state
  are retained. Usage limits remain cumulative and do not reset after restart.
- The build context uses an allowlist. State, dotenv files, private artifacts,
  videos and the original corpus are excluded. No provider credentials are baked in.

## Local package privacy review

`deployment/bundle/manifest.json` records 109 file hashes: the 48 referenced PNG
captures, the original renderer and referenced assets, minimized view data and two
allowlisted evidence files. All 48 captures passed local Tesseract OCR checks for
configured private contact/credential patterns. Text assets and metadata were also
checked. PNG text/EXIF chunks were removed while original compressed pixels remain.
Unreferenced captures/assets and inherited cross-store header/aggregate data were
excluded. The resulting view identifies one Nisolo excerpt, not eight other visits.

An initial numeric-pattern warning was inspected: the image contained public XML
sitemap range IDs, not card data. Payment-number checks now use card-field context
rather than treating every long public product/sitemap ID as financial data.
Automated/OCR checks have limits and do not establish merchant imagery/display
permission. Public publication of imagery and Channel3 display still requires the
owner's material review. Raw provider response dumps and full profiles are absent.

The generated bundle is intentionally Git-ignored. Source-only push would not
include it. Before a Git-backed Render build, the reviewed bundle must be explicitly
approved and included, or an approved image must be published instead. Neither
publication route has been taken.

## Reproduce the local image acceptance

From the release repository root, with the reviewed bundle present:

```sh
docker build --platform linux/amd64 -f deployment/Dockerfile -t agentcosign-experience:review .
mkdir -p state/image-review
docker run --name agentcosign-experience-review --platform linux/amd64 \
  -p 127.0.0.1:64350:10000 \
  -e PUBLIC_ORIGIN=http://127.0.0.1:64350 \
  -e MAX_LIVE_RUNS=0 -e MAX_ACTIVE_SESSIONS=2 \
  --mount "type=bind,src=$PWD/state/image-review,target=/var/data" \
  agentcosign-experience:review
```

Open http://127.0.0.1:64350. Acceptance deliberately uses no model/Channel3 keys,
no PayPal config and zero model-run allowance. Recorded evidence remains available;
this is not a new successful live shopper test. Stop the local acceptance container
when finished; keep its separate test state if reproducing restart checks.

The prepared bundle can be regenerated into a FRESH output directory with
`python tools/prepare_experience_bundle.py --replay /absolute/reviewed-excerpt --out /absolute/new-bundle`.
The preparation requires local Tesseract; it is not run during image startup and
does not fetch private data in a Render build.

Final image ID: `sha256:ab0009cd78ac58740ccfa976fcf792bed8c8a9d920e6ec03e17137012fb1adbc`.
Regression suite: **82 passed**.

## Verified scope

- Linux amd64 image builds; all 109 deployed files match the bundle manifest.
- Image starts using the external mapped port/origin; `/health` passes.
- All 48 screenshot URLs work; recorded stages and original report render.
- Recovery $82.08 and historical payment $210.34 remain separate/read-only.
- Wrong Origin is refused; valid Origin + CSRF reaches the deliberate zero-budget
  refusal without contacting a provider. Payment/provider action routes return 403.
- Third active session returns 429 with a working recorded route; expiring test
  rows permits another session while preserving the expired records.
- Container restart retains session rows and zero model/shopper usage.
- Regression suite includes deployment configuration, HTTPS cookie flags and
  capacity behavior. JSON/JS/whitespace and bundle-integrity checks passed.

## Still required before actual activation

Review the bundle and public source, authorize their publication and service
activation, verify current Render credits/cost settings, then supply runtime model
and Channel3 secrets privately. Keep PayPal unconfigured. Do not change the
existing compute/disk plan merely by applying this review template. Confirm actual
judging access and cumulative model allowances; application limits are not provider
or hosting billing caps. Perform actual hosted HTTPS clean-browser/live-shopper
acceptance after activation; it has not occurred for this new entry.

Render field names were checked against the [official Blueprint reference](https://render.com/docs/blueprint-spec).
The review template uses `autoDeployTrigger: 'off'`; no Blueprint was applied.
