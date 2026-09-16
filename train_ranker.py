"""Experimental LOCAL ImageReward scoring-head adaptation, never submits tasks.

Only verified preference labels train correction weights. Wiki captions are
not preference labels. Grouped train-only CV selects regularization. The existing
small, repeatedly inspected test set is exploratory, not a certification.
"""
import os
os.environ.setdefault('HF_HOME', r'D:\Ollama\hf-cache')
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
import argparse
import hashlib
import json
from pathlib import Path
import time
import torch
from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'ranker'
VERSION = 'imagereward-encoder768-full-prompt-v2'

def verified():
    items = []
    for p in sorted((ROOT / 'examples').glob('*/example.json')):
        r = json.loads(p.read_text(encoding='utf-8'))
        if r.get('correct_choice') in ('1', '2') and r.get('verification', '').strip() and not r.get('review_required'):
            items.append((p, r))
    groups = {}
    for _, r in items:
        group = r['image_group']
        if group in groups and groups[group] != r['split']:
            raise ValueError('Same image group appears in train and test')
        groups[group] = r['split']
    return items

def fingerprint(items):
    records = []
    for p, r in items:
        records.append([r['id'], r['prompt'], r['correct_choice'], r['verification'], r['split'], r['image_group'],
                        [hashlib.sha256((p.parent / f'image_{i}.png').read_bytes()).hexdigest() for i in (1, 2)]])
    return hashlib.sha256(json.dumps([VERSION, records], sort_keys=True).encode()).hexdigest()

def load_model():
    import ImageReward as RM
    checkpoint=Path(r'D:\Ollama\ImageReward\ImageReward.pt')
    config=checkpoint.with_name('med_config.json')
    model = RM.load(str(checkpoint) if checkpoint.exists() else 'ImageReward-v1.0',
                    device='cuda' if torch.cuda.is_available() else 'cpu',
                    download_root=str(checkpoint.parent), med_config=str(config) if config.exists() else None)
    model.eval().requires_grad_(False)
    return model

@torch.inference_mode()
def features(model, prompt, images):
    """Use every prompt token, in original order, rather than truncate at 35.

    ImageReward was trained with short text. Averaging chunk-conditioned scores
    is an experimental extension; it cannot represent all cross-chunk relations.
    The first chunk score is retained as the published truncation baseline.
    """
    tokens = model.blip.tokenizer(prompt, add_special_tokens=False)['input_ids']
    chunks = [tokens[i:i+33] for i in range(0, max(1, len(tokens)), 33)]
    rows, original = [], []
    for image in images:
        pixels = model.preprocess(Image.open(image).convert('RGB')).unsqueeze(0).to(model.device)
        visual = model.blip.visual_encoder(pixels)
        attention = torch.ones(visual.shape[:-1], dtype=torch.long, device=model.device)
        partial = []
        for chunk in chunks:
            ids = torch.tensor([[model.blip.tokenizer.cls_token_id, *chunk,
                                 model.blip.tokenizer.sep_token_id]], device=model.device)
            result = model.blip.text_encoder(ids, attention_mask=torch.ones_like(ids),
                        encoder_hidden_states=visual, encoder_attention_mask=attention, return_dict=True)
            hidden = result.last_hidden_state[:, 0, :].float()
            # The pretrained penultimate MLP features collapse to rank one.
            # Retain the encoder representation so adaptation can learn NEW
            # visual criteria rather than merely rescale/invert one score.
            partial.append(hidden.squeeze(0))
        partial = torch.stack(partial)
        rows.append(partial.mean(0).cpu())
        original.append(((model.mlp(partial[0])-model.mean)/model.std).item())
    rows = torch.stack(rows)
    base = ((model.mlp(rows.to(model.device))-model.mean)/model.std).flatten().cpu()
    return rows, base, original, len(tokens), len(chunks)

def extract(items):
    OUT.mkdir(exist_ok=True)
    cache = OUT / 'features.pt'
    digest = fingerprint(items)
    if cache.exists():
        saved = torch.load(cache, weights_only=True)
        if saved['fingerprint'] == digest:
            return saved
    model = load_model()
    rows = []
    for n, (path, record) in enumerate(items, 1):
        start = time.monotonic()
        f, base, original, ntokens, nchunks = features(model, record['prompt'],
                                      [path.parent / f'image_{i}.png' for i in (1, 2)])
        rows.append({'id': record['id'], 'group': record['image_group'], 'split': record['split'],
                     'choice': int(record['correct_choice']), 'features': f, 'base': base,
                     'original': original, 'prompt_tokens': ntokens, 'chunks': nchunks,
                     'seconds': time.monotonic()-start})
        print(f'Feature {n}/{len(items)}: {nchunks} prompt chunks, {time.monotonic()-start:.1f}s', flush=True)
    saved = {'fingerprint': digest, 'version': VERSION, 'rows': rows}
    torch.save(saved, cache)
    del model
    if torch.cuda.is_available(): torch.cuda.empty_cache()
    return saved

