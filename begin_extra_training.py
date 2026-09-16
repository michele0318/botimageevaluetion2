"""Proceed after reading the new module's instructions, then inspect its UI."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    browser=pw.chromium.connect_over_cdp('http://127.0.0.1:9223')
    context=browser.contexts[0]
    page=next(p for p in context.pages if p.get_by_role('button',name='I have read the instructions, proceed to training',exact=True).count())
    page.get_by_role('button',name='I have read the instructions, proceed to training',exact=True).click()
    page.wait_for_timeout(2000)
    data=page.evaluate('''() => ({text:document.body.innerText,
        inputs:[...document.querySelectorAll('input')].map(e=>({type:e.type,name:e.name,id:e.id,value:e.value})),
        images:[...document.querySelectorAll('img')].map(e=>({id:e.id,cls:e.className,alt:e.alt,visible:!!e.getClientRects().length,src:e.currentSrc})),
        buttons:[...document.querySelectorAll('button')].filter(e=>e.getClientRects().length).map(e=>({text:e.innerText,id:e.id})),
        canvases:[...document.querySelectorAll('canvas')].map(e=>({id:e.id,width:e.width,height:e.height}))})''')
    Path('site_material/extra_task_dom.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    for image in data['images']: image.pop('src',None)
    print(json.dumps(data,ensure_ascii=True))
