# Current release: approved v5 published and hosted acceptance passed

See [HOSTED-V5-ACCEPTANCE](submission/HOSTED-V5-ACCEPTANCE.md). Source/assets commit
5137330 is published; real HTTPS/shopper recovery and automated test approval passed
in a new $86.28 cart. Zero new PayPal payments. Service suspended after acceptance
per owner instruction, state retained; video upload and formal submission pending.

Earlier dated records below retain their historical scope.

---

# Live return fix and offline positive acceptance — 2026-11-04

Live return aliases preserve the existing session/cart and mode. A separate Linux
container with network=none completed synthetic intent confirmation, merchant
form submission, authenticated quote review and automated test-buyer approval.
After actual restart, cart/version/quote/intent/approval bindings and one-session,
one-approval counts persisted; payment calls zero. Browser return click also
preserved the same approved cart. 83 regressions passed.

See [deployment/OFFLINE-POSITIVE.md](deployment/OFFLINE-POSITIVE.md). This is not a
new real shopper, human approval, Channel3 result, PayPal purchase or hosted HTTPS
acceptance. Mounted fixture scripts are excluded from the production image.
Render suspended; no push, upload, external service call or new payment.

---

# Local deployment-package review — 2026-11-04

The full one-link experience now has a Linux Docker image, hosted-origin/port
configuration, friendly full-capacity responses and expiry-aware active capacity.
A minimized replay package contains 48 OCR-checked captures and 109 hashed files;
private corpus/state/config/videos and inherited cross-store summary data are
excluded. See [deployment/REVIEW.md](deployment/REVIEW.md).

Local image URL: http://127.0.0.1:64350 . Model runs deliberately disabled during
acceptance; no provider credentials configured. Recorded UI, assets, capacity,
Origin refusal, payment refusal and restart persistence checked. Existing payment
runs unchanged. Generated bundle is Git-ignored, pending publication approval.
Render stays suspended; no push, upload, new payment or hosted activation.

---

# Local one-link experience — 2026-11-04

[EXPERIENCE.md](EXPERIENCE.md) documents the local report entry on port 64340.
Recorded replay and five saved-evidence stages are separate from a new isolated
live shopper session. 77 regression tests passed; browser checks exercised the
recorded steps and mode navigation. No new model run is claimed for this preview.
Render remains suspended; no new payment, push, upload or submission.

---

# Current owner-review status — 2026-11-04

Canonical video: owner-cut-v2, 2:21.93, owner English narration and small camera
overlay. See [VIDEO.md](VIDEO.md), [English submission draft](submission/DEVPOST.md)
and [judge access checklist](submission/JUDGE-PATH.md). Prior video references
below are history and are superseded by this entry.

Local Channel3/report recovery and exact $82.08 human approval are separate from
historical recorded-work-01 $210.34 payment. No new payment for this update.
Render remains suspended. Latest source is local, not pushed; no video uploaded
or formal submission made. Own-key live reproduction is documented; exact private
historical replay assets, unrestricted hosted judge access, human evaluation and
external usability are not supplied or claimed.

---

# Current release status

**Latest P0:** Render hosted acceptance passed, then the service was suspended at the owner’s request. Three original requests reached confirmation; one real shopper reached a $210.34 eligible quote. Hosted payment is disabled. See [hosted acceptance](submission/P0-HOSTED-ACCEPTANCE.md). Earlier entries below are historical.

Final submission-video: 1:45.40, held locally pending owner review and upload. Earlier edits are audit history and superseded. See [VIDEO.md](VIDEO.md) for run identities and recording boundaries.

- Standalone example browser agent uses public Anthropic and Playwright dependencies; private harness is not required.
- 47 buyer/cart/payment/deadline/return-recovery tests pass. Clean temporary-environment installation and local tests completed.
- Main video transaction: recorded-work-01, cart 931f5a3060347c945c4ee6c5, $210.34. Real shopper 28.4 seconds; exact purchase approval; PayPal order 61L113898K399762F and capture 0JK088713N9840907 COMPLETED; two sequential repeats returned the same capture; one capture POST and one merchant receipt.
- Separate approval-pickup-01: order 62F55632W3809564C APPROVED, zero capture POST. Its footage is visibly labeled separate, then the video returns to the main run.
- Final main-order refresh is GET-only. POST request counts unchanged; no new payment. Final live result card replaces contradictory old shopper-job status.
- Two existing synthetic profile/task source pairs are minimized and hash-linked. Mappings are curated, not general automated intent extraction.
- Eight controlled inputs compared against independent-agent source-review labels. Four positive matches, two explicit conflicts, two evidence gaps; no disagreements. Original four non-blind, new delivery variants labeled before outputs. Not human labels or holdout performance.
- MIT release prepared with credential-free clean Python 3.12 reproduction. External integrator reproduction, YouTube upload and Devpost submission remain incomplete. Public repository publication status is recorded in submission/RELEASE.md.