def tensors(rows):
    x = torch.stack([r['features'][0]-r['features'][1] for r in rows]).double()
    base = torch.tensor([float(r['base'][0]-r['base'][1]) for r in rows], dtype=torch.float64)
    y = torch.tensor([1. if r['choice']==1 else -1. for r in rows], dtype=torch.float64)
    return x, base, y

def fit(rows, strength):
    x, base, y = tensors(rows)
    scale = x.square().mean(0).sqrt().clamp_min(1e-6)
    w = torch.zeros(x.shape[1], dtype=torch.float64, requires_grad=True)
    optimizer = torch.optim.LBFGS([w], lr=1, max_iter=100, line_search_fn='strong_wolfe')
    def closure():
        optimizer.zero_grad()
        loss = torch.nn.functional.softplus(-y*(base+(x/scale)@w)).mean()+strength*w.square().sum()/2
        loss.backward()
        return loss
    optimizer.step(closure)
    return w.detach(), scale

def assess(rows, w, scale):
    x, base, y = tensors(rows)
    margins = base + (x/scale)@w
    return {'correct': int((margins*y>0).sum()), 'count': len(rows),
            'loss': float(torch.nn.functional.softplus(-y*margins).mean()),
            'predictions': [1 if m>0 else 2 for m in margins.tolist()]}

def train(saved):
    rows = saved['rows']
    training = [r for r in rows if r['split']=='train']
    test = [r for r in rows if r['split']=='test']
    if len(training)<10 or not test: raise ValueError('Insufficient verified data')
    groups = sorted({r['group'] for r in training})
    folds = {group: i%5 for i, group in enumerate(groups)}
    scores = []
    for strength in (.01, .1, 1., 10., 100.):
        correct = count = 0
        loss = 0.
        for fold in range(5):
            fit_rows = [r for r in training if folds[r['group']]!=fold]
            val_rows = [r for r in training if folds[r['group']]==fold]
            w, scale = fit(fit_rows, strength)
            result = assess(val_rows, w, scale)
            correct += result['correct']; count += result['count']; loss += result['loss']*result['count']
        scores.append({'regularization': strength, 'correct': correct, 'count': count, 'loss': loss/count})
    selected = min(scores, key=lambda r: (-r['correct'], r['loss']))
    w, scale = fit(training, selected['regularization'])
    torch.save({'weights': w, 'scale': scale, 'fingerprint': saved['fingerprint'], 'version': VERSION,
                'regularization': selected['regularization'], 'train_ids': [r['id'] for r in training]}, OUT/'adapter.pt')
    report = {'version': VERSION, 'fingerprint': saved['fingerprint'], 'weights_trained': w.numel(),
              'trained_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
              'model_source': json.loads(Path(r'D:\Ollama\ImageReward\provenance.json').read_text())
                    if Path(r'D:\Ollama\ImageReward\provenance.json').exists() else 'ImageReward-v1.0',
              'training_count': len(training), 'test_count': len(test), 'train_only_cv': scores,
              'selected_regularization': selected['regularization'],
              'train_adapted': assess(training, w, scale), 'test_adapted': assess(test, w, scale),
              'test_full_prompt_baseline': assess(test, torch.zeros_like(w), scale),
              'test_original_35_token_baseline': sum((1 if r['original'][0]>r['original'][1] else 2)==r['choice'] for r in test),
              'test_ids': [r['id'] for r in test], 'max_prompt_tokens': max(r['prompt_tokens'] for r in rows),
              'median_extraction_seconds': sorted(r['seconds'] for r in rows)[len(rows)//2],
              'limitations': ['Small repeatedly inspected holdout; exploratory only.',
                 'No Llama/Qwen weights changed. Only ImageReward correction head.',
                 'Wiki figure captions are not preference labels and were not used to train this head.',
                 'Prompt chunks preserve all tokens but may lose cross-chunk relationships.',
                 '224px center-cropped ImageReward input can miss edge details and small text.'],
              'automatic_deployment': False}
    (OUT/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('training_count','test_count','test_adapted','test_full_prompt_baseline','test_original_35_token_baseline')}, indent=2))

if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train-only', action='store_true')
    args = parser.parse_args()
    torch.set_num_threads(4)
    items = verified()
    if args.train_only:
        saved = torch.load(OUT/'features.pt', weights_only=True)
        if saved['fingerprint'] != fingerprint(items): raise ValueError('Stale feature cache')
    else:
        saved = extract(items)
    train(saved)
