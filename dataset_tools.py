"""Local collection and evaluation. This module does not train model weights."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import time

from PIL import Image, ImageOps, ImageChops, ImageStat

DATA = Path(__file__).resolve().parent / 'examples'


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def normalize_images(images):
    normalized = []
    for raw in images:
        buffer = io.BytesIO()
        ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert('RGB').save(buffer, format='PNG')
        normalized.append(buffer.getvalue())
    return normalized


def same_pixels(first, second):
    if first == second:
        return True
    a, b = Image.open(io.BytesIO(first)).convert('RGB'), Image.open(io.BytesIO(second)).convert('RGB')
    if a.size != b.size:
        return False
    difference = ImageChops.difference(a, b)
    # Browser screenshots can change a few least-significant channel values.
    return max(v[1] for v in difference.getextrema()) <= 2 and max(ImageStat.Stat(difference).mean) <= .001


def capture(prompt, images, directory=DATA):
    normalized = normalize_images(images)
    if not prompt.strip() or len(normalized) != 2:
        raise ValueError('Servono un prompt e due immagini.')
    hashes = [hashlib.sha256(raw).hexdigest() for raw in normalized]
    identity = hashlib.sha256(json.dumps([prompt, hashes]).encode()).hexdigest()
    # Keep even reversed pairs and alternate prompts for identical images in one split.
    group = hashlib.sha256(''.join(sorted(hashes)).encode()).hexdigest()
    for old_path, old in records(directory):
        if old['prompt'].strip() != prompt.strip():
            continue
        old_images = [(old_path.parent / f'image_{i}.png').read_bytes() for i in (1, 2)]
        if all(same_pixels(a, b) for a, b in zip(normalized, old_images)):
            return old_path
        if all(same_pixels(a, b) for a, b in zip(normalized, old_images[::-1])):
            group = old['image_group']
    folder = directory / identity
    folder.mkdir(parents=True, exist_ok=True)
    record = folder / 'example.json'
    if not record.exists():
        for index, raw in enumerate(normalized, 1):
            (folder / f'image_{index}.png').write_bytes(raw)
        write_json(record, {'id': identity, 'prompt': prompt, 'correct_choice': None,
                            'verification': '', 'split': 'test' if int(group[:8], 16) % 5 == 0 else 'train',
                            'image_group': group, 'image_hashes': hashes})
    return record


def records(directory=DATA):
    return [(path, json.loads(path.read_text(encoding='utf-8')))
            for path in sorted(directory.glob('*/example.json'))]


def corrected_answer(prompt, images, directory=DATA):
    """Read verified corrections afresh; exact prompt/pixels only, including reversed order."""
    normalized = normalize_images(images)
    hashes = [hashlib.sha256(raw).hexdigest() for raw in normalized]
    choices = set()
    for path, record in records(directory):
        if record['prompt'].strip() != prompt.strip() or record['correct_choice'] not in ('1', '2') or not record['verification'].strip():
            continue
        saved = record.get('image_hashes')
        if not saved:
            saved = [hashlib.sha256((path.parent / f'image_{i}.png').read_bytes()).hexdigest() for i in (1, 2)]
        if hashes == saved:
            choices.add(record['correct_choice'])
        elif hashes == saved[::-1]:
            choices.add(str(3 - int(record['correct_choice'])))
        else:
            old_images = [(path.parent / f'image_{i}.png').read_bytes() for i in (1, 2)]
            if all(same_pixels(a, b) for a, b in zip(normalized, old_images)):
                choices.add(record['correct_choice'])
            elif all(same_pixels(a, b) for a, b in zip(normalized, old_images[::-1])):
                choices.add(str(3 - int(record['correct_choice'])))
    if len(choices) > 1:
        raise ValueError('Correzioni umane in conflitto per la stessa coppia: verificare gli esempi prima di inviare.')
    return next(iter(choices), None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('status')
    commands.add_parser('export')
    label = commands.add_parser('label')
    label.add_argument('id')
    label.add_argument('choice', choices=['1', '2'])
    label.add_argument('--verification', required=True, help='Fonte o motivo della risposta corretta verificata')
    evaluate = commands.add_parser('evaluate')
    evaluate.add_argument('--split', choices=['train', 'test'], default='test')
    evaluate.add_argument('--model', help='Modello Ollama locale da confrontare; non cambia il modello del bot')
    evaluate.add_argument('--strategy', choices=['direct', 'evidence'], default='direct')
    evaluate.add_argument('--without-site-knowledge', action='store_true')
    args = parser.parse_args()
    items = records()
    if args.command == 'status':
        verified = [r for _, r in items if r['correct_choice'] in ('1', '2') and r['verification'].strip()]
        print(f'Esempi: {len(items)}. Verificati: {len(verified)}. Test verificati: {sum(r["split"] == "test" for r in verified)}.')
        first = [r['attempts'][0] for _, r in items if r.get('attempts') and r['attempts'][0].get('accepted') is not None]
        print(f'Prime risposte con esito verificato dal sito: {sum(a["accepted"] for a in first)}/{len(first)} corrette.')
        print(f'Criteri generalizzabili salvati: {sum(bool(r.get("lesson")) for _, r in items)}.')
        print('Nessun addestramento dei pesi eseguito da questo strumento.')
        return
    if args.command == 'label':
        matches = [(p, r) for p, r in items if r['id'] == args.id]
        if len(matches) != 1 or not args.verification.strip():
            parser.error('ID esatto e verifica non vuota richiesti.')
        path, record = matches[0]
        record.update(correct_choice=args.choice, verification=args.verification.strip())
        write_json(path, record)
        print('Risposta verificata salvata. I pesi del modello non sono stati modificati.')
        return
    if args.command == 'export':
        verified = [(p, r) for p, r in items if r['correct_choice'] in ('1', '2') and r['verification'].strip()]
        if not verified:
            parser.error('Nessun esempio verificato da esportare. Non vengono inventate risposte corrette.')
        import run_task_bot as bot
        destination = DATA / ('export-' + time.strftime('%Y%m%d-%H%M%S'))
        (destination / 'images').mkdir(parents=True)
        splits = {'train': [], 'test': []}
        for path, record in verified:
            name = 'images/' + record['id'] + '.png'
            images = [(path.parent / f'image_{i}.png').read_bytes() for i in (1, 2)]
            (destination / name).write_bytes(bot.comparison_image(images))
            splits[record['split']].append({'image': name, 'conversations': [
                {'from': 'human', 'value': '<image>\n' + bot.SYSTEM + '\nSOURCE CONTEXT / PROMPT:\n' + record['prompt']},
                {'from': 'gpt', 'value': 'Image ' + record['correct_choice']}]})
        for split, examples in splits.items():
            write_json(destination / (split + '.json'), examples)
        print(f'Esportazione QwenVL: {destination}. Train: {len(splits["train"])}. Test: {len(splits["test"])}.')
        print('Solo preparazione dei dati: nessun addestramento dei pesi eseguito.')
        return
    selected = [(p, r) for p, r in items if r['split'] == args.split
                and r['correct_choice'] in ('1', '2') and r['verification'].strip()]
    if not selected:
        parser.error('Nessun esempio verificato nella suddivisione richiesta: accuratezza non misurabile.')
    import run_task_bot as bot
    import gemini_provider
    provider = gemini_provider.config()
    if args.model and provider.get('provider') == 'gemini':
        parser.error('--model riguarda Ollama. Per Gemini viene usato il modello configurato.')
    if args.model:
        bot.MODEL = args.model
    bot.ollama_check()
    bot.warmup()
    results = []
    for path, record in selected:
        start = time.monotonic()
        metrics = {}
        try:
            # Hold-out accuracy must not be inflated by looking up its saved answer.
            references=[{'label':r['label'],'data':(path.parent/r['file']).read_bytes()} for r in record.get('reference_images',[])]
            choice = bot.decide(record['prompt'], [(path.parent / f'image_{i}.png').read_bytes() for i in (1, 2)], use_corrections=False, lesson_split='train', metrics=metrics, strategy=args.strategy,
                                contextual_hints=record.get('contextual_hints',''), references=references,
                                use_site_knowledge=not args.without_site_knowledge)
            error = None
        except Exception as failure:
            choice, error = None, type(failure).__name__
        results.append({'id': record['id'], 'expected': record['correct_choice'], 'predicted': choice,
                        'correct': choice == record['correct_choice'], 'error': error,
                        'seconds': round(time.monotonic() - start, 2), 'usage': metrics})
    report = {'provider': provider.get('provider', 'ollama'), 'model': provider.get('model', bot.MODEL), 'context': bot.CONTEXT, 'split': args.split, 'strategy': args.strategy,
              'site_knowledge': not args.without_site_knowledge,
              'system_hash': hashlib.sha256(bot.SYSTEM.encode()).hexdigest(), 'correction_lookup': False,
              'count': len(results), 'correct': sum(r['correct'] for r in results), 'results': results,
              'note': 'Gli errori sono conteggiati come risposte non corrette. Nessuna garanzia sui task futuri.'}
    report_path = DATA / ('report-' + time.strftime('%Y%m%d-%H%M%S') + '.json')
    write_json(report_path, report)
    print(f'Corrette: {report["correct"]}/{len(results)}. Rapporto: {report_path}')


if __name__ == '__main__':
    main()
