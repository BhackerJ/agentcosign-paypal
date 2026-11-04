# Current release status

Final submission-video: 1:45.40, held locally pending owner review and upload. Earlier edits are audit history and superseded. See [VIDEO.md](VIDEO.md) for run identities and recording boundaries.

- Standalone example browser agent uses public Anthropic and Playwright dependencies; private harness is not required.
- 47 buyer/cart/payment/deadline/return-recovery tests pass. Clean temporary-environment installation and local tests completed.
- Main video transaction: recorded-work-01, cart 931f5a3060347c945c4ee6c5, $210.34. Real shopper 28.4 seconds; exact purchase approval; PayPal order 61L113898K399762F and capture 0JK088713N9840907 COMPLETED; two sequential repeats returned the same capture; one capture POST and one merchant receipt.
- Separate approval-pickup-01: order 62F55632W3809564C APPROVED, zero capture POST. Its footage is visibly labeled separate, then the video returns to the main run.
- Final main-order refresh is GET-only. POST request counts unchanged; no new payment. Final live result card replaces contradictory old shopper-job status.
- Two existing synthetic profile/task source pairs are minimized and hash-linked. Mappings are curated, not general automated intent extraction.
- Eight controlled inputs compared against independent-agent source-review labels. Four positive matches, two explicit conflicts, two evidence gaps; no disagreements. Original four non-blind, new delivery variants labeled before outputs. Not human labels or holdout performance.
- MIT release prepared with credential-free clean Python 3.12 reproduction. External integrator reproduction, YouTube upload and Devpost submission remain incomplete. Public repository publication status is recorded in submission/RELEASE.md.
