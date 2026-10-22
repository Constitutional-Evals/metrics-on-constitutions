import copy,json,math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from constitution_distance.granite_pilot import run_pilot
from constitution_distance.api import APIError
from constitution_distance.storage import BudgetError
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from final_granite_pilot import request,validate,variants

class FakeAPI:
 calls=0;mode='valid'
 def __init__(self,*args,**kw):pass
 def request(self,path,payload):
  type(self).calls+=1;n=type(self).calls
  if self.mode=='retry' and n==1 or self.mode=='fail':raise APIError(429,True)
  p=.7 if self.mode=='drift' and n>1 else .5
  r={'model':payload['model'],'provider':'Cloudflare','_http_status':200,'usage':{'prompt_tokens':10,'completion_tokens':1,'total_tokens':11,'cost':.00003},'choices':[{'message':{'content':'0'},'logprobs':{'content':[{'token':'0','logprob':math.log(1-p),'top_logprobs':[{'token':'0','logprob':math.log(1-p),'bytes':[48]},{'token':'1','logprob':math.log(p),'bytes':[49]}]}]}}]}
  if self.mode=='nonlabel':
   ch=r['choices'][0];ch['message']['content']='2';ch['logprobs']['content'][0]['token']='2';ch['logprobs']['content'][0]['logprob']=-10.
   for e in ch['logprobs']['content'][0]['top_logprobs']:e['logprob']=math.log(.4995)
  if self.mode=='invalid':r['choices'][0]['logprobs']=None
  return r

META={'endpoint':{'provider_name':'Cloudflare','context_length':131000}}
class GraniteRunnerTests(unittest.TestCase):
 def spec(self):
  req=request([{'role':'user','content':'0 or1'}]);return {'test':True,'items':[{'id':'pair','replica':k,'request':copy.deepcopy(req),'swapped':False} for k in [0,1]]}
 def runfake(self,mode='valid',budget=.75):
  FakeAPI.calls=0;FakeAPI.mode=mode
  return patch('constitution_distance.granite_pilot.API',FakeAPI),patch('constitution_distance.granite_pilot.metadata',return_value=META),patch('constitution_distance.granite_pilot.time.sleep')
 def test_valid_resume_no_recomputation(self):
  with tempfile.TemporaryDirectory() as d:
   a,b,c=self.runfake()
   with a,b,c:
    r=run_pilot(self.spec(),validate,d,.75,workers=1);self.assertEqual(FakeAPI.calls,2)
    s=run_pilot(self.spec(),validate,d,.75,workers=1);self.assertEqual(FakeAPI.calls,2);self.assertEqual(r['run_id'],s['run_id'])
 def test_retry_is_reserved_and_billed_conservatively(self):
  with tempfile.TemporaryDirectory() as d:
   a,b,c=self.runfake('retry')
   with a,b,c:
    r=run_pilot(self.spec(),validate,d,.75,workers=1);self.assertEqual(FakeAPI.calls,3);self.assertGreater(r['budget']['conservative_spending_usd'],r['budget']['actual_spending_usd'])
 def test_invalid_and_repeat_failure_stop_before_batch(self):
  for mode,n in [('invalid',1),('fail',2),('drift',2)]:
   with tempfile.TemporaryDirectory() as d:
    a,b,c=self.runfake(mode)
    with a,b,c:
     with self.assertRaises(ValueError):run_pilot(self.spec(),validate,d,.75,workers=1)
     self.assertEqual(FakeAPI.calls,n)
     self.assertTrue(list(Path(d).glob('*/STOP.json')))
 def test_budget_blocks_dispatch(self):
  with tempfile.TemporaryDirectory() as d:
   a,b,c=self.runfake()
   with a,b,c:
    with self.assertRaises(BudgetError):run_pilot(self.spec(),validate,d,.001,workers=1)
    self.assertEqual(FakeAPI.calls,0)

class FactorialMetricsTests(unittest.TestCase):
 def test_average_distance_is_not_distance_of_averages(self):
  from constitution_distance.pilot_metrics import factorial_distances
  r=factorial_distances([[[0.],[1.]],[[1.],[0.]],[[0.],[1.]],[[1.],[0.]]])
  self.assertEqual(r['counterbalanced_sum_l1'][0][1],0)
  self.assertEqual(r['average_condition_distance_not_primary'][0][1],1)
 def test_factorial_contrasts_and_std(self):
  from constitution_distance.pilot_metrics import factorial_cell
  r=factorial_cell([.1,.3,.4,.6]);self.assertAlmostEqual(r['label_effect'],.2);self.assertAlmostEqual(r['order_effect'],.3);self.assertAlmostEqual(r['interaction'],0);self.assertAlmostEqual(r['counterbalanced'],.35)

class AmendmentTests(unittest.TestCase):
 spec=GraniteRunnerTests.spec
 runfake=GraniteRunnerTests.runfake
 def test_authorized_one_attempt_gate_does_not_retry_transient_failure(self):
  with tempfile.TemporaryDirectory() as d:
   a,b,c=self.runfake('retry');spec=self.spec();spec['items'][0]['maximum_attempts']=1
   with a,b,c:
    with self.assertRaises(ValueError):run_pilot(spec,validate,d,.75,workers=1)
    self.assertEqual(FakeAPI.calls,1)
    self.assertTrue(list(Path(d).glob('*/STOP.json')))
 def test_exact_record_import_does_not_recompute_or_rebill(self):
  with tempfile.TemporaryDirectory() as d:
   a,b,c=self.runfake()
   with a,b,c:
    first=run_pilot(self.spec(),validate,d,.75,workers=1)
    records=[json.loads(l) for l in (Path(first['out'])/'responses.jsonl').read_text().splitlines()]
    second=run_pilot({**self.spec(),'amended':True},validate,d,.75,workers=1,adopt_records=records)
    self.assertEqual(FakeAPI.calls,2);self.assertEqual(first['budget']['actual_spending_usd'],second['budget']['actual_spending_usd'])
 def test_nonlabel_sample_with_genuine_label_logs_is_not_a_probability_failure(self):
  with tempfile.TemporaryDirectory() as d:
   a,b,c=self.runfake('nonlabel')
   with a,b,c:
    r=run_pilot(self.spec(),validate,d,.75,workers=1)
    records=[json.loads(l) for l in (Path(r['out'])/'responses.jsonl').read_text().splitlines()]
    self.assertTrue(all(not x['result']['format_compliant'] for x in records))
    self.assertTrue(all(x['result']['p_to_do']==.5 for x in records))
