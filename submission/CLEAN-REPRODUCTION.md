# Clean-environment reproduction

Date: November 3, 2026. Source copied into an isolated temporary directory, separate from the original project and private corpus. New Python 3.12.11 virtual environment, public pinned dependencies, Chromium installation checked. Exact installed package versions are saved in requirements.lock.txt.

Results: 39 unit/HTTP contracts passed; eight controlled evaluation outputs reproduced with zero label disagreements; both scenario startup/API smoke checks passed. The checks verified English buyer/developer pages, API authentication and pending buyer confirmation. Provider calls were forbidden in the smoke check and remained zero. No sandbox configuration or model credential was supplied. No new payment was made.

These checks verify installation, server operation and local contracts. They do not constitute another live model-shopping run, another PayPal transaction, or reproduction by an independent external person. Real shopper/payment steps are documented separately in TESTING.md and require provider access.
