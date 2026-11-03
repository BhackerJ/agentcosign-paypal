"""Paired offline rules over frozen, annotated facts. No payment execution."""
import argparse
import collections
import hashlib
import json
import time
from pathlib import Path


def budget_rule(facts):
    amount, limit = facts.get('observed_cents'), facts.get('limit_cents')
    if amount is None or limit is None or not facts.get('currency'):
        return 'insufficient_evidence'
    if amount > limit:
        return 'block'
    if facts['basis'] == facts['limit_basis'] or (
            facts['basis'] == 'estimated_total' and facts['limit_basis'] == 'all_in'):
        return 'pass'
    return 'insufficient_evidence'


def constraint_rule(constraint):
    actual = constraint.get('observed')
    if actual is None:
        return 'insufficient_evidence'
    if constraint['operator'] == 'eq':
        matches = actual == constraint['required']
    elif constraint['operator'] == 'lte':
        matches = isinstance(actual, (int, float)) and not isinstance(actual, bool) and actual <= constraint['required']
    elif constraint['operator'] == 'subset':
        matches = set(actual).issubset(set(constraint['required']))
    else:
        raise ValueError('Unsupported operator: ' + constraint['operator'])
    return 'pass' if matches else 'block'


def combine(results):
    if not results:
        return 'not_applicable'
    for decision in ('block', 'insufficient_evidence', 'needs_clarification'):
        if decision in results:
            return decision
    return 'pass'


def evaluate_policy(facts, intent_aware):
    """Quote eligibility for buyer review; never a payment authorization."""
    budget = budget_rule(facts['budget'])
    semantic = [constraint_rule(c) for c in facts['constraints']] if intent_aware else []
    result = combine([budget, *semantic])
    # An estimate or a cart subtotal is never a complete, approved payment quote.
    if result != 'block' and (not facts['quote_complete']
                              or facts['budget']['basis'] != 'all_in'):
        result = 'insufficient_evidence'
    if result == 'pass':
        result = 'allow'
    return {'budget_rule': budget, 'intent_rules': semantic,
            'intent_summary': combine(semantic), 'gate': result}


def evaluate(facts, intent_aware):
    result = evaluate_policy(facts, intent_aware)
    if result['gate'] == 'allow' and not facts['buyer_approval_verified']:
        result = {**result, 'gate': 'insufficient_evidence'}
    return result


def verify_sources(cases, roots):
    checked = set()
    for case in cases:
        for ref in case['source_refs']:
            key = (ref['root'], ref['path'], ref['sha256'])
            if key in checked:
                continue
            path = (roots[ref['root']] / ref['path']).resolve()
            path.relative_to(roots[ref['root']].resolve())
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != ref['sha256']:
                raise ValueError('Source changed: ' + ref['path'])
            checked.add(key)
    return len(checked)


def run(path, out, roots=None):
    started = time.perf_counter()
    snapshot = json.loads(path.read_text())
    cases = snapshot['cases']
    source_count = verify_sources(cases, roots) if roots else None
    rows = []
    for case in cases:
        frozen = {k: v for k, v in case.items() if k not in ('expected', 'facts_sha256')}
        digest = hashlib.sha256(json.dumps(frozen, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        if digest != case['facts_sha256']:
            raise ValueError('Annotated facts changed: ' + case['case_id'])
        # Labels never enter either evaluator.
        facts = {k: case[k] for k in ('budget', 'constraints', 'quote_complete', 'buyer_approval_verified')}
        baseline, intent = evaluate(facts, False), evaluate(facts, True)
        expected = case['expected']
        actual = {'budget': baseline['budget_rule'], 'intent': intent['intent_summary'],
                  'budget_gate': baseline['gate'], 'intent_gate': intent['gate']}
        rows.append({'case_id': case['case_id'], 'family_id': case['family_id'],
                     'budget_only': baseline, 'intent_aware': intent,
                     'annotation_agreement': actual == expected})
    families = collections.defaultdict(list)
    for row in rows:
        families[row['family_id']].append(row)
    summary = {
        'cases': len(cases), 'semantic_families': len(families),
        'budget_gate_counts': dict(collections.Counter(r['budget_only']['gate'] for r in rows)),
        'intent_gate_counts': dict(collections.Counter(r['intent_aware']['gate'] for r in rows)),
        'additional_block_points': sum(r['intent_aware']['gate'] == 'block' and r['budget_only']['gate'] != 'block' for r in rows),
        'additional_block_families': sum(any(r['intent_aware']['gate'] == 'block' and r['budget_only']['gate'] != 'block' for r in group) for group in families.values()),
        'complete_safe_payment_cases': sum(c['quote_complete'] and c['buyer_approval_verified'] and c['expected']['intent_gate'] == 'allow' for c in cases),
        'scoped_positive_cases': sum(c['expected']['intent'] == 'pass' for c in cases),
        'scoped_positive_false_blocks': sum(c['expected']['intent'] == 'pass' and r['intent_aware']['intent_summary'] == 'block' for c, r in zip(cases, rows)),
        'human_adjudicated_cases': 0, 'heldout_cases': 0,
        'human_validated_unsafe_allow_rate': None, 'complete_safe_allow_rate': None,
        'human_validated_false_block_rate': None,
        'annotation_disagreements': sum(not r['annotation_agreement'] for r in rows),
        'source_files_verified': source_count, 'model_calls': 0, 'store_requests': 0, 'payment_calls': 0,
    }
    report = {'version': 1, 'mode': 'offline_development_replay',
              'snapshot_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'evaluator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'elapsed_seconds': round(time.perf_counter() - started, 4),
              'summary': summary, 'families': dict(families), 'results': rows,
              'limitations': ['Assistant annotations, not independent human ground truth.',
                              'Purposive development cases, no heldout generalization estimate.',
                              'Additional explicit blocks are not additional prevented payments: baseline abstained.',
                              'No complete approved quote in this batch; full safe/unsafe payment rates unavailable.',
                              'Unknown/clarification categories are not counted as successful purchases.']}
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cases', type=Path, default=Path(__file__).with_name('reviewed-cases.json'))
    parser.add_argument('--out', type=Path, default=Path(__file__).with_name('evaluation-results.json'))
    parser.add_argument('--verify-source', type=Path)
    parser.add_argument('--workspace', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    roots = {'corpus': args.verify_source, 'workspace': args.workspace} if args.verify_source else None
    print(json.dumps(run(args.cases, args.out, roots)['summary'], indent=2))
