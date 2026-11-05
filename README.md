# AgentCoSign

Purchase authorization and verified PayPal sandbox payments for personal agents.
Your agent shops; AgentCoSign checks the evidence; you approve the exact purchase.
The example personal-agent client is ours. No Muse or Instinct integration is claimed.

**Current owner-review video: 2:21.93, English owner narration, small camera overlay and a local one-link evidence preview.**
See [the canonical video record](VIDEO.md) for the exact version and separate runs.
No public video URL exists yet. [English Devpost draft](submission/DEVPOST.md) ·
[Judge reproduction path](submission/JUDGE-PATH.md) · [Current status](STATUS.md).

## One-link judge experience

The release candidate includes the original report renderer, a minimized historical
replay and allowlisted saved evidence. Start with the recorded route; use
**Explore recorded run → Next** to inspect the five stages. **Try a new live
shopper** starts a separate session using server-side model and Channel3 access.
Read-only evidence never grants current purchase authority.

See [judge instructions](submission/JUDGE-PATH.md) for the exact click path and
[Docker review](deployment/REVIEW.md) for verification scope.
The candidate bundle is local and not yet published. Render remains suspended;
no working public judge URL is claimed.

With the reviewed `deployment/bundle` present, build and run recorded mode:

```sh
docker build --platform linux/amd64 -f deployment/Dockerfile -t agentcosign-experience:review .
docker run --rm -p 127.0.0.1:64350:10000 \
  -e PUBLIC_ORIGIN=http://127.0.0.1:64350 -e MAX_LIVE_RUNS=0 \
  agentcosign-experience:review
```

Open http://127.0.0.1:64350. This route needs no keys. Live mode additionally
requires private server-side `ANTHROPIC_API_KEY` and `CHANNEL3_API_KEY`, persistent
state and sufficient run capacity. Never embed keys in the browser or repository.
The one-link server disables PayPal actions; saved PayPal evidence is separate.

## Start here

The Render service is **suspended by owner request**; it is not a working judge
entry. The latest Channel3/report changes remain local and have not been pushed.
The public repository therefore does not yet contain this complete review version.

Use Python 3.12 from the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m playwright install chromium
PYTHONPATH=app:tests python -m unittest discover -s tests
python evaluate_release.py
python tools/check_local.py
```

These checks use no model credentials or real payment provider. Mock-provider tests
and controlled evaluation are not new shopping or payment evidence.

## Run the example personal agent

Configure your own `ANTHROPIC_API_KEY` privately in the server environment, then:

```sh
python app/judge.py --state state/judge-fresh --port 64300
```

Open http://127.0.0.1:64300 in a fresh browser. Enter a shoe request with one USD
maximum; review and confirm the extracted requirements; start the browser shopper;
then use the separate buyer card to review the exact quote. The default catalog is
fictional fixture data. No `/developer` page or local access-token file is needed
for this session-isolated entry. Model use may incur provider fees.

For real Channel3 discovery and the explicitly staged same-cart recovery challenge,
follow [CHANNEL3.md](CHANNEL3.md) and [the judge path](submission/JUDGE-PATH.md).
Both Channel3 and model keys are required. Missing facts stay unknown; the challenge
stops if current results do not contain suitable candidates. Channel3 mode refuses
PayPal configuration. Shipping, tax and pair quantities are simulated; no retailer
order or fulfillment occurs.

## What the video proves

- An October 14 real-store replay exposes a resoling evidence gap found afterward.
  There was no live CoSign block in that historical store visit.
- `report-recorded-02`: an assigned missing-evidence candidate is paused. The
  controller reopens the same cart; the model selects a replacement and executes
  browser Remove/Add actions. The human approved the exact **$82.08** quote.
  Intent confirmation was automated test setup; payment calls were zero.
- Separate `recorded-work-01`: **$210.34** PayPal sandbox capture and order/capture
  GET verification; two sequential repeats returned the same capture, with one
  capture POST and one local merchant receipt. This is a different cart/order.

Updated report UI is a labeled read-only review of saved events; the original
human approval click appears in an inset. That approval is now expired and grants
no current payment authority. The local release candidate includes only the minimized replay bundle described
in [PUBLIC-RESOURCES.md](PUBLIC-RESOURCES.md); raw source data remains private.
[CONVERSATION.md](CONVERSATION.md) describes the report adapter. Publishing the
bundle remains subject to the resource review and owner release approval.

## Optional PayPal sandbox reproduction

The existing fixture-mode payment implementation is documented in [TESTING.md](TESTING.md).
It requires your own sandbox app, merchant and personal buyer account. Keep secrets
out of Git. Leave PayPal unconfigured for no-payment review; payment then stays
disabled. Actually reproducing a sandbox transaction is optional and separate from
credential-free checks and preserved evidence. We are not running another payment
as part of this review.

A PayPal return URL is not proof of payment. Existing-order GET remains available
after quote expiry; capture does not. See TESTING.md for conservative recovery.
The agent API can request purchase review but cannot confirm intent, approve or pay.

## Scope and license

This prototype uses curated synthetic profile/task extracts, deterministic evidence
checks, versioned carts and exact quote/intent approval bindings. Preset retry
success is not a general autonomous-recovery rate. The 24-case human-label packet
is prepared; human results and external usability remain pending. AI labels are
not human evidence. Sequential repeats do not establish concurrent exactly-once
behavior. No production-money, retailer checkout or fulfillment claim is made.

MIT licensed; see [LICENSE](LICENSE) and [THIRD_PARTY.md](THIRD_PARTY.md).
[Reproduction record](submission/CLEAN-REPRODUCTION.md) distinguishes prior clean
installation from the latest isolated-copy checks. Judge credentials, continuing
hosted access, the documented third-party use assumptions and public release still require review
before a fully accessible submission can be claimed.

Hosted product-data use terms and disclosures are available at `/demo-terms`.
See [public-resource review](PUBLIC-RESOURCES.md) for the remaining Nisolo screenshot/video release decision.

Before a new live session, read the Demo terms, check the agreement box and choose
**Agree to terms and start**. The server saves the session, version, document
SHA-256 and UTC timestamp; this consent does not confirm intent or approve a purchase.
Recorded inspection does not require agreement. A changed terms version/hash
requires new consent before live actions.
