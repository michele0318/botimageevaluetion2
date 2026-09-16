"""Archive every linked Image Wiki article from the authenticated site."""
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
import run_task_bot as bot

root = bot.ROOT / 'site_material'
articles = root / 'articles'
articles.mkdir(exist_ok=True)
links = json.loads((root / 'wiki_links.json').read_text(encoding='utf-8'))
urls = sorted({x['href'].split('#')[0] for x in links if '/wiki/' in x['href'] and urlsplit(x['href']).path.rstrip('/') != '/wiki'})
with sync_playwright() as pw:
    browser = pw.chromium.connect_over_cdp('http://127.0.0.1:9223')
    context = browser.contexts[0]
    page = context.new_page()
    for index, url in enumerate(urls, 1):
        slug = urlsplit(url).path.rstrip('/').rsplit('/', 1)[-1]
        if not re.fullmatch(r'[a-z0-9-]+', slug):
            raise ValueError('Unexpected article path')
        page.goto(url, wait_until='domcontentloaded', timeout=60000)
        data = page.evaluate('''() => {
          const root=document.querySelector('article') || document.querySelector('main') || document.body;
          const copy=root.cloneNode(true);
          copy.querySelectorAll('script,style,nav,header,footer').forEach(e=>e.remove());
          return {title:document.title,text:copy.innerText || copy.textContent,
            headings:[...root.querySelectorAll('h1,h2,h3')].map(e=>e.textContent),
            figures:[...root.querySelectorAll('figure')].map(f=>({caption:f.textContent,images:[...f.querySelectorAll('img')].map(i=>({src:i.src,alt:i.alt}))})),
            images:[...root.querySelectorAll('img')].map(i=>({src:i.src,alt:i.alt})),
            links:[...root.querySelectorAll('a')].map(a=>({text:a.textContent,href:a.href}))};
        }''')
        data.update(url=url)
        (articles / (slug + '.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'{index}/{len(urls)} {slug}', flush=True)
    page.close()
print('Raccolta completa.', flush=True)
