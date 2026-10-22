import copy,csv,importlib.util,json,math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from constitution_distance.core import load_constitutions,load_scenarios,messages,digest,extract_probabilities
from constitution_distance.controls import control_request,probability_to_do
from constitution_distance.runner import scenario_approval
from constitution_distance.studies import run_study
from constitution_distance.api import API
from constitution_distance.storage import BudgetError

ROOT=Path(__file__).resolve().parents[1]


class MethodologyTests(unittest.TestCase):
    def test_label_mapping_and_order_are_independent_and_source_unchanged(self):
        s={'id':'x','text':'Original question?','action1':'Do A','action0':'Do B'}
        c=load_constitutions(ROOT/'data/constitutions')[0]
        original={'messages':messages(c,s),'temperature':1};before=copy.deepcopy(original)
        self.assertEqual(control_request(original,s),original)
        for swapped in [False,True]:
            for reverse in [False,True]:
                r=control_request(original,s,swapped=swapped,reverse_order=reverse)
                user=r['messages'][1]['content'];one='0' if swapped else '1';zero='1' if swapped else '0'
                self.assertIn(one+' (to_do): "Do A"',user);self.assertIn(zero+' (not_to_do): "Do B"',user)
                self.assertEqual(user.index('(to_do)')>user.index('(not_to_do)'),reverse)
                self.assertIn(one+' selects the to_do action',r['messages'][0]['content'])
                self.assertIn(s['text'],user)
        self.assertEqual(original,before)
        p={'p0':.3,'binary_mass':.9,'p1_conditional':2/3}
        self.assertAlmostEqual(probability_to_do(p,True),1/3)
        self.assertAlmostEqual(probability_to_do(p,False),2/3)

    def test_candidate_is_live_blocked_and_hash_checked_after_approval(self):
        import hashlib
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'scenarios.jsonl';p.write_text('original')
            m=p.with_suffix('.manifest.json');m.write_text(json.dumps({'execution_approved':False}))
            self.assertFalse(scenario_approval(p,True)['execution_approved'])
            with self.assertRaisesRegex(ValueError,'preliminary'):scenario_approval(p,False)
            m.write_text(json.dumps({'execution_approved':True,'approved_file_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
            self.assertTrue(scenario_approval(p,False)['execution_approved'])
            p.write_text('changed')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):scenario_approval(p,True)

    def test_full_audit_complete_exact_and_never_claims_human_approval(self):
        path=ROOT/'data/audit/scenario-audit.jsonl'
        if not path.exists():self.skipTest('Generated full audit is not present')
        ss=load_scenarios(ROOT/'data/scenarios-v2.jsonl');by={s['id']:s for s in ss}
        rows=[json.loads(l) for l in path.read_text().splitlines()]
        self.assertEqual(len(rows),1360);self.assertEqual({r['dilemma_id'] for r in rows},set(by))
        for r in rows:
            s=by[r['dilemma_id']]
            self.assertEqual((r['situation'],r['to_do'],r['not_to_do']),(s['text'],s['action1'],s['action0']))
            self.assertFalse(r['human_reviewed']);self.assertEqual(r['source_scenario_sha256'],digest(s))
            self.assertIn(r['classification'],{'valid','ambiguous','requires_review'})
        queue=[json.loads(l) for l in (ROOT/'data/audit/human-review-queue.jsonl').read_text().splitlines()]
        self.assertEqual({r['dilemma_id'] for r in queue},{r['dilemma_id'] for r in rows if r['classification']!='valid'})
        candidate=load_scenarios(ROOT/'data/scenarios-reviewed.jsonl')
        self.assertEqual({s['id'] for s in candidate},{r['dilemma_id'] for r in rows if r['classification']=='valid'})
        approval=json.loads((ROOT/'data/scenarios-reviewed.manifest.json').read_text())
        self.assertEqual(approval['approved_scenario_count'],0);self.assertFalse(approval['execution_approved'])
        self.assertEqual(len(candidate),1336)

    def test_auxiliary_zero_budget_idempotence_and_no_config_overwrite(self):
        request={'model':'meta-llama/llama-3.3-70b-instruct','messages':[{'role':'user','content':'Question'}],
          'max_tokens':1,'provider':{'only':['parasail/fp8'],'allow_fallbacks':False,'require_parameters':True,
                                   'max_price':{'prompt':.22,'completion':.5}}}
        items=[{'id':'a','request':request}]
        meta={'endpoint':{'context_length':1000,'provider_name':'Parasail'}}
        response={'model':request['model'],'provider':'Parasail','usage':{'prompt_tokens':10,'completion_tokens':1,'cost':.00001}}
        calls=[]
        def fake(*a):calls.append(1);return response
        with tempfile.TemporaryDirectory() as td:
            options=dict(ledger_path=Path(td)/'ledger.sqlite',output=Path(td)/'out')
            with self.assertRaises(BudgetError):run_study('test',items,lambda i,r:'ok',budget=0,**options)
            with patch('constitution_distance.studies.metadata',return_value=meta),patch.object(API,'request',fake),patch.dict('os.environ',{'OPENROUTER_API_KEY':'fake-test-key'}):
                records=run_study('test',items,lambda i,r:'ok',budget=.01,**options)
                self.assertEqual(len(records),1)
                run_study('test',items,lambda i,r:'ok',budget=0,**options)
                self.assertEqual(len(calls),1)
                with self.assertRaisesRegex(ValueError,'different configuration'):
                    run_study('changed',items,lambda i,r:'ok',budget=.01,**options)


if __name__=='__main__':unittest.main()
