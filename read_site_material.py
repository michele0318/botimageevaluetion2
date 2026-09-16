"""Collect the site's instructional content without answering any task."""
import json
from pathlib import Path
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
import run_task_bot as bot

destination = bot.ROOT / 'site_material'
destination.mkdir(exist_ok=True)
with sync_playwright() as pw:
    browser = pw.chromium.connect_over_cdp('http://127.0.0.1:9223')
    context = browser.contexts[0]
    frame = bot.task_frame(context)
    if not frame:
        raise RuntimeError('No task frame available')
    material = frame.evaluate('''() => ({
        buttons:[...document.querySelectorAll('button')].filter(b=>['Instructions','FAQ'].includes(b.innerText.trim())).map(b=>b.outerHTML),
        dialogs:[...document.querySelectorAll('.modal,[role=dialog]')].map(d=>({id:d.id,text:d.textContent})),
        prompt:document.querySelector('#prompt-display')?.outerHTML
    })''')
    (destination / 'dialogs.json').write_text(json.dumps(material, ensure_ascii=False, indent=2), encoding='utf-8')
    link = frame.get_by_role('link', name='Image Wiki', exact=True)
    wiki_url = urljoin(frame.url, link.get_attribute('href'))
    wiki = context.new_page()
    wiki.goto(wiki_url, wait_until='domcontentloaded')
    wiki.locator('body').wait_for()
    (destination / 'wiki.txt').write_text(wiki.locator('body').inner_text(), encoding='utf-8')
    links = wiki.locator('a').evaluate_all('(links)=>links.map(a=>({text:a.innerText,href:a.href}))')
    (destination / 'wiki_links.json').write_text(json.dumps(links, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Saved {len(material['dialogs'])} dialogs and {len(links)} wiki links.")
