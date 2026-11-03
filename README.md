# AgentCoSign

**Final English demo:** 1:45.40; public video upload pending owner review · [Run identities and recording boundaries](VIDEO.md) · [Current status](STATUS.md)

Purchase authorization and PayPal sandbox payment for personal agents.

This standalone release uses minimized, hash-verified extracts from two existing synthetic profile/task pairs: walking-width and resolable-work-shoes. The buyer confirms the intent; the example browser agent shops; the API evaluates the server-owned quote; the buyer separately approves purchase and PayPal payment. Buyer and developer surfaces are English.

## Run

Python 3.11+ is required.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.lock.txt
python -m playwright install chromium
export ANTHROPIC_API_KEY='your-key'
python app/server.py --scenario resolable-work-shoes --state state/work --port 64200
```

Open the one-use URL stored in `state/work/access.private.json`. Confirm the shopping instructions yourself, then visit `/developer` to start the real shopper. The model chooses visible browser controls. Browser video is saved under the state directory. The deliberately assigned initial candidate has missing resoling evidence. Unknown is treated as insufficient evidence, not proof of a defect.

Use `--scenario walking-width --state state/walking` for the other scenario. Keep separate state directories. Restarting issues a fresh buyer entry URL; it preserves the cart and invalidates the previous buyer session.

## PayPal sandbox

Create your own sandbox business app and personal buyer account at developer.paypal.com. Copy `.env.example` to a private config file, fill its values, and add `--paypal-config /absolute/path/to/private-config` to the server command. The buyer approves the exact quote, continues to PayPal, and returns to check status and capture. The developer console offers sequential repeat verification. Without configuration, payment is explicitly disabled.

Agent API: `GET /api/purchase`; `POST /api/review` with current `cart_version` and confirmed `intent_sha256`. Authenticate with the bearer key in the state directory. The agent cannot confirm intent, approve purchase or initiate payment through these API routes.

```sh
python app/client.py --origin http://127.0.0.1:64200 --key-file state/work/agent-key.private.txt --review
PYTHONPATH=app:tests python -m unittest discover -s tests
```

## Evidence and limits

The main recorded-work-01 transaction completed a $210.34 sandbox payment, Order/Capture GET verification and two sequential repeat checks: one capture POST and one merchant receipt. The separately labeled approval-pickup-01 is an approval-only order, not captured. Final result footage refreshes the same main order read-only. See VIDEO.md for exact run identities. The final video remains local until owner approval.

The two source mappings are curated; no generic profile extraction or Muse/Instinct integration is claimed. Buyer/developer views share authentication. This is a loopback prototype. Model usage requires provider access and may incur cost. Eight controlled cases have independent-agent source-review labels, not human or held-out benchmark evidence. Delivery days are explicit fictional merchant commitments from a common order-date anchor.

Original full-file hashes identify historical sources; the fixture manifest verifies the separately minimized extracts. No full profiles, addresses, private harness or credentials are required to install this release.

## License and reproduction

MIT licensed; see LICENSE. Public dependency licenses remain with their respective packages. See TESTING.md and submission/CLEAN-REPRODUCTION.md for the credential-free clean-environment checks. The real model and sandbox paths require your own provider access; no model credits or hosted judge service are included.
