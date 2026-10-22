"""Experimental vLLM raw-logit export validation, isolated from the reference runner.

No vLLM engine is launched. An installed, pinned GPU build must expose a complete
pre-processor next-token raw_logits vector before it can be compared. Sampled
tokens, processed scores and truncated top-k exports are never valid substitutes.
"""
import math
from .local import probabilities


def validate_raw_export(export,prompt,revision,tokenizer_revision):
    import torch
    if export.get('backend')!='vllm' or export.get('mode')!='raw_logits':raise ValueError('Unprocessed vLLM raw logits required')
    if export.get('revision')!=revision or export.get('tokenizer_revision')!=tokenizer_revision:raise ValueError('Revision mismatch')
    if export.get('input_ids')!=prompt['input_ids'] or export.get('label_ids')!=prompt['label_ids']:raise ValueError('Token identity mismatch')
    if export.get('temperature')!=1 or export.get('top_p')!=1:raise ValueError('Wrong probability definition')
    for key in ['vllm_version','hardware','tensor_parallel_size','attention','batch_invariance','cache']:
        if key not in export.get('runtime',{}):raise ValueError('Missing vLLM execution provenance: '+key)
    logits=export.get('logits')
    if not isinstance(logits,list) or len(logits)!=export.get('vocab_size') or not logits:raise ValueError('Full vocabulary required, not truncated top-k')
    if any(isinstance(z,bool) or not isinstance(z,(int,float)) or not math.isfinite(z) for z in logits):raise ValueError('Invalid raw logits')
    return probabilities(torch.tensor(logits,dtype=torch.float32),prompt['label_ids'])


def compare_probabilities(reference,optimized):
    if set(reference)!=set(optimized) or not reference:raise ValueError('Identical nonempty pair coverage required')
    rows=[]
    for key in sorted(reference):
        a,b=reference[key],optimized[key]
        if a['input_hash']!=b['input_hash']:raise ValueError('Different prompt tokens')
        p=abs(a['probabilities']['p1_conditional']-b['probabilities']['p1_conditional'])
        d=abs(a['probabilities']['log_odds']-b['probabilities']['log_odds'])
        rows.append({'id':key,'probability_difference':p,'log_odds_difference':d,'within_provisional_tolerance':p<=.001 and d<=.01})
    return {'pairs':rows,'passes':all(r['within_provisional_tolerance'] for r in rows),'warning':'Cross-backend compatibility check, not within-backend reproducibility or scientific approval'}
