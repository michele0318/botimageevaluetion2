"""Open the observed external module link and archive its initial instructions."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
import run_task_bot as bot

with sync_playwright() as pw:
    browser=pw.chromium.connect_over_cdp('http://127.0.0.1:9223')
    context=browser.contexts[0]
    with context.expect_page(timeout=30000) as event:
        if not bot.click_named(context,'link','Open External Platform'):
            raise RuntimeError('No visible external-platform link')
    page=event.value
    page.wait_for_load_state('domcontentloaded',timeout=60000)
    page.locator('body').wait_for(timeout=30000)
    page.wait_for_timeout(2000)
    data=page.evaluate('''() => ({text:document.body.innerText,
       buttons:[...document.querySelectorAll('button,a')].filter(e=>e.getClientRects().length)
         .map(e=>({text:e.innerText.trim(),id:e.id})).filter(e=>e.text),
       dialogs:[...document.querySelectorAll('.modal')].map(e=>({id:e.id,text:e.textContent}))})''')
    Path('site_material/extra_platform.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(data,ensure_ascii=True))
