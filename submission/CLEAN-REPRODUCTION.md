# Clean-environment reproduction

Date: November 3, 2026. Source copied into an isolated temporary directory, separate from the original project and private corpus. New Python 3.12.11 virtual environment, public pinned dependencies, Chromium installation checked. Exact installed package versions are saved in requirements.lock.txt.

Results: 39 unit/HTTP contracts passed; eight controlled evaluation outputs reproduced with zero label disagreements; both scenario startup/API smoke checks passed. The checks verified English buyer/developer pages, API authentication and pending buyer confirmation. Provider calls were forbidden in the smoke check and remained zero. No sandbox configuration or model credential was supplied. No new payment was made.

These checks verify installation, server operation and local contracts. They do not constitute another live model-shopping run, another PayPal transaction, or reproduction by an independent external person. Real shopper/payment steps are documented separately in TESTING.md and require provider access.

After publication, signed-out GitHub API and raw README access were verified. The public repository was cloned into a second isolated directory; both scenario UI/API smoke checks passed again with provider calls forbidden and zero actual provider calls. Full contract tests were not redundantly rerun after documentation-only publication.

## Recovery-fix reproduction

A new Python 3.12.11 environment was installed from requirements.lock.txt and a separate tracked-source copy. The revised suite includes three regressions: real Chromium cross-site return/cancel with Strict cookies and explicit same-site continuation; GET-only recovery for an expired existing mock order with capture blocked; completed receipt visibility after expiry. Public evidence pointers were also resolved against shipped JSON. Full suite/evaluation/smoke results for this revision are recorded in RECOVERY-FIXES.md. These tests use local HTTP servers and a fake PayPal provider, never a real model or payment call.
