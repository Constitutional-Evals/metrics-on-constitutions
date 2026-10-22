"""Budgeted, provider-pinned runner. SQLite is authoritative; CSV/JSON are exports."""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import csv
from decimal import Decimal
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import random
import time

from .api import API, APIError
from .core import PROMPT_VERSION, digest, distance_matrix, extract_probabilities, load_constitutions, load_scenarios, messages
from .storage import BudgetError, Ledger, dollars, money, now


class IdentityError(ValueError):
    pass


def write_json(path, obj):
    path = Path(path)
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('w') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n'); f.flush(); os.fsync(f.fileno())
    temp.replace(path)


def payload(args, constitution, scenario):
    return {"model": args.model, "messages": messages(constitution, scenario),
            "temperature": 1, "top_p": 1, "max_tokens": 1,
            "logprobs": True, "top_logprobs": args.top_logprobs,
            "provider": {"only": [args.provider], "allow_fallbacks": False,
                         "require_parameters": True,
                         "max_price": {"prompt": args.input_price, "completion": args.output_price}}}


def metadata(api, args):
    model = next((m for m in api.request('/models')['data'] if m['id'] == args.model), None)
    endpoints = api.request('/models/' + args.model + '/endpoints')['data']
    endpoint = next((e for e in endpoints['endpoints'] if e.get('tag') == args.provider), None)
    if not model or not endpoint:
        raise ValueError("Exact requested model/provider endpoint not available")
    required = {'logprobs', 'top_logprobs', 'temperature', 'top_p', 'max_tokens'}
    if not required <= set(endpoint.get('supported_parameters', [])):
        raise ValueError("Pinned endpoint does not advertise all required parameters")
    for key, ceiling in [('prompt', args.input_price), ('completion', args.output_price)]:
        if Decimal(endpoint['pricing'][key]) * 1_000_000 > Decimal(str(ceiling)):
            raise BudgetError("Advertised endpoint pricing exceeds configured price ceiling")
    context = endpoint.get('context_length')
    if not isinstance(context, int) or context < 1:
        raise ValueError("Pinned endpoint has no valid context limit for cost reservation")
    return {'model': model, 'endpoint': endpoint, 'observed_at': now()}


def reservation(meta, args):
    # Reserve the entire advertised context, not a tokenizer estimate. This includes
    # all input template tokens and ignores any cache discount, with 10% headroom.
    amount = (Decimal(meta['endpoint']['context_length']) * Decimal(str(args.input_price))
              + Decimal(str(args.output_price))) / 1_000_000 * Decimal('1.10')
    return money(amount)


def validate_response(response, args, meta):
    if response.get('model') != args.model:
        raise IdentityError("Returned model differs from requested model")
    if response.get('provider') != meta['endpoint']['provider_name']:
        raise IdentityError("Returned provider differs from pinned provider")
    probabilities = extract_probabilities(response)
    usage = response.get('usage', {})
    for key in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
        if type(usage.get(key)) is not int or usage[key] < 0:
            raise ValueError("Missing or invalid token usage")
    if usage['completion_tokens'] != 1 or usage['prompt_tokens'] < 1:
        raise ValueError("Expected exactly one billed output token")
    if usage['prompt_tokens'] > meta['endpoint']['context_length']:
        raise ValueError("Billed prompt exceeds advertised context limit")
    if usage['total_tokens'] != usage['prompt_tokens'] + usage['completion_tokens']:
        raise ValueError("Inconsistent total token usage")
    if not isinstance(usage.get('cost'), (int, float)) or isinstance(usage.get('cost'), bool):
        raise ValueError("Missing actual cost; cannot settle this request as valid")
    money(usage['cost'])
    return probabilities


def scenario_approval(path, dry_run=False):
    """A candidate with an approval sidecar cannot accidentally become a live run."""
    path=Path(path);sidecar=path.with_suffix('.manifest.json')
    if not sidecar.exists():return None
    approval=json.loads(sidecar.read_text())
    if approval.get('execution_approved') is not True:
        if not dry_run:
            raise ValueError('Scenario set is preliminary and not execution-approved; review its manifest first')
    elif approval.get('approved_file_sha256')!=hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError('Approved scenario-file hash mismatch')
    return {'manifest_sha256':hashlib.sha256(sidecar.read_bytes()).hexdigest(),
            'execution_approved':approval.get('execution_approved') is True}


