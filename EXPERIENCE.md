# Current publication and hosted acceptance

Approved v5 source and replay assets are public on the default `main` branch.
Actual Render HTTPS/live acceptance passed; compute was suspended afterward
under the owner’s cost-control instruction. See
[acceptance record](submission/HOSTED-V5-ACCEPTANCE.md). Earlier local-preview
observations below retain their original scope.

---

# One-link judge experience — local preview

Open http://127.0.0.1:64340 while the local preview is running. No installation or
judge-owned key is required in the browser. Everything is English. Render remains
suspended; this is not yet a hosted public entry.

## Recorded route (default)

The original report/replay renderer remains the main interface. Its native player
shows existing captured pages and original messages. “Play full store replay”
rewinds it and automatically resumes its intermediate key-moment pauses. The
native speed, timeline and manual controls remain available. “Pause replay” stops
guided playback. Next/Previous reveal five evidence stages without changing pages:

1. Historical October 14 Nisolo visit; resoling was a post-run finding, not a live block.
2. Separately identified report-recorded-02: assigned candidate, actual missing-material response.
3. Saved browser Remove/Products/Add actions and allow response in the same new cart.
4. Exact historical $82.08 approval, now expired and read-only; zero payment calls.
5. Different recorded-work-01 $210.34 PayPal sandbox receipt and sequential repeat evidence.

The display export in evidence/recorded-recovery.json contains allowlisted
request/actions, quote/intent hashes and approval binding. It does not contain
private browser sessions, credentials, raw model prompts or raw provider data.
The optional export tool reads the source SQLite database in read-only mode.
The minimized replay assets are included in the local candidate bundle;
publication still needs the rights review described in PUBLIC-RESOURCES.md.

## New live route

“Try a new live shopper” creates a fresh isolated buyer session before opening the
existing report integration. It is explicitly marked NEW LIVE RUN, separate from
the left historical replay and from report-recorded-02. Sending a request performs
real model extraction; confirming intent and starting the shopper uses the existing
Channel3 recovery/authorization/buyer backend. Server-side model and Channel3
keys must be configured privately; the browser never receives them. The challenge
is preset and controller-assisted; the model chooses its replacement through real
browser actions. New totals need not match the saved run.

Opening this route creates a session only; it does not make a model call or approve
anything. The local owner-preview check opened the route and verified its empty
buyer workflow, but did not execute a new model shopping run. Prior live acceptance
belongs to the previously identified runs, not this new preview session.

This server refuses payment/provider actions including pay, capture, check,
refresh and repeat. Channel3 mode also refuses PayPal configuration. Historical
approval cannot be replayed as current buyer authority.

## Start locally (maintainer)

After the existing dependency setup, configure the two provider keys privately:

```sh
python app/experience.py --state state/experience-fresh --replay deployment/bundle/replay --port 64340
```

Use a fresh state directory; do not point this server at historical payment state.
The preview uses the existing compact report style and buyer backend. No private
replay directory or Secret is copied into the repository by startup.

## Verification

77 regression tests pass, including session-free recorded access, distinct live
sessions with zero usage reservation, evidence allowlists, and payment/write refusal.
Browser checks verified replay starts, the five stage controls, historical expired
approval, separate receipt, and switching both directions between modes. An initial
live-heading observer loop was corrected by updating the DOM only when its value
changes; mode links force full navigation to avoid the report router retaining the
other mode's contents. No new payment or public deployment occurred.

## Usability review fixes — local acceptance

Run identities now stay in a fixed strip below the mode navigation. The page and
scroll targets use its measured height, so wrapping labels do not cover stage
headings. The strip changes from report-recorded-02 to recorded-work-01 for the
separate receipt and says NEW LIVE RUN for the new session.

Trusted clicks on native Play/Pause, pointer input on the slider, and replay
keyboard controls exit guided mode. Programmatic key-moment resumes do not.
The delayed guided start also checks that guided mode is still active.

A new live session scrolls to its heading with the same header offset. Before a
request is sent, the empty buyer-card article has zero layout height and a short
“Send a request to begin” prompt appears instead. The existing buyer card is
revealed when the request is submitted; buyer authority remains unchanged.

Browser acceptance checked native Pause staying paused after another tool round
trip, keyboard takeover, all recorded stages, header/stage geometry at desktop
and narrow viewport overrides, and the live initial card's hidden/zero-height
state. Overrides were reset afterward. JavaScript syntax, diff whitespace and
the two HTTP boundary tests passed. No new model request, shopping run or payment
was performed in this verification.

Before a new live session, read the Demo terms, check the agreement box and choose
**Agree to terms and start**. The server saves the session, version, document
SHA-256 and UTC timestamp; this consent does not confirm intent or approve a purchase.
Recorded inspection does not require agreement. A changed terms version/hash
requires new consent before live actions.