## 2026-11-04 — local P0 judge-entry implementation

Added natural-language draft extraction, separate example-agent and buyer pages,
session-isolated stores and agent keys, queued browser shopping, resource limits,
and a deployment scaffold. Existing CAPTURE payment flow is preserved.

Validation: 56 local tests passed (47 existing + 9 new). New extraction tests
inject model output; new payment tests use FakePayPal. No new real model run,
PayPal transaction, recording, deployment, public push or upload was performed.
See [JUDGE.md](JUDGE.md) for remaining live-model, hosting and credential gates.


## 2026-11-04 — new local live payment acceptance

Existing credentials were reused without disclosure. Live draft extraction and
browser shopping reached the authorization API. Following human PayPal approval,
the new isolated P0 cart completed capture and order/capture GET reconciliation.
Two sequential repeat requests returned the same capture: one capture POST and
one local merchant receipt. Amount: USD 210.34. This is new-run evidence, not old
recording reuse, and does not prove concurrent exactly-once behavior.

Two live-acceptance fixes (fenced model JSON and same-origin form referrer policy)
have regression coverage; 58 tests passed before payment verification. Natural
language acceptance included rewritten requests after refusals; do not claim
3/3 first-attempt accuracy. Hosting, external browser acceptance and operating
limits remain pending. No public push or upload was performed.

Original-request follow-up: both refused inputs now reach confirmation verbatim in live-model clean-browser tests. Strict under-budget parsing and walking type are preserved. Final regression: 60 passing tests. Local amd64 container shopping/API, second-session isolation and restart checks pass with zero provider calls. Render configuration is prepared but unsubmitted; no deployment or public push is claimed.


## Authorized P0 publication and Render activation attempt

Reviewed P0 implementation commit `0a1c24b` was pushed to
`codex/p0-judge-entry` with owner authorization. Main was not changed.
Render activation of the Docker service with persistent state was attempted,
but the account required adding a payment card despite redeemed hackathon
credits. The card dialog was canceled under the owner's no-card constraint.
The dashboard still showed no services. No hosted browser acceptance can be
claimed; the local container results above remain the available acceptance.
No new PayPal transaction, video upload or formal submission occurred.

## Local P1 Channel3 work (not pushed or deployed)

An explicit Channel3 discovery mode now imports offer-scoped product data into
an isolated test merchant before the existing browser shopper and authorization
API run. Missing attributes remain unknown; source IDs, retrieval times and
response hashes are retained. PayPal configuration is refused in this mode.
72 local regression tests passed. Live feasibility and acceptance records are
held privately, with controlled policy checks separated from real-shopper runs.
See [CHANNEL3.md](CHANNEL3.md) for reproduction and boundaries. Render stays
suspended; no new payment, recording, video upload or submission occurred.

A separate local Channel3 recovery challenge now exercises the real shopper after
an explicitly assigned first candidate. Shopper completion calls the authenticated
authorization API; a refused cart is reopened without changing buyer requirements,
and the model selects its replacement through browser controls. Traces preserve
cart identity and review decisions. 73 regression tests pass. Live run evidence
remains private; purchase approval is pending, and no payment was performed.


The recovery run's subsequent human purchase approval has now been verified
against its exact quote, cart version and intent; payment calls remain zero.
Local English evidence/script material was updated without recording a new video.
A private 24-case blinded human-review packet is prepared, but labels, paired
metrics and independent usability are pending. No publication or deployment.

Independent-review corrections: the local demo now uses a same-run read-only
historical approval view, clearly expired, and explains the preset recovery
instruction plus controller reopening. An expired historical approval never
restores payment authority. 73 regression tests pass. The unissued human-review
pilot is superseded by a shuffled, stratified v2 packet held privately; no human
labels or comparison results have been generated. No new payment or publication.
