# Hosted judge experience — proposed next implementation

Status: proposed; not deployed. Render stays suspended until owner authorizes
resume/publication. No new PayPal payment is needed for this experience.

## One link, no installation or judge-owned API keys

The landing page identifies this as our example personal-agent client with
AgentCoSign authorization. Two explicitly separate routes are available:

1. **Explore the recorded shopping run** (default, no model usage): play the
   actual preserved store replay, inspect the post-run evidence gap, then step
   through saved report-recorded-02 actions, missing-material response, replacement
   and recorded buyer approval. Always label the historical store replay, new
   recovery run, updated read-only UI and expired historical approval. A click
   reveals saved evidence; it must never claim to execute a live shopper or grant
   a new approval. Preserve existing report/replay controls rather than rebuild
   another static presentation. Historical PayPal receipt is a separate labeled
   recorded-work-01 section. No PayPal creation/capture/repeat endpoints here.
2. **Try a live shopper** (optional): buyer confirms a request, server-side keys
   supply Channel3 and model access, shopper runs with real progress and staged
   recovery, buyer reviews/approves the new quote. Per-session cart isolation,
   queue and application usage limits remain. This is a new run with a new ID;
   never reuse the recorded approval. PayPal stays disabled in Channel3 mode.

Both routes must be accessible in a clean browser without a local CLI, token
file, developer console, user-installed dependencies or judge-supplied keys.

## Existing work to reuse

- Existing report integration: app/conversation.py and original replay renderer.
- Existing hosted HTTP/session/auth boundary: app/judge.py.
- Existing live staged recovery: tools/run_channel3_recovery.py.
- Existing approval backend and quote/intent binding: app/server.py and store.
- Final video: owner-cut-v2, referenced by VIDEO.md; video upload remains separate.

## Required work before resuming Render

- Prepare a minimized, rights/privacy-reviewed replay/evidence bundle. Do not
  deploy the full private state tree, browser session, full profiles, API responses
  or credentials. Current public package does not include the replay assets.
- Add a read-only recorded-evidence route and a clearly separate live session.
  Historical snapshots never enter mutable buyer approval/payment state.
- Update the Docker image: currently copies only app/fixtures and starts plain
  judge.py; report replay assets and the recovery tools are not included.
- Keep provider secrets server-side, no PayPal secret in this deployment.
- Test recorded path with external network calls forbidden, session isolation,
  blocked historical writes, clear run labels and a clean browser.
- Provide local review before publishing source or resuming the paid service.

## Deployment acceptance after owner approval

Publish the reviewed implementation, resume one Render instance, then check the
actual HTTPS entry in a fresh browser. Recorded evidence must work even if model
or Channel3 access fails. Live failures must preserve cart state and explain why;
never fall back to an unlabeled saved success. One live acceptance attempt needs
explicit model-call authorization; no additional PayPal payment. Verify credits
and current costs before resuming; application attempt limits are not a hard
hosting/provider billing cap. Video upload and Devpost submission stay unapproved.
