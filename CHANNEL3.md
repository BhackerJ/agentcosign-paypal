# Channel3 product discovery (local P1)

Run the existing example personal-agent entry with real Channel3 product data:

```sh
export CHANNEL3_API_KEY='your-private-key'
export ANTHROPIC_API_KEY='your-private-key'
python app/judge.py --catalog-provider channel3 --state state/channel3-judge --port 64321
```

Keep keys in your private environment, never in browser code or Git. The default
provider remains `fixtures`; Channel3 is explicit and never falls back to fixtures
when its API fails. Use a separate state directory for each provider.

The buyer submits and confirms instructions first. Starting the example shopper
searches Channel3 using structured product requirements only (not the full profile
or raw request), retrieves product details, and imports a small offer-scoped catalog
into the sandbox test merchant. The real browser shopper browses and adds products
using visible controls. The existing authenticated authorization API and separate
buyer approval card still control quote eligibility and exact purchase approval.

Only products in the Shoes category tree with a usable positive USD price are
imported. Detail 404s are recorded and skipped; other provider errors stop the run.
A title or a search match is not proof of a required fact. Size, width and color
come from the resolved selected variant, not a list of all available options.
Requested options are sent only when an exact option label exists; the returned
selection is checked by the ordinary intent rules and is never overwritten with
the requested value. Material currently maps to a single `upper-material` value;
ambiguous or absent material remains unknown. Resoling and delivery are unknown.
An unknown required fact cannot enter buyer approval. Imported evidence is a
retrieval-time snapshot, not a promise of current retailer stock.

The merchant sells one pair as its test unit. Its $10 shipping and 6% tax are
**simulated**, not retailer charges. The UI identifies the real product source,
retrieval time, product ID and observed requirements. The persisted quote includes
the source response hash. No real retailer cart, checkout or fulfillment exists.
Retailer landed-price verification is not implemented.

This P1 acceptance mode rejects PayPal configuration. Existing local PayPal
results belong to their original runs; they are not Channel3 purchases. No changes
to the existing fixture-mode payment flow are required.

## Private feasibility check

```sh
python tools/probe_channel3.py --out state/channel3-feasibility-unique-run
```

This makes 20 fixed searches and at most 60 unique detail lookups. It does not
start a shopper or make a payment. Outputs are private, under ignored `state/`.
The probe records default resolved options, not requested-size coverage or product
correctness. An API failure leaves a partial summary and stops; do not call it a
completed probe. Never overwrite an old run directory.

Synthetic adapter and authorization tests are in `tests/test_channel3.py` and use
no live credentials. They cover unknown attributes, selected-option relaxation,
invalid prices, provider errors, same-cart refusal/approval, restart persistence
and refusal to enable payments in this mode.

Before public distribution, review [Channel3 Publisher Terms](https://trychannel3.com/terms/publishers).
Application display is covered in sections 4–5; service benchmark/evaluation
publication requires prior written consent under section 7. Keep live diagnostic
results and source data private. No product offer links are exposed by this
adapter; adding affiliate links requires the corresponding disclosure.

API contract: [official Channel3 reference](https://github.com/channel3-ai/skills/blob/main/skills/channel3-api/references/api-reference.md).

## Explicit real-shopper recovery challenge

```sh
python tools/run_channel3_recovery.py --state state/channel3-recovery-new-run --port 64325
```

Use a fresh state directory. Enter a request for one pair of leather shoes with
one USD maximum, without other attributes. The challenge requires both a real
missing-material candidate and a documented leather candidate within that budget;
otherwise it stops. The initial candidate is deliberately assigned, not a naturally
observed model error. The model adds it through browser controls, asks the actual
authorization API to review it, reads the refusal, chooses a replacement itself,
and removes/adds products in the same cart. No script swaps cart products.

Private action traces retain cart IDs/versions/items and API decisions. Per-review
snapshots and screenshots are kept in the run state. Buyer purchase approval stays
separate; no PayPal configuration is accepted. A successful staged challenge is
not a natural error-rate or general autonomous-recovery benchmark.
