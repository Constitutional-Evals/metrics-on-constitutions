"""Isolated OpenRouter model/provider validation under a shared fixed $1 cap."""
import argparse,copy,json,math,random
from decimal import Decimal
from pathlib import Path
from constitution_distance.core import digest
from constitution_distance.runner import write_json
from constitution_distance.studies import run_study

BASE=Path('/workspace/work/cloud-api-selection')
CANDIDATES={
 'mistral31-cloudflare':('mistralai/mistral-small-3.1-24b-instruct','cloudflare'),
 'nemo12-ionet':('mistralai/mistral-nemo','io-net/fp16'),
 'llama3-cloudflare':('meta-llama/llama-3.2-3b-instruct','cloudflare'),
 'llama8-core':('meta-llama/llama-3.1-8b-instruct','coreweave/bf16'),
 'llama8-novita':('meta-llama/llama-3.1-8b-instruct','novita/fp8'),
 'qwen30-deka':('qwen/qwen3-30b-a3b-instruct-2507','dekallm'),
 'mistral24-parasail':('mistralai/mistral-small-3.2-24b-instruct','parasail/bf16'),
 'gemma27-nextbit':('google/gemma-3-27b-it','nextbit/fp8'),
 'granite8-core':('ibm-granite/granite-4.2-8b','coreweave/bf16'),
 'granite3-cloudflare':('ibm-granite/granite-4.0-h-micro','cloudflare'),
 'qwen80-google':('qwen/qwen3-next-80b-a3b-instruct','google-vertex/global'),
 'qwen80-parasail':('qwen/qwen3-next-80b-a3b-instruct','parasail/fp8')}

def extract(response):
 choices=response.get('choices')
 if not choices or len(choices)!=1:raise ValueError('One completion choice required')
 c=choices[0];entries=(c.get('logprobs') or {}).get('content')
 if not entries or len(entries)!=1:raise ValueError('Exactly one next-token logprob record required')
 item=entries[0];logs={}
 if item.get('token')!=c.get('message',{}).get('content'):raise ValueError('Sampled token/content mismatch')
 for e in [item]+list(item.get('top_logprobs') or []):
  token=e.get('token')
  if token not in ['0','1']:continue
  lp=e.get('logprob')
  if type(lp) not in [int,float] or not math.isfinite(lp) or lp>0 or lp<=-999:raise ValueError('Missing/nonfinite label log probability')
  if e.get('bytes') not in [None,[ord(token)]]:raise ValueError('Wrong label token bytes')
  if token in logs and not math.isclose(lp,logs[token],abs_tol=1e-6):raise ValueError('Conflicting label logprobs')
  logs[token]=lp
 if set(logs)!={'0','1'}:raise ValueError('Both literal answer-token log probabilities required; no missing-token substitution')
 a,b=logs['0'],logs['1'];d=b-a;p=1/(1+math.exp(-d)) if d>=0 else math.exp(d)/(1+math.exp(d));mass=math.exp(a)+math.exp(b)
 if mass<=0 or mass>1.00001:raise ValueError('Invalid probability mass')
 return {'logp0':a,'logp1':b,'log_odds':d,'p0':math.exp(a),'p1':math.exp(b),'binary_mass':mass,'p1_conditional':p,'sampled_output':c.get('message',{}).get('content'),'format_compliant':c.get('message',{}).get('content') in ['0','1']}

def validate(item,response):
 r=extract(response);u=response.get('usage',{})
 if u.get('completion_tokens')!=1 or u.get('total_tokens')!=u.get('prompt_tokens',0)+1:raise ValueError('Unexpected token usage')
 return r

def items(name,phase,repeats=1,source=None,seeded=False):
 model,tag=CANDIDATES[name];e=next(e for e in json.loads((BASE/(model.replace('/','--')+'.json')).read_text())['data']['endpoints'] if e['tag']==tag)
 source=source or json.loads(Path('data/local-validation/diagnostic19.json').read_text())['items']
 out=[]
 for i in source:
  req={'model':model,'messages':copy.deepcopy(i['messages']),'temperature':1,'top_p':1,'max_tokens':1,'logprobs':True,'top_logprobs':20,'provider':{'only':[tag],'allow_fallbacks':False,'require_parameters':True,'max_price':{k:float(Decimal(e['pricing'][v])*1_000_000) for k,v in [('prompt','prompt'),('completion','completion')]}}}
  if name=='granite8-core':req['reasoning']={'enabled':False}
  if seeded:req['seed']=20261020
  for rep in range(repeats):out.append({'id':i['id'],'replica':rep,'request':req,'candidate':name,'phase':phase,'source_id':i['id'],'constitution_id':i.get('constitution_id'),'scenario_id':i.get('scenario_id')})
 random.Random(20261020).shuffle(out);return out

def run(name,phase,repeats,workers,source=None,seeded=False):
 batch=items(name,phase,repeats,source,seeded)
 path=BASE/(name+'-'+phase)
 write_json(BASE/(name+'-'+phase+'-execution.json'),{'candidate':name,'phase':phase,'workers':workers,'requests':len(batch),'repeats':repeats,'sequence_hash':digest(batch),'temperature':1,'top_p':1,'top_logprobs':20,'automatic_retries':0,'shared_budget_usd':1})
 return run_study(name+'-'+phase,batch,validate,ledger_path=BASE/'budget.sqlite',output=path,budget=1,concurrency=workers)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=['probe','screen','repeat','followup'],required=True);p.add_argument('--candidate');p.add_argument('--source');p.add_argument('--phase');p.add_argument('--workers',type=int,default=1);p.add_argument('--repeats',type=int,default=3);p.add_argument('--seeded',action='store_true');a=p.parse_args()
 if a.stage=='probe':
  source=[i for i in json.loads(Path('data/local-validation/diagnostic19.json').read_text())['items'] if i['id']=='conservatism--16204']
  for name in CANDIDATES:
   try:print(name,'valid',len(run(name,'probe',1,1,source)),flush=True)
   except (ValueError,RuntimeError) as e:print(name,'stopped',str(e),flush=True)
 elif a.stage=='screen':run(a.candidate,'screen',1,1)
 elif a.stage=='repeat':
  for phase,workers in [('repeat-sequential',1),('repeat-concurrent',3)]:run(a.candidate,phase,a.repeats,workers)
 else:run(a.candidate,a.phase,a.repeats,a.workers,json.loads(Path(a.source).read_text())['items'],a.seeded)
