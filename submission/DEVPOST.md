# AgentCoSign

## Tagline
Purchase authorization and verified sandbox payments for personal agents.

## Inspiration
A personal shopping agent can stay within budget while selecting a candidate
whose required attributes are unsupported. Existing simulated shopping research
motivated a purchase check that preserves the buyer's requirements through exact
quote approval and payment verification.

## What it does
Your personal agent handles shopping. AgentCoSign checks a server-owned quote
against buyer-confirmed requirements. Unknown required facts pause eligibility;
matching evidence permits buyer review. Only the buyer approves the exact purchase.
The example client is ours; Muse and Instinct integrations are not implemented.

Channel3 supplies real product search and detail data to a sandbox test merchant.
Product IDs, source merchants, retrieval times and response hashes accompany the
quote. Shipping, tax and the merchant's pair unit are simulated. This does not
place an order with the source retailer or verify its landed price or fulfillment.

A separate sandbox payment path uses PayPal order creation, capture and GET
reconciliation. The agent has no buyer-approval or payment tools.

## Demonstrated evidence
The video first plays an existing real-store shopping replay (player 16×, with
additional recording speed labeled), using
original pages and messages from October 14. The resoling evidence gap is a
post-run finding, not a historical runtime block. It is separate from the new
Channel3 recovery episode below.

**New recorded report run: report-recorded-02.** In an explicitly
preset reject-and-retry challenge, the shopper adds an assigned real candidate.
Missing material evidence pauses authorization. The controller reopens the same
cart; the model independently selects a replacement and executes Remove/Add
through browser controls. Buyer requirements remain unchanged. Browser shopper
runtime was 23.7 seconds including setup/cleanup. The report conversation displays actual backend browser actions and CoSign feedback.
The buyer approved the recovered
$82.08 quote. The human approval click was recorded in the embedded report card without a
top-level page change. Zero payment calls were made in this run. Intent confirmation was
automated test setup; exact purchase approval was performed by the human buyer.

**Separate historical PayPal run: recorded-work-01.** A $210.34 sandbox purchase
completed capture and order/capture GET verification. Two sequential repeated
application requests returned the same capture, with one capture POST and one
local merchant receipt. The video uses that run's later read-only result footage;
it is a different cart and order, not a payment for the new Channel3 purchase.
This does not establish concurrent crash safety or universal exactly-once behavior.

An earlier source-copy check passed 75 tests using an existing isolated Python
environment. The published v5 clone subsequently passed 85 regression tests; see
HOSTED-V5-ACCEPTANCE.md and the reproduction record. These
are software checks, not shopper accuracy measurements. A 24-case human-review
packet is prepared; human labeling and its paired evaluation are pending. AI
assistant labels are not counted as human evidence. No comparative error-rate
claim is made.

## How we built it
Python and SQLite maintain versioned carts, confirmed intents and exact approval
bindings. Claude with Playwright chooses visible shopping actions. Deterministic
checks compare observed facts against the confirmed request. Channel3 discovery
is server-side and preserves missing attributes. PayPal sandbox GET checks verify
recorded order/capture identity, payer, merchant, currency, items and amounts.

## Existing work and new implementation
We reuse historical simulated-shopping failures and minimized synthetic
profile/task extracts, with their provenance retained. New work includes the
natural-language example client, session-isolated intent and quote review,
Channel3 discovery, recorded staged recovery, buyer approval and sandbox payment
verification. Preserved historical failures are not counted as new shopper runs.

## Limits and next steps
The staged recovery demonstrates replacement after an instructed failure, not an
unprompted retry strategy or natural error rate. Product evidence is a snapshot;
strict size, width, delivery and resoling requirements can remain unsupported.
Human evaluation and an external usability session remain unfinished. Render was
deployed and tested, then suspended at the owner's request; no currently available
hosted judging link is claimed. Payment is disabled in the Channel3 acceptance
mode. Source-data evaluation publication permission remains to be confirmed.

## AI tools
Claude chooses browser actions. Codex assisted implementation, tests, documentation
and evidence review. The 2:21.93 review video includes a labeled local recorded-evidence entry preview,
with no offline acceptance presented as real execution. It uses the owner’s English narration and a small camera
overlay while the application remains visible. There is no synthetic voice.

## Submission fields — owner review required
- Repository: https://github.com/BhackerJ/agentcosign-paypal
- Approved v5 Channel3/report source and reviewed replay assets are merged into the default main branch.
- Working access: [judge reproduction instructions](JUDGE-PATH.md); Render currently suspended. The intended hosted live route uses operator-provided model/Channel3 access. The minimized historical replay bundle is now included in the public branch.
- Review video: owner-cut-v4-ending, 2:21.93, English owner narration; [canonical version and run boundaries](../VIDEO.md). Public URL pending approval.
- Team, final category selections and judging credentials: owner confirmation pending.
- No video upload or Devpost submission has occurred.

Current access update: see HOSTED-V5-ACCEPTANCE.md. Actual hosted recovery and
automated test approval passed in a new $86.28 cart; service suspended afterward
for cost control. This is separate from the video’s human-approved $82.08 run
and the historical $210.34 PayPal purchase.
