# Local example personal-agent conversation

Run with private CHANNEL3_API_KEY and ANTHROPIC_API_KEY configured:

```
python app/conversation.py --state state/conversation-new --replay deployment/bundle/replay --port 64331
```

The local release candidate includes a minimized historical replay in
`deployment/bundle/replay`. The raw source corpus remains private; public bundle
publication is still subject to the rights review in PUBLIC-RESOURCES.md.
It uses existing captured real-store pages and agent messages, ending before
private checkout fields. Historical post-run findings are not live blocks.
The current test merchant episode is a different cart and task, explicitly labeled.
No third-party personal-agent integration or historical-store repair is claimed.

In the same conversation page, submit a leather-shoe request with one explicit
USD cap. Confirm the intent in the embedded buyer card, start the real shopper,
watch browser actions and actual authorization feedback, then review/approve the
exact quote in that card. It is served by the existing buyer backend, with existing
Origin, CSRF, cookie/session isolation and agent restrictions. Payments remain
unconfigured. Reopening a refused cart is controller-assisted; product Remove/Add
and replacement selection are model browser actions in the explicit challenge.

This is a functional local example client: live polling reads actual session cart
and shopper trace; it does not synthesize a pretend chat transcript. Historical
replay and current execution are labeled as separate episodes within one UI.
No new video is produced by this change. Do not publish the raw private replay corpus.
