# AgentCoSign

## Tagline

Buyer-controlled purchase authorization and verified PayPal payments for personal agents.

## Inspiration

A shopping agent can stay within budget and still select the wrong product. Our existing simulated shopping research included a request for Extra Wide shoes where a Standard-width candidate was selected. A budget check cannot detect that mismatch. We wanted personal agents to preserve the buyer's requirements all the way from shopping to approval and payment.

## What it does

AgentCoSign is a local purchase authorization and sandbox payment layer. An example personal agent shops through a browser and calls an authenticated quote-review API. AgentCoSign checks merchant-owned cart details against a source-linked intent that the buyer has confirmed. The buyer separately approves the exact items and all-in total, then approves in PayPal sandbox. The service captures and reads back the order and capture before issuing a verified receipt.

The example includes two existing synthetic profile/task pairs: Extra Wide walking shoes and resolable black leather work shoes. Their mappings are curated and traceable to minimized source extracts. Unknown required facts pause review rather than being treated as proof of compliance.

## How we built it

Python and SQLite maintain server-owned carts, quote versions, intent hashes and approval records. A standalone Claude/Playwright example client chooses visible browser actions. It has no buyer-approval or payment tools. PayPal Orders and Capture APIs execute sandbox payments, and GET reconciliation checks the payer, merchant, items, currency, amount and order association. Recorded request identities and unique local purchase/receipt records support safe sequential duplicate handling.

## What we tested

In recorded-work-01, the real browser shopper completed the deliberately assigned recovery challenge in 28.4 seconds. The buyer approved the exact $210.34 quote and PayPal order. Order 61L113898K399762F and capture 0JK088713N9840907 both returned COMPLETED. Two sequential repeated application requests returned the same capture, with one capture POST and one merchant receipt. A subsequent read-only refresh verified the same order without increasing POST counts.

The video includes a separately labeled approval-only pickup, approval-pickup-01. That is a different order: APPROVED, not captured. We do not present the two recordings as one continuous transaction.

Forty-two contract tests cover cart, buyer approval, payment and delivery boundaries. Eight controlled inputs were compared against separately authored agent-review labels: four matching candidates allowed, two conflicts blocked and two missing-evidence cases paused. Original cases were not blind; this is not human-labeled or held-out population performance evidence.

## Challenges and limitations

Quote eligibility is not permission to pay. Preserving that distinction, binding exact approvals, and treating missing merchant evidence honestly were central design challenges. Browser recording also required explicit run labels and a separate pickup to avoid implying continuity that had not been recorded.

This is a single-task loopback prototype using a fictional test merchant. Buyer and developer views share authentication. It does not demonstrate production multi-user security, real fulfillment, concurrent crash safety or universal exactly-once payment. There are no live Muse/Instinct integrations and no general automatic profile-to-intent extractor.

## Existing work and hackathon updates

Existing work: AgentCoSign's simulated shopping corpus, synthetic profiles/tasks and browser-shopping research. Hackathon-period work includes source-linked confirmed purchase intent, complete-quote comparisons, exact buyer approval, the personal-agent review/receipt API, PayPal sandbox order/capture/GET reconciliation, sequential duplicate verification, a standalone public-dependency example client, independent-agent review and the English demonstration. Preserved historical failures are not counted as new experiments.

## AI tools and technologies

Claude Sonnet 4.6 chooses browser actions in the example client. OpenAI Codex assisted implementation, tests, evidence organization, independent agent reviews and documentation. The English narration uses local synthetic speech. The policy checks are deterministic; evaluation labels are explicitly agent-reviewed rather than human ground truth. Built with Python, SQLite, Playwright, Anthropic SDK, PayPal Sandbox Orders/Captures APIs and FFmpeg.

## What's next

Validate the adapter with independent integrators and more diverse untouched shopping tasks; improve profile normalization, role separation, lifecycle recovery and concurrent-operation testing.

## Submission links — review before publishing

- Repository: https://github.com/BhackerJ/agentcosign-paypal
- Working build: README and TESTING.md in the public repository; local setup, no hosted service.
- Video: local video/agentcosign-final.mp4, 1:45.40. PUBLIC YOUTUBE URL NOT YET CREATED.
- No Devpost submission has been sent. Replace the video placeholder only after owner review and upload approval.
