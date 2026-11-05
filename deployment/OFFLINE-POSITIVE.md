# Offline positive container acceptance — November 4, 2026

**Run:** `offline-container-positive-01`. This is a new synthetic acceptance run, separate from
report-recorded-02 and every historical PayPal purchase. No real shopper, model,
Channel3 service, human approval or payment is claimed.

## Return fix

The existing `/conversation` return (except its internal panel endpoint) and
`/agent` now redirect to `/visits/1/?mode=live`. Neither calls `/live/new` or
sets a new judge cookie. Embedded buyer links also target this existing live page
at the top level. The root/default recorded experience remains unchanged.

HTTP regression and container checks confirm the same cart/session survives
returning after intent confirmation and after exact-purchase approval. A browser
also clicked the actual standalone buyer-page return link and reached that same
cart in the report.

## What ran inside the image

Image: `agentcosign-experience:return-review` ·
`sha256:ac39531ff60eaf8a1f971b29c0f1cfd194083bdf2ec2ad62e0f76aa88cf6954a`.
The production handlers, store, authorization API, buyer forms and renderer come
from that image. Two acceptance-only scripts were mounted read-only from `tests/`;
they are not copied into the production image and no test-mode switch was added
to the production entry.

The first container used **Docker `--network none`**. Requests were only to its
own loopback HTTP servers. The test launcher additionally blocks outbound DNS and
connections, refuses provider credentials and uses an injected synthetic draft
extractor plus deterministic fixture merchant form submissions. It does not run
Claude, Channel3 discovery, an AI browser shopper or PayPal.

The sequence used real application HTTP boundaries:

1. Create one isolated test session and submit the fixture request.
2. Confirm the exact intent with the buyer's form/cookie/CSRF.
3. Submit a fictional product through the merchant HTTP form; mark scripted test
   runner completion and call authenticated `/api/purchase` and `/api/review`
   on the container-local API origin.
4. Verify quote eligibility `allow`, while actual authorization remains
   `insufficient_evidence` until buyer approval.
5. Attempt approval with an agent bearer: rejected 403. Then submit the actual
   buyer approval form as an automated test buyer: accepted.
6. Verify actual authorization `allow`; return through both routes with the same
   session, cart, version, intent and quote.
7. Actually restart the container, reload through the saved private test cookie
   and verify all cart/quote/approval bindings are identical. No second approval
   is created. Expired records/quotes are not renewed by this test.

## Preserved result

| Field | Before and after restart |
| --- | --- |
| Cart | `a745c93d345bd59a8a6be0a5` |
| Cart version | 1 |
| Quote | `22d917eb391c04c55f5c2c4b` |
| Approval | `f72573945c5bc4d37464b414` |
| Amount | $210.34 · fictional test merchant |
| Quote/intent hashes | Identical and bound to approval |
| Sessions / approvals | One / one |
| Payment-provider calls | Zero |

83 full regression tests passed, including a same-cart live-return regression.
The production handler also rejects the mount-only `/offline/open-result` route.
This fixture run does not prove real Channel3/model recovery, actual hosted HTTPS
behavior or a new PayPal transaction. Those remain separate future acceptances.

## Reproduce without any external service

Prepare the reviewed replay bundle as in REVIEW.md and build the image. Use a
FRESH host state directory and a unique `OFFLINE_RUN_ID` for each new execution.
No keys or PayPal config should be passed:

```sh
mkdir -p state/offline-check-new
docker run -d --name agentcosign-offline-check --network none --platform linux/amd64 \
  -e PUBLIC_ORIGIN=http://127.0.0.1:10000 -e OFFLINE_RUN_ID=offline-check-new \
  --mount "type=bind,src=$PWD/state/offline-check-new,target=/var/data" \
  --mount "type=bind,src=$PWD/tests,target=/opt/check,readonly" \
  agentcosign-experience:return-review python /opt/check/container_offline_server.py
docker exec agentcosign-offline-check python /opt/check/container_positive_acceptance.py before
docker restart agentcosign-offline-check
docker exec agentcosign-offline-check python /opt/check/container_positive_acceptance.py after
```

The phase refuses to overwrite an existing before-result. Cookie/agent tokens
stay under ignored private state, never in the sanitized report. Reproduction
requires no test-user browser action: buyer approval here is automated and is
not counted as human evaluation.

## Local owner preview

After completing the no-network test, that instance was stopped. A separately
labeled loopback preview of its persisted fixture state is available at
http://127.0.0.1:64360/offline/open-result . It uses the same mounted test launcher
and outbound guard, without provider keys. The local test-only route opens only
this synthetic session; it is not part of the production server. The page clearly
says OFFLINE ACCEPTANCE and identifies synthetic fixtures/automated test approval.
No Render activation, push, upload, external service or new payment occurred.
