import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from constitution_distance.core import digest
from constitution_distance.exploratory import StageLedger, run_batch, BASELINE, CANARY
from constitution_distance.exploratory import all_pairs, canary_items
from constitution_distance.storage import BudgetError, money
from test_granite_final_pilot import FakeAPI, META
from final_granite_pilot import request, validate


class PilotAPI(FakeAPI):
    calls=0
    mode='valid'
    def request(self,path,payload):
        response=super().request(path,payload)
        if self.mode=='null-once' and self.calls==1 or self.mode=='null-always':
            response['choices'][0]['logprobs']=None
        if self.mode=='missing-label':
            response['choices'][0]['logprobs']['content'][0]['top_logprobs'].pop()
        if self.mode=='identity':response['provider']='Other'
        return response


class StageBudgetTests(unittest.TestCase):
    def test_atomic_concurrent_reservations_and_persistent_stage_cap(self):
        from concurrent.futures import ThreadPoolExecutor
        with tempfile.TemporaryDirectory() as d:
            ledger=StageLedger(Path(d)/'ledger.sqlite',10)
            pairs=[('c',str(i),0) for i in range(3)]
            ledger.register('r',{}, {},pairs);ledger.register_stage('b','r',.1,2000,{'approved':True})
            def claim(pair):
                try:return ledger.claim_stage('b','r',pair,request([]),money(.04))
                except BudgetError:return None
            with ThreadPoolExecutor(max_workers=3) as pool:ids=list(pool.map(claim,pairs))
            self.assertEqual(sum(i is not None for i in ids),2)
            self.assertEqual(ledger.stage_totals('b')['outstanding_reservations_usd'],.08)
            ledger.close();ledger=StageLedger(Path(d)/'ledger.sqlite',10)
            self.assertEqual(ledger.stage_totals('b')['outstanding_reservations_usd'],.08)
            with self.assertRaises(ValueError):ledger.register_stage('b','r',1,2000,{'approved':True})
            with self.assertRaises(BudgetError):ledger.claim_stage('b','r',pairs[ids.index(None)],request([]),money(.04))
            ledger.close()

    def test_experiment_cap_and_duplicate_claim_and_unknown_billing(self):
        with tempfile.TemporaryDirectory() as d:
            ledger=StageLedger(Path(d)/'ledger.sqlite',.05);p=('c','s',0)
            ledger.register('r',{}, {},[p]);ledger.register_stage('b','r',1,2000,{})
            aid=ledger.claim_stage('b','r',p,request([]),money(.04))
            self.assertIsNone(ledger.claim_stage('b','r',p,request([]),money(.04)))
            ledger.settle(aid,'retry',error='unknown billing')
            with self.assertRaises(BudgetError):ledger.claim_stage('b','r',p,request([]),money(.04),retry=True)
            self.assertEqual(ledger.totals()['conservative_spending_usd'],.04)
            ledger.close()


