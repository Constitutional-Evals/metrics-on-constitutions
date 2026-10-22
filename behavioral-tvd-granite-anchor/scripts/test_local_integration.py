"""Offline multi-process integration with tiny RANDOM Llama weights; not scientific evidence."""
import argparse,json,os,subprocess,sys
from pathlib import Path
from transformers import AutoTokenizer,LlamaConfig,LlamaForCausalLM
import torch
from constitution_distance.local import snapshot_lock,immutable_json

p=argparse.ArgumentParser();p.add_argument('--tokenizer-snapshot',required=True);p.add_argument('--output',required=True);a=p.parse_args()
out=Path(a.output).absolute();out.mkdir(parents=True,exist_ok=True)
tok=AutoTokenizer.from_pretrained(a.tokenizer_snapshot,local_files_only=True)
revision='a'*40;snapshot=out/'fixture'/revision;snapshot.mkdir(parents=True,exist_ok=True)
torch.manual_seed(123);model=LlamaForCausalLM(LlamaConfig(vocab_size=len(tok),hidden_size=32,intermediate_size=64,num_hidden_layers=2,num_attention_heads=4,num_key_value_heads=2,max_position_embeddings=8192,attention_dropout=0)).to(torch.bfloat16);model.save_pretrained(snapshot,safe_serialization=True)
lock=snapshot_lock(snapshot,'software-test/random-Llama-NOT-PRETRAINED',revision,a.tokenizer_snapshot,Path(a.tokenizer_snapshot).name);immutable_json(out/'lock.json',lock)
items=json.loads(Path('data/local-validation/diagnostic19.json').read_text())['items'][:2]
items.append({'id':'short-control','messages':[{'role':'system','content':'Answer 0 or 1.'},{'role':'user','content':'Choose 0 or 1.'}]})
immutable_json(out/'inputs.json',{'items':items})
base=[sys.executable,'-m','constitution_distance.local_cli','benchmark','--lock',str(out/'lock.json'),'--inputs',str(out/'inputs.json'),'--output',str(out/'runs'),'--device','cpu','--software-test','--repeats','2']
env={**os.environ,'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}
def run(extra):
 done=subprocess.run(base+extra,env=env,text=True,capture_output=True,check=True);print(done.stderr,file=sys.stderr);return json.loads(done.stdout)
results=[]
for options in [[],['--batch-size','2'],['--attention','sdpa'],['--cache','prefill'],['--cache','split']]:
 first=run(options+['--session','restart-1']);resume=run(options+['--session','restart-1']);assert resume['performed']==0
 second=run(options+['--session','restart-2']);assert first['run_id']==second['run_id'] and second['performed']==6
 analysis=out/('analysis-'+first['run_id']+'.json')
 subprocess.run([sys.executable,'-m','constitution_distance.local_cli','analyze','--run',first['run_directory'],'--out',str(analysis)],env=env,check=True)
 results.append({'options':options,'first':first,'resume':resume,'restart':second,'analysis':json.loads(analysis.read_text())})
immutable_json(out/'integration-summary.json',{'model':'tiny random Llama, BF16; SmolLM2 official tokenizer; not pretrained or 70B reproducibility evidence','conditions':results})
