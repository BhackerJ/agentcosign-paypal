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
