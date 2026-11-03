"""Single-process adapter: stop after shopper report, never invoke a panelist."""
import types
import re


def report_status(driver_status, report):
    if driver_status != 'ok':
        return driver_status
    markers = set(re.findall(r'^\s*(?:#{1,6}\s*)?(?:\*\*|__|`)?(DONE|NEEDS_APPROVAL|CANNOT_COMPLETE)(?:\*\*|__|`)?(?=\s|[.:\u2014\u2013-]|$)', report, re.MULTILINE))
    if len(markers) != 1:
        return 'unrecognized_report'
    return {'DONE': 'done', 'NEEDS_APPROVAL': 'needs_human', 'CANNOT_COMPLETE': 'cannot_complete'}[markers.pop()]


def stop_at_report(runner, task_prompt, principal, report, turns, time_left, *, t=0):
    turns.append({'agent': report, 'panelist': {'key': 'end', 'text': 'END',
                  'reason': 'Human handoff; simulated panelist disabled'}, 't': t})
    return None


def single_turn(run_function):
    # Copy only this function's globals: no mutation of the shared driver module.
    if 'answer' not in run_function.__code__.co_names:
        raise RuntimeError('Driver panelist boundary changed; review adapter before running')
    adapted = types.FunctionType(run_function.__code__, {**run_function.__globals__, 'answer': stop_at_report},
                                 run_function.__name__, run_function.__defaults__, run_function.__closure__)
    adapted.__kwdefaults__ = dict(run_function.__kwdefaults__ or {})
    return adapted
