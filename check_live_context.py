"""Read contextual resources from the current page, without inference or submission."""
from playwright.sync_api import sync_playwright
from dataset_tools import capture
import run_task_bot as bot
with sync_playwright() as pw:
    browser=pw.chromium.connect_over_cdp('http://127.0.0.1:9223')
    frame=bot.task_frame(browser.contexts[0])
    prompt,images,_=bot.snapshot(frame)
    path=capture(prompt,images)
    hints,references=bot.task_resources(frame,path)
    print(f'Read {len(hints)} context characters and {len(references)} reference images. No inference or submission.')
