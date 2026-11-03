# Evaluation after independent review

Reproduce with `python evaluate_release.py`. Expected labels are read from separately authored `independent-labels.json`, never generated from candidate/requirement comparisons.

Eight controlled complete-quote inputs: four matching candidates allowed; two explicit conflicts blocked; two missing-evidence cases paused. Policy outcomes agree with all eight independent-agent labels. Budget-only permits all eight. Missing evidence is reported separately from known mismatches and is not counted as proven harm prevented.

The reviewer is an independent agent, not a human. It had seen prior outputs for the original four inputs, so those are non-blind source reviews. The four newly constructed delivery variants were labeled before their new policy outputs. All are controlled inputs based on two existing synthetic shopping tasks, not a held-out corpus or population error-rate measurement. Historical-summary labels are excluded from this public release; all eight published controlled labels point to shipped fixture data.

Delivery means an explicit test-merchant commitment within fourteen days of the same order-date anchor: 7/14 qualify, 15 conflicts, unknown pauses. These are fictional catalog promises, not measured real fulfillment. Deadline checks now use an inclusive upper bound. Relative-day fixtures do not demonstrate calendar/timezone extraction.

The prior evaluator freeze and old controlled results remain historical snapshots. The corrected evaluator has a new hash; the post-fix source/label snapshot is saved under review-fix-resume/snapshot.json. No claim of an untouched policy holdout is made.
