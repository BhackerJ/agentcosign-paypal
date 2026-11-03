# Final English video

Final English video: **1:45.40**. Public upload is pending owner review; no public video URL exists yet. Scene metadata and SHA-256 are in video/final-manifest.json and video/final-scenes.json.

The diagram explains Personal agent → AgentCoSign → Buyer → PayPal, with quote eligibility distinct from permission to pay. The final result card is a GET-only refresh of the already completed main order; it does not initiate payment or rerun duplicate requests.

| Segment | Run | Evidence boundary |
| --- | --- | --- |
| Intent, shopper | recorded-work-01 | Existing source task, buyer-confirmed intent; deliberately assigned missing-evidence candidate; 28.4-second real browser shopping |
| Buyer / PayPal approval pickup | approval-pickup-01 | Different cart and order; separately and continuously labeled; APPROVED, no capture; login entry omitted |
| Verified payment result | recorded-work-01 | Order 61L113898K399762F; capture 0JK088713N9840907; $210.34; two measured sequential repeats; one capture POST and one merchant receipt |
| Final status recording | recorded-work-01, subsequent read-only refresh | Same order, new GET checks only; unchanged POST counts; no new payment |

No claim of continuous footage of one approval-to-payment session is made. A caption and narration identify the supplemental approval order and return to the main transaction. Recorded shopper/browser footage may be time-scaled to narration. The old contradictory status text is not relabeled inside old footage; it is replaced with a newly recorded live final status.

All products are fictional and all payment funds are sandbox. Sequential duplicate results do not establish concurrent crash safety or a general exactly-once guarantee. Narration uses a synthetic English voice. Public YouTube upload and formal submission are pending.

Current evidence: `evidence/final-readonly-verification.json`, `evidence/main-payment.json`, `evidence/approval-pickup.json`, and `video/final-scenes.json`.
