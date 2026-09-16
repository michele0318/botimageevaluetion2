"""Open the other visible comparison module; read its instructions before training."""
import json
import re
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
import run_task_bot as bot

with sync_playwright() as pw:
    browser=pw.chromium.connect_over_cdp('http://127.0.0.1:9223')
    context=browser.contexts[0]
    page=context.pages[0]
    title=page.get_by_text("Which image is a better response to the user's request?",exact=True)
    title.wait_for(timeout=30000)
    card=title
    for _ in range(8):
        card=card.locator('..')
        buttons=card.get_by_role('button',name=re.compile(r'^(Continue|Start tasks)$'))
        if buttons.count()==1:
            buttons.click(); break
        if buttons.count()>1: raise RuntimeError('Ambiguous module button')
    else: raise RuntimeError('No module button')
    deadline=time.monotonic()+90
    opened=False
    while time.monotonic()<deadline:
        candidates=[f.get_by_role('link',name='Open External Platform',exact=True)
                    for p in context.pages for f in p.frames]
        link=next((link for link in candidates if link.count()==1 and link.is_visible()),None)
        if link is not None:
            with context.expect_page(timeout=30000) as event:
                link.click()
            external=event.value
            opened=True; break
        page.wait_for_timeout(500)
    if not opened: raise RuntimeError('External training link not available')
    external.wait_for_load_state('domcontentloaded',timeout=60000)
    external.wait_for_timeout(2000)
    entries=[]
    for p in context.pages:
        for frame in p.frames:
            data=frame.evaluate('''() => ({text:document.body?.innerText || '',
                buttons:[...document.querySelectorAll('button,a')].filter(e=>e.getClientRects().length)
                 .map(e=>({text:e.innerText.trim(),id:e.id})).filter(e=>e.text)})''')
            entries.append(data)
    Path('site_material/extra_training_intro.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(entries[-1],ensure_ascii=True))
