"""Retrieve a bounded set of grounded rules from all archived site articles."""
import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'site_material' / 'knowledge'
STOP = set('image images prompt with from this that which have will into when only than should text called guide wiki'.split())

def words(text):
    return [w for w in re.findall(r'[a-z]{3,}', text.lower()) if w not in STOP]

def guidance(prompt, directory=ROOT, budget=1400):
    entries=[]
    for path in sorted(directory.glob('*.json')):
        item=json.loads(path.read_text(encoding='utf-8'))
        for rule in item.get('rules',[]):
            entries.append((item['title'], rule['rule'], Counter(words(item['title']+' '+rule['rule']))))
    if not entries:
        return ''
    query=set(words(prompt))
    frequency=Counter(w for _,_,terms in entries for w in terms)
    ranked=[]
    for title, rule, terms in entries:
        score=sum(math.log(1+len(entries)/(1+frequency[w]))*min(terms[w],2) for w in query if w in terms)
        if score:
            ranked.append((score,title,rule))
    selected=[]
    titles=set()
    for _,title,rule in sorted(ranked, reverse=True):
        line=f'- {title}: {rule}'
        if title in titles or len('\n'.join(selected+[line]))>budget:
            continue
        selected.append(line)
        titles.add(title)
        if len(selected)==4:
            break
    return ('\nSITE WIKI GUIDANCE (conditional, apply only when relevant):\n'+'\n'.join(selected)) if selected else ''