def run(args):
    if args.concurrency < 1 or args.attempts < 1 or args.top_logprobs < 2 or args.replicates < 1:
        raise ValueError("Concurrency, attempts, replicates must be positive; top-logprobs >= 2")
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be positive")
    if args.max_requests is not None and args.max_requests < 1:
        raise ValueError("--max-requests must be positive")
    money(args.budget_usd); money(args.input_price); money(args.output_price)
    cs = load_constitutions(args.constitutions)
    if args.constitution_ids:
        if len(set(args.constitution_ids)) != len(args.constitution_ids) or set(args.constitution_ids) - {c['id'] for c in cs}:
            raise ValueError("Constitution IDs must be unique known anchors")
        cs = [c for c in cs if c['id'] in args.constitution_ids]
    approval=scenario_approval(args.scenarios,args.dry_run)
    ss = load_scenarios(args.scenarios)
    if args.limit:
        ss = ss[:args.limit]
    # Check the actual serialized messages, roles and order, not just the template.
    for s in ss:
        base = messages(cs[0], s)
        for c in cs:
            actual = payload(args, c, s)['messages']
            if [m['role'] for m in actual] != ['system', 'user'] or actual[1] != base[1]:
                raise ValueError("Scenario messages/ordering changed across constitutions")
            if actual[0]['content'].split('\n\nCONSTITUTION:\n')[0] != base[0]['content'].split('\n\nCONSTITUTION:\n')[0]:
                raise ValueError("System instructions differ outside constitution content")
    settings = {k: v for k, v in payload(args, cs[0], ss[0]).items() if k != 'messages'}
    spec = {'prompt_version': PROMPT_VERSION, 'constitution_order': [c['id'] for c in cs],
            'constitutions': cs, 'scenarios': ss, 'settings': settings,
            'system_template_sha256': digest(messages(cs[0], ss[0])[0]['content'].split('\n\nCONSTITUTION:\n')[0]),
            'scenario_prompt_hashes': {s['id']: digest(messages(cs[0], s)[1]) for s in ss},
            'metric': args.metric, 'replicates': args.replicates,
            'phase': args.phase, 'extraction_version': 2}
    if approval is not None:spec['scenario_approval']=approval
    run_id = digest(spec)
    pairs = [(c['id'], s['id'], r) for c in cs for s in ss for r in range(args.replicates)]
    print(f"{len(cs)} constitutions x {len(ss)} dilemmas x {args.replicates} replicates = {len(pairs)} evaluations; run {run_id}", flush=True)
    if args.dry_run:
        print('Dry run: no API requests or files created.'); return
    out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    with (out / '.run.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Run already locked by another process") from None
        manifest = out / 'manifest.json'
        if manifest.exists():
            saved = json.loads(manifest.read_text())
            if saved['run_id'] != run_id:
                raise ValueError("Output directory belongs to a different experiment")
            if saved['ledger'] != str(Path(args.ledger).resolve()) or not Path(args.ledger).exists():
                raise ValueError("Resume requires the original authoritative ledger; refusing to recompute exported results")
        ledger = Ledger(args.ledger, args.budget_usd)
        try:
            key = os.environ.get('OPENROUTER_API_KEY')
            api = API('https://openrouter.ai/api/v1', key, attempts=1)
            old = ledger.db.execute('SELECT metadata FROM runs WHERE id=?', (run_id,)).fetchone()
            if manifest.exists() and old is None:
                raise ValueError("Manifest run is absent from authoritative ledger; refusing to recompute")
            meta = json.loads(old[0]) if old else None
            states = ledger.states(run_id)
            todo = [p for p in pairs if p not in states or states[p]['state'] == 'pending'
                    or (args.retry_missing and states[p]['state'] in {'invalid', 'error', 'retry'})]
            if todo and args.budget_usd == 0:
                # No paid or metadata requests when the caller has authorized no spending.
                raise BudgetError("Budget defaults to zero; explicitly set --budget-usd to authorize inference")
            if todo and not key:
                raise ValueError("Configure OPENROUTER_API_KEY securely")
            if todo:
                current_meta = metadata(api, args)
                # A resumed run retains its original metadata; record every new observation.
                write_json(out / 'endpoint-latest.json', current_meta)
                if meta is None:
                    meta = current_meta
            if meta is None:
                raise ValueError("No metadata available for this run")
            ledger.register(run_id, spec, meta, pairs)
            if not manifest.exists():
                write_json(manifest, {'run_id': run_id, 'spec': spec, 'metadata': meta,
                                     'created_at': now(), 'ledger': str(Path(args.ledger).resolve())})
            write_json(out / 'message-audit.json', {
                'checked_pairs': len(cs)*len(ss), 'roles': ['system', 'user'],
                'user_messages_identical_across_constitutions': True,
                'only_constitution_content_varies_in_system_message': True,
                'prompt_version': PROMPT_VERSION})
            # Never trust a corrupt checkpoint just because its state says valid.
            for pair, row in ledger.states(run_id).items():
                if row['state'] == 'valid':
                    record = json.loads(row['record'])
                    c = next(c for c in cs if c['id'] == pair[0]); s = next(s for s in ss if s['id'] == pair[1])
                    expected = payload(args, c, s)
                    if (record['request'] != expected or record['prompt_hash'] != digest(expected['messages'])
                            or record['request_hash'] != digest(expected)
                            or record['probabilities'] != validate_response(record['response'], args, record['metadata'])):
                        raise ValueError("Stored valid checkpoint failed integrity validation")
            reserve = reservation(current_meta, args) if todo else 0
            cs_by = {c['id']: c for c in cs}; ss_by = {s['id']: s for s in ss}

            def query(pair):
                request = payload(args, cs_by[pair[0]], ss_by[pair[1]])
                for attempt in range(args.attempts):
                    aid = ledger.claim(run_id, pair, request, reserve,
                                       retry_missing=args.retry_missing or attempt > 0,
                                       max_requests=args.max_requests)
                    if aid is None:
                        return
                    try:
                        response = api.request('/chat/completions', request)
                    except APIError as exc:
                        retry = exc.retryable and attempt + 1 < args.attempts
                        ledger.settle(aid, 'retry' if retry else 'error', error=str(exc), http_status=exc.status)
                        if not retry:
                            return
                        time.sleep(max(exc.retry_after, min(30, 2 ** attempt) + random.random()))
                        continue
                    except (ValueError, TypeError, KeyError, OSError) as exc:
                        ledger.settle(aid, 'invalid', error='Malformed response or transport error: ' + type(exc).__name__)
                        return
                    try:
                        probabilities = validate_response(response, args, current_meta)
                    except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError) as exc:
                        ledger.settle(aid, 'invalid', response=response, error='Invalid response: ' + str(exc),
                                      http_status=response.get('_http_status') if isinstance(response, dict) else None)
                        if isinstance(exc, IdentityError):
                            raise RuntimeError("Returned model/provider identity mismatch; stopping dispatch") from None
                        return
                    record = {'run_id': run_id, 'constitution_id': pair[0], 'scenario_id': pair[1],
                              'replica': pair[2], 'attempt_id': aid, 'completed_at': now(),
                              'request': request, 'request_hash': digest(request),
                              'prompt_hash': digest(request['messages']), 'metadata': current_meta,
                              'probabilities': probabilities, 'response': response}
                    ledger.settle(aid, 'valid', record, response, http_status=response.get('_http_status'))
                    return

            failure = None
            try:
                # First pending request is the live capability gate. It is part of the grid.
                if todo:
                    gate = todo.pop(0)
                    query(gate)
                    if ledger.states(run_id)[gate]['state'] != 'valid':
                        raise ValueError("Capability gate failed; no batch dispatched (see missing.json)")
                with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
                    items = iter(todo); futures = set()
                    def submit():
                        item = next(items, None)
                        if item is not None:
                            futures.add(pool.submit(query, item))
                    for _ in range(args.concurrency): submit()
                    while futures:
                        done, futures = wait(futures, return_when=FIRST_COMPLETED)
                        for future in done:
                            try: future.result()
                            except Exception as exc:
                                failure = failure or exc
                        if failure is None:
                            for _ in done: submit()
                        count = sum(r['state'] == 'valid' for r in ledger.states(run_id).values())
                        if count % 24 == 0 or not futures:
                            print(f"Valid {count}/{len(pairs)}; ledger {ledger.totals()}", flush=True)
                if failure: raise failure
                if any(r['state'] != 'valid' for r in ledger.states(run_id).values()):
                    raise ValueError("Run incomplete; inspect missing.json; failed responses are not automatically retried")
            finally:
                export(out, ledger, run_id, cs, ss, args)
        finally:
            ledger.close()


