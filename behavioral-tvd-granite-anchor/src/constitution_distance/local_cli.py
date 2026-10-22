"""Explicit local-only validation commands; no full-experiment launcher."""
import argparse,json
from pathlib import Path
from .local import MODEL_70B,snapshot_lock,immutable_json,execute,analyze_run


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    lock=sub.add_parser('lock');lock.add_argument('--snapshot',required=True);lock.add_argument('--model-id',required=True);lock.add_argument('--revision',required=True);lock.add_argument('--tokenizer-snapshot');lock.add_argument('--tokenizer-revision');lock.add_argument('--out',required=True)
    run=sub.add_parser('benchmark');run.add_argument('--lock',required=True);run.add_argument('--inputs',required=True);run.add_argument('--output',required=True)
    run.add_argument('--dtype',choices=['bfloat16','float16'],default='bfloat16');run.add_argument('--device',choices=['cuda','cpu'],default='cuda')
    run.add_argument('--attention',choices=['eager','sdpa'],default='eager');run.add_argument('--cache',choices=['off','prefill','split'],default='off')
    run.add_argument('--gpu-headroom-gib',type=int,default=8)
    run.add_argument('--batch-size',type=int,default=1);run.add_argument('--repeats',type=int,default=30);run.add_argument('--seed',type=int,default=20261020)
    run.add_argument('--session',default='restart-1');run.add_argument('--planned-sessions',nargs='+',default=['restart-1','restart-2'])
    run.add_argument('--dry-run',action='store_true');run.add_argument('--limit',type=int);run.add_argument('--software-test',action='store_true')
    comparison=sub.add_parser('compare');comparison.add_argument('--reference',required=True);comparison.add_argument('--candidate',required=True);comparison.add_argument('--out',required=True)
    analysis=sub.add_parser('analyze');analysis.add_argument('--run',required=True);analysis.add_argument('--out',required=True)
    a=p.parse_args()
    if a.command=='compare':
        from .local_comparison import compare_runs
        obj=compare_runs(a.reference,a.candidate);immutable_json(a.out,obj);print(json.dumps(obj,indent=2))
    elif a.command=='lock':
        obj=snapshot_lock(a.snapshot,a.model_id,a.revision,a.tokenizer_snapshot,a.tokenizer_revision);immutable_json(a.out,obj);print('Wrote immutable snapshot lock:',a.out)
    elif a.command=='analyze':
        obj=analyze_run(a.run);immutable_json(a.out,obj);print(json.dumps({k:v for k,v in obj.items() if k not in ['pair_checks','block_matrices']},indent=2))
    else:
        lock=json.loads(Path(a.lock).read_text());items=json.loads(Path(a.inputs).read_text())['items']
        if a.gpu_headroom_gib<0 or a.repeats<1 or a.batch_size<1 or len(items)<1 or a.session not in a.planned_sessions or len(set(a.planned_sessions))!=len(a.planned_sessions):raise ValueError('Invalid schedule')
        if a.cache=='split' and a.batch_size!=1:raise ValueError('Split-cache condition requires batch size one')
        if len(items)>480:raise ValueError('Validation CLI cannot launch the full constitutional experiment')
        if lock['model_id']!=MODEL_70B and not a.software_test:raise ValueError('Small models require --software-test; not a 70B reliability result')
        config={'dtype':a.dtype,'device':a.device,'attention':a.attention,'cache':a.cache,'batch_size':a.batch_size,'repeats':a.repeats,'seed':a.seed,'cpu_threads':1,'gpu_headroom_gib':a.gpu_headroom_gib,'planned_sessions':a.planned_sessions,'software_test':a.software_test}
        if a.dry_run:
            print(json.dumps({'status':'dry-run; no model loading or inference','items':len(items),'evaluations_per_session':len(items)*a.repeats,'planned_sessions':a.planned_sessions,'total_planned_evaluations':len(items)*a.repeats*len(a.planned_sessions),'configuration':config},indent=2));return
        print(json.dumps(execute(lock,items,config,a.output,a.session,a.limit),indent=2))

if __name__=='__main__':main()
