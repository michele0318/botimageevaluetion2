"""Archive the images actually linked by the collected teaching articles."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
import requests
from dataset_tools import write_json

root=Path(__file__).resolve().parent/'site_material'
destination=root/'images'
destination.mkdir(exist_ok=True)
urls=sorted({image['src'] for path in (root/'articles').glob('*.json')
             for image in json.loads(path.read_text(encoding='utf-8'))['images']})
session=requests.Session()
session.trust_env=False
manifest=[]
for i,url in enumerate(urls,1):
    if urlsplit(url).scheme not in ('https','http'):
        continue
    name=hashlib.sha256(url.encode()).hexdigest()
    path=destination/(name+'.bin')
    if not path.exists():
        response=session.get(url,timeout=(10,60))
        response.raise_for_status()
        if len(response.content)>40_000_000:
            raise ValueError('Teaching image exceeds archive limit')
        path.write_bytes(response.content)
    manifest.append({'source':url,'file':'images/'+path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    if i%20==0 or i==len(urls):
        print(f'{i}/{len(urls)} teaching images archived',flush=True)
write_json(root/'image_manifest.json',manifest)
