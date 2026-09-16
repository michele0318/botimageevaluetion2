import json
from pathlib import Path
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    browser=pw.chromium.connect_over_cdp('http://127.0.0.1:9223')
    page=next(p for p in browser.contexts[0].pages if p.locator('#img2').count())
    data=page.evaluate('''() => ({
        inputs:[...document.querySelectorAll('input')].map(e=>({type:e.type,name:e.name,id:e.id,value:e.value,checked:e.checked})),
        images:[...document.querySelectorAll('img')].filter(e=>e.getClientRects().length).map(e=>({id:e.id,cls:e.className,alt:e.alt,src:e.currentSrc,parent:e.parentElement.outerHTML})),
        ids:[...document.querySelectorAll('[id]')].filter(e=>e.getClientRects().length).map(e=>({id:e.id,tag:e.tagName,cls:e.className,text:e.innerText?.slice(0,140)}))})''')
    Path('site_material/extra_ui.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    for image in data['images']:
        image.pop('src'); image.pop('parent')
    print(json.dumps(data,ensure_ascii=True))
