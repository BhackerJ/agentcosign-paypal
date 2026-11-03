"""Buyer-only review of server-owned quotations."""
import datetime
import html

from shop import Refused


def render_review(store, buyer):
    esc = html.escape
    money = lambda value: f'${value/100:.2f}'
    state = store.snapshot(buyer['task_id'])
    intent = state['intent']
    body = '<p class="label">AGENTCOSIGN · BUYER REVIEW</p><h1>Your choice. Your approval.</h1>'
    body += '<p>Local sandbox demo · fictional merchandise and fixed test shipping/tax.</p>'
    body += f'<section><h2>Your request</h2><p>One pair · size {esc(intent["required_size"])} · Extra Wide · total budget {money(intent["budget_cents"])} USD.</p></section>'
    quote = state['quote']
    hidden = ''
    if quote:
        hidden = f'<input type="hidden" name="csrf" value="{esc(buyer["csrf"])}"><input type="hidden" name="quote_id" value="{esc(quote["quote_id"])}"><input type="hidden" name="quote_hash" value="{esc(quote["sha256"])}">'
    refresh = f'<form method="post" action="/buyer/requote">{hidden}<button>Request a fresh quotation</button></form>'
    if not quote:
        body += '<section><h2>Waiting for a completed quotation</h2><p>The shopper has no current frozen quote to approve. A changed cart needs a new quotation.</p><a href="/buyer/review">Refresh status</a></section>'
    else:
        try:
            assessment = store.assessment(buyer['task_id'], quote)
        except Refused:
            body += '<section><h2>Quotation expired or changed</h2><p>Approval is unavailable. Request a fresh quotation, then review the new items and total.</p>'+refresh+'</section>'
        else:
            body += f'<section><h2>Exact quotation</h2><p>Seller: {esc(quote["merchant_id"])} · USD</p>'
            for line in quote['lines']:
                body += f'<div class="item"><h3>{esc(line["name"])}</h3><p>Quantity {line["quantity"]} · {esc(line["unit"])} · size {esc(line.get("size", "n/a"))} · width {esc(line.get("width", "n/a"))}<br>{money(line["price_cents"])} per unit</p></div>'
            body += '<dl>'
            for key, label in [('subtotal_cents', 'Merchandise'), ('discount_cents', 'Discount'), ('shipping_cents', 'Test shipping'), ('tax_cents', 'Test tax'), ('total_cents', 'Total USD')]:
                body += f'<div><dt>{label}</dt><dd>{money(quote[key])}</dd></div>'
            body += '</dl>'
            expiry = datetime.datetime.fromtimestamp(quote['expires_at'], datetime.timezone.utc).isoformat(timespec='seconds')
            body += f'<p class="small">Quote {esc(quote["quote_id"])} · cart version {quote["cart_version"]}<br>Valid until {expiry}</p></section>'
            if quote.get('paypal_merchant_id'):
                body += f'<p class="small">PayPal sandbox seller account: {esc(quote["paypal_merchant_id"])}</p>'
            with store.lock:
                decision = store.db.execute('SELECT status FROM approvals WHERE quote_id=?', (quote['quote_id'],)).fetchone()
            gate = assessment['intent_aware_quote_policy']['gate']
            if decision and decision['status'] == 'declined':
                body += '<section><h2>Quotation declined</h2><p>No active approval remains. A new quotation is required to approve again.</p>'+refresh+'</section>'
            else:
                approved = assessment['buyer_approval'] == 'app_approved'
                body += '<section><h2>'+('Quotation approved' if approved else 'Review decision')+'</h2>'
                body += '<p>'+('Your approval is saved for these exact items, seller and total. See the separate PayPal status below.' if approved and store.payments else 'Your approval is saved for these exact items, seller and total. PayPal has not been started; no payment has been made.' if approved else 'Approve only if the items, seller and full total match what you want. This saves app approval; it does not pay.')+'</p>'
                if gate != 'allow':
                    failures = [c['key'] for c, result in zip(store.facts(buyer['task_id'], quote)['constraints'], assessment['intent_aware_quote_policy']['intent_rules']) if result != 'pass']
                    body += f'<p class="blocked">Approval blocked: {esc(", ".join(failures) or "budget or missing evidence")} does not satisfy your request.</p>'
                if gate == 'allow' and not approved:
                    body += f'<form method="post" action="/buyer/approve">{hidden}<button>Approve these items and {money(quote["total_cents"])}</button></form>'
                body += f'<form method="post" action="/buyer/decline">{hidden}<button class="secondary">'+('Withdraw my approval' if approved else 'Decline this quotation')+'</button></form></section>'
    if store.payments:
        from payments import render_payment
        with store.lock:
            body += render_payment(store, buyer)
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AgentCoSign · Buyer review</title><style>
    *{box-sizing:border-box}body{font:17px/1.65 system-ui;background:#edf5f1;color:#183b32;max-width:850px;margin:auto;padding:28px}h1{font-size:38px;line-height:1.2}h2{font-size:22px}h3{font-size:18px}.label{letter-spacing:2px;font-size:12px}section{background:white;border:1px solid #c7dcd2;border-radius:16px;padding:24px;margin:20px 0}.item{border-bottom:1px solid #d9e6df}dl>div{display:flex;justify-content:space-between;gap:15px;padding:5px 0}dd{margin:0;font-weight:650}dl>div:last-child{font-size:24px;border-top:1px solid #bfd5ca;padding-top:12px}.small{font-size:12px;overflow-wrap:anywhere;color:#526c62}button{font:inherit;padding:14px 20px;border:0;border-radius:8px;background:#15654b;color:white;cursor:pointer;max-width:100%}.secondary{background:#e9efec;color:#294b40}form{margin-top:14px}.blocked{color:#a42b27}a{color:#15654b}@media(max-width:500px){body{padding:16px}section{padding:18px}h1{font-size:30px}}
    </style>'''+body+'</html>'
