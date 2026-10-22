import importlib.util,math,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'scripts/cloud_api_comparison.py';spec=importlib.util.spec_from_file_location('cloud_comparison',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def response(entries,sampled='0'):
 return {'choices':[{'message':{'content':sampled},'logprobs':{'content':[{'token':sampled,'logprob':-4.,'top_logprobs':entries}]}}]}

class CloudDistributionTests(unittest.TestCase):
 def test_full_and_conditional_probabilities_remain_distinct(self):
  r=m.extract(response([{'token':'1','logprob':-2.,'bytes':[49]},{'token':'0','logprob':-3.,'bytes':[48]}],sampled='\n'))
  self.assertAlmostEqual(r['p1_conditional'],1/(1+math.exp(-1)));self.assertAlmostEqual(r['binary_mass'],math.exp(-2)+math.exp(-3));self.assertFalse(r['format_compliant']);self.assertEqual(r['sampled_output'],'\n')
 def test_no_missing_token_or_conflicting_logprob_substitution(self):
  with self.assertRaises(ValueError):m.extract(response([{'token':'1','logprob':-2.}],sampled='\n'))
  for entries in [[{'token':'0','logprob':-2.},{'token':'1','logprob':-3.}],[{'token':'0','logprob':-4.},{'token':'1','logprob':-3.,'bytes':[48]}]]:
   with self.assertRaises(ValueError):m.extract(response(entries))
 def test_unranked_top_logprobs_extract_by_token_not_position(self):
  r=m.extract(response([{'token':'1','logprob':-.1},{'token':'0','logprob':-4.}]))
  self.assertGreater(r['p1_conditional'],.9)

 def test_sample_token_identity_is_checked_without_using_it_as_probability(self):
  r=response([{'token':'0','logprob':-4.},{'token':'1','logprob':-.1}]);r['choices'][0]['message']['content']='1'
  with self.assertRaises(ValueError):m.extract(r)
