# Return and expired-order recovery fixes

- PayPal return/cancel now serve a neutral 200 page. The buyer explicitly continues to the same-site review page. SameSite=Strict and CSRF protections remain enabled. Return query parameters do not grant approval or payment status.
- An existing provider order always has a read-only status-check entry, including when its quote expires. Expired quotes cannot authorize capture. Existing orders are not automatically renewed or replaced. New-quote refresh applies only before a provider order exists; this conservative prototype deliberately stops rather than starting a replacement transaction.
- Completed receipts stay visible after quote expiry. Session expiry recovery uses a newly issued local buyer entry; the recorded order is preserved.
- Public labels now contain only the eight reproducible controlled inputs. Every evidence pointer resolves to a shipped fixture JSON path/selector. Historical-summary reviews were removed from this public export, without adding them to evaluation denominators.
- Verification: 42 local contracts, including three new recovery tests; eight controlled label comparisons; both English UI/API smoke scenarios. Payment provider is mocked/forbidden in these checks. No new real order, capture, model call, video upload or Devpost submission.
- Complete real-model integration by an external judge/user still requires separately documented model and sandbox access. This revision does not claim that independent full-flow exercise has happened.

## Failed capture recovery

A refused or unknown capture no longer leaves the buyer without a next step. A refused capture returns to ready with a new request ID and offers another PayPal payment method. A timeout, server error or restart stays in reconciliation and retries with the same request ID after reading the order back. Five contracts cover this with a fake provider; no new order, charge or live sandbox decline was exercised.
