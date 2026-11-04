"""Standalone AI example client: Claude chooses normal browser actions.

No private harness, buyer credentials, payment tools, or direct cart mutations.
"""

import json, os, secrets, time
from urllib.parse import urlsplit
from shop import serve, token_hash


def run_shopper(app):
    import anthropic
    from playwright.sync_api import sync_playwright

    s = app.s
    task = app.task
    start = time.monotonic()
    token = secrets.token_urlsafe(24)
    if not os.environ.get('ANTHROPIC_API_KEY'):
        raise RuntimeError('ANTHROPIC_API_KEY is required for real browser shopping')
    if s.snapshot(task)['quote']:
        s.reopen(task)
    with s.lock, s.db:
        s.db.execute(
            'UPDATE carts SET visit_hash=?,visit_expires=? WHERE task_id=?',
            (token_hash(token), time.time() + 600, task),
        )
    merchant = serve(s)
    entry = merchant.origin + '/visit/' + token
    intent = s.snapshot(task)['intent']
    trace = []
    messages = []
    passed = False
    used_tokens = 0
    token_limit = getattr(app, 'shopper_max_tokens', 150000)
    time_limit = getattr(app, 'shopper_max_seconds', 300)
    initial_empty = not bool(s.snapshot(task)['items'])
    model = os.environ.get('SHOPPER_MODEL', 'claude-sonnet-4-6')
    client = anthropic.Anthropic(max_retries=0, timeout=60)
    tool = {
        'name': 'browser',
        'description': 'Use a visible link or button by its exact accessible name, or inspect the current page. Never use scripts, APIs or payment actions.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'action': {'type': 'string', 'enum': ['inspect', 'click', 'finish']},
                'role': {'type': 'string', 'enum': ['button', 'link']},
                'name': {'type': 'string'},
            },
            'required': ['action'],
        },
    }
    prompt = (
        'You are the example personal shopping agent. Follow these buyer-confirmed instructions: '
        + json.dumps({k: intent[k] for k in ['request', 'requirements', 'budget_cents', 'quantity']})
        + (
            '. This is a deliberately staged recovery test. Initially add SKU '
            + app.fixture['challenge_first_sku']
            + ' through the UI, then inspect its feedback and correct the SAME cart.'
            if initial_empty and app.fixture.get('challenge_first_sku')
            else '. Inspect the available products and current cart. Choose products from buyer requirements; preserve any correct products already in the cart.'
        )
        + '  Select only one qualifying pair. Unknown required facts cannot pass. Use visible controls only. Never visit buyer/payment pages. Finish only after reading the final cart and its total. Do not claim payment.'
    )
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            options = {'viewport': {'width': 1280, 'height': 900}}
            if getattr(app, 'record_video', True):
                options.update(record_video_dir=str(app.out / 'video'), record_video_size={'width': 1280, 'height': 900})
            context = browser.new_context(**options)
            allowed_origin = merchant.origin

            def route(r):
                url = urlsplit(r.request.url)
                if url.scheme + '://' + url.netloc == allowed_origin and (
                    url.path in ('/shop', '/cart') or url.path.startswith('/visit/')
                ):
                    r.continue_()
                else:
                    r.abort()

            context.route('**/*', route)
            page = context.new_page()
            page.goto(entry)
            messages = [
                {
                    'role': 'user',
                    'content': prompt + '\nCurrent page:\n' + page.locator('body').aria_snapshot(),
                }
            ]
            for turn in range(35):
                if time.monotonic() - start > time_limit:
                    raise TimeoutError('Shopper time limit')
                # Conservatively reserve the serialized UTF-8 input plus output before each call.
                reservation = len(json.dumps({'messages': messages, 'tools': [tool]}, ensure_ascii=False).encode()) + 4096 + 1200
                if used_tokens + reservation > token_limit:
                    raise RuntimeError('Shopper token budget reached; cart preserved')
                response = client.messages.create(
                    timeout=max(1, min(60, time_limit - (time.monotonic() - start))),
                    model=model, max_tokens=1200, tools=[tool], messages=messages
                )
                used_tokens += response.usage.input_tokens + response.usage.output_tokens
                messages.append(
                    {
                        'role': 'assistant',
                        'content': [b.model_dump(exclude_none=True) for b in response.content],
                    }
                )
                calls = [b for b in response.content if b.type == 'tool_use']
                if not calls:
                    messages.append(
                        {
                            'role': 'user',
                            'content': 'Submit your final cart for verification using browser action finish. A text report alone does not complete the task.',
                        }
                    )
                    continue
                outputs = []
                finished = False
                for b in calls:
                    action = b.input.get('action')
                    error = False
                    try:
                        if b.name != 'browser':
                            raise ValueError('Only browser tool is available')
                        if action == 'click':
                            if b.input.get('role') not in ('button', 'link'):
                                raise ValueError('Choose a visible button or link')
                            target = page.get_by_role(b.input['role'], name=b.input['name'], exact=True)
                            if target.count() != 1 or not target.is_visible():
                                raise ValueError('Control not uniquely visible')
                            target.click(timeout=10000)
                        elif action == 'finish':
                            if urlsplit(page.url).path != '/cart':
                                raise ValueError('Read the final cart first')
                            s.runner_finished(task, 'done')
                            quote = s.freeze(task)
                            assessment = s.assessment(task, quote)
                            if assessment['intent_aware_quote_policy']['gate'] != 'allow':
                                s.reopen(task)
                                raise ValueError('Current cart is not eligible; correct it using the page')
                            passed = True
                            finished = True
                        elif action != 'inspect':
                            raise ValueError('Unknown action')
                        content = page.locator('body').aria_snapshot()
                    except Exception as exc:
                        content = (
                            type(exc).__name__
                            + ': action failed; inspect the page and retry with visible controls.'
                        )
                        error = True
                    trace.append(
                        {
                            'turn': turn,
                            'action': dict(b.input),
                            'error': error,
                            'elapsed_seconds': round(time.monotonic() - start, 2),
                        }
                    )
                    outputs.append(
                        {'type': 'tool_result', 'tool_use_id': b.id, 'content': content, 'is_error': error}
                    )
                app.job = 'Browser shopper: completed ' + str(len(trace)) + ' actions. No payment initiated.'
                messages.append({'role': 'user', 'content': outputs})
                if finished:
                    break
            context.close()
            browser.close()
        if not passed:
            raise RuntimeError('Shopper did not finish in the tool budget')
    finally:
        merchant.shutdown()
        merchant.server_close()
        if not passed:
            s.runner_finished(task, 'failed')
        st = s.snapshot(task)
        (app.out / 'shopper-result.json').write_text(
            json.dumps(
                {
                    'evidence_type': 'new_standalone_live_browser_run',
                    'historical_case': app.fixture['id'],
                    'cart_id': st['cart_id'],
                    'seconds': round(time.monotonic() - start, 1),
                    'passed': passed,
                    'model': model,
                    'initial_wrong_candidate_deliberately_assigned': bool(initial_empty and app.fixture.get('challenge_first_sku')),
                    'model_tokens': used_tokens,
                    'actions': trace,
                    'items': st['items'],
                    'quote': st['quote'],
                    'payment_calls': 0,
                },
                indent=2,
            )
        )
