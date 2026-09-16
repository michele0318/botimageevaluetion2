"""Download public ImageReward weights with their Hugging Face SHA256."""
import hashlib
import json
from pathlib import Path
import requests

root=Path(r'D:\Ollama\ImageReward')
root.mkdir(parents=True,exist_ok=True)
repo='zai-org/ImageReward'
response=requests.get(f'https://huggingface.co/api/models/{repo}',params={'blobs':'true'},timeout=30)
response.raise_for_status()
info=response.json()
revision=info['sha']
for name in ('med_config.json','ImageReward.pt'):
    entry=next(x for x in info['siblings'] if x['rfilename']==name)
    expected=entry.get('lfs',{}).get('sha256')
    target=root/name
    if target.exists() and (not expected or hashlib.file_digest(target.open('rb'),'sha256').hexdigest()==expected):
        print(f'{name}: already verified',flush=True)
        continue
    partial=target.with_suffix(target.suffix+'.partial')
    with requests.get(f'https://huggingface.co/{repo}/resolve/{revision}/{name}',stream=True,timeout=(30,120)) as stream:
        stream.raise_for_status()
        size=0; next_report=250_000_000
        with partial.open('wb') as handle:
            for chunk in stream.iter_content(1024*1024):
                handle.write(chunk); size+=len(chunk)
                if size>=next_report:
                    print(f'{name}: {size//1_000_000} MB',flush=True); next_report+=250_000_000
    with partial.open('rb') as handle:
        actual=hashlib.file_digest(handle,'sha256').hexdigest()
    if expected and actual!=expected: raise ValueError(f'Checksum mismatch: {name}')
    partial.replace(target)
    print(f'{name}: downloaded and verified',flush=True)
(root/'provenance.json').write_text(json.dumps({'repository':repo,'revision':revision},indent=2))
