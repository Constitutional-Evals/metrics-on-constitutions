"""Offline reference tests. Small/random weights test code, never 70B reliability."""
import copy,importlib.util,json,math,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from constitution_distance.local import Checkpoint,serialize_prompt,snapshot_lock,verify_lock,probabilities,analyze_run
from constitution_distance.core import digest,messages,load_constitutions,load_scenarios
TORCH=importlib.util.find_spec('torch') is not None

class Tokenizer:
    chat_template='test template'
    def encode(self,s,add_special_tokens=False):return list(s.encode())
    def decode(self,ids,skip_special_tokens=False):return bytes(ids).decode()
    def apply_chat_template(self,msgs,tokenize=False,add_generation_prompt=False):
        s=''.join(m['role']+':'+m['content']+'\n' for m in msgs)+('assistant:' if add_generation_prompt else '')
        return self.encode(s) if tokenize else s

class LocalIntegrityTests(unittest.TestCase):
    def test_prompt_serialization_label_identity_and_generation_prefix(self):
        p=serialize_prompt(Tokenizer(),[{'role':'user','content':'Choose'}])
        self.assertTrue(p['text'].endswith('assistant:'));self.assertEqual(p['last_position'],len(p['input_ids'])-1)
        self.assertEqual(p['label_ids'],{'0':48,'1':49});self.assertEqual(p['input_hash'],digest(p['input_ids']))
    def test_rejects_merged_label_context(self):
        class Bad(Tokenizer):
            def encode(self,s,add_special_tokens=False):return [1] if s.endswith('assistant:0') else super().encode(s)
        with self.assertRaisesRegex(ValueError,'single-token'):serialize_prompt(Bad(),[{'role':'user','content':'x'}])
    def test_checkpoint_resume_duplicate_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            s={'backend':'test'};c=Checkpoint(d,s);c.put('a',{'value':1});path=c.path;c.close()
            c=Checkpoint(d,s);self.assertEqual(c.records['a']['value'],1)
            with self.assertRaises(ValueError):c.put('a',{'value':2})
            c.db.execute('UPDATE records SET body=?',(json.dumps({'slot':'a','value':3}),));c.close()
            with self.assertRaisesRegex(ValueError,'checksum'):Checkpoint(d,s)
            other=Checkpoint(d,{'backend':'changed'});self.assertNotEqual(path,other.path);other.close()
    def test_snapshot_hashes_and_rejects_quantization(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/('a'*40);p.mkdir();(p/'config.json').write_text('{}');(p/'model.safetensors').write_bytes(b'test')
            lock=snapshot_lock(p,'small','a'*40);verify_lock(lock)
            (p/'model.safetensors').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'checksum'):verify_lock(lock)
            (p/'config.json').write_text('{"quantization_config": {"load_in_4bit":true}}')
            with self.assertRaisesRegex(ValueError,'Quantized'):snapshot_lock(p,'small','a'*40)
            with self.assertRaisesRegex(ValueError,'Immutable'):snapshot_lock(p,'small','main')
    def test_saved_diagnostic_messages_are_existing_definitions(self):
        root=Path(__file__).resolve().parents[1];cs={c['id']:c for c in load_constitutions(root/'data/constitutions')};ss={s['id']:s for s in load_scenarios(root/'data/scenarios-v2.jsonl')}
        inputs=json.loads((root/'data/local-validation/diagnostic19.json').read_text())['items'];self.assertEqual(len(inputs),19)
        for i in inputs:self.assertEqual(i['messages'],messages(cs[i['constitution_id']],ss[i['scenario_id']]))
    def test_missing_session_cannot_pass(self):
        with tempfile.TemporaryDirectory() as d:
            spec={'inputs':[{'id':'x'}],'config':{'repeats':2,'planned_sessions':['a','b']}}
            c=Checkpoint(d,spec)
            for k in range(2):c.put(str(k),{'item_id':'x','session_label':'a','repeat':k,'process_id':'p','probabilities':{'p1_conditional':.5,'log_odds':0}})
            path=c.path;c.close();a=analyze_run(path);self.assertFalse(a['pair_gate_passes']);self.assertEqual(len(a['missing_observed_sessions']),2)

@unittest.skipUnless(TORCH,'Install local extras for tensor tests')
class NumericTests(unittest.TestCase):
    def test_full_vocab_normalization_not_binary_softmax(self):
        import torch
        r=probabilities(torch.tensor([0.,math.log(3),math.log(6)]),{'0':0,'1':1})
        self.assertAlmostEqual(r['p0'],.1,places=6);self.assertAlmostEqual(r['p1'],.3,places=6);self.assertAlmostEqual(r['p1_conditional'],.75,places=7)
        self.assertAlmostEqual(r['binary_mass'],.4,places=6)
    def test_extreme_logits_nonfinite_and_invalid_identity(self):
        import torch
        for logits in [[-10000.,10000.],[10000.,-10000.]]:
            r=probabilities(torch.tensor(logits),{'0':0,'1':1});self.assertTrue(0<=r['p1_conditional']<=1)
        for z,ids in [(torch.tensor([float('nan'),1.]),{'0':0,'1':1}),(torch.ones(2),{'0':0,'1':0}),(torch.ones(2,2),{'0':0,'1':1})]:
            with self.assertRaises(ValueError):probabilities(z,ids)
    def test_right_padded_final_position_and_no_generate(self):
        import torch
        from constitution_distance.local import Reference
        ref=Reference.__new__(Reference);ref.torch=torch;ref.config={'cache':'off'}
        ref.tokenizer=type('Tok',(),{'pad_token_id':0})()
        class Fake:
            def get_input_embeddings(self):return type('E',(),{'weight':torch.zeros(1)})()
            def __call__(self,**kw):
                self.kw=kw
                # Each position has an identifiable label logit.
                z=torch.stack([kw['input_ids'].float(),torch.zeros_like(kw['input_ids']).float()],-1)
                return type('O',(),{'logits':z})()
        ref.model=Fake();ps,metrics=ref.forward([{'input_ids':[1,2,3],'label_ids':{'0':0,'1':1}},{'input_ids':[4],'label_ids':{'0':0,'1':1}}])
        self.assertEqual([p['logit0'] for p in ps],[3.,4.]);self.assertEqual(ref.model.kw['attention_mask'].tolist(),[[1,1,1],[1,0,0]])
        self.assertEqual(metrics['input_tokens'],4)

