# Judge testing instructions

## Availability

Source and reviewed replay assets are public on `codex/p0-judge-entry`. The actual
HTTPS endpoint https://agentcosign-paypal-p0.onrender.com passed clean-browser
acceptance, including real shopper recovery and automated test-buyer approval.
It was then suspended under the owner's post-acceptance cost-control instruction.
Restore it before giving the hosted link to judges. See HOSTED-V5-ACCEPTANCE.md.
No installation or judge-owned provider key is needed when the service is online.

## Recorded experience — no credentials or payment

1. Open the supplied entry URL. The original shopping report opens in recorded mode.
2. Choose **Explore recorded run** and play the store replay. Native pause and
   timeline controls work; the run/source strip stays visible.
3. Use **Next** to inspect the missing-material check, browser replacement and
   saved exact approval. This is recorded evidence, not a new shopper execution.
4. The $82.08 approval belongs to `report-recorded-02`, is expired and read-only.
   No approval or payment can be repeated from this historical card.
5. The last stage shows `recorded-work-01`: a separate $210.34 PayPal sandbox
   purchase, capture/GET checks and two sequential duplicate requests. It is not
   payment for the Channel3 cart.

The October 14 Nisolo replay is a separate historical visit. Its resoling gap
was discovered afterward; no historical live CoSign block is claimed.

## Optional new live shopper — server credentials required

1. Select **Try a new live shopper**. A new isolated cart/session is created.
2. Enter “Find one pair of leather shoes under $900.” Review the extracted
   requirements and confirm only if they match your intent.
3. Start the shopper. This preset challenge assigns a real Channel3 candidate
   missing required evidence. CoSign pauses eligibility; the controller reopens
   the cart and the model chooses a replacement through browser Remove/Add.
4. Inspect the exact quote and evidence, then choose **Approve exact purchase**
   if appropriate. This is a new approval in the new cart. Payment is disabled.
5. Return links preserve that cart. Keep its run identity separate from recordings.

The hosted operator must supply model/Channel3 access; judges must not supply keys.
Search results, prices and totals vary. Missing suitable candidates, provider
failures or capacity exhaustion must be shown honestly; recorded output is never
substituted for a failed live run. Real data feeds a fictional merchant: shipping,
tax and pair units are simulated, and no source retailer order is placed.

## Developer reproduction

README.md includes credential-free tests and the recorded-mode Docker command.
The candidate archive contains `deployment/bundle`; a source-only checkout without
that bundle cannot build the exact replay image. For live standalone reproduction
see CHANNEL3.md. TESTING.md documents the separate optional PayPal sandbox path;
no new payment is required for this review or publication.

## Before releasing these instructions

Verify the public code/assets from a clean clone, actual hosted HTTPS behavior,
server-side credentials and judging-period access/capacity. Complete source imagery
and data-display rights review (PUBLIC-RESOURCES.md). Put any necessary private
test credentials only in a confirmed private channel, never in public prose.

Hosted product-data use terms and disclosures are available at `/demo-terms`.
See [public-resource review](../PUBLIC-RESOURCES.md) for the remaining Nisolo screenshot/video release decision.

Before a new live session, read the Demo terms, check the agreement box and choose
**Agree to terms and start**. The server saves the session, version, document
SHA-256 and UTC timestamp; this consent does not confirm intent or approve a purchase.
Recorded inspection does not require agreement. A changed terms version/hash
requires new consent before live actions.
