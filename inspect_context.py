import json
from playwright.sync_api import sync_playwright
import run_task_bot as bot
with sync_playwright() as pw:
    browser = pw.chromium.connect_over_cdp('http://127.0.0.1:9223')
    frame = bot.task_frame(browser.contexts[0])
    value = frame.evaluate('''() => [...document.querySelectorAll('[id*="hint"],[class*="hint"],[id*="context"],[class*="context"]')]
        .map(e=>({tag:e.tagName,id:e.id,cls:e.className,text:e.innerText}))''')
    (bot.ROOT/'site_material/context_inventory.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Saved {len(value)} context elements without image URLs.')