@unittest.skipUnless(TORCH,'Install local extras')
class OptimizedExportTests(unittest.TestCase):
    def test_only_complete_raw_vectors_with_exact_tokens_are_accepted(self):
        from constitution_distance.vllm_validation import validate_raw_export
        prompt={'input_ids':[7,8],'label_ids':{'0':0,'1':1}}
        e={'backend':'vllm','mode':'raw_logits','revision':'a','tokenizer_revision':'a','input_ids':[7,8],'label_ids':{'0':0,'1':1},'temperature':1,'top_p':1,'runtime':{k:'recorded' for k in ['vllm_version','hardware','tensor_parallel_size','attention','batch_invariance','cache']},'vocab_size':3,'logits':[0.,1.,2.]}
        r=validate_raw_export(e,prompt,'a','a');self.assertGreater(r['p1_conditional'],.5)
        for change in [{'mode':'processed_logits'},{'logits':[0.,1.]},{'input_ids':[7,9]},{'revision':'other'}]:
            with self.assertRaises(ValueError):validate_raw_export({**e,**change},prompt,'a','a')
    def test_cross_backend_gate_never_hides_a_difference(self):
        from constitution_distance.vllm_validation import compare_probabilities
        r={'x':{'input_hash':'same','probabilities':{'p1_conditional':.5,'log_odds':0}}}
        o=copy.deepcopy(r);o['x']['probabilities']['p1_conditional']=.6;self.assertFalse(compare_probabilities(r,o)['passes'])
        o['x']['input_hash']='different'
        with self.assertRaises(ValueError):compare_probabilities(r,o)

class BlockDistanceTests(unittest.TestCase):
    def test_complete_blocks_report_sum_and_mean_and_fixed_threshold(self):
        with tempfile.TemporaryDirectory() as d:
            items=[{'id':f'c{c}--s{s}','constitution_id':f'c{c}','scenario_id':f's{s}'} for c in range(24) for s in range(20)]
            spec={'inputs':items,'config':{'repeats':2,'planned_sessions':['a']}};cp=Checkpoint(d,spec)
            for repeat in range(2):
                for i in items:
                    c=int(i['constitution_id'][1:]);p=.01*c+(repeat*.001 if c==0 else 0)
                    cp.put(f'{repeat}-{i["id"]}',{'item_id':i['id'],'session_label':'a','repeat':repeat,'process_id':'one','probabilities':{'p1_conditional':p,'log_odds':0}})
            path=cp.path;cp.close();a=analyze_run(path);self.assertTrue(a['block_gate_passes']);self.assertAlmostEqual(a['maximum_normalized_distance_change'],.001)
            for b in a['block_matrices']:
                for j in range(24):
                    self.assertEqual(b['summed_l1'][j][j],0)
                    for k in range(24):
                        self.assertEqual(b['summed_l1'][j][k],b['summed_l1'][k][j]);self.assertAlmostEqual(b['summed_l1'][j][k]/20,b['normalized_l1'][j][k])

class ConfigurationComparisonTests(unittest.TestCase):
    def test_separate_complete_runs_compared_without_merging(self):
        from constitution_distance.local_comparison import compare_runs
        with tempfile.TemporaryDirectory() as d:
            paths=[]
            for mode,p in [('off',.5),('prefill',.6)]:
                spec={'inputs':[{'id':'x'}],'prompt_hashes':{'x':'tokens'},'lock':{'revision':'r','tokenizer_revision':'r','model':{'files':{'weight':'sha'}},'tokenizer':{'files':{'tokenizer':'sha'}}},'config':{'repeats':2,'planned_sessions':['a'],'cache':mode}}
                cp=Checkpoint(d,spec)
                for k in range(2):cp.put(str(k),{'item_id':'x','probabilities':{'p1_conditional':p,'log_odds':0}})
                paths.append(cp.path);cp.close()
            result=compare_runs(*paths);self.assertAlmostEqual(result['maximum_mean_probability_difference'],.1)
            db=sqlite3.connect(paths[1]/'checkpoint.sqlite');db.execute('DELETE FROM records WHERE slot=?',('1',));db.commit();db.close()
            with self.assertRaisesRegex(ValueError,'complete'):compare_runs(*paths)