def export(out, ledger, run_id, cs, ss, args):
    states = ledger.states(run_id)
    records = {p: json.loads(r['record']) for p, r in states.items() if r['state'] == 'valid'}
    missing = [{'constitution_id': p[0], 'scenario_id': p[1], 'replica': p[2], 'state': r['state']}
               for p, r in states.items() if r['state'] != 'valid']
    write_json(out / 'missing.json', missing)
    # Exports can always be rebuilt from SQLite, including after an interrupted export.
    temp = out / 'responses.jsonl.tmp'
    with temp.open('w') as f:
        for p in sorted(records): f.write(json.dumps(records[p], ensure_ascii=False) + '\n')
        f.flush(); os.fsync(f.fileno())
    temp.replace(out / 'responses.jsonl')
    write_json(out / 'attempts.json', ledger.attempts(run_id))
    ids = [c['id'] for c in cs]
    vectors = [[records[(c, s['id'], 0)]['probabilities'][args.metric] if (c,s['id'],0) in records else None
                for s in ss] for c in ids]
    with (out / 'vectors.csv').open('w', newline='') as f:
        w = csv.writer(f,lineterminator="\n"); w.writerow(['constitution_id'] + [s['id'] for s in ss])
        w.writerows([[c] + row for c, row in zip(ids, vectors)])
    complete = all(all(p is not None for p in v) for v in vectors)
    # Incomplete rows have unknown distances to other rows. Never sum just the
    # shared observed cells: that would understate the requested 20-item L1.
    matrix = [[0.0 if i == j else
               math.fsum(abs(a-b) for a,b in zip(x,y))
               if all(p is not None for p in x+y) else None
               for j,y in enumerate(vectors)] for i,x in enumerate(vectors)]
    for name, divisor in [('distances_l1.csv', 1), ('distances_mean_l1.csv', len(ss))]:
        with (out / name).open('w', newline='') as f:
            w=csv.writer(f,lineterminator="\n"); w.writerow(['constitution_id']+ids)
            w.writerows([[c]+[p/divisor if p is not None else None for p in row] for c,row in zip(ids,matrix)])
    usage = [r['response']['usage'] for r in records.values()]
    probabilities=[r['probabilities'] for r in records.values()]
    qc={'all_primary_probabilities_in_range':all(0<=p[args.metric]<=1 for p in probabilities),
        'all_binary_mass_at_least_0_95':all(p['binary_mass']>=.95 for p in probabilities),
        'minimum_binary_mass':min((p['binary_mass'] for p in probabilities),default=None),
        'distances_symmetric_including_missing_mask':all(matrix[i][j]==matrix[j][i] for i in range(len(cs)) for j in range(len(cs))),
        'zero_diagonal':all(matrix[i][i]==0 for i in range(len(cs))),
        'nonnegative_known_distances':all(v>=0 for row in matrix for v in row if v is not None)}
    write_json(out / 'summary.json', {'run_id': run_id, 'metric': args.metric, 'exported_at': now(),
        'constitutions': len(cs), 'scenarios': len(ss), 'replicates': args.replicates,
        'responses': len(records), 'missing': len(missing), 'complete_matrix': complete,
        'valid_response_cost_usd': math.fsum(u['cost'] for u in usage),
        'prompt_tokens': sum(u['prompt_tokens'] for u in usage),
        'completion_tokens': sum(u['completion_tokens'] for u in usage), 'ledger': ledger.totals(),
        'quality_control':qc,'data_quality_complete':complete and not missing and all(v for k,v in qc.items() if k!='minimum_binary_mass')})


