import contextlib
import io
import json
import math
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

from constitution_distance import cli, runner
from constitution_distance.api import API, APIError
from constitution_distance.core import (digest, distance_matrix, extract_probabilities,
    load_constitutions, load_scenarios, messages, strip_scenarios, unique_dilemmas)
from constitution_distance.prepare import action_issues, select_scenarios
from constitution_distance.storage import BudgetError, Ledger, money

ROOT = Path(__file__).resolve().parents[1]


def scenario(i='55', group='workplace'):
    return {'id':str(i), 'text':f'Case {i}: Choose action A or action B?', 'action1':'Take action A',
            'action0':'Take action B', 'topic_group':group, 'topic':1}


def response(p0=.3, p1=.6):
    return {'id':'mock-response', 'provider':'Parasail', 'model':'meta-llama/llama-3.3-70b-instruct',
        '_http_status':200, 'usage':{'prompt_tokens':100,'completion_tokens':1,'total_tokens':101,'cost':.00002},
        'choices':[{'message':{'content':'1'}, 'logprobs':{'content':[{'token':'1',
        'logprob':math.log(p1),'top_logprobs':[{'token':'0','logprob':math.log(p0)},
        {'token':'1','logprob':math.log(p1)}]}]}}]}


def fake_metadata():
    return {'model':{'id':'meta-llama/llama-3.3-70b-instruct'},'endpoint':{
        'provider_name':'Parasail','tag':'parasail/fp8','context_length':1000,
        'pricing':{'prompt':'.00000022','completion':'.0000005'}},'observed_at':'test'}


