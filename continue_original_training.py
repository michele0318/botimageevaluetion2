"""Continue the ORIGINAL aesthetic training in the existing saved-profile browser."""
import socket
from playwright.sync_api import sync_playwright
import run_task_bot as bot
import training_loop

lock=socket.socket()
lock.bind(('127.0.0.1',47831))
(bot.STATE/'stop.request').unlink(missing_ok=True)
bot.ollama_check(wait=120)
bot.warmup()
with sync_playwright() as pw:
    browser=pw.chromium.connect_over_cdp('http://127.0.0.1:9223')
    context=browser.contexts[0]
    context.set_default_timeout(10000)
    page=context.new_page()
    try:
        training_loop.run(context,page)
    except bot.Stop as error:
        print(str(error),flush=True)
        (bot.ROOT/'original_training_pause.txt').write_text(str(error),encoding='utf-8')
