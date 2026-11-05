# Latest isolated-copy verification — November 4, 2026

A fresh temporary source copy excluded state, credentials, private corpus and
video assets. The existing isolated Python 3.12 environment was reused; this was
not a fresh dependency installation or an independent external-person test.
Model, Channel3 and PayPal credential environment variables were removed.

- `PYTHONPATH=app:tests python -m unittest discover -s tests`: **75 passed**.
- `python evaluate_release.py`: **8 controlled cases**, zero intent-policy
  disagreements with development/source-review labels. These are not human labels,
  held-out measurements or a real-world prevented-purchase rate.
- `python tools/check_local.py`: both fixture scenarios passed English UI,
  authentication and pending-confirmation startup/API checks; **provider calls=0**.

Local HTTP binding required execution outside the restricted filesystem sandbox.
No live model, Channel3 search, PayPal order/capture, deployment, push or upload was
performed. The exact historical report assets are deliberately not included in this
copy and their absence is documented in JUDGE-PATH.md.

Earlier clean installation/public-clone checks below retain their original dates
and scope; they do not prove availability of today's unpushed local changes.

---

# Clean-environment reproduction

Date: November 3, 2026. Source copied into an isolated temporary directory, separate from the original project and private corpus. New Python 3.12.11 virtual environment, public pinned dependencies, Chromium installation checked. Exact installed package versions are saved in requirements.lock.txt.

Results: 39 unit/HTTP contracts passed; eight controlled evaluation outputs reproduced with zero label disagreements; both scenario startup/API smoke checks passed. The checks verified English buyer/developer pages, API authentication and pending buyer confirmation. Provider calls were forbidden in the smoke check and remained zero. No sandbox configuration or model credential was supplied. No new payment was made.

These checks verify installation, server operation and local contracts. They do not constitute another live model-shopping run, another PayPal transaction, or reproduction by an independent external person. Real shopper/payment steps are documented separately in TESTING.md and require provider access.

After publication, signed-out GitHub API and raw README access were verified. The public repository was cloned into a second isolated directory; both scenario UI/API smoke checks passed again with provider calls forbidden and zero actual provider calls. Full contract tests were not redundantly rerun after documentation-only publication.

## Recovery-fix reproduction

A new Python 3.12.11 environment was installed from requirements.lock.txt and a separate tracked-source copy. The revised suite includes three regressions: real Chromium cross-site return/cancel with Strict cookies and explicit same-site continuation; GET-only recovery for an expired existing mock order with capture blocked; completed receipt visibility after expiry. Public evidence pointers were also resolved against shipped JSON. Full suite/evaluation/smoke results for this revision are recorded in RECOVERY-FIXES.md. These tests use local HTTP servers and a fake PayPal provider, never a real model or payment call.
