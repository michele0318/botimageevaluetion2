"""Inspect available training controls through the existing saved-profile browser."""
import json
from playwright.sync_api import sync_playwright
from pathlib import Path

with sync_playwright() as pw:
    browser=pw.chromium.connect_over_cdp('http://127.0.0.1:9223')
    pages=[]
    for page in browser.contexts[0].pages:
        for frame in page.frames:
            try:
                data=frame.evaluate('''() => ({
                    text:document.body?.innerText || '',
                    buttons:[...document.querySelectorAll('button,a')].filter(e=>e.getClientRects().length)
                         .map(e=>({text:e.innerText.trim(),id:e.id})).filter(e=>e.text),
                    task:!!document.querySelector('#prompt-display')
                })''')
                pages.append(data)
                print(json.dumps({'task':data['task'],'text':data['text'][:5000],
                                  'buttons':data['buttons']},ensure_ascii=True))
            except Exception as error:
                print(type(error).__name__)
    Path('site_material/live_training_state.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf-8')
