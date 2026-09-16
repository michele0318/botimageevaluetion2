"""CPU-only tests of real optimization and split protection; no model download."""
import copy
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import torch
import train_ranker as ranker

torch.set_num_threads(2)
rows=[]
for i in range(20):
    sign=1 if i%2==0 else -1
    f=torch.zeros(2,16)
    f[0,0]=sign
    rows.append({'features':f,'base':torch.tensor([-float(sign),0.]),'choice':1 if sign==1 else 2})
w, scale=ranker.fit(rows,.01)
assert w.abs().sum()>0
assert ranker.assess(rows,w,scale)['correct']==20
assert ranker.assess(rows,torch.zeros_like(w),scale)['correct']==0
reversed_rows=[]
for row in rows:
    r=copy.deepcopy(row)
    r.update(features=r['features'].flip(0),base=r['base'].flip(0),choice=3-r['choice'])
    reversed_rows.append(r)
assert ranker.assess(reversed_rows,w,scale)['correct']==20
with tempfile.TemporaryDirectory() as temp:
    root=Path(temp)
    for i, split in enumerate(('train','test')):
        p=root/'examples'/str(i); p.mkdir(parents=True)
        (p/'example.json').write_text(json.dumps({'id':str(i),'correct_choice':'1',
                         'verification':'verified fixture','split':split,'image_group':'same'}))
    with patch.object(ranker,'ROOT',root):
        try: ranker.verified()
        except ValueError: pass
        else: raise AssertionError('Train/test leakage not rejected')
print('PASS: correction weights learn preference, reverse consistently, reject group leakage')
