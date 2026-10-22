"""Offline-only Transformers direct-forward reference. Never calls generate or hosted APIs."""
from __future__ import annotations
import hashlib,json,math,os,platform,random,re,sqlite3,time,uuid
from pathlib import Path
from .core import digest,distance_matrix

VERSION=1
PROCESS_ID=uuid.uuid4().hex
MODEL_70B='meta-llama/Llama-3.3-70B-Instruct'


def file_hash(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def immutable_json(path,obj):
    """Exclusive creation, never overwrite scientific records."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:
        json.dump(obj,f,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)
        f.write('\n');f.flush();os.fsync(f.fileno())


def snapshot_lock(model_path,model_id,revision,tokenizer_path=None,tokenizer_revision=None):
    """Hash downloaded artifacts; no network, unsafe pickle weights or remote code."""
    tokenizer_path=tokenizer_path or model_path;tokenizer_revision=tokenizer_revision or revision
    for rev in (revision,tokenizer_revision):
        if not re.fullmatch('[0-9a-f]{40}',rev):raise ValueError('Immutable 40-character commit revisions required')
    result={'model_id':model_id,'revision':revision,'tokenizer_revision':tokenizer_revision}
    for label,path,rev in [('model',model_path,revision),('tokenizer',tokenizer_path,tokenizer_revision)]:
        path=Path(path).absolute()
        if path.name!=rev:raise ValueError('Use a downloaded HF snapshots/<immutable SHA> directory')
        files={str(p.relative_to(path)):file_hash(p) for p in sorted(path.rglob('*')) if p.is_file()}
        if not files:raise ValueError('Empty snapshot')
        result[label]={'path':str(path),'files':files}
    if not any(n.endswith('.safetensors') for n in result['model']['files']):raise ValueError('Safe unquantized weight files required')
    cfg=json.loads((Path(model_path)/'config.json').read_text())
    if cfg.get('quantization_config'):raise ValueError('Quantized models are not the reference')
    return result


def verify_lock(lock):
    for label in ['model','tokenizer']:
        root=Path(lock[label]['path']);expected=lock[label]['files']
        current={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
        if current!=set(expected):raise ValueError('Snapshot file set changed')
        for name,h in expected.items():
            if file_hash(root/name)!=h:raise ValueError('Snapshot checksum mismatch: '+name)


def serialize_prompt(tokenizer,messages):
    if not tokenizer.chat_template:raise ValueError('Official tokenizer chat template required')
    text=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
    ids=tokenizer.apply_chat_template(messages,tokenize=True,add_generation_prompt=True)
    if not ids or ids!=tokenizer.encode(text,add_special_tokens=False):raise ValueError('Chat template tokenization mismatch')
    labels={}
    for label in ['0','1']:
        single=tokenizer.encode(label,add_special_tokens=False)
        extended=tokenizer.encode(text+label,add_special_tokens=False)
        if len(single)!=1 or extended!=ids+single or tokenizer.decode(single,skip_special_tokens=False)!=label:
            raise ValueError('Answer label is not an exact single-token continuation: '+label)
        labels[label]=single[0]
    if labels['0']==labels['1']:raise ValueError('Answer token collision')
    return {'messages':messages,'text':text,'input_ids':ids,'input_hash':digest(ids),'messages_hash':digest(messages),
            'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'label_ids':labels,'last_position':len(ids)-1}


def probabilities(logits,label_ids):
    """Full-vocabulary FP32 log normalization; conditional target from raw label difference."""
    import torch
    z=logits.detach().to(dtype=torch.float32)
    if z.ndim!=1 or not torch.isfinite(z).all():raise ValueError('Nonfinite or incorrectly shaped logits')
    ids=[label_ids['0'],label_ids['1']]
    if len(set(ids))!=2 or any(type(i) is not int or i<0 or i>=len(z) for i in ids):raise ValueError('Invalid candidate token IDs')
    logs=torch.log_softmax(z,dim=-1)
    a,b=[float(z[i].item()) for i in ids];d=b-a
    # Stable scalar sigmoid avoids exp overflow; no sampled answer is involved.
    p=1/(1+math.exp(-d)) if d>=0 else math.exp(d)/(1+math.exp(d))
    lp0,lp1=[float(logs[i].item()) for i in ids]
    return {'logit0':a,'logit1':b,'log_odds':d,'logp0':lp0,'logp1':lp1,
            'p0':math.exp(lp0),'p1':math.exp(lp1),'binary_mass':math.exp(lp0)+math.exp(lp1),
            'p1_conditional':p,'normalization':'full vocabulary torch.log_softmax FP32; T=1'}


class Checkpoint:
    """Single writer; durable atomic records; interrupted slots are retried, successes never replaced."""
    def __init__(self,path,spec):
        self.run_id=digest(spec);self.path=Path(path)/self.run_id;self.path.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path/'checkpoint.sqlite',isolation_level=None)
        self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS config (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS records (slot TEXT PRIMARY KEY, body TEXT NOT NULL, hash TEXT NOT NULL)')
        self.db.execute('INSERT OR IGNORE INTO config VALUES (?,?)',(self.run_id,json.dumps(spec,sort_keys=True)))
        saved=self.db.execute('SELECT id,body FROM config').fetchall()
        if len(saved)!=1 or saved[0][0]!=self.run_id or digest(json.loads(saved[0][1]))!=self.run_id:raise ValueError('Checkpoint configuration corrupted')
        self.records={}
        for slot,body,h in self.db.execute('SELECT slot,body,hash FROM records'):
            obj=json.loads(body)
            if digest(obj)!=h or obj['slot']!=slot:raise ValueError('Checkpoint record checksum failed')
            self.records[slot]=obj
    def put(self,slot,record):
        if slot in self.records:raise ValueError('Completed record is immutable')
        obj={**record,'slot':slot};body=json.dumps(obj,sort_keys=True,allow_nan=False)
        self.db.execute('INSERT INTO records VALUES (?,?,?)',(slot,body,digest(obj)));self.records[slot]=obj
    def close(self):self.db.close()


class Reference:
    def __init__(self,lock,config):
        import torch,transformers
        from transformers import AutoModelForCausalLM,AutoTokenizer
        self.torch=torch;self.config=config
        artifact_config=json.loads((Path(lock['model']['path'])/'config.json').read_text())
        if lock['model_id']==MODEL_70B and any(artifact_config.get(k)!=v for k,v in {'hidden_size':8192,'num_hidden_layers':80,'num_attention_heads':64,'num_key_value_heads':8,'vocab_size':128256}.items()):raise ValueError('Unexpected 70B architecture')
        if config['dtype'] not in ['bfloat16','float16']:raise ValueError('Reference requires BF16 or FP16, never quantization')
        if lock['model_id']==MODEL_70B and (not torch.cuda.is_available() or config['device']!='cuda'):
            raise ValueError('70B requires suitable CUDA hardware; no CPU/offload substitution')
        if config['device']=='cuda' and not torch.cuda.is_available():raise ValueError('CUDA unavailable')
        torch.manual_seed(config['seed']);torch.set_num_threads(config.get('cpu_threads',1))
        torch.use_deterministic_algorithms(True)
        if torch.cuda.is_available():
            torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False
            if os.environ.get('CUBLAS_WORKSPACE_CONFIG') not in [':4096:8',':16:8']:raise ValueError('Set CUBLAS_WORKSPACE_CONFIG=:4096:8 before launching Python')
        self.tokenizer=AutoTokenizer.from_pretrained(lock['tokenizer']['path'],local_files_only=True,trust_remote_code=False)
        self.tokenizer.padding_side='right'
        if self.tokenizer.pad_token_id is None:self.tokenizer.pad_token=self.tokenizer.eos_token
        dtype=getattr(torch,config['dtype']);start=time.perf_counter()
        max_memory={i:torch.cuda.get_device_properties(i).total_memory-config.get('gpu_headroom_gib',8)*1024**3 for i in range(torch.cuda.device_count())} if config['device']=='cuda' else None
        self.model=AutoModelForCausalLM.from_pretrained(lock['model']['path'],local_files_only=True,trust_remote_code=False,
            use_safetensors=True,torch_dtype=dtype,attn_implementation=config['attention'],
            device_map='auto' if config['device']=='cuda' else None,max_memory=max_memory)
        if config['device']=='cpu':self.model.to('cpu')
        if getattr(self.model.config,'quantization_config',None) or getattr(self.model,'is_quantized',False):raise ValueError('Quantization prohibited')
        if any(p.is_floating_point() and p.dtype!=dtype for p in self.model.parameters()):raise ValueError('Unexpected weight precision')
        if config['device']=='cuda' and any(p.device.type!='cuda' for p in self.model.parameters()):raise ValueError('Insufficient GPU memory: CPU/disk offload prohibited')
        self.model.eval();self.sync();self.loading_seconds=time.perf_counter()-start
        self.runtime={'python':platform.python_version(),'torch':torch.__version__,'transformers':transformers.__version__,
            'cuda':torch.version.cuda,'cudnn':torch.backends.cudnn.version(),'gpu':[{'name':torch.cuda.get_device_name(i),'total_memory':torch.cuda.get_device_properties(i).total_memory,'capability':list(torch.cuda.get_device_capability(i))} for i in range(torch.cuda.device_count())],
            'device_map':{k:str(v) for k,v in getattr(self.model,'hf_device_map',{}).items()},'tensor_parallel_size':1,
            'parallelism':'Transformers Accelerate device_map sequential layer sharding; NOT tensor parallel',
            'gpu_headroom_gib':config.get('gpu_headroom_gib',8),'attention':self.model.config._attn_implementation,'dtype':str(dtype),'platform':platform.platform(),
            'chat_template':self.tokenizer.chat_template,'pad_token_id':self.tokenizer.pad_token_id,
            'deterministic_algorithms':torch.are_deterministic_algorithms_enabled(),'tf32':False,
            'cublas_workspace_config':os.environ.get('CUBLAS_WORKSPACE_CONFIG'),
            'packages':{n:__import__('importlib.metadata',fromlist=['version']).version(n) for n in ['accelerate','tokenizers','safetensors','huggingface-hub']}}
    def sync(self):
        for i in range(self.torch.cuda.device_count()):self.torch.cuda.synchronize(i)
    def forward(self,prompts):
        t=self.torch;length=max(len(p['input_ids']) for p in prompts);device=self.model.get_input_embeddings().weight.device
        ids=t.full((len(prompts),length),self.tokenizer.pad_token_id,dtype=t.long,device=device);mask=t.zeros_like(ids)
        for j,p in enumerate(prompts):ids[j,:len(p['input_ids'])]=t.tensor(p['input_ids'],device=device);mask[j,:len(p['input_ids'])]=1
        position_ids=(mask.cumsum(-1)-1).clamp(min=0)
        self.sync()
        for i in range(t.cuda.device_count()):t.cuda.reset_peak_memory_stats(i)
        start=time.perf_counter()
        with t.inference_mode():
            # Prefill mode is baseline. Split mode actually reuses past_key_values.
            if self.config['cache']=='split':
                if len(prompts)!=1:raise ValueError('Split-cache comparison currently supports batch size one only')
                prefix=self.model(input_ids=ids[:,:-1],attention_mask=mask[:,:-1],position_ids=position_ids[:,:-1],use_cache=True)
                output=self.model(input_ids=ids[:,-1:],attention_mask=mask,position_ids=position_ids[:,-1:],past_key_values=prefix.past_key_values,use_cache=True)
                last=output.logits[:,0,:]
            else:
                output=self.model(input_ids=ids,attention_mask=mask,position_ids=position_ids,use_cache=self.config['cache']=='prefill')
                last=output.logits[t.arange(len(prompts),device=output.logits.device),t.tensor([len(p['input_ids'])-1 for p in prompts],device=output.logits.device),:]
            results=[probabilities(last[j],p['label_ids']) for j,p in enumerate(prompts)]
        self.sync();seconds=time.perf_counter()-start
        return results,{'forward_seconds':seconds,'input_tokens':sum(len(p['input_ids']) for p in prompts),'padded_tokens':ids.numel(),
            'tokens_per_second':sum(len(p['input_ids']) for p in prompts)/seconds,
            'gpu_peak_allocated':[t.cuda.max_memory_allocated(i) for i in range(t.cuda.device_count())],
            'gpu_peak_reserved':[t.cuda.max_memory_reserved(i) for i in range(t.cuda.device_count())]}


def execute(lock,items,config,output,session_label='process-1',limit=None):
    """New process session labels create intentional repeats, ordinary resume skips valid slots."""
    import fcntl
    start=time.perf_counter();verify_lock(lock)
    # Exclusive process lock prevents simultaneous models/writers in this output root.
    if session_label not in config['planned_sessions']:raise ValueError('Unplanned process session')
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    with (root/'.writer.lock').open('a') as guard:
        fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ref=Reference(lock,config);prompts={i['id']:serialize_prompt(ref.tokenizer,i['messages']) for i in items}
        if len(prompts)!=len(items):raise ValueError('Duplicate input IDs')
        spec={'backend':'transformers-direct-v1','lock':lock,'config':config,'runtime':ref.runtime,'inputs':items,
              'prompt_hashes':{k:digest(p) for k,p in prompts.items()},'implementation_hash':file_hash(__file__)}
        cp=Checkpoint(root,spec)
        try:
            for k,p in prompts.items():
                path=cp.path/'prompts'/(digest(k)+'.json')
                if path.exists():
                    if json.loads(path.read_text())!=p:raise ValueError('Prompt archive corrupted')
                else:immutable_json(path,p)
            # Validate every resumed slot against its exact original input and numeric invariants.
            for r in cp.records.values():
                if r['prompt_digest']!=digest(prompts[r['item_id']]):raise ValueError('Checkpoint prompt mismatch')
                p=r['probabilities'];d=p['logit1']-p['logit0']
                if not math.isclose(d,p['log_odds'],abs_tol=1e-12) or not 0<=p['p1_conditional']<=1:raise ValueError('Invalid checkpoint probability')
            process_id=PROCESS_ID;invocation_id=uuid.uuid4().hex;session={'label':session_label,'process_id':process_id,'pid':os.getpid(),'loading_seconds':ref.loading_seconds,'runtime':ref.runtime}
            immutable_json(cp.path/'processes'/(invocation_id+'.json'),session)
            performed=0;keys=list(prompts)
            for repeat in range(config['repeats']):
                order=keys.copy()
                if config['batch_size']>1:random.Random(config['seed']+repeat).shuffle(order)
                for offset in range(0,len(order),config['batch_size']):
                    batch=order[offset:offset+config['batch_size']];slots={k:digest([session_label,repeat,k]) for k in batch}
                    if all(s in cp.records for s in slots.values()):continue
                    # If interrupted mid-batch, run remaining cells only; record changed composition.
                    pending=[k for k in batch if slots[k] not in cp.records]
                    if limit is not None and performed+len(pending)>limit:continue
                    ps,metrics=ref.forward([prompts[k] for k in pending])
                    for k,p in zip(pending,ps):
                        cp.put(slots[k],{'item_id':k,'repeat':repeat,'session_label':session_label,'process_id':process_id,
                            'prompt_digest':digest(prompts[k]),'input_hash':prompts[k]['input_hash'],'batch_members':pending,
                            'probabilities':p,'metrics':metrics})
                    performed+=len(pending)
            result={'run_id':cp.run_id,'run_directory':str(cp.path),'performed':performed,'records_total':len(cp.records),
                'expected_per_session':len(items)*config['repeats'],'missing_this_session':len(items)*config['repeats']-sum(r['session_label']==session_label for r in cp.records.values()),
                'loading_seconds':ref.loading_seconds,'total_seconds':time.perf_counter()-start}
            immutable_json(cp.path/'processes'/(invocation_id+'-summary.json'),result)
            return result
        finally:cp.close()


def analyze_run(directory):
    path=Path(directory);db=sqlite3.connect(path/'checkpoint.sqlite');spec=json.loads(db.execute('SELECT body FROM config').fetchone()[0]);db.close()
    if path.name!=digest(spec):raise ValueError('Run directory/configuration mismatch')
    cp=Checkpoint(path.parent,spec)
    try:
        groups={};sessions={}
        for r in cp.records.values():
            groups.setdefault(r['item_id'],[]).append(r)
            sessions.setdefault(r['session_label'],{}).setdefault(r['repeat'],{})[r['item_id']]=r['probabilities']['p1_conditional']
        checks=[]
        for k in [i['id'] for i in spec['inputs']]:
            rs=groups.get(k,[]);ps=[r['probabilities']['p1_conditional'] for r in rs];ls=[r['probabilities']['log_odds'] for r in rs]
            checks.append({'id':k,'n':len(rs),'probability_range':max(ps)-min(ps) if ps else None,'log_odds_range':max(ls)-min(ls) if ls else None,
                'passes':len(rs)>=2 and max(ps)-min(ps)<=.001 and max(ls)-min(ls)<=.01})
        expected_ids={i['id'] for i in spec['inputs']};expected_sessions=set(spec['config']['planned_sessions']);missing=[]
        for s in expected_sessions:
            for r in range(spec['config']['repeats']):
                for k in expected_ids-set(sessions.get(s,{}).get(r,{})):missing.append([s,r,k])
        block_matrices=[]
        items=spec['inputs'];cs=sorted({i['constitution_id'] for i in items if 'constitution_id' in i});ss=sorted({i['scenario_id'] for i in items if 'scenario_id' in i})
        is_block=len(cs)==24 and len(ss)==20 and len(items)==480
        if is_block:
            for s,blocks in sessions.items():
                for repeat,values in blocks.items():
                    if set(values)==expected_ids:
                        table={(i['constitution_id'],i['scenario_id']):values[i['id']] for i in items};summed=distance_matrix([[table[c,d] for d in ss] for c in cs]);block_matrices.append({'session':s,'repeat':repeat,'constitutions':cs,'scenarios':ss,'summed_l1':summed,'normalized_l1':[[v/len(ss) for v in row] for row in summed]})
        change=None
        if len(block_matrices)>1:
            change=max(abs(a['normalized_l1'][i][j]-b['normalized_l1'][i][j]) for a in block_matrices for b in block_matrices for i in range(24) for j in range(24))
        return {'run_id':cp.run_id,'provisional_thresholds':{'probability_range':.001,'log_odds_range':.01,'normalized_distance_change':.005},
            'pair_checks':checks,'missing_observed_sessions':missing,'observed_sessions':sorted(sessions),'cross_process_evidence':len({r['process_id'] for r in cp.records.values()})>1,
            'pair_gate_passes':all(c['passes'] for c in checks) and not missing and len({r['process_id'] for r in cp.records.values()})>=len(expected_sessions),
            'block_matrices':block_matrices,'maximum_normalized_distance_change':change,'block_gate_passes':change is not None and change<=.005 and not missing,
            'warning':'Software thresholds only; no automatic scientific approval. No evidence about sessions not yet launched.'}
    finally:cp.close()
