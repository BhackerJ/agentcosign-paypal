# Judge setup and testing

Requires Python 3.11+ and a desktop OS supported by Playwright. Install into a fresh environment from the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m playwright install chromium
PYTHONPATH=app:tests python -m unittest discover -s tests
python evaluate_release.py
python tools/check_local.py
python app/server.py --scenario resolable-work-shoes --state state/judge --port 64200
```

No credentials, external model calls or payments are needed for the test suite, controlled evaluation or initial service startup. Tests use a fake provider; preserved sandbox results are evidence, not live test payments.

Open the one-use URL stored in state/judge/access.private.json. Confirm the source-linked instructions. Without a model key, the service cannot run the real AI shopper; it will preserve the cart and report the stopped run.

## Real browser shopper

Set ANTHROPIC_API_KEY in the server process environment before starting it. The default model is claude-sonnet-4-6; SHOPPER_MODEL can select another model supported by your Anthropic account. Set provider spend limits as appropriate. The service uses public Python packages and requires no private harness. Visit /developer in the authenticated buyer browser and press Start / resume browser shopper. When complete, the exact quote appears on the buyer page; the example client has called the review API. The initial unsuitable candidate is deliberately assigned as a recovery test.

## Optional sandbox payment

Create a free PayPal developer account, a Sandbox REST app/business account and a personal sandbox buyer account at https://developer.paypal.com/. Use sandbox credentials only. Obtain the merchant and personal buyer Payer IDs from the sandbox account details. Copy .env.example to a local ignored file and populate all four identifiers/secret plus PAYPAL_ENV=sandbox. Keep the personal buyer password private; enter it in PayPal yourself.

Start a FRESH scenario state directory with `--paypal-config /absolute/path/to/your/private-config` from the beginning so quotes bind the sandbox merchant. The buyer approves the exact quote, continues to PayPal, logs in with the personal sandbox buyer (not the merchant), and completes approval. On return, click Continue to buyer review on the neutral return page, then Check PayPal status. The return URL is not payment proof. The Complete approved sandbox payment button performs capture and GET verification. This is an explicit optional transaction, not part of the no-payment test suite. The developer console offers sequential duplicate checks only after payment is verified.

Never use live credentials. No submitter credentials are published. Judges obtain their own sandbox/model access; no hosted free model access is currently supplied. Validate that this access route is practical before final submission.

## Resume and failures

Keep the same state directory to preserve a cart. Restarting issues a new one-use buyer URL and invalidates the old session; it does not reset recorded payment. Use a separate state directory for a new task/scenario. An existing recorded/in-flight payment prevents shopping again. Quote eligibility can expire after 15 minutes. If no PayPal order exists, request a fresh quote through the review UI and approve it again. If an order already exists, Check PayPal status remains available even after expiry. These checks are read-only and preserve the order. Capture remains disabled for an expired quote; this prototype does not renew or replace an existing order automatically. Keep the existing order for reconciliation rather than creating another order as a retry. A verified completed receipt remains visible after quote expiry. Unknown provider outcomes require reconciliation rather than blind retries. No automatic real-money path exists.

The prototype is loopback-only, single-task and shares buyer/developer authentication. Do not expose it directly as a production multi-user service. See VIDEO.md and STATUS.md for precise measured scope.

Browser regression coverage includes actual localhost-to-127.0.0.1 cross-site return/cancel navigation with SameSite=Strict, spoofed return parameters, expired existing-order GET recovery, blocked expired capture, and a completed receipt after expiry. Payment-provider behavior in the regression suite is mocked; no live order or charge is issued.