def export_existing(args):
    """Rebuild exports offline even when pending work has no spending authorization."""
    out = Path(args.output)
    with (out / '.run.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Run is active; refusing an inconsistent concurrent export") from None
        _export_existing(args)


def _export_existing(args):
    from argparse import Namespace
    out = Path(args.output)
    saved = json.loads((out / 'manifest.json').read_text())
    if not Path(saved['ledger']).exists():
        raise ValueError("Original authoritative ledger is missing")
    spec = saved['spec']; settings = spec['settings']
    check_args = Namespace(model=settings['model'], metric=spec['metric'], replicates=spec['replicates'])
    ledger = Ledger(saved['ledger'], 0)
    try:
        old = ledger.db.execute('SELECT spec FROM runs WHERE id=?', (saved['run_id'],)).fetchone()
        if old is None or json.loads(old[0]) != spec:
            raise ValueError("Manifest and authoritative ledger differ")
        for row in ledger.states(saved['run_id']).values():
            if row['state'] == 'valid':
                r = json.loads(row['record'])
                if r['request_hash'] != digest(r['request']) or r['prompt_hash'] != digest(r['request']['messages']):
                    raise ValueError("Checkpoint request hash mismatch")
                if r['probabilities'] != validate_response(r['response'], check_args, r['metadata']):
                    raise ValueError("Checkpoint probability integrity mismatch")
        export(out, ledger, saved['run_id'], spec['constitutions'], spec['scenarios'], check_args)
    finally:
        ledger.close()