class CoreTests(unittest.TestCase):
    def test_raw_conditional_and_logs(self):
        r=extract_probabilities(response())
        self.assertAlmostEqual(r['p1'],.6); self.assertAlmostEqual(r['p0'],.3)
        self.assertAlmostEqual(r['p1_conditional'],2/3); self.assertAlmostEqual(r['logp0'],math.log(.3))

    def test_malformed_missing_conflicting_and_refusal(self):
        variations=[]
        for kind in ['null','empty','missing','conflicting','sentinel','nan','positive','boolean','refusal','two_tokens','mismatch']:
            obj=response(); item=obj['choices'][0]['logprobs']['content'][0]
            if kind=='null': obj['choices'][0]['logprobs']=None
            if kind=='empty': item['top_logprobs']=[]
            if kind=='missing': item['top_logprobs']=item['top_logprobs'][1:]
            if kind=='conflicting': item['logprob']=-5
            if kind in ['sentinel','nan','positive','boolean']:
                item['top_logprobs'][0]['logprob']={'sentinel':-9999,'nan':float('nan'),'positive':.1,'boolean':True}[kind]
            if kind=='refusal': obj['choices'][0]['message']['content']='Sorry'
            if kind=='two_tokens': obj['choices'][0]['logprobs']['content'].append(dict(item))
            if kind=='mismatch': item['token']='0'
            with self.subTest(kind=kind), self.assertRaises(ValueError): extract_probabilities(obj)

    def test_extreme_probability_has_no_artificial_floor(self):
        obj=response();item=obj['choices'][0]['logprobs']['content'][0];item['logprob']=-900
        item['top_logprobs']=[{'token':'0','logprob':-.1},{'token':'1','logprob':-900}]
        self.assertEqual(extract_probabilities(obj)['p1_conditional'],0)
        with self.assertRaises(ValueError):extract_probabilities(response(.9,.9))

    def test_distance_arithmetic_and_validation(self):
        self.assertEqual(distance_matrix([[0,.25,1],[1,.5,0]]),[[0,2.25],[2.25,0]])
        for vectors in [[],[[]],[[float('nan')]],[[1.01]],[[.5],[.4,.2]]]:
            with self.assertRaises(ValueError): distance_matrix(vectors)

    def test_anchor_cleaning_and_actual_message_invariance(self):
        cs=load_constitutions(ROOT/'data/constitutions');self.assertEqual(len(cs),24)
        s=scenario();s['negative_consequence']='FORBIDDEN';s['values_aggregated']='FORBIDDEN'
        prompts=[messages(c,s) for c in cs]
        self.assertEqual(len({digest(p[1]) for p in prompts}),1)
        for p in prompts:
            self.assertEqual([m['role'] for m in p],['system','user'])
            self.assertIn(s['text'],p[1]['content']);self.assertIn('1 (to_do): "Take action A"',p[1]['content'])
            self.assertIn('0 (not_to_do): "Take action B"',p[1]['content']);self.assertNotIn('FORBIDDEN',json.dumps(p))
        for c in cs:self.assertEqual(c,strip_scenarios(c))
        self.assertEqual(strip_scenarios({'x':[{'scenarios':['REMOVE'],'a':2}]}),{'x':[{'a':2}]})

    def test_pair_dedup_and_structural_rejections(self):
        rows=[{'dilemma_idx':55,'dilemma_situation':'Choose A or B?','action_type':a,
               'action':text,'topic':1,'topic_group':'workplace','negative_consequence':'FORBIDDEN'}
              for a,text in [('to_do','A'),('not_to_do','B')]]
        s=unique_dilemmas(rows)[0];self.assertEqual((s['action1'],s['action0']),('A','B'))
        self.assertNotIn('FORBIDDEN',json.dumps(s))
        with self.assertRaises(ValueError):unique_dilemmas(rows[:1])
        rows[1]['dilemma_situation']='Mismatch'
        with self.assertRaises(ValueError):unique_dilemmas(rows)

    def test_legacy_questions_rejected_and_ambiguity_not_rewritten(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'s.jsonl';p.write_text('{"id":"1","text":"Yes?"}\n')
            with self.assertRaisesRegex(ValueError,'paired action'):load_scenarios(p)
        s=scenario();s['action0']=s['action1'];before=dict(s)
        self.assertIn('identical_action_descriptions',action_issues(s));self.assertEqual(s,before)

    def test_seeded_stratification(self):
        ss=[scenario(str(i),g) for i,g in enumerate(['a']*5+['b']*5+['c']*5)]
        x=select_scenarios(ss,5,123)
        self.assertEqual(x,select_scenarios(list(reversed(ss)),5,123))
        self.assertEqual({s['topic_group'] for s in x},{'a','b','c'})
        self.assertEqual(len({s['id'] for s in x}),5)


class LedgerTests(unittest.TestCase):
    def setup_ledger(self,td,cap=.01):
        l=Ledger(Path(td)/'ledger.sqlite',cap);l.register('run',{'x':1},{},[('c',str(i),0) for i in range(5)])
        return l

    def test_zero_budget_and_exact_exhaustion(self):
        with tempfile.TemporaryDirectory() as td:
            l=self.setup_ledger(td,0)
            with self.assertRaises(BudgetError):l.claim('run',('c','0',0),{'messages':[]},money(.001))
            self.assertEqual(len(l.attempts('run')),0);l.close()
        with tempfile.TemporaryDirectory() as td:
            l=self.setup_ledger(td,.001)
            a=l.claim('run',('c','0',0),{'messages':[]},money(.001))
            with self.assertRaises(BudgetError):l.claim('run',('c','1',0),{'messages':[]},1)
            l.settle(a,'valid',{'ok':True},{'usage':{'cost':.0004}})
            self.assertIsNotNone(l.claim('run',('c','1',0),{'messages':[]},money(.0006)))
            self.assertIsNone(l.claim('run',('c','0',0),{'messages':[]},1,True));l.close()

    def test_empty_zero_ledger_can_be_explicitly_authorized(self):
        with tempfile.TemporaryDirectory() as td:
            l=self.setup_ledger(td,0);l.close()
            l=Ledger(Path(td)/'ledger.sqlite',.01)
            self.assertIsNotNone(l.claim('run',('c','0',0),{'messages':[]},money(.001)));l.close()

    def test_concurrent_reservations_and_duplicate_prevention(self):
        with tempfile.TemporaryDirectory() as td:
            l=self.setup_ledger(td,.002)
            def claim(i):
                try:return l.claim('run',('c',str(i),0),{'messages':[]},money(.001))
                except BudgetError:return None
            with ThreadPoolExecutor(max_workers=5) as p:claims=list(p.map(claim,range(5)))
            self.assertEqual(sum(x is not None for x in claims),2)
            self.assertEqual(l.totals()['outstanding_reservations_usd'],.002)
            claimed_index=next(i for i,a in enumerate(claims) if a is not None)
            self.assertIsNone(l.claim('run',('c',str(claimed_index),0),{'messages':[]},1))
            l.close()

    def test_crash_keeps_reservation_and_uncertain_pair_is_not_retried(self):
        with tempfile.TemporaryDirectory() as td:
            l=self.setup_ledger(td,.001);l.claim('run',('c','0',0),{'messages':[]},money(.001));l.close()
            l=Ledger(Path(td)/'ledger.sqlite',.001)
            self.assertIsNone(l.claim('run',('c','0',0),{'messages':[]},1,True))
            with self.assertRaises(BudgetError):l.claim('run',('c','1',0),{'messages':[]},1)
            l.close()

    def test_unknown_cost_charged_conservatively_and_request_cap(self):
        with tempfile.TemporaryDirectory() as td:
            l=self.setup_ledger(td,.01);a=l.claim('run',('c','0',0),{'messages':[]},money(.001))
            l.settle(a,'error',error='Network failure')
            self.assertEqual(l.totals()['conservative_spending_usd'],.001)
            self.assertEqual(l.totals()['actual_spending_usd'],0)
            with self.assertRaises(BudgetError):l.claim('run',('c','1',0),{'messages':[]},1,max_requests=1)
            l.close()

    def test_actual_cost_over_reservation_still_recorded(self):
        with tempfile.TemporaryDirectory() as td:
            l=self.setup_ledger(td);a=l.claim('run',('c','0',0),{'messages':[]},money(.001))
            with self.assertRaises(BudgetError):l.settle(a,'invalid',response={'usage':{'cost':.002}})
            self.assertEqual(l.totals()['actual_spending_usd'],.002);l.close()


class PipelineTests(unittest.TestCase):
    def args(self,td,n=3):
        s=Path(td)/'scenarios.jsonl';s.write_text(''.join(json.dumps(scenario(i))+'\n' for i in range(n)))
        return cli.parser().parse_args(['run','--scenarios',str(s),'--constitutions',str(ROOT/'data/constitutions'),
            '--constitution-ids','kantian-deontology','utilitarianism','--output',str(Path(td)/'out'),
            '--ledger',str(Path(td)/'budget.sqlite'),'--budget-usd','.1','--attempts','2','--concurrency','3'])

    @contextlib.contextmanager
    def mocks(self,func):
        with patch.dict(os.environ,{'OPENROUTER_API_KEY':'fake-test-key'}),patch.object(runner,'metadata',return_value=fake_metadata()),patch.object(API,'request',func),contextlib.redirect_stdout(io.StringIO()):
            yield

    def test_six_calls_resume_no_network_and_integrity(self):
        calls=[]
        def request(client,path,payload=None):calls.append(payload);return response()
        with tempfile.TemporaryDirectory() as td:
            args=self.args(td)
            with self.mocks(request):runner.run(args)
            self.assertEqual(len(calls),6)
            for p in calls:
                self.assertEqual(p['provider']['only'],['parasail/fp8']);self.assertFalse(p['provider']['allow_fallbacks'])
                self.assertTrue(p['provider']['require_parameters']);self.assertEqual(p['temperature'],1)
            args.budget_usd=0
            with self.mocks(request):runner.run(args)
            self.assertEqual(len(calls),6)
            args.model='different/model'
            with self.mocks(request),self.assertRaisesRegex(ValueError,'different experiment'):runner.run(args)
            summary=json.loads((Path(td)/'out/summary.json').read_text());self.assertEqual(summary['missing'],0)
            self.assertNotIn('fake-test-key',(Path(td)/'out/responses.jsonl').read_text())

    def test_resume_rejects_swapped_ledger_and_corrupt_record(self):
        with tempfile.TemporaryDirectory() as td:
            args=self.args(td,1)
            with self.mocks(lambda *a:response()):runner.run(args)
            original=args.ledger;args.ledger=str(Path(td)/'different.sqlite')
            with self.mocks(lambda *a:self.fail('Duplicate inference')),self.assertRaisesRegex(ValueError,'original authoritative ledger'):runner.run(args)
            args.ledger=original
            l=Ledger(args.ledger,.1)
            r=l.db.execute('SELECT run,cid,sid,replica,record FROM evaluations LIMIT 1').fetchone()
            record=json.loads(r['record']);record['prompt_hash']='corrupt'
            l.db.execute('UPDATE evaluations SET record=? WHERE run=? AND cid=? AND sid=? AND replica=?',
                         (json.dumps(record),r['run'],r['cid'],r['sid'],r['replica']));l.close()
            with self.mocks(lambda *a:self.fail('Duplicate inference')),self.assertRaisesRegex(ValueError,'integrity'):runner.run(args)

    def test_default_zero_never_dispatches(self):
        with tempfile.TemporaryDirectory() as td:
            args=self.args(td);args.budget_usd=0
            with self.mocks(lambda *a: self.fail('API call on zero budget')),self.assertRaises(BudgetError):runner.run(args)

    def test_invalid_is_missing_and_not_retried_by_normal_resume(self):
        calls=[]
        def request(*a):
            calls.append(1);obj=response();obj['choices'][0]['logprobs']=None;return obj
        with tempfile.TemporaryDirectory() as td:
            args=self.args(td)
            with self.mocks(request),self.assertRaisesRegex(ValueError,'Capability'):runner.run(args)
            self.assertEqual(len(calls),1)
            with self.mocks(lambda *a: response()),self.assertRaisesRegex(ValueError,'incomplete'):runner.run(args)
            missing=json.loads((Path(td)/'out/missing.json').read_text());self.assertEqual(len(missing),1)
            self.assertEqual(missing[0]['state'],'invalid')
            args.retry_missing=True
            with self.mocks(lambda *a: response()):runner.run(args)
            self.assertEqual(json.loads((Path(td)/'out/missing.json').read_text()),[])

    def test_transient_retry_is_reserved_and_backoff_bounded(self):
        calls=[]
        def request(*a):
            calls.append(1)
            if len(calls)==1:raise APIError(429,True,0)
            return response()
        with tempfile.TemporaryDirectory() as td:
            args=self.args(td,1)
            with self.mocks(request),patch.object(runner.time,'sleep') as sleep:runner.run(args)
            self.assertEqual(len(calls),3);self.assertEqual(sleep.call_count,1)
            self.assertLessEqual(sleep.call_args[0][0],31)
            attempts=json.loads((Path(td)/'out/attempts.json').read_text());self.assertEqual(len(attempts),3)
            self.assertEqual(attempts[0]['state'],'retry')

    def test_partial_budget_resume_never_recomputes_success(self):
        calls=[]
        def request(client,path,payload=None):calls.append(digest(payload));return response()
        with tempfile.TemporaryDirectory() as td:
            args=self.args(td,2);args.max_requests=2
            with self.mocks(request),self.assertRaises(BudgetError):runner.run(args)
            self.assertEqual(len(calls),2)
            args.max_requests=4
            with self.mocks(request):runner.run(args)
            self.assertEqual(len(calls),4);self.assertEqual(len(set(calls)),4)

    def test_model_provider_cost_and_usage_rejected(self):
        args=cli.parser().parse_args(['run'])
        for field,value in [('model','wrong'),('provider','Novita'),('usage',{})]:
            r=response();r[field]=value
            with self.assertRaises(ValueError):runner.validate_response(r,args,fake_metadata())

    def test_partial_matrix_has_unknown_distances_and_offline_export(self):
        count=[]
        def request(*a):
            count.append(1);r=response()
            if len(count)==2:r['choices'][0]['logprobs']=None
            return r
        with tempfile.TemporaryDirectory() as td:
            args=self.args(td,2);args.concurrency=1
            with self.mocks(request),self.assertRaisesRegex(ValueError,'incomplete'):runner.run(args)
            with patch.object(API,'request',side_effect=AssertionError('Offline export made an API request')):
                runner.export_existing(cli.parser().parse_args(['export','--output',args.output]))
            import csv
            with (Path(td)/'out/distances_l1.csv').open() as f:rows=list(csv.reader(f))
            self.assertEqual(rows[1][1:],["0.0",""]);self.assertEqual(rows[2][1:],["","0.0"])

    def test_identity_mismatch_stops_capability_gate(self):
        calls=[]
        def request(*a):calls.append(1);r=response();r['provider']='Wrong';return r
        with tempfile.TemporaryDirectory() as td:
            args=self.args(td)
            with self.mocks(request),self.assertRaisesRegex(RuntimeError,'identity mismatch'):runner.run(args)
            self.assertEqual(len(calls),1)

    def test_fetch_preserves_action_pairs_and_excludes_annotations(self):
        def request(client,path,payload=None):
            rows=[{'dilemma_idx':55,'dilemma_situation':'Choose A or B?','action_type':a,'action':b,
                   'topic':1,'topic_group':'workplace','negative_consequence':'FORBIDDEN','values_aggregated':'FORBIDDEN'}
                  for a,b in [('to_do','A'),('not_to_do','B')]]
            return {'num_rows_total':2,'features':[{'name':k} for k in rows[0]],'rows':[{'row_idx':i,'row':r} for i,r in enumerate(rows)]}
        with tempfile.TemporaryDirectory() as td,patch.object(API,'request',request),contextlib.redirect_stderr(io.StringIO()):
            p=Path(td)/'s.jsonl';args=cli.parser().parse_args(['fetch','--config','fixture','--output',str(p)]);cli.fetch(args)
            self.assertEqual(len(load_scenarios(p)),1);self.assertNotIn('FORBIDDEN',p.read_text())


if __name__=='__main__':unittest.main()
