"""Optional cloud inference. No retries after a possibly billed request."""
import base64
from contextlib import contextmanager
import datetime as dt
import io
import json
import math
import os
import re
import sqlite3
import time
from PIL import Image, ImageOps
import requests

DEFAULT_MODEL = 'gemini-3.8-flash'
HTTP = requests.Session()
HTTP.trust_env = False


def config():
    import run_task_bot as bot
    path = bot.STATE / 'ai-provider.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'provider': 'ollama'}


def enabled():
    return config().get('provider') == 'gemini'


def key():
    import run_task_bot as bot
    value = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    path = bot.STATE / 'gemini-key.bin'
    if not value and path.exists():
        value = bot.protect_session(path.read_bytes(), decrypt=True).decode()
    if not value:
        raise bot.Stop('Chiave Gemini mancante. Esegui configure_gemini.py sul PC.')
    return value


def rates(model):
    import run_task_bot as bot
    if model != DEFAULT_MODEL or dt.date.today() > dt.date(2027, 1, 31):
        raise bot.Stop('Verificare e aggiornare le tariffe Gemini prima di usare questo modello/data.')
    return (.75, 3.75) if dt.date.today().year == 2026 else (1.5, 7.5)


@contextmanager
def ledger():
    import run_task_bot as bot
    bot.STATE.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(bot.STATE / 'gemini-usage.sqlite', timeout=10)
    db.execute('CREATE TABLE IF NOT EXISTS calls (id INTEGER PRIMARY KEY, day TEXT, usd REAL, status TEXT)')
    db.commit()
    try:
        with db:
            yield db
    finally:
        db.close()


def reserve(amount, cap):
    import run_task_bot as bot
    if not math.isfinite(cap) or cap <= 0:
        raise bot.Stop('Limite giornaliero Gemini non valido.')
    with ledger() as db:
        db.execute('BEGIN IMMEDIATE')
        day = dt.date.today().isoformat()
        spent = db.execute('SELECT COALESCE(SUM(usd),0) FROM calls WHERE day=?', (day,)).fetchone()[0]
        if spent + amount > cap:
            raise bot.Stop('Limite giornaliero stimato Gemini raggiunto; nessun invio.')
        return db.execute('INSERT INTO calls(day,usd,status) VALUES(?,?,?)', (day, amount, 'reserved')).lastrowid


def post(model, method, body, secret):
    import run_task_bot as bot
    try:
        response = HTTP.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:{method}',
                             headers={'x-goog-api-key': secret}, json=body, timeout=(10, 180))
    except requests.RequestException:
        raise bot.Stop('Gemini non raggiungibile. Nessun tentativo automatico aggiuntivo.') from None
    if response.status_code != 200:
        raise bot.Stop(f'Gemini HTTP {response.status_code}; controllare quota, modello e chiave. Nessun invio.')
    return response.json()


def generate(system, content, images=(), references=(), metrics=None, choice=False):
    import run_task_bot as bot
    settings = config()
    model = settings.get('model', DEFAULT_MODEL)
    if not re.fullmatch(r'gemini-[a-z0-9.-]+', model):
        raise bot.Stop('Nome modello Gemini non valido.')
    input_rate, output_rate = rates(model)
    secret = key()
    parts = [{'text': content}]
    labeled = [(f'CANDIDATE {i}', data) for i, data in enumerate(images, 1)]
    labeled += [(f'REFERENCE R{i} (not a candidate): {ref["label"]}', ref['data']) for i, ref in enumerate(references, 1)]
    for label, data in labeled:
        picture = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert('RGB')
        buffer = io.BytesIO()
        picture.save(buffer, format='PNG')
        parts.extend([{'text': label}, {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(buffer.getvalue()).decode('ascii')}}])
    generation = {'responseMimeType': 'application/json', 'maxOutputTokens': 2048,
                  'thinkingConfig': {'thinkingLevel': 'LOW'}}
    if choice:
        generation['responseSchema'] = {'type': 'OBJECT', 'properties': {'choice': {'type': 'STRING', 'enum': ['1', '2']}}, 'required': ['choice']}
    body = {'systemInstruction': {'parts': [{'text': system}]},
            'contents': [{'role': 'user', 'parts': parts}], 'generationConfig': generation}
    started = time.monotonic()
    counted = post(model, 'countTokens', {'generateContentRequest': {'model': 'models/' + model, **body}}, secret)
    tokens = counted.get('totalTokens')
    if not isinstance(tokens, int) or tokens <= 0:
        raise bot.Stop('Conteggio token Gemini non valido; inferenza annullata.')
    # Small input margin; full output allowance includes reasoning tokens.
    reservation = reserve((tokens * 1.1 * input_rate + 2048 * output_rate) / 1e6,
                          float(settings.get('daily_usd', 1)))
    result = post(model, 'generateContent', body, secret)
    usage = result.get('usageMetadata', {})
    actual = None
    if isinstance(usage.get('promptTokenCount'), int) and isinstance(usage.get('totalTokenCount'), int):
        prompt_tokens = usage['promptTokenCount']
        output_tokens = max(0, usage['totalTokenCount'] - prompt_tokens)
        actual = (prompt_tokens * input_rate + output_tokens * output_rate) / 1e6
        with ledger() as db:
            db.execute('UPDATE calls SET usd=?,status=? WHERE id=?', (actual, 'accounted', reservation))
    if metrics is not None:
        metrics.update(provider='gemini', model=model, usage=usage, estimated_usd=actual,
                       seconds=round(time.monotonic()-started, 2))
    candidates = result.get('candidates', [])
    if len(candidates) != 1 or candidates[0].get('finishReason') != 'STOP':
        raise bot.Stop('Gemini non ha completato una risposta valida; nessun invio.')
    answer = ''.join(part.get('text', '') for part in candidates[0].get('content', {}).get('parts', []) if not part.get('thought'))
    try:
        parsed = json.loads(answer)
    except ValueError:
        raise bot.Stop('JSON Gemini non valido; nessun invio.') from None
    if not isinstance(parsed, dict) or (choice and (set(parsed) != {'choice'} or parsed['choice'] not in ('1', '2'))):
        raise bot.Stop('Scelta Gemini non valida; nessun invio.')
    bot.say(f'Gemini {model}: {time.monotonic()-started:.1f} s.')
    return parsed['choice'] if choice else parsed