class ExploratoryRunnerTests(unittest.TestCase):
    def manifest(self):
        req=request([{'role':'user','content':'0 or1'}])
        return {'settings':{k:v for k,v in req.items() if k!='messages'},'scenarios':[
          {'id':'s','text':'Choose?','action1':'Act','action0':'Refrain'}],
          'constitutions':{'c':{'id':'c'}},'constitution_order':['c'],
          'batches':[{'number':1,'scenario_ids':['s']}],'schedule_seed':123,
          'canaries':[{'constitution_id':'c','scenario_id':'s','request':req,
                       'expected':{'p1_conditional':.5,'log_odds':0,'logp0':-.6931471805599453,'logp1':-.6931471805599453}}]}
    def auth(self,m):return {'run_id':digest(m),'stage':'batch-0001','approved':True,'stage_cap_usd':1,'maximum_primary_attempts':2000}
    def mocks(self,mode):
        PilotAPI.calls=0;PilotAPI.mode=mode
        return (patch('constitution_distance.exploratory.verify_manifest'),
                patch('constitution_distance.exploratory.metadata',return_value=META),
                patch('constitution_distance.exploratory.API',PilotAPI),
                patch('constitution_distance.exploratory.time.sleep'))
    def test_success_idempotent_resume_and_no_later_batch_dispatch(self):
        m=self.manifest()
        with tempfile.TemporaryDirectory() as d:
            a,b,c,e=self.mocks('valid')
            with a,b,c,e:
                r=run_batch(m,1,d,self.auth(m),validate,10,1,3)
                self.assertEqual(r['valid'],{'primary':4,'baseline':4,'canary':2})
                self.assertEqual(PilotAPI.calls,10)
                r2=run_batch(m,1,d,self.auth(m),validate,10,1,3)
                self.assertEqual(PilotAPI.calls,10)
                self.assertEqual(r['experiment_budget']['actual_spending_usd'],r2['experiment_budget']['actual_spending_usd'])
                with self.assertRaises(ValueError):run_batch(m,2,d,self.auth(m),validate,10,1,3)
    def test_null_once_retries_and_preserves_failed_attempt(self):
        m=self.manifest()
        with tempfile.TemporaryDirectory() as d:
            a,b,c,e=self.mocks('null-once')
            with a,b,c,e:
                r=run_batch(m,1,d,self.auth(m),validate,10,1,1)
            self.assertEqual(PilotAPI.calls,11);self.assertEqual(r['failed_attempts'],1)
            attempts=json.loads((Path(d)/'batch-0001/attempts.json').read_text())
            self.assertEqual(attempts[0]['error'],'logprobs:null')
            self.assertEqual(r['missing'],0)
    def test_null_exhaustion_missing_labels_and_identity_stop(self):
        for mode,n in [('null-always',3),('missing-label',1),('identity',1),('drift',10)]:
            m=self.manifest()
            with tempfile.TemporaryDirectory() as d:
                a,b,c,e=self.mocks(mode)
                with a,b,c,e:
                    with self.assertRaises(ValueError):run_batch(m,1,d,self.auth(m),validate,10,1,1)
                self.assertEqual(PilotAPI.calls,n)
                summary=json.loads((Path(d)/'batch-0001/summary.json').read_text())
                self.assertEqual(summary['status'],'STOPPED')
                self.assertGreater(summary['missing'],0)
                if mode!='drift':self.assertEqual(summary['valid']['primary'],0)
    def test_zero_budget_blocks_all_calls(self):
        m=self.manifest()
        with tempfile.TemporaryDirectory() as d:
            a,b,c,e=self.mocks('valid')
            with a,b,c,e:
                with self.assertRaises(BudgetError):run_batch(m,1,d,self.auth(m),validate)
            self.assertEqual(PilotAPI.calls,0)

    def test_primary_physical_cap_stops_dispatch(self):
        m=self.manifest();auth=self.auth(m);auth['maximum_primary_attempts']=2
        with tempfile.TemporaryDirectory() as d:
            a,b,c,e=self.mocks('valid')
            with a,b,c,e:
                with self.assertRaises(ValueError):run_batch(m,1,d,auth,validate,10,1,1)
            summary=json.loads((Path(d)/'batch-0001/summary.json').read_text())
            self.assertEqual(summary['primary_physical_attempts'],2)

    def test_partial_resume_adds_fresh_canary_without_recomputing_valid(self):
        m=self.manifest();rid=digest(m);auth=self.auth(m)
        with tempfile.TemporaryDirectory() as d:
            ledger=StageLedger(Path(d)/'ledger.sqlite',10)
            ledger.register(rid,m,META,list(all_pairs(m)))
            ledger.register_stage('batch-0001',rid,1,2000,auth)
            i=canary_items(m,1,0)[0];req=i['request'];a,b,c,e=self.mocks('valid')
            response=PilotAPI().request('/chat/completions',req)
            aid=ledger.claim_stage('batch-0001',rid,i['pair'],req,money(.003))
            r={'request':req,'request_hash':digest(req),'prompt_hash':digest(req['messages']),
               'result':validate(i,response),'response':response,'item':{k:v for k,v in i.items() if k!='request'}}
            ledger.settle(aid,'valid',r,response);ledger.close()
            with a,b,c,e:
                summary=run_batch(m,1,d,auth,validate,10,1,1)
            self.assertEqual(PilotAPI.calls,11) # seeded1 + remaining9 + freshQC1
            self.assertEqual(summary['valid']['canary'],3)
