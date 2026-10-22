"""Freeze a blocked full-experiment candidate and prove dry-run makes no API calls."""
import hashlib,io,json,re
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch
from constitution_distance.cli import parser
from constitution_distance.core import PROMPT_VERSION,digest,load_constitutions,load_scenarios,messages
from constitution_distance.runner import payload,run,write_json
from constitution_distance.api import API


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    out=Path('configs');out.mkdir(exist_ok=True)
    candidate=Path('data/scenarios-reviewed.jsonl');sidecar=candidate.with_suffix('.manifest.json')
    approval=json.loads(sidecar.read_text());ss=load_scenarios(candidate);cs=load_constitutions('data/constitutions');n=len(ss)*len(cs)
    argv=['run','--scenarios',str(candidate),'--output','runs/full-reviewed-candidate',
        '--ledger','runs/full-reviewed-budget.sqlite','--budget-usd','0','--concurrency','4',
        '--attempts','3','--max-requests',str(n+360),'--phase','full-reviewed-candidate','--dry-run']
    args=parser().parse_args(argv);buffer=io.StringIO()
    with patch.object(API,'request',side_effect=AssertionError('Dry run attempted network API access')),redirect_stdout(buffer):run(args)
    log=buffer.getvalue();assert f'{len(cs)} constitutions x {len(ss)} dilemmas' in log
    result=Path('results/methodology');result.mkdir(parents=True,exist_ok=True);(result/'full-dry-run.txt').write_text(log)
    example=payload(args,cs[0],ss[0]);settings={k:v for k,v in example.items() if k!='messages'}
    sentinel={'id':'TEMPLATE','text':'__SITUATION__','action1':'__TO_DO__','action0':'__NOT_TO_DO__'}
    template=messages({'__CONSTITUTION_JSON__':True},sentinel)
    template[0]['content']=template[0]['content'].replace('{"__CONSTITUTION_JSON__": true}','{constitution_json}')
    template[1]['content']=template[1]['content'].replace('__SITUATION__','{dilemma_situation}').replace('"__TO_DO__"','{to_do_action_as_json_string}').replace('"__NOT_TO_DO__"','{not_to_do_action_as_json_string}')
    reliability=json.loads((result/'reliability-analysis.json').read_text())
    manifest={'schema_version':1,'status':'BLOCKED_PENDING_SCENARIO_AND_METHODOLOGY_APPROVAL','ready_to_run':False,
        'full_experiment_executed':False,'approved_scenario_count':0,'approved_scenario_file_sha256':None,
        'candidate_scenario_count':len(ss),'candidate_evaluation_count':n,
        'candidate_scenario_file':str(candidate),'candidate_scenario_file_sha256':sha(candidate),
        'approval_manifest_file':str(sidecar),'approval_manifest_sha256':sha(sidecar),
        'full_original_library_count':1360,'proposed_excluded_count':len(approval['proposed_excluded_ids']),
        'pending_semantic_review_count':len(approval['pending_semantic_review_ids']),
        'constitution_count':24,'constitution_file_sha256':{str(p):sha(p) for p in sorted(Path('data/constitutions').glob('*.json'))},
        'cleaned_constitutions_sha256':digest(cs),'prompt_version':PROMPT_VERSION,
        'exact_prompt_templates':template,'template_renderer':'constitution_distance.core.messages/scenario_prompt',
        'inference_parameters':settings,'example_exact_request':example,
        'primary_probability':'P(to_do | token in {0,1}) = exp(logp1)/(exp(logp0)+exp(logp1)) in canonical mapping; stable log-space computation',
        'saved_probability_fields':['logp0','logp1','p0','p1','binary_mass','p1_conditional'],
        'summed_l1':'D(c,d)=sum over included dilemmas abs(p[c,i]-p[d,i])',
        'mean_absolute_difference':'MAD(c,d)=D(c,d)/N_included; N determined from the approved frozen scenario file',
        'candidate_mean_absolute_difference_divisor':len(ss),'final_mean_absolute_difference_divisor':None,
        'design_decision':'Canonical fixed mapping retained only as a candidate; label/order counterbalancing has not been silently adopted.',
        'execution':{'budget_default_usd':0,'currently_authorized_full_run_budget_usd':0,'proposed_budget_for_user_review_usd':25,
            'retry_attempts_per_evaluation':3,'max_dispatches_including_retries':n+360,'concurrency':4,
            'checkpoint':'SQLite WAL, synchronous FULL, unique run/constitution/dilemma/replica keys',
            'spending':'Reserve whole endpoint context and max output at provider price ceilings with 10% headroom; unknown charges remain conservatively charged',
            'resume':'Same frozen inputs, output, manifest and authoritative ledger; valid records are never recomputed; uncertain work requires reconciliation',
            'budget_lifetime':'One fixed-cap ledger across the run and all resumes; not reset per invocation'},
        'required_pre_execution_approvals':['Approve the 24 uncertain scenario dispositions and accepted automated-screening policy for the others.',
            'Choose canonical fixed mapping with limited claims or a counterbalanced/replicated redesign after the failed numerical/label-order diagnostics.',
            'Regenerate hashes and counts after all approvals; sign scenario manifest and set execution_approved=true with matching approved_file_sha256.',
            'Explicitly authorize a full-run budget; run and review dry-run before any live execution.'],
        'required_completion_qc':['Exactly 24*N unique valid main evaluations; no missing cells or duplicate pairs.',
            'Both literal label token log probabilities available; all saved probabilities finite and in [0,1].',
            'Returned model/provider match pinned identity on every response; exact prompt/configuration hashes validate.',
            'Binary mass >=0.95 or documented adjudication; no absent token replaced by zero.',
            'Summed-L1 and MAD matrices have correct dimensions, symmetry, zero diagonal, nonnegative entries and triangle inequalities.',
            'MAD divides by final approved N, not original 1360 or pilot 20.',
            'Budget and outstanding/unknown charges reconciled; all outputs reconstructed from authoritative checkpoints.',
            'Pre-registered numerical and label/order reliability acceptance policy satisfied or explicitly documented limitations approved.'],
        'diagnostic_acceptance_thresholds_proposed_not_approved':{'max_identical_request_probability_range':.02,'max_transformed_label_or_order_mean_difference':.05},
        'observed_near_half_diagnostic':next(r for r in reliability['comparisons'] if r['stratum']=='near_half'),
        'dry_run':{'network_api_calls':0,'inference_calls':0,'candidate_fingerprint':re.search(r'run ([0-9a-f]{64})',log).group(1),
                   'argv':argv,'log':str(result/'full-dry-run.txt')},
        'implementation_file_sha256':{str(p):sha(p) for p in sorted(Path('src/constitution_distance').glob('*.py'))}}
    manifest['audit_provenance_sha256']={str(p):sha(p) for p in [Path('data/audit/scenario-audit.jsonl'),Path('data/audit/human-review-queue.jsonl'),Path('results/methodology/reliability-analysis.json')]}
    projection=Path('results/methodology/candidate-cost-projection.json')
    if projection.exists():manifest['proposed_cost_projection']=json.loads(projection.read_text())
    write_json(out/'full-experiment-candidate.json',manifest)
    print(log,end='');print('Plan is blocked: zero human-approved scenarios and numerical/label-order acceptance unresolved.')

if __name__=='__main__':main()
