"""Deterministic topic sampling and conservative action-mapping audit.

Lexical screening is not a semantic proof. Flagged alternatives are retained
verbatim and are never automatically repaired or silently dropped.
"""
from collections import Counter, defaultdict
import json
from pathlib import Path
import random
import re

from .core import digest, load_scenarios


def normalize(text):
    return re.sub(r'[^\w\s]', '', text.casefold()).strip()


def action_issues(s):
    one, zero = normalize(s['action1']), normalize(s['action0'])
    issues = []
    if one == zero:
        issues.append('identical_action_descriptions')
    neg = r"^(?:not to |not |do not |dont |refrain from |avoid |stop )"
    if re.match(neg, one) and re.match(neg, zero):
        issues.append('both_descriptions_start_with_negation_review')
    # A strict match is only a useful screen; paraphrases legitimately fail it.
    if re.sub(neg, '', zero) != one:
        issues.append('not_a_literal_negation_semantic_review_needed')
    if min(len(one.split()), len(zero.split())) <= 1:
        issues.append('short_action_description_review')
    if re.search(r'\b(?:or|versus|vs)\b', one + ' ' + zero):
        issues.append('action_description_contains_alternatives_review')
    return issues


def select_scenarios(scenarios, size, seed):
    groups = defaultdict(list)
    for s in sorted(scenarios, key=lambda s: int(s['id'])):
        if not s.get('topic_group'):
            raise ValueError("Topic group is required for stratified selection")
        groups[s['topic_group']].append(s)
    if size < len(groups) or size > len(scenarios):
        raise ValueError("Pilot size must cover all topic groups and fit the dataset")
    rng = random.Random(seed)
    selected = [rng.choice(groups[g]) for g in sorted(groups)]
    picked = {s['id'] for s in selected}
    # Additional groups are chosen in randomized cycles, at most one per cycle.
    while len(selected) < size:
        order = sorted(groups); rng.shuffle(order)
        for g in order:
            candidates = [s for s in groups[g] if s['id'] not in picked]
            if candidates and len(selected) < size:
                s = rng.choice(candidates); selected.append(s); picked.add(s['id'])
    rng.shuffle(selected)
    return selected


def prepare(args):
    scenarios = load_scenarios(args.scenarios)
    selected = select_scenarios(scenarios, args.size, args.seed)
    out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    audits = [{'id': s['id'], 'topic_group': s.get('topic_group'), 'text': s['text'],
               'action1': s['action1'], 'action0': s['action0'], 'issues': action_issues(s)}
              for s in scenarios]
    manifest = {'seed': args.seed, 'algorithm': 'sorted groups; one seeded choice/group; randomized extra-group cycles; final seeded shuffle',
        'source_sha256': digest(scenarios), 'selected_ids': [s['id'] for s in selected],
        'selected_sha256': digest(selected), 'topic_counts': dict(Counter(s['topic_group'] for s in selected)),
        'source_topic_counts': dict(Counter(s['topic_group'] for s in scenarios)),
        'flagged_dilemmas': sum(bool(a['issues']) for a in audits),
        'issue_counts': dict(Counter(i for a in audits for i in a['issues'])),
        'selection_did_not_exclude_flagged_actions': True,
        'audit_limit': 'Lexical screening only; unflagged is not proof of semantic complementarity.'}
    for name, value in [('selection.json', manifest), ('action-audit.json', audits)]:
        (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
    (out / 'scenarios.jsonl').write_text(''.join(json.dumps(s, ensure_ascii=False)+'\n' for s in selected))
    print(json.dumps(manifest, indent=2))
