"""Explicit artifact acquisition only. Never invoked automatically by the backend."""
import argparse
from huggingface_hub import snapshot_download
p=argparse.ArgumentParser();p.add_argument('--model',choices=['meta-llama/Llama-3.3-70B-Instruct','HuggingFaceTB/SmolLM2-135M-Instruct'],required=True);p.add_argument('--revision',required=True);p.add_argument('--allow-70b-download',action='store_true');a=p.parse_args()
import re
if not re.fullmatch('[a-f0-9]{40}',a.revision):p.error('Immutable commit SHA required')
if a.model.startswith('meta-llama/') and not a.allow_70b_download:p.error('70B download requires explicit --allow-70b-download authorization')
print(snapshot_download(a.model,revision=a.revision,allow_patterns=['*.safetensors','*.json','tokenizer.model','merges.txt','vocab.json','special_tokens_map.json'],max_workers=2))
