"""Read-only inspection of project guidance in the saved browser profile."""
import json
import time
import argparse
from playwright.sync_api import sync_playwright, Error
import run_task_bot as bot

parser=argparse.ArgumentParser()
parser.add_argument('--project-only',action='store_true')
args=parser.parse_args()
# An explicit new inspection supersedes an old close request left by a browser
# that was already closed when the request was written.
(bot.ROOT / 'close-guide-browser.request').unlink(missing_ok=True)

with sync_playwright() as pw:
    context = pw.chromium.launch_persistent_context(
        str(bot.STATE / 'browser'), headless=False,
        args=['--remote-debugging-address=127.0.0.1', '--remote-debugging-port=9223'],
        viewport={'width': 1440, 'height': 1000})
    try:
        bot.restore_session(context)
        page = context.pages[0]
        try:
            if args.project_only:
                page.goto(bot.PROJECT,wait_until='domcontentloaded',timeout=60000)
            else:
                bot.open_tasks(context, page)
        except bot.Stop as error:
            print(str(error), flush=True)
        entries = []
        for page in context.pages:
            for frame in page.frames:
                try:
                    entries.append(frame.evaluate('''() => ({text:document.body.innerText,
                        links:[...document.querySelectorAll('a')].map(a=>({text:a.innerText,href:a.getAttribute('href')})),
                        buttons:[...document.querySelectorAll('button')].map(b=>({text:b.innerText,id:b.id}))})'''))
                except Exception:
                    pass
        (bot.ROOT / 'guide_inventory.json').write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf-8')
        print('Inventario guide salvato; browser di lettura disponibile sulla porta locale 9223.', flush=True)
        while context.pages and not (bot.ROOT / 'close-guide-browser.request').exists():
            try:
                context.pages[0].wait_for_timeout(500)
            except Error:
                if not context.pages:
                    break
    finally:
        (bot.ROOT / 'close-guide-browser.request').unlink(missing_ok=True)
        context.close()
